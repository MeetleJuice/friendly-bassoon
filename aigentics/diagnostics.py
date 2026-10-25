"""Packaged health checks and reproducible agent exercises, independent of pytest.

All file/command exercises use disposable directories. No user-project command is run.
"""

from contextlib import closing
from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
import threading
import time
from uuid import uuid4
from urllib.parse import urlsplit
import ipaddress
import httpx
from . import __version__
from .catalog import CatalogRunner
from .models import Agent, ModelRef, Profile, Reply, ToolCall
from .providers import Provider
from .reporting import RECENT_ERROR_CODES, RECENT_ERROR_TYPES, RECENT_STATES, recent_run_counts
from .runtime import Runtime, looks_like_text_tool_call
from .store import Store, now
from .tools import Workspace, ToolRunner, CommandArgs, run_command

SUITE_VERSION = "8"
OFFLINE_CHECK_COUNT = 25


def model_evidence(events):
    """Bounded protocol structure only, never raw synthetic/model/provider text."""
    from .tool_diagnostics import tool_diagnostics

    metadata, traces = {}, []
    requests = {e["data"]["request_id"]: e["data"] for e in events if e["kind"] == "model.requested"}
    invalid = {e["data"]["request_id"] for e in events if e["kind"] == "protocol.invalid_response"}
    failures = [e["data"] for e in events if e["kind"] == "provider.failed"]
    for event in events:
        data = event["data"]
        if event["kind"] == "model.capabilities":
            metadata = {
                key: data[key]
                for key in (
                    "tools",
                    "source",
                    "template_sha256",
                    "template_chars",
                    "template_mentions_tools",
                    "parser",
                    "renderer",
                    "template_source",
                )
                if key in data
            }
        if event["kind"] == "model.responded":
            request = requests.get(data["request_id"], {})
            traces.append(
                {
                    "step": request.get("step"),
                    "duration_ms": data["duration_ms"],
                    "native_call_count": data["tool_calls"],
                    "content_chars": data["content_chars"],
                    "text_tool_response": data["request_id"] in invalid,
                    "tool_schema_sha256": request.get("tool_schema_sha256"),
                    "advertised_tool_count": len(request.get("tools_advertised", [])),
                    "request_chars": request.get("request_chars"),
                    "tool_schema_chars": request.get("tool_schema_chars"),
                    "response_shape": data.get("response_shape", {}),
                    "usage": {
                        key: value
                        for key, value in data.get("usage", {}).items()
                        if key in ("prompt_eval_count", "eval_count", "total_duration")
                        and isinstance(value, (int, float))
                    },
                }
            )
    return {
        "tool_diagnostics": tool_diagnostics(events),
        "mismatches": next(
            (e["data"].get("mismatches", []) for e in reversed(events) if e["kind"] == "run.summary"), []
        ),
        "initial_mismatches": next(
            (e["data"].get("mismatches", []) for e in events if e["kind"] == "completion.evaluated"), []
        ),
        "completion_feedback_count": sum(e["kind"] == "completion.feedback_requested" for e in events),
        "initial_task_checks": next(
            (
                e["data"]["checks"]
                for e in events
                if e["kind"] in ("completion.evaluated", "completion.feedback_requested")
            ),
            {},
        ),
        "initial_acceptance_checks": next(
            (
                e["data"].get("acceptance", {})
                for e in events
                if e["kind"] in ("completion.evaluated", "completion.feedback_requested")
            ),
            {},
        ),
        "acceptance_checks": next(
            (e["data"].get("acceptance_checks", {}) for e in reversed(events) if e["kind"] == "run.summary"),
            {},
        ),
        "failure_shape": failures[-1].get("response_shape", {}) if failures else {},
        "model_metadata": metadata,
        "request_traces": traces[:8],
        "failure_usage": failures[-1].get("usage", {}) if failures else {},
        "provider_error_code": failures[-1].get("code", "PROVIDER_ERROR") if failures else "NONE",
        "http_status": failures[-1].get("http_status")
        if failures
        else next(
            (
                e["data"]["http_status"]
                for e in reversed(events)
                if e["kind"] == "model.responded" and type(e["data"].get("http_status")) is int
            ),
            None,
        ),
        "native_calls_total": sum(row["native_call_count"] for row in traces),
    }


@dataclass
class CheckResult:
    id: str
    status: str
    code: str
    message: str
    duration_ms: int
    evidence: dict

    def as_dict(self):
        return vars(self)


def tool_call(name, **arguments):
    return ToolCall(id=str(uuid4()), name=name, arguments=arguments)


def _require(value, message="Check did not match its expected result"):
    if not value:
        raise AssertionError(message)


