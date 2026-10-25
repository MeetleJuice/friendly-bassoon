"""Explicitly approved GitHub issue reports; never commit user diagnostics to source history."""

import copy
import json
import re
from urllib.parse import urlencode, urlsplit
import httpx
from .updates import REPOSITORY
from .ollama_settings import OLLAMA_USAGE_FIELDS, public_thinking, public_observation, THINKING_MODES

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
        "NoProgressError",
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
        "JsonProposalError",
        "WriteTargetError",
        "EmptyFinalResponse",
    )
)
RECENT_ERROR_CODES = frozenset(
    (
        "NO_PROGRESS",
        "TOOL_ARGUMENT_VALIDATION",
        "JSON_PROPOSAL",
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
        "THINKING_CONTROL_UNAVAILABLE",
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


def public_shape(value):
    value = value if isinstance(value, dict) else {}
    safe = {
        k: min(v, 2_000_000)
        for k, v in value.items()
        if k in ("thinking_chars", "content_chars", "native_call_count") and type(v) is int and v >= 0
    }
    safe.update(
        {
            k: v
            for k, v in value.items()
            if k in ("stream", "tool_calls_field_present", "content_field_present") and type(v) is bool
        }
    )
    if value.get("finish_reason") in (
        "stop",
        "length",
        "tool_calls",
        "load",
        "unload",
        "content_filter",
        "other",
    ):
        safe["finish_reason"] = value["finish_reason"]
    return safe


def public_acceptance(value):
    allowed = {
        "EXACT_OUTPUT",
        "OUTPUT_CONTENT",
        "FINAL_ANSWER",
        "INPUTS_UNCHANGED",
        "NO_UNEXPECTED_FILES",
        "CHECKER_ERROR",
    }
    return (
        {k: v for k, v in value.items() if k in allowed and type(v) is bool}
        if isinstance(value, dict)
        else {}
    )


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
    planned = report.get("planned_cases")
    if type(planned) is int and (0 if report.get("kind") == "crew_campaign" else 1) <= planned <= (
        66 if report.get("kind") == "crew_campaign" else 32
    ):
        result["planned_cases"] = planned
    result["environment"] = {
        key: report.get("environment", {}).get(key) for key in ("os", "os_release", "architecture", "python")
    }
    campaign = report.get("kind") == "crew_campaign"
    if campaign:
        from .campaign import ALL_CASE_IDS as PLAN_IDS
        from .crew import CREW_VERSION

        if report.get("mode") in ("quick", "standard", "deep", "measurement", "focused"):
            result["mode"] = report["mode"]
        if report.get("crew_version") in ("midnight-crew-1", "midnight-crew-2", CREW_VERSION):
            result["crew_version"] = report["crew_version"]
        if report.get("stop_reason") in ("cancelled", "campaign_budget", "finished", "benchmark_changed"):
            result["stop_reason"] = report["stop_reason"]
        value = report.get("budget_used_ms")
        if type(value) is int and value >= 0:
            result["budget_used_ms"] = min(value, 7_380_000)

    if campaign:
        if isinstance(report.get("ollama_observation"), dict):
            result["ollama_observation"] = public_observation(report["ollama_observation"])
        comparison = report.get("thinking_comparison")
        if isinstance(comparison, dict):
            result["thinking_comparison"] = public_thinking(comparison)
            if type(comparison.get("eligible")) is bool:
                result["thinking_comparison"]["eligible"] = comparison["eligible"]
            if comparison.get("skip_code") in (
                "THINKING_CONTROL_UNAVAILABLE",
                "THINKING_NOT_APPLICABLE",
                "THINKING_ROUTE_UNSUPPORTED",
            ):
                result["thinking_comparison"]["skip_code"] = comparison["skip_code"]
    if campaign:
        digest = report.get("manifest_id")
        if isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest):
            result["manifest_id"] = digest
        if type(report.get("manifest_verified")) is bool:
            result["manifest_verified"] = report["manifest_verified"]
        if report.get("track") in ("measurement", "discovery"):
            result["track"] = report["track"]
    safe_checks = []
    allowed = {
        "request_timeout_seconds",
        "session_budget_seconds",
        "validation_recovery_verified",
        "checkpoint_recovery_verified",
        "crew_fixture_verified",
        "correctness_fixture_verified",
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
        "team_pilot_fixture_verified",
        "json_proposal_fixture_verified",
    }
    if include_model:
        allowed.add("model")
    for row in report.get("checks", []):
        if campaign and row.get("id") not in PLAN_IDS:
            continue
        check = {key: row[key] for key in ("id", "status", "code", "message", "duration_ms")}
        check["evidence"] = {key: value for key, value in row.get("evidence", {}).items() if key in allowed}
        evidence = row.get("evidence", {})
        if (
            "crew_fixture_verified" in check["evidence"]
            and type(check["evidence"]["crew_fixture_verified"]) is not bool
        ):
            del check["evidence"]["crew_fixture_verified"]
        if "requirement_checks" in evidence:
            from .test_suite import REQUIREMENT_LABELS

            labels = REQUIREMENT_LABELS
            if campaign:
                from .campaign import REQUIREMENT_LABELS as campaign_labels

                labels = {**labels, **campaign_labels}
            values = evidence["requirement_checks"]
            check["evidence"]["requirement_checks"] = (
                {key: value for key, value in values.items() if key in labels and type(value) is bool}
                if isinstance(values, dict)
                else {}
            )
        if "final_response_status" in evidence:
            check["evidence"]["final_response_status"] = (
                evidence["final_response_status"]
                if evidence["final_response_status"] in ("present", "missing", "not_reached", "not_recorded")
                else "not_recorded"
            )
        if type(evidence.get("completion_feedback_count")) is int:
            check["evidence"]["completion_feedback_count"] = min(
                1, max(0, evidence["completion_feedback_count"])
            )
        if "initial_task_checks" in evidence:
            from .task_checks import public_task_checks

            check["evidence"]["initial_task_checks"] = public_task_checks(evidence["initial_task_checks"])
        for key in ("initial_acceptance_checks", "acceptance_checks"):
            if key in evidence:
                check["evidence"][key] = public_acceptance(evidence[key])
        if "failure_shape" in evidence:
            check["evidence"]["failure_shape"] = public_shape(evidence["failure_shape"])
        if evidence.get("group") in ("comparison", "variation", "experiment", "measurement"):
            check["evidence"]["group"] = evidence["group"]
        from .contracts import public_mismatches
        from .tool_diagnostics import public_tool_diagnostics

        for key in ("mismatches", "initial_mismatches"):
            if key in evidence:
                check["evidence"][key] = public_mismatches(evidence[key])
        if "tool_diagnostics" in evidence:
            check["evidence"]["tool_diagnostics"] = public_tool_diagnostics(evidence["tool_diagnostics"])
        if "task_checks" in evidence:
            from .task_checks import public_task_checks

            check["evidence"]["task_checks"] = public_task_checks(evidence["task_checks"])
        if "tool_error_types" in evidence:
            check["evidence"]["tool_error_types"] = recent_run_counts(
                {"tool_error_types": evidence["tool_error_types"]}
            )["tool_error_types"]
        if "failure_usage" in evidence:
            values = evidence["failure_usage"]
            check["evidence"]["failure_usage"] = (
                {
                    k: min(v, 10**15)
                    for k, v in values.items()
                    if k in OLLAMA_USAGE_FIELDS and type(v) is int and v >= 0
                }
                if isinstance(values, dict)
                else {}
            )
        if "validation_issue_counts" in evidence:
            from .tools import VALIDATION_ISSUE_CODES

            counts = evidence["validation_issue_counts"]
            check["evidence"]["validation_issue_counts"] = (
                {
                    k: min(v, 32000)
                    for k, v in counts.items()
                    if k in VALIDATION_ISSUE_CODES and type(v) is int and 0 <= v
                }
                if isinstance(counts, dict)
                else {}
            )
        if "execution_counts" in evidence:
            from .evidence import bounded_counts

            check["evidence"]["execution_counts"] = bounded_counts(evidence["execution_counts"])
        from .inference import public_run_details, public_model_details

        check["evidence"].update(public_run_details(evidence))
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
        if isinstance(evidence.get("thinking_mode"), str) and evidence.get("thinking_mode") in THINKING_MODES:
            check["evidence"]["thinking_mode"] = evidence["thinking_mode"]
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
            check["evidence"]["model_metadata"].update(public_thinking(evidence["model_metadata"]))
            check["evidence"]["model_metadata"].update(public_model_details(evidence["model_metadata"]))
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
                        "request_chars",
                        "tool_schema_chars",
                    )
                    if key in trace
                }
                if (
                    isinstance(trace.get("thinking_mode"), str)
                    and trace.get("thinking_mode") in THINKING_MODES
                ):
                    safe["thinking_mode"] = trace["thinking_mode"]
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
                    key: value for key, value in trace.get("usage", {}).items() if key in OLLAMA_USAGE_FIELDS
                }
                traces.append(safe)
            check["evidence"]["request_traces"] = traces
        if campaign:
            check = safe_campaign_row(check, evidence)
        safe_checks.append(check)
    result["checks"] = safe_checks
    # Only bounded aggregate counters are shared; no session IDs, hashes or original messages.
    if "recent_runs" in report:
        result["recent_runs"] = recent_run_counts(report.get("recent_runs", {}))
    return result


