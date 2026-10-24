"""Versioned, isolated live-model exercises; no user projects or host commands."""

from contextlib import closing
from pathlib import Path
import tempfile
import time
from .diagnostics import DiagnosticRunner, model_evidence
from .evidence import base_report
from .runtime import Runtime
from .store import Store
from .harness import exercise_tools, suite_budget
from .task_checks import TaskChecks
from .tools import Workspace
from .tools import VALIDATION_ISSUE_CODES


def local_profile(store, agent):
    from urllib.parse import urlsplit
    import ipaddress

    profile = next((p for p in store.profiles() if p.id == agent.primary.profile_id), None)
    host = urlsplit(profile.base_url).hostname if profile else None
    try:
        local = host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = False
    if not profile or profile.kind != "ollama" or not local:
        raise ValueError("Select a local Ollama agent. Automatic suites never invoke cloud models.")
    return profile


CASES = (
    ("discover", "List the files in this project using list_files.", "list_files"),
    ("read", "Read input.txt using read_file and report its contents.", "read_file"),
    ("search", "Use search to find the word lighthouse in this project.", "search"),
    ("map", "Use project_map to inspect this project.", "project_map"),
    ("retrieve", "Use retrieve_context to find lighthouse in this project.", "retrieve_context"),
    (
        "create",
        "Create output.txt containing exactly lighthouse followed by a newline. Then read it back. Use tools.",
        "write_file",
    ),
    (
        "edit",
        "Read output.txt, then replace its contents with exactly lighthouse followed by a newline. Then read it back. Use tools.",
        "write_file",
    ),
    (
        "python",
        "Create output.py containing exactly value = 7 followed by a real newline. Then read it back. Use tools. Do not run commands.",
        "write_file",
    ),
    ("readonly", "This is a read-only test. Read input.txt using tools. Do not modify files.", "read_file"),
    (
        "denial",
        "Try to create output.txt containing lighthouse using write_file. If approval is denied, stop and report the denial. Do not try another path.",
        "write_file",
    ),
    (
        "empty",
        "Empty-file exercise: create empty.txt with exactly zero bytes, then read it back using read_file. Use native tools.",
        "write_file",
    ),
    (
        "unicode",
        "Unicode exercise: create unicode.txt with exactly café 🌊 followed by a real newline. Then read it back using tools.",
        "write_file",
    ),
    (
        "multiline",
        "Multiline Python exercise: create square.py containing exactly two lines: def square(number): followed by a newline, then four spaces followed by return number * number and a final newline. Read it back. Do not run commands.",
        "write_file",
    ),
    (
        "nested",
        "Nested-path exercise: create src/report.txt containing exactly harbor followed by a newline, then read it back using tools.",
        "write_file",
    ),
    (
        "multi_file",
        "Two-file exercise: create first.txt containing exactly alpha followed by a newline and second.txt containing exactly beta followed by a newline. Read both newly written files back using native tools.",
        "write_file",
    ),
    (
        "transform",
        "Two-input exercise: read input.txt and second_input.txt using native read_file, then create combined.txt with their exact contents concatenated in that order. Read combined.txt back. Do not use commands.",
        "write_file",
    ),
    (
        "noop",
        "No-op exercise: read output.txt, then propose write_file with exactly the same contents using expected_sha256='last_read'. Read it again. This tests that an unchanged file is not rewritten; do not change any content.",
        "write_file",
    ),
    (
        "stale",
        "Stale-revision exercise in disposable files: read output.txt. Deliberately attempt to write exactly lighthouse followed by a newline using expected_sha256='0000000000000000000000000000000000000000000000000000000000000000'. This one attempt must be rejected as stale. Then read output.txt again, retry the intended write using expected_sha256='last_read', and read the saved result back. Stop after recovery; no commands.",
        "write_file",
    ),
)