def _denied(function, exception=PermissionError):
    try:
        function()
    except exception:
        return
    raise AssertionError("Operation was not blocked")


class ScriptedProvider:
    """Controlled native responses for runtime exercises; labeled fixtures in reports."""

    def __init__(self, profile, credentials):
        self.profile = profile

    def capabilities(self, model):
        return {"tools": True, "source": "diagnostic fixture"}

    def chat(self, model, messages, tools):
        calls = [m for m in messages if m["role"] == "tool"]
        if self.profile.id == "text-fixture":
            return Reply(content='{"name":"list_files","arguments":{"path":""}}')
        if not calls:
            # Also verify recovery from the real observed plain-text response shape.
            if not any("Runtime feedback:" in m.get("content", "") for m in messages):
                return Reply(content='{"name":"list_files","arguments":{"path":""}}')
            return Reply(
                calls=[
                    tool_call(
                        "write_file",
                        path="diagnostic_hello.txt",
                        content="Hello, Aigentics!\n",
                        expected_sha256="new",
                    )
                ]
            )
        if len(calls) == 1:
            return Reply(calls=[tool_call("read_file", path="diagnostic_hello.txt")])
        return Reply(content="The fixture file was created and read back.")


def safe_recent_summary(store):
    """Allowlisted counts only. No paths, tasks, agent names, prompts, notes or raw errors."""
    states, errors, protocol, legacy = {}, {}, 0, 0
    runtime_codes, runtime_types, stages = {}, {}, {}
    execution, tool_codes, assessments = {}, {}, {}
    coverage = {
        "sessions": 0,
        "task_checks_recorded": 0,
        "final_status_recorded": 0,
        "current_version_sessions": 0,
    }
    for session in store.sessions()[:20]:
        state = session["state"] if session["state"] in RECENT_STATES else "unknown"
        failed = state in (
            "failed",
            "protocol_error",
            "timed_out",
            "limit_reached",
            "interrupted",
            "needs_review",
            "incomplete_response",
        )
        session_codes, session_types, session_stages = set(), set(), set()
        coverage["sessions"] += 1
        recorded_checks, recorded_final, current_version = False, False, False
        for message in store.messages(session["id"]):
            if (
                message.get("role") == "assistant"
                and isinstance(message.get("content"), str)
                and looks_like_text_tool_call(message["content"])
            ):
                legacy += 1
        states[state] = states.get(state, 0) + 1
        assessment = store.assessment(session["id"])
        label = assessment.get("label") if assessment else "not_assessed"
        if label in ("goal_met", "needs_work", "not_assessed"):
            assessments[label] = assessments.get(label, 0) + 1
        for event in store.events(session["id"]):
            data = event["data"]
            if event["kind"] == "run.summary":
                recorded_checks = isinstance(data.get("task_checks"), dict)
                recorded_final = data.get("final_response_status") in ("present", "missing", "not_reached")
                current_version = event.get("app_version") == __version__
                from .evidence import bounded_counts

                for name, value in bounded_counts(
                    data.get("tools", {})
                    | {
                        key: data[key]
                        for key in ("unresolved_tool_errors", "python_files_needing_attention")
                        if key in data
                    }
                ).items():
                    execution[name] = execution.get(name, 0) + value
            if event["kind"] == "tool.result" and data.get("code") in RECENT_ERROR_CODES:
                code = data["code"]
                tool_codes[code] = tool_codes.get(code, 0) + 1
            if event["kind"] == "protocol.invalid_response":
                protocol += 1
            if event["kind"] == "tool.result" and data.get("status") == "failed":
                kind = data.get("error_type", "ToolFailure")
                if not isinstance(kind, str) or kind not in RECENT_ERROR_TYPES:
                    kind = "OtherError"
                errors[kind] = errors.get(kind, 0) + 1
            if failed and event["kind"] in ("runtime.error", "provider.failed"):
                if "code" in data or event["kind"] == "provider.failed":
                    code = data.get("code", "PROVIDER_ERROR")
                    session_codes.add(
                        code if isinstance(code, str) and code in RECENT_ERROR_CODES else "UNKNOWN_ERROR"
                    )
                if event["kind"] == "runtime.error":
                    kind = data.get("type", "OtherError")
                    kind = kind if isinstance(kind, str) and kind in RECENT_ERROR_TYPES else "OtherError"
                    session_types.add(kind)
                    session_stages.add(
                        "native_protocol"
                        if kind == "NativeToolProtocolError"
                        else "final_response"
                        if kind == "EmptyFinalResponse"
                        else "provider"
                        if kind == "ProviderError"
                        else "runtime"
                    )
                else:
                    session_stages.add("provider")
        # Count affected sessions once per classification, even when an adapter retries/falls back.
        coverage["task_checks_recorded"] += int(recorded_checks)
        coverage["final_status_recorded"] += int(recorded_final)
        coverage["current_version_sessions"] += int(current_version)
        for counter, values in (
            (runtime_codes, session_codes),
            (runtime_types, session_types),
            (stages, session_stages),
        ):
            for value in values:
                counter[value] = counter.get(value, 0) + 1
    return {
        "limit": 20,
        **recent_run_counts(
            {
                "states": states,
                "tool_error_types": errors,
                "protocol_failures": protocol,
                "legacy_text_tool_responses": legacy,
                "runtime_error_codes": runtime_codes,
                "runtime_error_types": runtime_types,
                "failure_stages": stages,
                "execution_counts": execution,
                "tool_error_codes": tool_codes,
                "user_assessments": assessments,
                "coverage": coverage,
            }
        ),
    }