def issue_body(report, credentials, include_model=False):
    public = public_report(report, include_model)
    label = {
        "agent_suite": "agent suite",
        "crew_campaign": "crew evaluation",
        "api_models": "API checks",
        "tool_probe": "tool-call probe",
        "run_review": "run review",
        "python_check": "Python check",
    }.get(report.get("kind"), "diagnostics")
    title = f"Aigentics {label} {report['app_version']}: {report['state']}"
    if report.get("kind") == "crew_campaign":
        return title, compact_campaign_body(credentials.scrub(public))
    body = (
        f"<!-- aigentics-report:{report['id']} -->\n"
        "Diagnostic report shared with the user's approval. Allowlisted diagnostic and execution metadata only.\n\n"
        "```json\n" + credentials.json(public, indent=2, ensure_ascii=False) + "\n```\n"
    )
    if len(body.encode("utf-8")) > MAX_BODY and report.get("kind") == "agent_suite":
        body = compact_suite_body(public)
    if len(body.encode("utf-8")) > MAX_BODY:
        raise ReportingError("Report is too large to submit. Save it locally instead.")
    return title, body


def compact_suite_body(payload):
    """Complete bounded per-case evidence, without repeated schemas/traces in URLs."""
    rows = payload.get("checks", [])
    if len(rows) > 32:
        raise ReportingError("Too many suite cases for browser sharing")

    def number(value, limit=10**15):
        return str(min(value, limit)) if type(value) is int and value >= 0 else "?"

    def usage(traces, key):
        values = [t.get("usage", {}).get(key) for t in traces]
        known = [v for v in values if type(v) is int and v >= 0]
        return number(sum(known)) if known else "?"

    budgets, errors, issues, codes, requirements = {}, {}, {}, {}, {}
    lines = []

    def alias(mapping, value, prefix):
        if value not in mapping:
            mapping[value] = prefix + str(len(mapping) + 1)
        return mapping[value]

    for row in rows:
        e = row.get("evidence", {})
        budget = "/".join(
            number(e.get(k))
            for k in ("max_output_tokens", "request_timeout_seconds", "session_budget_seconds")
        )
        bid = alias(budgets, budget, "B")
        err = (
            ",".join(
                alias(errors, k, "E") + ":" + number(v)
                for k, v in sorted(e.get("tool_error_types", {}).items())
            )
            or "-"
        )
        validation = (
            ",".join(
                alias(issues, k, "V") + ":" + number(v)
                for k, v in sorted(e.get("validation_issue_counts", {}).items())
            )
            or "-"
        )
        code = row.get("code", "UNKNOWN")
        code = code if isinstance(code, str) and re.fullmatch(r"[A-Z_]{1,60}", code) else "UNKNOWN"
        cid = "OK" if code == "OK" else alias(codes, code, "C")
        counts = e.get("execution_counts", {})
        traces = e.get("request_traces", [])
        rejected = e.get("failure_usage", {})
        reject = "/".join(number(rejected.get(k)) for k in OLLAMA_USAGE_FIELDS) if rejected else "-"
        task = e.get("task_checks", {})
        missing = (
            "/".join(
                number(task.get(key))
                for key in ("missing_writes", "missing_readbacks", "missing_tools", "revision_mismatches")
            )
            if any(
                key in task
                for key in ("missing_writes", "missing_readbacks", "missing_tools", "revision_mismatches")
            )
            else "-"
        )
        unmet = (
            ",".join(
                alias(requirements, key, "R")
                for key, value in sorted(e.get("requirement_checks", {}).items())
                if value is False
            )
            or "-"
        )
        fields = [
            row["id"],
            {"passed": "P", "failed": "F", "skipped": "S", "warning": "W"}.get(row["status"], "?"),
            cid,
            number(row.get("duration_ms")),
            number(e.get("native_calls_total")),
            e.get("runtime_state", "?"),
            str(int(e["file_matches"])) if type(e.get("file_matches")) is bool else "?",
            number(counts.get("writes_verified")) + "/" + number(counts.get("failed")),
            e.get("task_checks", {}).get("status", "not_recorded")
            + "/"
            + e.get("final_response_status", "not_recorded"),
            usage(traces, "prompt_eval_count") + "/" + usage(traces, "eval_count"),
            reject,
            bid,
            e.get("provider_error_code", "NONE"),
            err,
            validation,
            number(counts.get("recovered_validation_errors")),
            number(counts.get("unchanged_writes")) + "/" + number(counts.get("recovered_edit_errors")),
            missing,
            unmet,
        ]
        lines.append("|".join(fields))

    def legend(mapping):
        return "; ".join(f"{v}={k}" for k, v in mapping.items()) or "none"

    env = payload.get("environment", {})
    first = next((r.get("evidence", {}) for r in rows if r.get("evidence", {}).get("model_metadata")), {})
    metadata = {k: first[k] for k in ("model_metadata", "model") if k in first}
    return (
        "Reviewed agent-suite summary. Detailed bounded evidence retained locally.\n"
        + "Report ID: "
        + str(payload.get("id"))
        + "\nApp/suite/result: "
        + str(payload.get("app_version"))
        + "/"
        + str(payload.get("suite_version"))
        + "/"
        + str(payload.get("state"))
        + "\nEnvironment: "
        + ", ".join(str(env.get(k, "?")) for k in ("os", "os_release", "architecture", "python"))
        + "\nP=passed; F=failed; S=skipped; W=warning; ?=unavailable. Usage is known-only, not a complete billing total.\n"
        + "case|result|code|ms|native|runtime|matched|writes/errors=|checks/final|tokens in/out=|rejected_usage(in/out/raw-duration)|budget|provider|errors|validation|recovered-validation|noop/stale-recovered|missing-write/read/tool/revision|unmet\n"
        + "\n".join(lines)
        + "\nBudgets(output/request-s/session-s): "
        + legend(budgets)
        + "\nError types: "
        + legend(errors)
        + "\nValidation: "
        + legend(issues)
        + "\nCodes: "
        + legend(codes)
        + ("\nUnmet requirements: " + legend(requirements) if requirements else "")
        + ("\nModel evidence: " + json.dumps(metadata, separators=(",", ":")) if metadata else "")
    )


