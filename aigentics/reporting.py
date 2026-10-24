"""Explicitly approved GitHub issue reports; never commit user diagnostics to source history."""

import copy
import json
import re
from urllib.parse import urlencode, urlsplit
import httpx
from .updates import REPOSITORY

ISSUES_URL = f"https://github.com/{REPOSITORY}/issues"
MAX_BODY = 45000

# Counter keys come only from application-owned classifications. A valid-looking identifier
# can still be a secret, so arbitrary exception names/codes are never shared as keys.
RECENT_STATES = frozenset(
    (
        "running",
        "interrupted",
        "failed",
        "completed",
        "response_only",
        "needs_review",
        "protocol_error",
        "timed_out",
        "cancelled",
        "limit_reached",
        "unknown",
        "incomplete_response",
    )
)
RECENT_ERROR_TYPES = frozenset(
    (
        "ProviderError",
        "NativeToolProtocolError",
        "RunTimeout",
        "TimeoutError",
        "InterruptedError",
        "PermissionError",
        "ValueError",
        "ValidationError",
        "FileNotFoundError",
        "IsADirectoryError",
        "NotADirectoryError",
        "UnicodeDecodeError",
        "OSError",
        "RuntimeError",
        "KeyError",
        "TypeError",
        "CommandFailure",
        "ToolFailure",
        "OtherError",
        "StaleFileError",
        "WriteTargetError",
        "EmptyFinalResponse",
    )
)
RECENT_ERROR_CODES = frozenset(
    (
        "PROVIDER_ERROR",
        "HTTP_ERROR",
        "TIMEOUT",
        "CONNECTION_ERROR",
        "MALFORMED_JSON",
        "INVALID_MODEL_LIST",
        "INVALID_MODEL_INFO",
        "INVALID_CHAT_RESPONSE",
        "MALFORMED_NATIVE_CALL",
        "STREAM_PROTOCOL_ERROR",
        "TOOLS_UNSUPPORTED",
        "NATIVE_TOOL_PROTOCOL",
        "UNKNOWN_ERROR",
        "STALE_FILE",
        "WRITE_TARGET_MISMATCH",
        "EMPTY_FINAL_RESPONSE",
    )
)
RECENT_FAILURE_STAGES = frozenset(("provider", "runtime", "native_protocol", "final_response"))