# Explicit fixtures and byte contracts, not prose-based goal grading. Fresh inputs per case.
CASE_OUTPUTS = {
    "create": {"output.txt": b"lighthouse\n"},
    "edit": {"output.txt": b"lighthouse\n"},
    "python": {"output.py": b"value = 7\n"},
    "empty": {"empty.txt": b""},
    "unicode": {"unicode.txt": "café 🌊\n".encode("utf-8")},
    "multiline": {"square.py": b"def square(number):\n    return number * number\n"},
    "nested": {"src/report.txt": b"harbor\n"},
    "multi_file": {"first.txt": b"alpha\n", "second.txt": b"beta\n"},
    "transform": {"combined.txt": b"lighthouse\nharbor\n"},
    "noop": {"output.txt": b"lighthouse\n"},
    "stale": {"output.txt": b"lighthouse\n"},
}
CASE_TITLES = (
    "Discover project files",
    "Read exact input",
    "Search project text",
    "Map the project",
    "Retrieve relevant context",
    "Create exact output",
    "Edit safely and read back",
    "Write valid Python",
    "Respect read-only mode",
    "Respect denied approval",
    "Create an empty file",
    "Preserve Unicode text",
    "Write real multiline Python",
    "Create a nested path",
    "Create and verify two files",
    "Transform two inputs",
    "Skip unchanged writes",
    "Recover a deliberately stale revision",
)
COMPLEX_CASES = frozenset(("multiline", "multi_file", "transform", "stale"))

# Fixed vocabulary: safe for public reports, never interpolated from model arguments.
REQUIREMENT_LABELS = {
    "EXACT_OUTPUT": "Output bytes match the requested result",
    "INPUTS_UNCHANGED": "Original inputs and unrelated files are unchanged",
    "NATIVE_OPERATION": "The required native operation succeeded on the intended target",
    "TASK_CHECKS": "All configured runtime task checks passed",
    "VERIFIED_WRITE": "Every requested output has a verified write",
    "POST_WRITE_READBACK": "Every requested output was read after its current write",
    "EDIT_ORDER": "Read the original file, save the edit, then read the saved revision",
    "NOOP_ORDER": "Read the original file, propose unchanged contents, then read again",
    "NOOP_NO_WRITE": "The unchanged proposal caused no physical write or approval",
    "STALE_REJECTED_ONCE": "Exactly one deliberately stale revision was rejected",
    "STALE_RECOVERED": "The stale edit was recovered without hiding the original error",
    "STALE_ORDER": "Read, stale rejection, reread, successful save, final read occurred in order",
    "TRANSFORM_INPUT_ORDER": "Both inputs were read before the transformed output was saved",
    "DENIAL_RESPECTED": "The intended write was denied once and left no file changes",
    "RUNTIME_FINISHED": "The run finished in its expected state",
}


def requirement_failures(checks):
    """Only application-owned boolean requirements; unknown/private fields never escape."""
    return [key for key in REQUIREMENT_LABELS if checks.get(key) is False]


def bounded_tool_timeline(results):
    """Local bounded action sequence, without arguments, source, paths or raw errors."""
    from .registry import TOOLS

    errors = {
        "ValidationError",
        "ValueError",
        "FileNotFoundError",
        "PermissionError",
        "StaleFileError",
        "WriteTargetError",
        "OSError",
        "UnicodeDecodeError",
    }
    timeline = []
    for result in results[:32]:
        tool, status = result.get("tool"), result.get("status")
        if tool not in TOOLS or status not in ("succeeded", "failed"):
            continue
        row = {"tool": tool, "status": status}
        duration = result.get("duration_ms")
        if type(duration) is int and duration >= 0:
            row["duration_ms"] = min(duration, 300000)
        for key in ("verified", "unchanged"):
            if type(result.get(key)) is bool:
                row[key] = result[key]
        if result.get("error_type") in errors:
            row["error_type"] = result["error_type"]
        timeline.append(row)
    return timeline


def matching_results(events, observed, trial, name, predicate, status="succeeded"):
    """Correlate known arguments to actual result events without keeping raw arguments."""
    hashes = {trial.fingerprint(c.arguments) for c in observed if c.name == name and predicate(c.arguments)}
    executions = {
        e["data"]["execution_id"]
        for e in events
        if e["kind"] == "tool.requested"
        and e["data"].get("tool") == name
        and e["data"].get("arguments_sha256") in hashes
    }
    return [
        (i, e["data"])
        for i, e in enumerate(events)
        if e["kind"] == "tool.result"
        and e["data"].get("execution_id") in executions
        and e["data"].get("status") == status
    ]