def prepare_browser_draft(title, body):
    """Pure local URL preparation; callers preview its exact body before opening a browser."""
    # Browser URLs have practical limits. Keep complete check statuses/codes and a stable report ID;
    # larger details stay local. Direct API sharing can include the whole preview.
    url = ISSUES_URL + "/new?" + urlencode({"title": title, "body": body})
    if len(url) > 7500:
        match = re.search(r"<!-- aigentics-report:([^>]+) -->", body)
        try:
            payload = json.loads(body.split("```json\n", 1)[1].split("\n```", 1)[0])
            if payload.get("kind") == "agent_suite":
                compact = compact_suite_body(payload)
                url = ISSUES_URL + "/new?" + urlencode({"title": title, "body": compact})
                if len(url) > 7500:
                    raise ReportingError("Browser suite summary exceeds its limit; full report remains local")
                return url
            rows = [
                f"- {r['id']}"
                + (" [" + r["evidence"]["provider"] + "]" if r.get("evidence", {}).get("provider") else "")
                + f": {r['status']} ({r['code']})"
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
            "crew_fixture_verified",
            "correctness_fixture_verified",
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
            + (
                "\nRecent run counts: "
                + json.dumps(recent_run_counts(payload["recent_runs"]), separators=(",", ":"))
                if "recent_runs" in payload
                else ""
            )
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


CAMPAIGN_CODES = frozenset(
    (
        "OK",
        "MODEL_OR_RUNTIME_FAILED",
        "SESSION_BUDGET_EXHAUSTED",
        "NATIVE_PROTOCOL_FAILED",
        "OUTPUT_BYTES_MISMATCH",
        "REQUIRED_OPERATIONS_NOT_VERIFIED",
        "RUN_NOT_COMPLETED",
        "SUITE_CASE_FAILED",
        "TOOL_DISABLED",
        "INTERRUPTED_CASE_NOT_REPLAYED",
        "CAMPAIGN_BUDGET_EXHAUSTED",
        "THINKING_CONTROL_UNAVAILABLE",
        "THINKING_NOT_APPLICABLE",
        "THINKING_ROUTE_UNSUPPORTED",
        "ROLE_REQUIREMENTS_NOT_MET",
        "CANCELLED",
        "UNKNOWN",
    )
)
CAMPAIGN_ROLES = ("george", "orion", "scout", "ada", "vera", "sentinel", "atlas")


def safe_campaign_row(check, original):
    """Campaign records share fixed identifiers and typed measurements, never generated text."""
    evidence = check.get("evidence", {})
    from .inference import public_run_details, public_model_details

    safe = public_run_details(evidence)
    for key in (
        "duration_ms",
        "native_calls_total",
        "max_output_tokens",
        "request_timeout_seconds",
        "session_budget_seconds",
        "http_status",
    ):
        value = evidence.get(key)
        if type(value) is int and 0 <= value:
            safe[key] = min(value, 10**15)
    for key in ("file_matches", "readback_recorded", "timing_unknown"):
        if type(evidence.get(key)) is bool:
            safe[key] = evidence[key]
    state = evidence.get("runtime_state")
    if isinstance(state, str) and state in RECENT_STATES:
        safe["runtime_state"] = state
    provider = evidence.get("provider_error_code")
    if isinstance(provider, str) and provider in RECENT_ERROR_CODES | {"NONE", "OUTPUT_LIMIT"}:
        safe["provider_error_code"] = provider
    for key in (
        "requirement_checks",
        "completion_feedback_count",
        "initial_task_checks",
        "mismatches",
        "initial_mismatches",
        "tool_diagnostics",
        "initial_acceptance_checks",
        "acceptance_checks",
        "failure_shape",
        "group",
        "task_checks",
        "execution_counts",
        "failure_usage",
        "validation_issue_counts",
        "tool_error_types",
        "tool_error_codes",
    ):
        if key in evidence:
            safe[key] = evidence[key]
    from .campaign import MEASUREMENT_TRIALS

    trial = MEASUREMENT_TRIALS.get(check["id"])
    if trial:
        safe.update(case_id=trial.case_id, arm=trial.arm, repeat=trial.repeat, track="measurement")
    if isinstance(original.get("thinking_mode"), str) and original.get("thinking_mode") in THINKING_MODES:
        safe["thinking_mode"] = original["thinking_mode"]
    final = evidence.get("final_response_status")
    if final in ("present", "missing", "not_reached", "not_recorded"):
        safe["final_response_status"] = final
    metadata = evidence.get("model_metadata", {})
    digest = metadata.get("template_sha256")
    if isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest):
        safe["model_metadata"] = {"template_sha256": digest}
    if public_thinking(metadata):
        safe.setdefault("model_metadata", {}).update(public_thinking(metadata))
    if public_model_details(metadata):
        safe.setdefault("model_metadata", {}).update(public_model_details(metadata))
    if isinstance(evidence.get("model"), str) and len(evidence["model"]) <= 200:
        safe["model"] = evidence["model"]
    if type(original.get("timing_unknown")) is bool:
        safe["timing_unknown"] = original["timing_unknown"]
    role = original.get("role")
    if role in CAMPAIGN_ROLES:
        safe["role"] = role
    attempt = original.get("attempt")
    if type(attempt) is int and 1 <= attempt <= 3:
        safe["attempt"] = attempt
    safe["request_traces"] = [
        {
            "usage": {
                key: min(value, 10**15)
                for key, value in trace.get("usage", {}).items()
                if key in OLLAMA_USAGE_FIELDS and type(value) is int and value >= 0
            }
        }
        for trace in evidence.get("request_traces", [])[:8]
    ]
    return {
        "id": check["id"],
        "status": check["status"]
        if check["status"] in ("passed", "failed", "skipped", "warning")
        else "failed",
        "code": check["code"]
        if isinstance(check["code"], str) and check["code"] in CAMPAIGN_CODES
        else "UNKNOWN",
        "message": "Application-owned synthetic campaign criteria.",
        "duration_ms": min(check["duration_ms"], 10**15)
        if type(check.get("duration_ms")) is int and check["duration_ms"] >= 0
        else 0,
        "evidence": safe,
    }


