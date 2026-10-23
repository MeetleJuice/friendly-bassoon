"""Application-owned report interpretation and minimal project/run evidence."""

import platform
from uuid import uuid4
from . import __version__
from .store import now
from .verification import check_python

EXECUTION_KEYS = frozenset(
    (
        "requested",
        "succeeded",
        "failed",
        "writes_verified",
        "commands_passed",
        "recovered_edit_errors",
        "python_checks_passed",
        "python_checks_failed",
        "unresolved_tool_errors",
        "python_files_needing_attention",
    )
)


def bounded_counts(value):
    value = value if isinstance(value, dict) else {}
    return {
        key: min(number, 32000)
        for key, number in value.items()
        if key in EXECUTION_KEYS and type(number) is int and number >= 0
    }


def base_report(kind, suite, privacy):
    return {
        "schema_version": 1,
        "suite_version": suite,
        "kind": kind,
        "id": str(uuid4()),
        "created": now(),
        "app_version": __version__,
        "state": "passed",
        "environment": {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
        },
        "checks": [],
        "privacy": privacy,
    }


def python_report(store, workspace, relative):
    result = check_python(workspace, relative)
    report = base_report(
        "python_check",
        "python-static-1",
        "Static check metadata only. No source, file path, credentials or program execution.",
    )
    report["checks"] = [
        {
            "id": "python_static",
            "status": result["status"],
            "code": result["code"],
            "message": "Python compilation and basic literal assignment checks only; program not run.",
            "duration_ms": 0,
            "evidence": {
                "python_check_code": result["code"],
                "python_check_line": result["line"],
                "program_executed": False,
            },
        }
    ]
    report["state"] = "passed" if result["status"] == "passed" else "needs_attention"
    report["summary"] = {
        "passed": int(result["status"] == "passed"),
        "failed": int(result["status"] != "passed"),
        "warning": 0,
        "skipped": 0,
    }
    # Current revision is local-only, useful for identifying what was checked.
    report["local_file"] = relative
    report["local_workspace"] = str(workspace.root)
    report["local_sha256"] = result["sha256"]
    store.save_diagnostic(report)
    return report


def run_report(store, sid):
    session = next((row for row in store.sessions() if row["id"] == sid), None)
    if not session or session["state"] == "running":
        raise ValueError("Select a finished run first")
    events = store.events(sid)
    summary = next((e["data"] for e in reversed(events) if e["kind"] == "run.summary"), {})
    counts = bounded_counts(
        summary.get("tools", {})
        | {
            key: summary[key]
            for key in ("unresolved_tool_errors", "python_files_needing_attention")
            if key in summary
        }
    )
    from .reporting import RECENT_STATES, RECENT_ERROR_CODES
    from .diagnostics import safe_recent_summary

    state = session["state"] if session["state"] in RECENT_STATES else "unknown"
    report = base_report(
        "run_review",
        "run-review-1",
        "Execution counters and check codes only. No task, source, paths, messages or assessment notes.",
    )
    assessment = store.assessment(sid)
    label = assessment.get("label") if assessment else None
    report["state"] = "passed" if state == "completed" and label == "goal_met" else "needs_attention"
    model = next((e["data"].get("model") for e in events if e["kind"] == "model.requested"), None)
    evidence = {
        "runtime_state": state,
        "execution_counts": counts,
        "user_goal_met": label == "goal_met",
        "user_assessment": label if label in ("goal_met", "needs_work") else "not_assessed",
    }
    if model:
        evidence["model"] = model
    codes = {}
    for event in events:
        code = event["data"].get("code")
        if (
            event["kind"] in ("tool.result", "runtime.error", "provider.failed")
            and code in RECENT_ERROR_CODES
        ):
            codes[code] = min(codes.get(code, 0) + 1, 32000)
    evidence["tool_error_codes"] = codes
    from .verification import PYTHON_CHECK_CODES

    check_codes = {}
    for event in events:
        code = event["data"].get("python_check", {}).get("code") if event["kind"] == "tool.result" else None
        if code in PYTHON_CHECK_CODES:
            check_codes[code] = min(check_codes.get(code, 0) + 1, 32000)
    evidence["python_check_codes"] = check_codes
    report["checks"] = [
        {
            "id": "selected_run",
            "status": "passed" if report["state"] == "passed" else "warning",
            "code": "RUN_EVIDENCE",
            "message": "Saved execution evidence; model claims are not test results.",
            "duration_ms": summary.get("duration_ms", 0),
            "evidence": evidence,
        }
    ]
    report["recent_runs"] = safe_recent_summary(store)
    report["summary"] = {
        "passed": int(report["state"] == "passed"),
        "failed": 0,
        "warning": int(report["state"] != "passed"),
        "skipped": 0,
    }
    report["local_session_id"] = sid
    store.save_diagnostic(report)
    return report


def report_guidance(report):
    checks = report.get("checks", [])
    kind = report.get("kind", "health")
    if kind == "api_models":
        return (
            "Model lists checked. This did not test model generation or tool use.\n"
            "Next: choose a saved agent in Test model for one small tool-call probe."
        )
    if kind == "python_check":
        row = checks[0] if checks else {}
        from .verification import describe_python

        return describe_python(
            {"code": row.get("code"), "line": row.get("evidence", {}).get("python_check_line")}
        ) + (
            "\nNext: test dependencies and launch the program yourself, or approve a specific test command."
            if report.get("state") == "passed"
            else "\nNext: ask your agent to read and fix this file, then check it again."
        )
    if kind == "run_review":
        evidence = checks[0].get("evidence", {}) if checks else {}
        counts = evidence.get("execution_counts", {})
        return (
            f"Files saved: {counts.get('writes_verified', 0)}; approved commands passed: {counts.get('commands_passed', 0)}.\n"
            f"Recovered edit errors: {counts.get('recovered_edit_errors', 0)}; unresolved tool errors: "
            f"{counts.get('unresolved_tool_errors', 'unknown')}.\n"
            "Next: verify the actual result and label the run Goal met or Needs work. No program behavior is certified by saving files."
        )
    if kind == "tool_probe":
        passed = sum(row.get("status") == "passed" for row in checks)
        return (
            f"Native tool-call probes passed: {passed}/{len(checks)}. No project tools were executed.\n"
            + (
                "Next: verify actual file creation/read-back with Diagnose using this agent."
                if passed
                else "Next: try one different installed tool-capable model; repeating identical probes adds little evidence."
            )
        )
    local = next((row for row in checks if row.get("id") == "selected_local_model"), None)
    built_in = [row for row in checks if row.get("id") not in ("selected_local_model", "update_connection")]
    passed = sum(row.get("status") == "passed" for row in built_in)
    text = f"Built-in app checks: {passed}/{len(built_in)} passed. These use disposable test files.\n"
    if local and local.get("status") == "failed":
        text += "Selected model workflow: needs attention. The model did not verify the required file task.\n"
        if local.get("evidence", {}).get("runtime_state") == "protocol_error":
            text += "It returned text instead of native tool calls.\n"
        text += "Next: share this report, then test a different saved model once in Test model."
    elif local and local.get("status") == "passed":
        text += "Selected model workflow: file creation and read-back passed.\nNext: try one small task in a disposable project."
    else:
        text += "Real model workflow: not verified by this run.\nNext: select a local agent and enable its real file-create/read-back test."
    if passed != len(built_in):
        text += "\nAn app check also needs attention; review the individual checks below."
    return text