def recent_run_counts(recent):
    """Validate old/malformed records too; only bounded typed aggregates leave the app."""
    recent = recent if isinstance(recent, dict) else {}
    result = {}
    for key, allowed in (
        ("states", RECENT_STATES),
        ("tool_error_types", RECENT_ERROR_TYPES),
        ("runtime_error_codes", RECENT_ERROR_CODES),
        ("runtime_error_types", RECENT_ERROR_TYPES),
        ("failure_stages", RECENT_FAILURE_STAGES),
    ):
        counts = recent.get(key, {})
        result[key] = (
            {
                name: min(count, 20 if key != "tool_error_types" else 32000)
                for name, count in counts.items()
                if name in allowed and type(count) is int and count >= 0
            }
            if isinstance(counts, dict)
            else {}
        )
    for key in ("protocol_failures", "legacy_text_tool_responses"):
        count = recent.get(key, 0)
        result[key] = min(count, 32000) if type(count) is int and count >= 0 else 0
    from .evidence import bounded_counts

    result["execution_counts"] = bounded_counts(recent.get("execution_counts"))
    coverage = recent.get("coverage", {})
    result["coverage"] = (
        {
            key: min(value, 20)
            for key, value in coverage.items()
            if key
            in ("sessions", "task_checks_recorded", "final_status_recorded", "current_version_sessions")
            and type(value) is int
            and value >= 0
        }
        if isinstance(coverage, dict)
        else {}
    )
    for key, allowed in (
        ("tool_error_codes", RECENT_ERROR_CODES),
        ("user_assessments", ("goal_met", "needs_work", "not_assessed")),
    ):
        value = recent.get(key, {})
        result[key] = (
            {
                name: min(count, 32000)
                for name, count in value.items()
                if name in allowed and type(count) is int and count >= 0
            }
            if isinstance(value, dict)
            else {}
        )
    return result


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
            "kind",
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
        "native_calls_total",
        "provider_error_code",
        "http_status",
        "failure_stage",
        "model_count",
        "request_count",
        "generation_requests",
        "partial_catalog",
        "provider",
        "catalog_fixture_verified",
        "retention_fixture_verified",
        "active_report_protected",
        "route",
        "stream",
        "challenge_verified",
        "max_output_tokens",
        "finish_reason",
        "tool_calls_field_present",
        "text_tool_response",
        "probe_fixture_verified",
        "project_retrieval_fixture_verified",
        "registry_fixture_verified",
        "python_check_code",
        "python_check_line",
        "program_executed",
        "python_check_fixture_verified",
        "revision_fixture_verified",
        "user_goal_met",
        "user_assessment",
        "final_response_status",
        "task_checks_fixture_verified",
        "empty_final_fixture_verified",
    }
    if include_model:
        allowed.add("model")
    for row in report.get("checks", []):
        check = {key: row[key] for key in ("id", "status", "code", "message", "duration_ms")}
        check["evidence"] = {key: value for key, value in row.get("evidence", {}).items() if key in allowed}
        evidence = row.get("evidence", {})
        if "final_response_status" in evidence:
            check["evidence"]["final_response_status"] = (
                evidence["final_response_status"]
                if evidence["final_response_status"] in ("present", "missing", "not_reached", "not_recorded")
                else "not_recorded"
            )
        if "task_checks" in evidence:
            from .task_checks import public_task_checks

            check["evidence"]["task_checks"] = public_task_checks(evidence["task_checks"])
        if "execution_counts" in evidence:
            from .evidence import bounded_counts

            check["evidence"]["execution_counts"] = bounded_counts(evidence["execution_counts"])
        if "tool_error_codes" in evidence:
            check["evidence"]["tool_error_codes"] = recent_run_counts(
                {"tool_error_codes": evidence["tool_error_codes"]}
            )["tool_error_codes"]
        if "python_check_codes" in evidence:
            from .verification import PYTHON_CHECK_CODES

            values = evidence["python_check_codes"]
            check["evidence"]["python_check_codes"] = (
                {
                    key: min(value, 32000)
                    for key, value in values.items()
                    if key in PYTHON_CHECK_CODES and type(value) is int and value >= 0
                }
                if isinstance(values, dict)
                else {}
            )
        if "model_metadata" in evidence:
            check["evidence"]["model_metadata"] = {
                key: value
                for key, value in evidence["model_metadata"].items()
                if key
                in (
                    "tools",
                    "source",
                    "template_sha256",
                    "template_chars",
                    "template_mentions_tools",
                    "parser",
                    "renderer",
                    "template_source",
                )
            }
        if "request_traces" in evidence:
            traces = []
            for trace in evidence["request_traces"][:8]:
                safe = {
                    key: trace[key]
                    for key in (
                        "step",
                        "duration_ms",
                        "native_call_count",
                        "content_chars",
                        "text_tool_response",
                        "tool_schema_sha256",
                        "advertised_tool_count",
                    )
                    if key in trace
                }
                safe["response_shape"] = {
                    key: value
                    for key, value in trace.get("response_shape", {}).items()
                    if key
                    in (
                        "tool_calls_field_present",
                        "content_field_present",
                        "thinking_chars",
                        "finish_reason",
                        "stream",
                    )
                }
                safe["usage"] = {
                    key: value
                    for key, value in trace.get("usage", {}).items()
                    if key in ("prompt_eval_count", "eval_count", "total_duration")
                }
                traces.append(safe)
            check["evidence"]["request_traces"] = traces
        safe_checks.append(check)
    result["checks"] = safe_checks
    # Only bounded aggregate counters are shared; no session IDs, hashes or original messages.
    result["recent_runs"] = recent_run_counts(report.get("recent_runs", {}))
    return result