class DiagnosticRunner:
    def __init__(self, store, credentials, provider_factory=Provider, updater=None):
        self.store, self.credentials = store, credentials
        self.provider_factory, self.updater = provider_factory, updater

    def run(self, cancel, emit=lambda event: None, agent=None, include_model=False, include_network=True):
        report = {
            "schema_version": 1,
            "suite_version": SUITE_VERSION,
            "kind": "health",
            "id": str(uuid4()),
            "created": now(),
            "app_version": __version__,
            "state": "running",
            "environment": {
                "os": platform.system(),
                "os_release": platform.release(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
            },
            "checks": [],
            "recent_runs": safe_recent_summary(self.store),
            "privacy": "Metadata and synthetic test results only. No project text, credentials, paths or transcripts.",
        }
        self.store.save_diagnostic(report)
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="aigentics-diagnostic-") as folder:
            scratch = Path(folder)
            ws = Workspace(scratch)

            def permissions():
                runner = ToolRunner(ws, Agent(), lambda *args: False, cancel)
                _denied(
                    lambda: runner.execute(
                        tool_call("write_file", path="denied.txt", content="no", expected_sha256="new")
                    )
                )
                _require(not (scratch / "denied.txt").exists())
                _denied(lambda: runner.execute(tool_call("run_command", argv=["not-executed"])))
                return {"denied_writes": 1, "denied_commands": 1}

            def boundaries():
                for path in ("../escape", ".env", ".git/config", str(scratch.parent / "outside.txt")):
                    _denied(lambda p=path: ws.path(p))
                return {"blocked_paths": 4}

            def files():
                runner = ToolRunner(ws, Agent(), lambda kind, details: kind == "write_file", cancel)
                result = runner.execute(
                    tool_call(
                        "write_file", path="probe.txt", content="synthetic data\n", expected_sha256="new"
                    )
                )
                read = runner.execute(tool_call("read_file", path="probe.txt"))
                _require(result["verified"] and read["content"] == "synthetic data\n")
                original_hash = read["sha256"]
                (scratch / "probe.txt").write_text("changed externally", encoding="utf-8")
                _denied(
                    lambda: runner.execute(
                        tool_call(
                            "write_file", path="probe.txt", content="stale", expected_sha256=original_hash
                        )
                    ),
                    ValueError,
                )
                return {"writes_verified": 1, "reads_verified": 1, "stale_edits_blocked": 1}

            def cancellation():
                stop = threading.Event()
                stop.set()
                runner = ToolRunner(ws, Agent(), lambda *args: True, stop)
                _denied(
                    lambda: runner.execute(
                        tool_call("write_file", path="cancelled.txt", content="no", expected_sha256="new")
                    ),
                    InterruptedError,
                )
                _require(not (scratch / "cancelled.txt").exists())
                return {"cancelled_write_blocked": True}

            def processes():
                argv = (
                    [
                        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "cmd.exe"),
                        "/d",
                        "/c",
                        "echo Aigentics diagnostic",
                    ]
                    if os.name == "nt"
                    else [sys.executable, "-c", "print('Aigentics diagnostic')"]
                )
                result = run_command(scratch, CommandArgs(argv=argv, timeout_seconds=5), cancel)
                _require(result["exit_code"] == 0 and "Aigentics diagnostic" in result["output"])
                return {"exit_code": result["exit_code"], "fixed_command": True}

            def timeouts():
                argv = (
                    [
                        os.path.join(
                            os.environ.get("SystemRoot", r"C:\Windows"),
                            "System32",
                            "WindowsPowerShell",
                            "v1.0",
                            "powershell.exe",
                        ),
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        "Start-Sleep -Seconds 5",
                    ]
                    if os.name == "nt"
                    else [sys.executable, "-c", "import time; time.sleep(5)"]
                )
                result = run_command(scratch, CommandArgs(argv=argv, timeout_seconds=1), cancel)
                if cancel.is_set():
                    raise InterruptedError("Cancelled")
                _require(result["reason"] == "timeout")
                return {"timeout_enforced": True}

            def database():
                with self.store.lock:
                    rows = self.store.db.execute("PRAGMA quick_check").fetchall()
                    version = self.store.db.execute("PRAGMA user_version").fetchone()[0]
                _require(all(row[0] == "ok" for row in rows))
                return {"schema_version": version, "integrity": "ok"}

            def definitions():
                agents, profiles = self.store.agents(), self.store.profiles()
                ids = {p.id for p in profiles}
                missing = sum(ref.profile_id not in ids for a in agents for ref in [a.primary, *a.fallbacks])
                _require(missing == 0, "An agent references a missing provider")
                return {"agents_validated": len(agents), "profiles_validated": len(profiles)}

            def redaction():
                from .credentials import Credentials

                fixture = Credentials()
                fixture._values = {"FIXTURE_API_KEY": "synthetic-fixture-value-123"}
                text = fixture.json(
                    {"nested": {"authorization": "unknown", "message": "synthetic-fixture-value-123"}}
                )
                _require(
                    "synthetic-fixture-value-123" not in text
                    and json.loads(text)["nested"]["authorization"] == "[REDACTED]"
                )
                return {"nested_json_valid": True, "credential_redaction": True}

            def adapters():
                checks = 0
                for kind in ("ollama", "openai"):
                    function = {"name": "list_files", "arguments": {} if kind == "ollama" else "{}"}
                    message = {"content": "", "tool_calls": [{"id": "fixture", "function": function}]}
                    data = {"message": message} if kind == "ollama" else {"choices": [{"message": message}]}
                    transport = httpx.MockTransport(lambda request, data=data: httpx.Response(200, json=data))
                    provider = Provider(
                        Profile(id="fixture", name="Fixture", kind=kind), self.credentials, transport
                    )
                    reply = provider.chat("fixture", [], [])
                    _require(len(reply.calls) == 1 and reply.calls[0].name == "list_files")
                    checks += 1
                return {"protocol_fixtures_passed": checks, "external_requests": 0}

            def runtime_fixture(text_only):
                work = scratch / ("protocol" if text_only else "coding")
                work.mkdir()
                with closing(
                    Store(scratch / ("protocol.sqlite3" if text_only else "coding.sqlite3"), self.credentials)
                ) as fixture_store:
                    identity = "text-fixture" if text_only else "coding-fixture"
                    fixture_store.save_profile(Profile(id=identity, name="Controlled fixture"))
                    trial_agent = Agent(
                        primary=ModelRef(profile_id=identity, model="fixture"),
                        tools=["list_files", "read_file", "write_file"],
                        max_steps=8,
                    )
                    sid, state = Runtime(fixture_store, self.credentials, ScriptedProvider).run(
                        trial_agent,
                        work,
                        "Create diagnostic_hello.txt containing Hello, Aigentics! and read it back.",
                        lambda kind, details: kind == "write_file"
                        and details["path"] == "diagnostic_hello.txt",
                        cancel,
                    )
                    if cancel.is_set():
                        raise InterruptedError("Cancelled")
                    if text_only:
                        _require(state == "protocol_error" and not (work / "diagnostic_hello.txt").exists())
                        return {"text_never_executed": True, "bounded_recovery": True}
                    _require(
                        state == "completed"
                        and (work / "diagnostic_hello.txt").read_text(encoding="utf-8")
                        == "Hello, Aigentics!\n"
                    )
                    _require(
                        any(
                            e["kind"] == "tool.result"
                            and e["data"]["tool"] == "read_file"
                            and e["data"]["status"] == "succeeded"
                            for e in fixture_store.events(sid)
                        )
                    )
                    return {
                        "fixture_goal_verified": True,
                        "native_recovery_verified": True,
                        "cloud_requests": 0,
                    }

            def catalogs():
                calls = []

                def handle(request):
                    calls.append(request)
                    _require(
                        request.method == "GET" and request.url.path == "/models" and not request.content
                    )
                    return httpx.Response(200, json={"data": [{"id": "synthetic-model"}]})

                with closing(Store(scratch / "catalog.sqlite3", self.credentials)) as trial:
                    profile = Profile(
                        id="catalog",
                        name="Synthetic catalog",
                        kind="openai",
                        base_url="https://catalog.invalid",
                    )
                    trial.save_profile(profile)
                    trial.save_profile(profile.model_copy(update={"id": "alias"}))
                    runner = CatalogRunner(
                        trial, self.credentials, lambda p, c: Provider(p, c, httpx.MockTransport(handle))
                    )
                    result = runner.run(cancel)
                    _require(result["state"] == "passed" and len(calls) == 1)
                    _require(len(trial.catalogs()) == 2)
                    return {
                        "catalog_fixture_verified": True,
                        "generation_requests": 0,
                        "external_requests": 0,
                    }

            def retention():
                with closing(Store(scratch / "retention.sqlite3", self.credentials)) as trial:
                    trial.set_setting("max_reports", 5)
                    for index in range(7):
                        trial.save_diagnostic({"id": str(index), "created": now(), "state": "passed"})
                    trial.save_diagnostic({"id": "active", "created": now(), "state": "running"})
                    trial.prune()
                    _require(len(trial.diagnostic_reports()) == 6)
                    _require(any(row["id"] == "active" for row in trial.diagnostic_reports()))
                    return {"retention_fixture_verified": True, "active_report_protected": True}

            def registry():
                from .registry import TOOL_REGISTRY
                from .tools import SCHEMAS, tool_definitions

                _require(set(TOOL_REGISTRY) == set(SCHEMAS))
                enabled = Agent(tools=list(TOOL_REGISTRY), allow_writes=True, allow_commands=True)
                definitions = {row["function"]["name"]: row["function"] for row in tool_definitions(enabled)}
                _require(set(definitions) == set(TOOL_REGISTRY))
                readonly = enabled.model_copy(update={"allow_writes": False, "allow_commands": False})
                _require(
                    {row["function"]["name"] for row in tool_definitions(readonly)}
                    == {name for name, spec in TOOL_REGISTRY.items() if spec.permission == "read"}
                )
                for name, spec in TOOL_REGISTRY.items():
                    _require(spec.read_only == (spec.permission == "read"))
                    _require(definitions[name]["description"] == spec.description)
                    _require(definitions[name]["parameters"] == SCHEMAS[name].model_json_schema())
                root = scratch / "registry"
                root.mkdir()
                (root / "source.py").write_text("registry_fixture = True\n", encoding="utf-8")
                approvals = []
                runner = ToolRunner(
                    Workspace(root), enabled, lambda kind, details: approvals.append(kind) or False, cancel
                )
                arguments = {
                    "list_files": {"path": "."},
                    "read_file": {"path": "source.py"},
                    "search": {"query": "registry_fixture"},
                    "project_map": {},
                    "retrieve_context": {"query": "registry_fixture"},
                }
                for name, values in arguments.items():
                    _require(runner.execute(tool_call(name, **values)) is not None)
                _denied(lambda: runner.execute(tool_call("unregistered_fixture")))
                _denied(
                    lambda: runner.execute(
                        tool_call("write_file", path="denied.txt", content="no", expected_sha256="new")
                    )
                )
                _denied(lambda: runner.execute(tool_call("run_command", argv=["not-executed"])))
                _require(approvals == ["write_file", "run_command"] and not (root / "denied.txt").exists())
                return {"registry_fixture_verified": True, "external_requests": 0}

            def retrieval():
                from .retrieval import project_map, retrieve_context

                root = scratch / "retrieval"
                (root / "src").mkdir(parents=True)
                source = "def diagnostic_retrieval_marker():\n    return 'synthetic public value'\n"
                (root / "src" / "main.py").write_text(source, encoding="utf-8")
                for name in (".env", "credentials.json", "ignored.txt", "excluded.txt"):
                    (root / name).write_text("diagnostic_retrieval_marker private fixture", encoding="utf-8")
                (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
                (root / ".aigenticsignore").write_text("excluded.txt\n", encoding="utf-8")
                outside = scratch / "outside-retrieval.txt"
                outside.write_text("diagnostic_retrieval_marker linked fixture", encoding="utf-8")
                try:
                    (root / "linked.txt").symlink_to(outside)
                except OSError:
                    pass  # Windows may require a privilege to create the synthetic link.
                workspace = Workspace(root)
                mapped = project_map(workspace, cancel)
                _require([row["path"] for row in mapped["files"]] == ["src/main.py"])
                result = retrieve_context(workspace, "diagnostic_retrieval_marker", cancel)
                _require(bool(result["snippets"]))
                original_hash = workspace.read("src/main.py")["sha256"]
                lines = source.splitlines()
                for snippet in result["snippets"]:
                    _require(snippet["path"] == "src/main.py" and snippet["sha256"] == original_hash)
                    _require(1 <= snippet["line"] <= snippet["end_line"] <= len(lines))
                    _require(snippet["text"] == "\n".join(lines[snippet["line"] - 1 : snippet["end_line"]]))
                updated = source.replace("synthetic public value", "fresh synthetic value")
                (root / "src" / "main.py").write_text(updated, encoding="utf-8")
                fresh = retrieve_context(workspace, "fresh synthetic value", cancel)
                _require(bool(fresh["snippets"]))
                _require(all(row["sha256"] != original_hash for row in fresh["snippets"]))
                bounded = retrieve_context(workspace, "diagnostic_retrieval_marker", cancel, max_chars=24)
                _require(sum(len(row["text"]) for row in bounded["snippets"]) <= 24)
                stopped = threading.Event()
                stopped.set()
                _denied(lambda: project_map(workspace, stopped), InterruptedError)
                _denied(lambda: retrieve_context(workspace, "fixture", stopped), InterruptedError)
                return {"project_retrieval_fixture_verified": True, "external_requests": 0}

            def native_probe_fixture():
                from .probes import ToolProbe

                def respond(request):
                    body = json.loads(request.content)
                    _require(request.url.path == "/api/chat" and body["options"]["num_predict"] == 96)
                    _require([t["function"]["name"] for t in body["tools"]] == ["report_probe"])
                    challenge = body["messages"][-1]["content"].split("challenge '", 1)[1].split("'", 1)[0]
                    return httpx.Response(
                        200,
                        json={
                            "message": {
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "report_probe",
                                            "arguments": {"challenge": challenge},
                                        }
                                    }
                                ]
                            },
                            "done_reason": "stop",
                        },
                    )

                with closing(Store(scratch / "probe.sqlite3", self.credentials)) as trial:
                    trial.save_profile(Profile(id="probe", name="Probe fixture"))
                    agent = trial.save_agent(Agent(primary=ModelRef(profile_id="probe", model="fixture")))
                    result = ToolProbe(
                        trial, self.credentials, lambda p, c: Provider(p, c, httpx.MockTransport(respond))
                    ).run(agent.id, cancel)
                    _require(result["state"] == "passed" and not trial.sessions())
                    return {"probe_fixture_verified": True, "external_requests": 0}

            def python_check_fixture():
                from .verification import check_python

                root = scratch / "python-check"
                root.mkdir()
                trial = Workspace(root)
                (root / "good.py").write_text("raise RuntimeError('must never run')\n", encoding="utf-8")
                (root / "bad.py").write_text("WIDTH, HEIGHT = 800, 60, 600\n", encoding="utf-8")
                _require(check_python(trial, "good.py")["status"] == "passed")
                _require(check_python(trial, "bad.py")["code"] == "LITERAL_UNPACK_MISMATCH")
                return {"python_check_fixture_verified": True, "program_executed": False}

            def revision_fixture():
                root = scratch / "revision-check"
                root.mkdir()
                (root / "file.txt").write_text("before", encoding="utf-8")
                runner = ToolRunner(Workspace(root), Agent(), lambda *args: True, cancel)
                runner.execute(tool_call("read_file", path="file.txt"))
                _require(
                    runner.execute(
                        tool_call("write_file", path="file.txt", content="after", expected_sha256="last_read")
                    )["verified"]
                )
                _denied(
                    lambda: runner.execute(
                        tool_call("write_file", path="file.txt", content="stale", expected_sha256="last_read")
                    ),
                    ValueError,
                )
                return {"revision_fixture_verified": True, "stale_edits_blocked": 1}

            def task_checks_fixture():
                from .task_checks import TaskChecks, TaskEvidence

                root = scratch / "task-checks"
                root.mkdir()
                trial_ws = Workspace(root)
                checks = TaskChecks(
                    write_targets=["expected.txt"], required_tools=["write_file", "read_file"]
                )
                evidence = TaskEvidence(trial_ws, checks)
                runner = ToolRunner(trial_ws, Agent(), lambda *args: True, cancel, checks.write_targets)
                _denied(
                    lambda: runner.execute(
                        tool_call("write_file", path="wrong.txt", content="wrong", expected_sha256="new")
                    )
                )
                _require(not (root / "wrong.txt").exists())
                for name, values in (
                    ("write_file", {"path": "expected.txt", "content": "expected", "expected_sha256": "new"}),
                    ("read_file", {"path": "expected.txt"}),
                ):
                    call = tool_call(name, **values)
                    evidence.record(call, runner.execute(call), "succeeded")
                _require(evidence.evaluate()[0]["status"] == "passed")
                (root / "expected.txt").write_text("changed", encoding="utf-8")
                _require(evidence.evaluate()[0]["status"] == "needs_attention")
                return {"task_checks_fixture_verified": True, "external_requests": 0}

            def empty_final_fixture():
                from .task_checks import TaskChecks

                root = scratch / "empty-final"
                root.mkdir()
                requests = []

                class EmptyFinal:
                    def __init__(self, *args):
                        pass

                    def capabilities(self, model):
                        return {"tools": True, "source": "fixture"}

                    def chat(self, model, messages, tools):
                        requests.append(1)
                        if any(m["role"] == "tool" for m in messages):
                            return Reply(evidence={"thinking_chars": 123, "finish_reason": "stop"})
                        return Reply(
                            calls=[
                                tool_call(
                                    "write_file", path="saved.txt", content="preserved", expected_sha256="new"
                                )
                            ]
                        )

                with closing(Store(scratch / "empty.sqlite3", self.credentials)) as trial:
                    trial.save_profile(Profile(id="ollama", name="Fixture"))
                    sid, state = Runtime(trial, self.credentials, EmptyFinal).run(
                        Agent(),
                        root,
                        "Synthetic fixture",
                        lambda *args: True,
                        task_checks=TaskChecks(write_targets=["saved.txt"], require_readback=False),
                    )
                    _require(state == "incomplete_response" and len(requests) == 2)
                    _require((root / "saved.txt").read_text(encoding="utf-8") == "preserved")
                    _require(sum(e["kind"] == "tool.result" for e in trial.events(sid)) == 1)
                return {"empty_final_fixture_verified": True, "external_requests": 0}

            from .regression_checks import (
                validation_recovery_check,
                checkpoint_recovery_check,
                crew_evaluation_check,
                correctness_check,
            )

            cases = [
                ("database", database),
                ("definitions", definitions),
                ("file_boundaries", boundaries),
                ("permission_denial", permissions),
                ("file_write_read_and_stale_edit", files),
                ("cancellation", cancellation),
                ("command_execution", processes),
                ("command_timeout", timeouts),
                ("redaction", redaction),
                ("provider_protocol_fixtures", adapters),
                ("text_tool_regression", lambda: runtime_fixture(True)),
                ("native_agent_workflow", lambda: runtime_fixture(False)),
                ("model_catalog_fixture", catalogs),
                ("report_retention_fixture", retention),
                ("tool_registry_fixture", registry),
                ("project_retrieval_fixture", retrieval),
                ("native_probe_fixture", native_probe_fixture),
                ("python_check_fixture", python_check_fixture),
                ("revision_fixture", revision_fixture),
                ("task_checks_fixture", task_checks_fixture),
                ("empty_final_fixture", empty_final_fixture),
                ("validation_recovery_fixture", lambda: validation_recovery_check(self.credentials)),
                ("checkpoint_recovery_fixture", lambda: checkpoint_recovery_check(self.credentials)),
                ("crew_evaluation_fixture", lambda: crew_evaluation_check(self.credentials)),
                ("correctness_fixture", lambda: correctness_check(self.credentials)),
            ]
            for identity, function in cases:
                if cancel.is_set():
                    break
                emit({"kind": "diagnostic.started", "data": {"id": identity}})
                before = time.monotonic()
                try:
                    evidence = function()
                    status, code, message = (
                        "passed",
                        "OK",
                        "Check passed against its defined acceptance criteria.",
                    )
                except InterruptedError:
                    cancel.set()
                    break
                except Exception as exc:
                    evidence = {"error_type": type(exc).__name__}
                    status, code, message = (
                        "failed",
                        identity.upper() + "_FAILED",
                        "A built-in check failed. See the check ID and error type.",
                    )
                result = CheckResult(
                    identity, status, code, message, round((time.monotonic() - before) * 1000), evidence
                )
                report["checks"].append(result.as_dict())
                self.store.save_diagnostic(report)
                emit({"kind": "diagnostic.result", "data": result.as_dict()})
            if not cancel.is_set() and include_network:
                self._network_check(report, cancel, emit)
            if not cancel.is_set() and include_model:
                self._model_check(report, scratch, agent, cancel, emit)
        counts = {
            key: sum(row["status"] == key for row in report["checks"])
            for key in ("passed", "failed", "warning", "skipped")
        }
        report.update(
            state="cancelled"
            if cancel.is_set()
            else "needs_attention"
            if counts["failed"] or counts["warning"]
            else "passed",
            finished=now(),
            duration_ms=round((time.monotonic() - started) * 1000),
            summary=counts,
        )
        self.store.save_diagnostic(report)
        self.store.event(
            None, "diagnostic.completed", {"report_id": report["id"], "state": report["state"], **counts}
        )
        return report

    def _network_check(self, report, cancel, emit):
        before = time.monotonic()
        try:
            if not self.updater:
                raise RuntimeError("No updater configured")
            release = self.updater.check(cancel)
            result = CheckResult(
                "update_connection",
                "passed",
                "OK",
                "GitHub update check responded.",
                round((time.monotonic() - before) * 1000),
                {"newer_release_available": release is not None},
            )
        except InterruptedError:
            cancel.set()
            return
        except Exception as exc:
            result = CheckResult(
                "update_connection",
                "warning",
                "UPDATE_CONNECTION_UNAVAILABLE",
                "Update service could not be reached. Local diagnostics can still complete.",
                round((time.monotonic() - before) * 1000),
                {"error_type": type(exc).__name__},
            )
        report["checks"].append(result.as_dict())
        self.store.save_diagnostic(report)
        emit({"kind": "diagnostic.result", "data": result.as_dict()})

    def _model_check(self, report, scratch, agent, cancel, emit):
        before = time.monotonic()
        profile = next((p for p in self.store.profiles() if agent and p.id == agent.primary.profile_id), None)
        local = False
        if profile and profile.kind == "ollama":
            host = urlsplit(profile.base_url).hostname
            try:
                local = host == "localhost" or ipaddress.ip_address(host).is_loopback
            except ValueError:
                pass
        if not local:
            result = CheckResult(
                "selected_local_model",
                "skipped",
                "LOCAL_MODEL_NOT_SELECTED",
                "Select a local Ollama agent for a real model test. Cloud models are never invoked automatically.",
                0,
                {},
            )
        else:
            emit({"kind": "diagnostic.started", "data": {"id": "selected_local_model"}})
            try:
                root = scratch / "live-model"
                root.mkdir()
                metadata = {}
                try:
                    probe = self.provider_factory(
                        profile.model_copy(update={"timeout_seconds": 3}), self.credentials
                    )
                    version_data = probe.request("GET", "/api/version")
                    version = version_data.get("version", "")
                    if isinstance(version, str) and re.fullmatch(r"[0-9][0-9A-Za-z.+_-]{0,79}", version):
                        metadata["ollama_version"] = version
                except Exception:
                    pass  # An older server can still be tested; version discovery is optional.
                with closing(Store(scratch / "live.sqlite3", self.credentials)) as trial:
                    trial.save_profile(profile)
                    bounded = Agent(
                        primary=agent.primary,
                        tools=["list_files", "read_file", "write_file"],
                        max_steps=8,
                        max_seconds=min(agent.max_seconds, 180),
                    )
                    sid, state = Runtime(trial, self.credentials, self.provider_factory).run(
                        bounded,
                        root,
                        "Use native tools to create diagnostic_hello.txt with exactly Hello, Aigentics! followed by a newline. "
                        "Then read it back using read_file. This is a disposable test; no terminal commands are allowed.",
                        lambda kind, details: kind == "write_file"
                        and details["path"] == "diagnostic_hello.txt",
                        cancel,
                        emit=lambda e: emit(e) if e["kind"].startswith("protocol.") else None,
                    )
                    if cancel.is_set():
                        return
                    path = root / "diagnostic_hello.txt"
                    matched = path.exists() and path.read_text(encoding="utf-8") == "Hello, Aigentics!\n"
                    events = trial.events(sid)
                    readback = any(
                        e["kind"] == "tool.result"
                        and e["data"].get("tool") == "read_file"
                        and e["data"].get("status") == "succeeded"
                        for e in events
                    )
                    verified = state == "completed" and matched and readback
                    result = CheckResult(
                        "selected_local_model",
                        "passed" if verified else "failed",
                        "OK" if verified else "MODEL_WORKFLOW_NOT_VERIFIED",
                        "Actual file creation and read-back verified."
                        if verified
                        else "The selected model did not complete the verified tool workflow.",
                        round((time.monotonic() - before) * 1000),
                        {
                            **metadata,
                            **model_evidence(events),
                            "runtime_state": state,
                            "file_matches": matched,
                            "readback_recorded": readback,
                            "model": agent.primary.model,
                            "protocol_retries": sum(e["kind"] == "protocol.retry_requested" for e in events),
                            "failure_stage": "none"
                            if verified
                            else "native_protocol"
                            if state == "protocol_error"
                            else "provider_or_capability"
                            if state == "failed"
                            else "workflow_verification",
                        },
                    )
            except Exception as exc:
                result = CheckResult(
                    "selected_local_model",
                    "failed",
                    "MODEL_CHECK_FAILED",
                    "Local model test could not complete. Check Ollama/model availability.",
                    round((time.monotonic() - before) * 1000),
                    {"error_type": type(exc).__name__},
                )
        report["checks"].append(result.as_dict())
        self.store.save_diagnostic(report)
        emit({"kind": "diagnostic.result", "data": result.as_dict()})
