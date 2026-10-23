"""Explicitly approved GitHub issue reports; never commit user diagnostics to source history."""

import copy
import json
import re
from urllib.parse import urlencode, urlsplit
import httpx
from .updates import REPOSITORY

ISSUES_URL = f"https://github.com/{REPOSITORY}/issues"
MAX_BODY = 45000


class ReportingError(RuntimeError):
    pass


class SubmissionUnknown(ReportingError):
    """The server may have created an issue. Never retry a POST automatically."""


def public_report(report, include_model=False):
    """Rebuild a strictly allowlisted payload, never a whole session/database export."""
    result = {
        key: copy.deepcopy(report[key])
        for key in (
            "schema_version",
            "suite_version",
            "id",
            "created",
            "app_version",
            "state",
            "environment",
            "summary",
            "duration_ms",
            "privacy",
        )
        if key in report
    }
    result["environment"] = {
        key: report.get("environment", {}).get(key) for key in ("os", "os_release", "architecture", "python")
    }
    safe_checks = []
    allowed = {
        "blocked_paths",
        "denied_writes",
        "denied_commands",
        "writes_verified",
        "reads_verified",
        "stale_edits_blocked",
        "cancelled_write_blocked",
        "exit_code",
        "fixed_command",
        "timeout_enforced",
        "schema_version",
        "integrity",
        "agents_validated",
        "profiles_validated",
        "nested_json_valid",
        "credential_redaction",
        "protocol_fixtures_passed",
        "external_requests",
        "text_never_executed",
        "bounded_recovery",
        "fixture_goal_verified",
        "native_recovery_verified",
        "cloud_requests",
        "newer_release_available",
        "ollama_version",
        "runtime_state",
        "file_matches",
        "readback_recorded",
        "protocol_retries",
        "error_type",
    }
    if include_model:
        allowed.add("model")
    for row in report.get("checks", []):
        check = {key: row[key] for key in ("id", "status", "code", "message", "duration_ms")}
        check["evidence"] = {key: value for key, value in row.get("evidence", {}).items() if key in allowed}
        safe_checks.append(check)
    result["checks"] = safe_checks
    # Only bounded aggregate counters are shared; no session IDs, hashes or original messages.
    recent = report.get("recent_runs", {})
    result["recent_runs"] = {
        key: copy.deepcopy(recent.get(key, {}))
        for key in ("states", "tool_error_types", "protocol_failures", "legacy_text_tool_responses")
    }
    return result


def issue_body(report, credentials, include_model=False):
    public = public_report(report, include_model)
    title = f"Aigentics diagnostics {report['app_version']}: {report['state']}"
    body = (
        f"<!-- aigentics-report:{report['id']} -->\n"
        "Diagnostic report shared with the user's approval. Synthetic test results and metadata only.\n\n"
        "```json\n" + credentials.json(public, indent=2, ensure_ascii=False) + "\n```\n"
    )
    if len(body.encode("utf-8")) > MAX_BODY:
        raise ReportingError("Report is too large to submit. Save it locally instead.")
    return title, body


def prepare_browser_draft(title, body):
    """Pure local URL preparation; callers preview its exact body before opening a browser."""
    # Browser URLs have practical limits. Keep complete check statuses/codes and a stable report ID;
    # larger details stay local. Direct API sharing can include the whole preview.
    url = ISSUES_URL + "/new?" + urlencode({"title": title, "body": body})
    if len(url) > 7500:
        match = re.search(r"<!-- aigentics-report:([^>]+) -->", body)
        try:
            payload = json.loads(body.split("```json\n", 1)[1].split("\n```", 1)[0])
            rows = [f"- {r['id']}: {r['status']} ({r['code']})" for r in payload.get("checks", [])]
            summary = "\n".join(rows)
        except (ValueError, KeyError, IndexError):
            raise ReportingError("Use the generated report format for browser sharing")
        env = payload.get("environment", {})
        metadata = (
            "App: "
            + str(payload.get("app_version"))
            + "; suite: "
            + str(payload.get("suite_version"))
            + "; result: "
            + str(payload.get("state"))
            + "\nEnvironment: "
            + ", ".join(
                str(env.get(key, "unknown")) for key in ("os", "os_release", "architecture", "python")
            )
        )
        model_details = [
            str(r.get("evidence", {})) for r in payload.get("checks", []) if r["id"] == "selected_local_model"
        ]
        body = (
            "Diagnostic summary shared with user approval. Full report retained locally.\n"
            + (f"Report ID: {match[1]}\n" if match else "")
            + metadata
            + "\n"
            + summary
            + "\nRecent run counts: "
            + str(payload.get("recent_runs", {}))
            + ("\nLocal model result: " + "; ".join(model_details) if model_details else "")
        )
        url = ISSUES_URL + "/new?" + urlencode({"title": title, "body": body})
    if len(url) > 7500:
        raise ReportingError("Browser report is too long; use direct sharing or local export")
    return url


def browser_draft(title, body, approved=False):
    if not approved:
        raise ReportingError("Review and approve the report before opening a GitHub draft")
    return prepare_browser_draft(title, body)


class GitHubReporter:
    def __init__(self, credentials, transport=None):
        self.credentials, self.transport = credentials, transport

    def submit(self, title, body, token_ref="GITHUB_TOKEN", approved=False):
        if not approved:
            raise ReportingError("Explicit approval of this report is required")
        if len(body.encode("utf-8")) > MAX_BODY or len(title) > 200:
            raise ReportingError("Report is too large")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", token_ref):
            raise ReportingError("Use a variable name such as GITHUB_TOKEN, not the token value")
        token = self.credentials.get(token_ref)
        if not token:
            raise ReportingError("A GitHub token is required for direct submission")
        if self.credentials.redact(body) != body or self.credentials.redact(title) != title:
            raise ReportingError("A credential was detected. Review a redacted report before submitting.")
        try:
            with httpx.Client(timeout=20, follow_redirects=False, transport=self.transport) as client:
                response = client.post(
                    f"https://api.github.com/repos/{REPOSITORY}/issues",
                    headers={
                        "Authorization": "Bearer " + token,
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json={"title": title, "body": body},
                )
            if response.status_code >= 500:
                raise SubmissionUnknown(
                    "GitHub did not confirm submission. Search Issues for the report ID before trying again."
                )
            if response.status_code != 201:
                raise ReportingError(
                    f"GitHub returned HTTP {response.status_code}. Check repository access and Issues write permission."
                )
            data = response.json()
            url = data.get("html_url", "")
            if not re.fullmatch(re.escape(ISSUES_URL) + r"/[0-9]+", url):
                raise SubmissionUnknown(
                    "GitHub response could not be verified. Search Issues for the report ID."
                )
            parsed = urlsplit(url)
            if parsed.scheme != "https" or parsed.hostname != "github.com":
                raise SubmissionUnknown("Unexpected issue response")
            return url
        except (httpx.HTTPError, ValueError) as exc:
            raise SubmissionUnknown(
                "Submission outcome is unknown. Do not retry automatically; search GitHub Issues for the report ID."
            ) from exc
