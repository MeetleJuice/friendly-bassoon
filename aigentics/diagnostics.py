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
from .runtime import Runtime, looks_like_text_tool_call
from .store import Store, now
from .tools import Workspace, ToolRunner, CommandArgs, run_command

SUITE_VERSION = "2"


def model_evidence(events):
    """Bounded protocol structure only, never raw synthetic/model/provider text."""
    metadata, traces = {}, []
    requests = {e["data"]["request_id"]: e["data"] for e in events if e["kind"] == "model.requested"}
    invalid = {e["data"]["request_id"] for e in events if e["kind"] == "protocol.invalid_response"}
    failures = [e["data"] for e in events if e["kind"] == "provider.failed"]
    for event in events:
        data = event["data"]
        if event["kind"] == "model.capabilities":
            metadata = {
                key: data[key]
                for key in ("tools", "source", "template_sha256", "template_chars", "template_mentions_tools")
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
        "model_metadata": metadata,
        "request_traces": traces[:8],
        "provider_error_code": failures[-1].get("code", "PROVIDER_ERROR") if failures else "NONE",
        "http_status": failures[-1].get("http_status") if failures else None,
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
    for session in store.sessions()[:20]:
        state = session["state"]
        for message in store.messages(session["id"]):
            if (
                message.get("role") == "assistant"
                and isinstance(message.get("content"), str)
                and looks_like_text_tool_call(message["content"])
            ):
                legacy += 1
        states[state] = states.get(state, 0) + 1
        for event in store.events(session["id"]):
            if event["kind"] == "protocol.invalid_response":
                protocol += 1
            if event["kind"] == "tool.result" and event["data"].get("status") == "failed":
                kind = event["data"].get("error_type", "ToolFailure")
                # These are runtime class names, not arbitrary provider messages.
                if not isinstance(kind, str) or not kind.isidentifier() or len(kind) > 80:
                    kind = "ToolFailure"
                errors[kind] = errors.get(kind, 0) + 1
    return {
        "limit": 20,
        "states": states,
        "tool_error_types": errors,
        "protocol_failures": protocol,
        "legacy_text_tool_responses": legacy,
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
