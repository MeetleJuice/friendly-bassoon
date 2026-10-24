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
)


def run_suite(store, credentials, agent, cancel, emit, provider_factory=None, budget_mode="balanced"):
    from .providers import Provider

    profile = local_profile(store, agent)

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
        "agent-suite-3",
        "Synthetic acceptance counters only; no source, paths, prompts or credentials.",
    )
    report["local_scope"] = store.fingerprint(
        {"agent": agent.model_dump(), "profile": profile.model_dump(), "budget_mode": budget_mode}
    )
    report["state"] = "running"
    store.save_diagnostic(report)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="aigentics-suite-") as folder:
        scratch = Path(folder)
        with closing(Store(scratch / "suite.sqlite3", credentials)) as trial:
            for index, (identity, prompt, required) in enumerate(CASES):
                if cancel.is_set():
                    break
                budget = suite_budget(identity, budget_mode, agent.max_seconds, profile.timeout_seconds)
                trial.save_profile(
                    profile.model_copy(update={"timeout_seconds": budget["request_timeout_seconds"]})
                )
                observed.clear()
                before = time.monotonic()
                emit({"kind": "suite.started", "data": {"id": identity, "index": index + 1}})
                root = scratch / str(index)
                root.mkdir()
                (root / "input.txt").write_bytes(b"lighthouse\n")
                if identity == "edit":
                    (root / "output.txt").write_bytes(b"old\n")
                target = "output.py" if identity == "python" else "output.txt"
                writing = identity in ("create", "edit", "python", "denial")
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
                            "max_steps": min(agent.max_steps, 5),
                            "max_seconds": budget["session_budget_seconds"],
                            "context_chars": min(agent.context_chars, 16000),
                        }
                    )
                    decisions = []

                    def approve(kind, details):
                        allowed = (
                            identity != "denial" and kind == "write_file" and details.get("path") == target
                        )
                        decisions.append((kind, details.get("path"), allowed))
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
                                write_targets=[target] if writing else [],
                                require_readback=writing and identity != "denial",
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
                                    return call.arguments.get("path") == "input.txt"
                                if required in ("search", "retrieve_context"):
                                    return call.arguments.get("query") == "lighthouse"
                                if required == "list_files":
                                    return call.arguments.get("path", ".") in (".", "")
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
                        matched = True
                        if identity in ("create", "edit", "python"):
                            expected = b"value = 7\n" if identity == "python" else b"lighthouse\n"
                            matched = (root / target).is_file() and (root / target).read_bytes() == expected
                            used = used and summary.get("task_checks", {}).get("status") == "passed"
                        if identity == "denial":
                            used = ("write_file", target, False) in decisions
                            matched = (
                                sorted(p.name for p in root.iterdir()) == ["input.txt"]
                                and (root / "input.txt").read_bytes() == b"lighthouse\n"
                            )
                        if not writing:
                            matched = (
                                sorted(p.name for p in root.iterdir()) == ["input.txt"]
                                and (root / "input.txt").read_bytes() == b"lighthouse\n"
                            )
                        passed = (
                            used
                            and matched
                            and (
                                state == "completed"
                                or (identity == "denial" and state == "needs_review" and len(decisions) == 1)
                            )
                        )
                        status, code = ("passed", "OK") if passed else ("failed", "ACCEPTANCE_NOT_MET")
                        evidence = {
                            **model_evidence(events),
                            "model": agent.primary.model,
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
                store.save_diagnostic(report)
                emit({"kind": "suite.result", "data": row})
    report["summary"] = {
        k: sum(r["status"] == k for r in report["checks"]) for k in ("passed", "failed", "warning", "skipped")
    }
    report["state"] = (
        "cancelled"
        if cancel.is_set()
        else "passed"
        if report["summary"]["passed"] == 10
        else "needs_attention"
    )
    report["duration_ms"] = round((time.monotonic() - started) * 1000)
    store.save_diagnostic(report)
    store.prune()
    return report


def run_bundle(store, credentials, agent, cancel, emit, include_catalog=True, budget_mode="balanced"):
    local_profile(store, agent)
    health = DiagnosticRunner(store, credentials).run(cancel, emit, include_network=False)
    if not cancel.is_set() and include_catalog:
        from .catalog import CatalogRunner

        try:
            catalogs = CatalogRunner(store, credentials).run(cancel, emit)
            health["checks"].extend(catalogs["checks"])
            health["duration_ms"] += catalogs.get("duration_ms", 0)
        except Exception:
            row = {
                "id": "api_catalogs",
                "status": "warning",
                "code": "CATALOG_CHECK_UNAVAILABLE",
                "message": "Metadata checks unavailable; agent tests can still run.",
                "duration_ms": 0,
                "evidence": {"generation_requests": 0},
            }
            health["checks"].append(row)
            emit({"kind": "diagnostic.result", "data": row})
        health["summary"] = {
            key: sum(r["status"] == key for r in health["checks"])
            for key in ("passed", "failed", "warning", "skipped")
        }
        health["state"] = (
            "cancelled"
            if cancel.is_set()
            else "needs_attention"
            if any(health["summary"][k] for k in ("failed", "warning", "skipped"))
            else "passed"
        )
        store.save_diagnostic(health)
    if cancel.is_set():
        return [health]
    return [health, run_suite(store, credentials, agent, cancel, emit, budget_mode=budget_mode)]