def ordered_results(*groups):
    """An ordered acceptance chain; greedy selection is bounded by total event count."""
    previous = -1
    for group in groups:
        following = next((index for index, _ in group if index > previous), None)
        if following is None:
            return False
        previous = following
    return True


def succeeded_call(events, observed, trial, name, predicate):
    return bool(matching_results(events, observed, trial, name, predicate))


def run_suite(
    store,
    credentials,
    agent,
    cancel,
    emit,
    provider_factory=None,
    budget_mode="balanced",
    case_ids=None,
    *,
    persist=True,
):
    from .providers import Provider

    profile = local_profile(store, agent)
    cases = CASES
    if case_ids is not None:
        selected = tuple(case_ids)
        known = {case[0] for case in CASES}
        if not selected or len(selected) != len(set(selected)) or any(key not in known for key in selected):
            raise ValueError("Choose unique known suite case IDs")
        by_id = {case[0]: case for case in CASES}
        cases = tuple(by_id[key] for key in selected)

    suite_budget("edit", budget_mode, agent.max_seconds, profile.timeout_seconds)
    observed = []

    class BoundedProvider:
        def __init__(self, *args):
            self.inner = (provider_factory or Provider)(*args)

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def chat(self, model, messages, tools):
            if provider_factory is None:
                reply = self.inner.chat(model, messages, tools, max_output_tokens=budget["max_output_tokens"])
            else:
                reply = self.inner.chat(model, messages, tools)
            observed.extend(reply.calls)
            return reply

    report = base_report(
        "agent_suite",
        "agent-suite-5",
        "Synthetic acceptance counters only; no source, paths, prompts or credentials.",
    )
    report["local_scope"] = store.fingerprint(
        {"agent": agent.model_dump(), "profile": profile.model_dump(), "budget_mode": budget_mode}
    )
    report["planned_cases"] = len(cases)
    report["case_ids"] = [case[0] for case in cases]
    report["state"] = "running"
    if persist:
        store.save_diagnostic(report)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="aigentics-suite-") as folder:
        scratch = Path(folder)
        with closing(Store(scratch / "suite.sqlite3", credentials)) as trial:
            for index, (identity, prompt, required) in enumerate(cases):
                if cancel.is_set():
                    break
                budget = suite_budget(
                    "edit" if identity in COMPLEX_CASES else identity,
                    budget_mode,
                    agent.max_seconds,
                    profile.timeout_seconds,
                )
                trial.save_profile(
                    profile.model_copy(update={"timeout_seconds": budget["request_timeout_seconds"]})
                )
                observed.clear()
                before = time.monotonic()
                emit({"kind": "suite.started", "data": {"id": identity, "index": index + 1}})
                root = scratch / str(index)
                root.mkdir()
                (root / "input.txt").write_bytes(b"lighthouse\n")
                if identity in ("edit", "stale"):
                    (root / "output.txt").write_bytes(b"old\n")
                if identity == "noop":
                    (root / "output.txt").write_bytes(b"lighthouse\n")
                if identity == "transform":
                    (root / "second_input.txt").write_bytes(b"harbor\n")
                outputs = CASE_OUTPUTS.get(identity, {})
                targets = list(outputs) if identity != "noop" else []
                allowed_targets = set(outputs) if outputs else {"output.txt"}
                workspace = Workspace(root)

                def same_target(path, expected):
                    if not isinstance(path, str):
                        return False
                    try:
                        return workspace.path(path) == workspace.path(expected)
                    except (ValueError, PermissionError, OSError):
                        return False

                writing = bool(outputs) or identity == "denial"
                status, code, evidence = "skipped", "TOOL_DISABLED", {}
                if (
                    required in agent.tools
                    and (not writing or agent.allow_writes)
                    and (not writing or identity == "denial" or "read_file" in agent.tools)
                ):
                    bounded = agent.model_copy(
                        update={
                            "tools": exercise_tools(agent.tools, required, writing),
                            "allow_commands": False,
                            "fallbacks": [],
                            "allow_writes": agent.allow_writes and writing,
                            "max_steps": min(agent.max_steps, 8 if identity in COMPLEX_CASES else 5),
                            "max_seconds": budget["session_budget_seconds"],
                            "context_chars": min(agent.context_chars, 16000),
                        }
                    )
                    decisions = []

                    def approve(kind, details):
                        allowed = (
                            identity != "denial"
                            and kind == "write_file"
                            and any(same_target(details.get("path"), name) for name in allowed_targets)
                        )
                        target = next(
                            (name for name in allowed_targets if same_target(details.get("path"), name)),
                            details.get("path"),
                        )
                        decisions.append((kind, target, allowed))
                        return allowed

                    try:
                        sid, state = Runtime(trial, credentials, BoundedProvider).run(
                            bounded,
                            root,
                            prompt,
                            approve,
                            cancel,
                            capture=False,
                            task_checks=TaskChecks(
                                write_targets=targets if identity != "denial" else ["output.txt"],
                                require_readback=writing and identity not in ("denial", "noop"),
                                required_tools=["read_file", "write_file"] if identity == "noop" else [],
                            ),
                        )
                        events = trial.events(sid)
                        results = [e["data"] for e in events if e["kind"] == "tool.result"]
                        used = any(
                            r.get("tool") == required and r.get("status") == "succeeded" for r in results
                        )
                        if not writing:

                            def correct(call):
                                if call.name != required:
                                    return False
                                if required == "read_file":
                                    return same_target(call.arguments.get("path"), "input.txt")
                                if required in ("search", "retrieve_context"):
                                    return call.arguments.get("query") == "lighthouse"
                                if required == "list_files":
                                    return same_target(call.arguments.get("path", "."), ".")
                                return True

                            hashes = {trial.fingerprint(c.arguments) for c in observed if correct(c)}
                            successful = {
                                r["execution_id"]
                                for r in results
                                if r.get("tool") == required and r.get("status") == "succeeded"
                            }
                            used = used and any(
                                e["kind"] == "tool.requested"
                                and e["data"].get("execution_id") in successful
                                and e["data"].get("arguments_sha256") in hashes
                                for e in events
                            )
                        summary = next(
                            (e["data"] for e in reversed(events) if e["kind"] == "run.summary"), {}
                        )
                        requirements = {"NATIVE_OPERATION": bool(used)}
                        matched = True
                        inputs_unchanged = (root / "input.txt").read_bytes() == b"lighthouse\n"
                        if outputs:
                            matched = all(
                                (root / name).is_file() and (root / name).read_bytes() == data
                                for name, data in outputs.items()
                            )
                            requirements["EXACT_OUTPUT"] = bool(matched)
                            matched = matched and inputs_unchanged
                            checks = summary.get("task_checks", {})
                            requirements["TASK_CHECKS"] = checks.get("status") == "passed"
                            if targets:
                                requirements["VERIFIED_WRITE"] = checks.get("written_files") == len(targets)
                                requirements["POST_WRITE_READBACK"] = checks.get("readback_files") == len(
                                    targets
                                )
                            used = used and requirements["TASK_CHECKS"]
                        if identity == "edit":
                            reads = matching_results(
                                events,
                                observed,
                                trial,
                                "read_file",
                                lambda args: same_target(args.get("path"), "output.txt"),
                            )
                            saved = [
                                (i, row)
                                for i, row in matching_results(
                                    events,
                                    observed,
                                    trial,
                                    "write_file",
                                    lambda args: same_target(args.get("path"), "output.txt"),
                                )
                                if row.get("verified") is True and not row.get("unchanged")
                            ]
                            requirements["EDIT_ORDER"] = ordered_results(reads, saved, reads)
                            used = used and requirements["EDIT_ORDER"]
                        if identity == "noop":
                            reads = matching_results(
                                events,
                                observed,
                                trial,
                                "read_file",
                                lambda args: same_target(args.get("path"), "output.txt"),
                            )
                            writes = [
                                (i, row)
                                for i, row in matching_results(
                                    events,
                                    observed,
                                    trial,
                                    "write_file",
                                    lambda args: same_target(args.get("path"), "output.txt"),
                                )
                                if row.get("unchanged") is True
                            ]
                            requirements["NOOP_ORDER"] = ordered_results(reads, writes, reads)
                            requirements["NOOP_NO_WRITE"] = (
                                summary.get("tools", {}).get("unchanged_writes", 0) == 1
                                and summary.get("tools", {}).get("writes_verified", 0) == 0
                                and not decisions
                            )
                            used = used and requirements["NOOP_ORDER"] and requirements["NOOP_NO_WRITE"]
                        if identity == "stale":
                            reads = matching_results(
                                events,
                                observed,
                                trial,
                                "read_file",
                                lambda args: same_target(args.get("path"), "output.txt"),
                            )
                            rejected = [
                                (i, row)
                                for i, row in matching_results(
                                    events,
                                    observed,
                                    trial,
                                    "write_file",
                                    lambda args: same_target(args.get("path"), "output.txt")
                                    and args.get("expected_sha256") == "0" * 64,
                                    "failed",
                                )
                                if row.get("error_type") == "StaleFileError"
                            ]
                            saved = [
                                (i, row)
                                for i, row in matching_results(
                                    events,
                                    observed,
                                    trial,
                                    "write_file",
                                    lambda args: same_target(args.get("path"), "output.txt"),
                                )
                                if row.get("verified") is True and not row.get("unchanged")
                            ]
                            requirements["STALE_REJECTED_ONCE"] = len(rejected) == 1
                            requirements["STALE_RECOVERED"] = (
                                summary.get("tools", {}).get("recovered_edit_errors", 0) == 1
                            )
                            requirements["STALE_ORDER"] = ordered_results(
                                reads, rejected, reads, saved, reads
                            )
                            used = used and all(
                                requirements[key]
                                for key in ("STALE_REJECTED_ONCE", "STALE_RECOVERED", "STALE_ORDER")
                            )
                        if identity == "transform":
                            reads = [
                                matching_results(
                                    events,
                                    observed,
                                    trial,
                                    "read_file",
                                    lambda args, name=name: same_target(args.get("path"), name),
                                )
                                for name in ("input.txt", "second_input.txt")
                            ]
                            saved = [
                                (i, row)
                                for i, row in matching_results(
                                    events,
                                    observed,
                                    trial,
                                    "write_file",
                                    lambda args: same_target(args.get("path"), "combined.txt"),
                                )
                                if row.get("verified") is True and not row.get("unchanged")
                            ]
                            requirements["TRANSFORM_INPUT_ORDER"] = any(
                                all(any(r < w for r, _ in group) for group in reads) for w, _ in saved
                            )
                            used = used and requirements["TRANSFORM_INPUT_ORDER"]
                            inputs_unchanged = (
                                inputs_unchanged and (root / "second_input.txt").read_bytes() == b"harbor\n"
                            )
                            matched = matched and inputs_unchanged
                        if identity == "denial":
                            used = ("write_file", "output.txt", False) in decisions
                            matched = (
                                sorted(p.name for p in root.iterdir()) == ["input.txt"]
                                and (root / "input.txt").read_bytes() == b"lighthouse\n"
                            )
                            requirements["DENIAL_RESPECTED"] = used and matched and len(decisions) == 1
                            # A denied write is the expected operation; success is not required.
                            requirements["NATIVE_OPERATION"] = used
                        if not writing:
                            matched = (
                                sorted(p.name for p in root.iterdir()) == ["input.txt"]
                                and (root / "input.txt").read_bytes() == b"lighthouse\n"
                            )
                            inputs_unchanged = matched
                        requirements["INPUTS_UNCHANGED"] = inputs_unchanged
                        requirements["RUNTIME_FINISHED"] = state == "completed" or (
                            identity == "denial" and state == "needs_review" and len(decisions) == 1
                        )
                        passed = (
                            used
                            and matched
                            and (
                                state == "completed"
                                or (identity == "denial" and state == "needs_review" and len(decisions) == 1)
                            )
                        )
                        status = "passed" if passed else "failed"
                        code = (
                            "OK"
                            if passed
                            else "MODEL_OR_RUNTIME_FAILED"
                            if state == "failed"
                            else "SESSION_BUDGET_EXHAUSTED"
                            if state == "timed_out"
                            else "NATIVE_PROTOCOL_FAILED"
                            if state == "protocol_error"
                            else "OUTPUT_BYTES_MISMATCH"
                            if not matched
                            else "REQUIRED_OPERATIONS_NOT_VERIFIED"
                            if not used
                            else "RUN_NOT_COMPLETED"
                        )
                        evidence = {
                            **model_evidence(events),
                            "model": agent.primary.model,
                            "validation_issue_counts": {
                                code: sum(
                                    issue.get("code") == code
                                    for row in results
                                    for issue in row.get("validation_issues", [])
                                )
                                for code in VALIDATION_ISSUE_CODES
                                if any(
                                    issue.get("code") == code
                                    for row in results
                                    for issue in row.get("validation_issues", [])
                                )
                            },
                            "tool_timeline": bounded_tool_timeline(results),
                            "requirement_checks": requirements,
                            "unmet_requirements": requirement_failures(requirements),
                            "execution_counts": summary.get("tools", {}),
                            "tool_error_types": {
                                key: sum(
                                    e["kind"] == "tool.result" and e["data"].get("error_type") == key
                                    for e in events
                                )
                                for key in (
                                    "ValidationError",
                                    "ValueError",
                                    "FileNotFoundError",
                                    "PermissionError",
                                    "StaleFileError",
                                    "WriteTargetError",
                                )
                                if any(
                                    e["kind"] == "tool.result" and e["data"].get("error_type") == key
                                    for e in events
                                )
                            },
                            **budget,
                            "failure_stage": "none"
                            if passed
                            else "provider"
                            if state == "failed"
                            else "session_budget"
                            if state == "timed_out"
                            else "acceptance",
                            "task_checks": summary.get("task_checks", {}),
                            "final_response_status": summary.get("final_response_status", "not_reached"),
                            "native_calls_total": sum(
                                e["data"].get("tool_calls", 0)
                                for e in events
                                if e["kind"] == "model.responded"
                            ),
                            "file_matches": matched,
                            "runtime_state": state,
                        }
                    except Exception as exc:
                        status, code = "failed", "SUITE_CASE_FAILED"
                        evidence = {"local_error_type": type(exc).__name__}
                row = {
                    "id": identity,
                    "status": status,
                    "code": code,
                    "message": "Application-owned synthetic acceptance criteria.",
                    "duration_ms": round((time.monotonic() - before) * 1000),
                    "evidence": evidence,
                }
                report["checks"].append(row)
                if persist:
                    store.save_diagnostic(report)
                emit({"kind": "suite.result", "data": row})
    report["summary"] = {
        k: sum(r["status"] == k for r in report["checks"]) for k in ("passed", "failed", "warning", "skipped")
    }
    report["state"] = (
        "cancelled"
        if cancel.is_set()
        else "passed"
        if report["summary"]["passed"] == len(cases)
        else "needs_attention"
    )
    report["duration_ms"] = round((time.monotonic() - started) * 1000)
    if persist:
        store.save_diagnostic(report)
        store.prune()
    return report


def run_bundle(store, credentials, agent, cancel, emit, budget_mode="balanced"):
    """Automatic agent acceptance never checks API catalogs or refreshes keys."""
    local_profile(store, agent)
    health = DiagnosticRunner(store, credentials).run(cancel, emit, include_network=False)
    # Automatic acceptance reports describe this run, not an unchanged legacy-history sample.
    # Manual Diagnose and History remain available for broader troubleshooting.
    health.pop("recent_runs", None)
    store.save_diagnostic(health)
    if cancel.is_set():
        return [health]
    return [health, run_suite(store, credentials, agent, cancel, emit, budget_mode=budget_mode)]