def compact_campaign_body(payload):
    """Keep every case and failed requirement in one practical, reviewable browser draft."""
    rows = payload.get("checks", [])
    if len(rows) > 96:
        raise ReportingError("Too many campaign cases for browser sharing")

    def number(value):
        return str(min(value, 10**15)) if type(value) is int and value >= 0 else "?"

    def usage(evidence, key):
        values = [trace.get("usage", {}).get(key) for trace in evidence.get("request_traces", [])]
        known = [value for value in values if type(value) is int and value >= 0]
        rejected = evidence.get("failure_usage", {}).get(key)
        if type(rejected) is int and rejected >= 0:
            known.append(rejected)
        return number(sum(known)) if known else "?"

    modern = payload.get("suite_version") in ("crew-campaign-3", "crew-campaign-4", "crew-campaign-5")

    def case_name(identity):
        if not modern:
            return identity
        prefixes = {
            "baseline": "b",
            "repeat": "r",
            "george": "g",
            "scout": "s",
            "ada": "a",
            "vera": "v",
            "sentinel": "t",
            "atlas": "x",
            "experiment": "e",
        }
        first, _, rest = identity.partition("-")
        return prefixes.get(first, first) + "." + rest.removeprefix(first + "_")

    codes, requirements, budgets, providers = {}, {}, {}, {}

    def alias(mapping, value, prefix):
        if value not in mapping:
            mapping[value] = prefix + str(len(mapping) + 1)
        return mapping[value]

    # A bitset preserves all failed requirements without repeating long lists per row.
    failed_keys = sorted(
        {
            key
            for row in rows
            for key, value in row.get("evidence", {}).get("requirement_checks", {}).items()
            if value is False
        }
    )
    requirements = {key: index for index, key in enumerate(failed_keys)}
    lines = []
    for row in rows:
        e = row.get("evidence", {})
        code = row.get("code", "UNKNOWN")
        cid = "OK" if code == "OK" else alias(codes, code, "C")
        mask = sum(
            1 << requirements[key] for key, value in e.get("requirement_checks", {}).items() if value is False
        )
        unmet = format(mask, "x") if mask else "0"
        budget = "/".join(
            number(e.get(key))
            for key in ("max_output_tokens", "request_timeout_seconds", "session_budget_seconds")
        )
        bid = alias(budgets, budget, "B")
        provider = e.get("provider_error_code", "NONE")
        pid = "-" if provider == "NONE" else alias(providers, provider, "E")
        counts = e.get("execution_counts", {})
        task = e.get("task_checks", {})
        fields = [
            case_name(row["id"]),
            {"passed": "P", "failed": "F", "skipped": "S", "warning": "W"}.get(row["status"], "?"),
            cid,
            "?" if e.get("timing_unknown") is True else number(row.get("duration_ms")),
            number(e.get("native_calls_total")),
            number(counts.get("writes_verified")) + "/" + number(counts.get("failed")),
            number(task.get("missing_readbacks")),
            number(e.get("completion_feedback_count", 0)),
            "/".join(
                number(e.get("initial_task_checks", {}).get(key))
                for key in ("missing_writes", "missing_readbacks", "missing_sources")
            )
            if e.get("completion_feedback_count")
            else "-",
            usage(e, "prompt_eval_count") + "/" + usage(e, "eval_count"),
            bid,
            pid,
            unmet,
        ]
        if modern:
            initial = e.get("initial_task_checks", {})
            fields[8] += (
                "/" + number(initial.get("content_failures")) if e.get("completion_feedback_count") else ""
            )
            shape = e.get("failure_shape", {})
            fields.append(
                "/".join(
                    number(shape.get(k)) for k in ("thinking_chars", "content_chars", "native_call_count")
                )
                if shape
                else "-"
            )
            lines.append(" ".join(f.replace("/", ".") for f in fields))
        else:
            lines.append("|".join(fields))

    def legend(mapping):
        return "; ".join(f"{value}={key}" for key, value in mapping.items()) or "none"

    groups = []
    for group in ("comparison", "variation", "experiment", "measurement"):
        selected = [r for r in rows if r.get("evidence", {}).get("group") == group]
        if selected:
            groups.append(f"{group}:{sum(r['status'] == 'passed' for r in selected)}/{len(selected)}")
    shapes = []
    for r in rows:
        shape = r.get("evidence", {}).get("failure_shape", {})
        if shape and not modern:
            shapes.append(
                r["id"]
                + ":"
                + "/".join(
                    number(shape.get(k)) for k in ("thinking_chars", "content_chars", "native_call_count")
                )
            )
    role_scores = []
    for role in CAMPAIGN_ROLES:
        selected = [row for row in rows if row.get("evidence", {}).get("role") == role]
        role_scores.append(f"{role}:{sum(row['status'] == 'passed' for row in selected)}/{len(selected)}")
    first_model = next(
        (
            row.get("evidence", {})
            for row in rows
            if row.get("evidence", {}).get("model_metadata") or row.get("evidence", {}).get("model")
        ),
        {},
    )
    model_details = {key: first_model[key] for key in ("model_metadata", "model") if key in first_model}
    return (
        "Reviewed Midnight Crew campaign. Full bounded evidence retained locally.\n"
        + f"Report ID: {payload.get('id')}\n"
        + f"App/suite/result: {payload.get('app_version')}/{payload.get('suite_version')}/{payload.get('state')}\n"
        + ("Manifest: " + payload["manifest_id"] + "\n" if "manifest_id" in payload else "")
        + f"Crew/mode: {payload.get('crew_version', '?')}/{payload.get('mode', '?')}\n"
        + f"Recorded/planned: {len(rows)}/{payload.get('planned_cases', '?')}\n"
        + f"Stop: {payload.get('stop_reason', 'unknown')}; budget charged ms: {number(payload.get('budget_used_ms'))} (includes reserved interrupted-case allowance).\n"
        + ("Groups: " + ", ".join(groups) + "\n" if groups else "")
        + (
            "Rejected shapes(thinking-chars/content-chars/native-fields): " + ";".join(shapes) + "\n"
            if shapes
            else ""
        )
        + "Role scores(recorded only): "
        + ", ".join(role_scores)
        + "\n"
        + "P=passed F=failed S=skipped W=warning ?=unknown. Tokens include known rejected-response usage; not billing totals.\n"
        + (
            "IDs: b=baseline r=repeat g=george s=scout a=ada v=vera t=sentinel x=atlas e=experiment; role prefixes omitted from scenario names.\n"
            "Space columns; dots separate numeric groups.\n"
            "case result code ms native writes.errors missing-readbacks feedback initial-missing-write.read.source.content tokens-in.out budget provider unmet rejected-thinking.content.native\n"
            if modern
            else "case|result|code|ms|native|writes/errors|missing-readbacks|feedback-turns|initial-missing-write/read/source|tokens-in/out|budget|provider|unmet\n"
        )
        + "\n".join(lines)
        + "\nBudgets(output/request-s/session-s): "
        + legend(budgets)
        + "\nCodes: "
        + legend(codes)
        + "\nProvider: "
        + legend(providers)
        + "\nUnmet(hex bitmask; bit=required check): "
        + legend(requirements)
        + ("\nModel evidence: " + json.dumps(model_details, separators=(",", ":")) if model_details else "")
    )