def issue_body(report, credentials, include_model=False):
    public = public_report(report, include_model)
    label = {
        "agent_suite": "agent suite",
        "api_models": "API checks",
        "tool_probe": "tool-call probe",
        "run_review": "run review",
        "python_check": "Python check",
    }.get(report.get("kind"), "diagnostics")
    title = f"Aigentics {label} {report['app_version']}: {report['state']}"
    body = (
        f"<!-- aigentics-report:{report['id']} -->\n"
        "Diagnostic report shared with the user's approval. Allowlisted diagnostic and execution metadata only.\n\n"
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
            rows = [
                f"- {r['id']}"
                + (" [" + r["evidence"]["provider"] + "]" if r.get("evidence", {}).get("provider") else "")
                + f": {r['status']} ({r['code']})"
                + (
                    "; native="
                    + str(r.get("evidence", {}).get("native_calls_total", 0))
                    + "; state="
                    + str(r.get("evidence", {}).get("runtime_state", "unknown"))
                    + "; matched="
                    + str(r.get("evidence", {}).get("file_matches", False))
                    if payload.get("kind") == "agent_suite"
                    else ""
                )
                for r in payload.get("checks", [])
            ]
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
        model = next(
            (r.get("evidence", {}) for r in payload.get("checks", []) if r["id"] == "selected_local_model"),
            {},
        )
        model_details = {key: value for key, value in model.items() if key != "request_traces"}
        traces = [
            {
                "step": t.get("step"),
                "native": t.get("native_call_count"),
                "text_tool": t.get("text_tool_response"),
                "tool_field": t.get("response_shape", {}).get("tool_calls_field_present"),
                "finish": t.get("response_shape", {}).get("finish_reason"),
                "stream": t.get("response_shape", {}).get("stream"),
                "input_tokens": t.get("usage", {}).get("prompt_eval_count"),
                "output_tokens": t.get("usage", {}).get("eval_count"),
            }
            for t in model.get("request_traces", [])[-3:]
        ]
        if traces:
            model_details["last_three_requests"] = traces
        compact_keys = (
            "provider",
            "model",
            "route",
            "stream",
            "http_status",
            "native_calls_total",
            "challenge_verified",
            "generation_requests",
            "max_output_tokens",
            "finish_reason",
            "tool_calls_field_present",
            "text_tool_response",
            "provider_error_code",
            "model_count",
            "request_count",
            "partial_catalog",
            "probe_fixture_verified",
            "project_retrieval_fixture_verified",
            "registry_fixture_verified",
            "python_check_fixture_verified",
            "revision_fixture_verified",
            "python_check_code",
            "python_check_line",
            "program_executed",
            "runtime_state",
            "execution_counts",
            "tool_error_codes",
            "user_goal_met",
            "python_check_codes",
            "task_checks",
            "final_response_status",
            "task_checks_fixture_verified",
            "empty_final_fixture_verified",
            "user_assessment",
        )
        compact_checks = {
            row["id"]: {key: row["evidence"][key] for key in compact_keys if key in row.get("evidence", {})}
            for row in payload.get("checks", [])
            if row["id"] != "selected_local_model"
            and any(key in row.get("evidence", {}) for key in compact_keys)
        }
        body = (
            "Diagnostic summary shared with user approval. Full report retained locally.\n"
            + (f"Report ID: {match[1]}\n" if match else "")
            + metadata
            + "\n"
            + summary
            + "\nRecent run counts: "
            + json.dumps(recent_run_counts(payload.get("recent_runs", {})), separators=(",", ":"))
            + (
                "\nCheck evidence: " + json.dumps(compact_checks, separators=(",", ":"))
                if compact_checks
                else ""
            )
            + (
                "\nLocal model result: " + json.dumps(model_details, separators=(",", ":"))
                if model_details
                else ""
            )
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
