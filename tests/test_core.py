import json
import sys
import threading
import time
import httpx
import pytest
from pydantic import ValidationError
from aigentics.models import Agent, Profile, Reply, ToolCall, ModelRef
from aigentics.providers import Provider, ProviderError
from aigentics.store import Store
from aigentics.tools import Workspace, ToolRunner, CommandArgs, run_command
from aigentics.runtime import Runtime, cancellable_call, RunTimeout


def call(name, **arguments):
    return ToolCall(id="c1", name=name, arguments=arguments)


def test_validation_and_revision_persistence(store, credentials):
    with pytest.raises(ValidationError):
        Agent(max_steps=0)
    with pytest.raises(ValidationError):
        Agent(tools=["imaginary"])
    with pytest.raises(ValidationError):
        Agent(primary={"profile_id": "x", "model": "x", "key": "no"})
    a = store.save_agent(Agent())
    a.name = "Updated"
    a = store.save_agent(a)
    assert a.revision == 2
    other = Store(store.path, credentials, recover=False)
    assert other.agents()[0].name == "Updated"
    assert other.db.execute("PRAGMA user_version").fetchone()[0] == 4
    other.close()


@pytest.mark.parametrize(
    "url", ["http://api.example.com", "https://key:secret@example.com", "https://example.com?key=x"]
)
def test_profile_rejects_insecure_endpoints(url):
    with pytest.raises(ValidationError):
        Profile(id="p", name="p", base_url=url)


def test_credentials_redacted_and_never_saved_in_agents(store, credentials, tmp_path):
    env = tmp_path / "keys.env"
    secret = "a-private-value-123456"
    env.write_text("MY_API_KEY=" + secret, encoding="utf-8")
    assert credentials.load_env(env) == ["MY_API_KEY"]
    assert credentials.get("MY_API_KEY") == secret
    with pytest.raises(ValueError, match="credential"):
        store.save_agent(Agent(instructions=secret))
    sid = store.start(Agent(), tmp_path, True)
    store.event(sid, "failure", {"error": secret})
    store.messages(sid, [{"role": "user", "content": secret}])
    exported = tmp_path / "export.json"
    store.export(sid, exported)
    assert secret not in exported.read_text()
    assert "REDACTED" in exported.read_text()


def test_metadata_default_and_interrupted_recovery(store, credentials, tmp_path):
    sid = store.start(Agent(), tmp_path)
    store.messages(sid, [{"role": "user", "content": "private project content"}])
    assert store.messages(sid) == []
    reopened = Store(store.path, credentials)
    assert reopened.sessions()[0]["state"] == "interrupted"
    assert reopened.events(sid)[-1]["kind"] == "session.interrupted"
    reopened.close()


def test_delete_export_retention(store, tmp_path):
    sid = store.start(Agent(), tmp_path, True)
    store.messages(sid, [{"role": "user", "content": "hello"}])
    store.finish(sid, "completed", "done")
    store.export(sid, tmp_path / "out.json")
    assert json.loads((tmp_path / "out.json").read_text())["messages"][0]["content"] == "hello"
    store.delete_session(sid)
    assert store.events(sid) == []
    assert store.messages(sid) == []
    for _ in range(40):
        sid = store.start(Agent(), tmp_path)
        store.event(sid, "example", {"duration_ms": 2})
        store.finish(sid, "completed", "ok")
    store.set_setting("max_events", 100)
    store.prune()
    assert store.db.execute("SELECT COUNT(*) FROM events").fetchone()[0] <= 100


@pytest.mark.parametrize(
    "path", ["../escape.txt", ".env", ".env.local", ".git/config", "nested/../../bad", "key.pem"]
)
def test_workspace_protected_paths(tmp_path, path):
    with pytest.raises(PermissionError):
        Workspace(tmp_path).path(path)


def test_absolute_symlink_and_hardlink_boundaries(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("private")
    ws = Workspace(root)
    with pytest.raises(PermissionError):
        ws.path(str(outside))
    try:
        (root / "link").symlink_to(outside)
        (root / "hard").hardlink_to(outside)
    except OSError:
        pytest.skip("Filesystem does not support links")
    with pytest.raises(PermissionError):
        ws.read("link")
    with pytest.raises(PermissionError):
        ws.read("hard")


def test_write_approval_and_stale_edit(tmp_path):
    ws = Workspace(tmp_path)
    agent = Agent()
    approvals = []
    denied = ToolRunner(ws, agent, lambda *a: False, threading.Event())
    with pytest.raises(PermissionError):
        denied.execute(call("write_file", path="hello.py", content="print('hello')\n", expected_sha256="new"))
    assert not (tmp_path / "hello.py").exists()
    runner = ToolRunner(ws, agent, lambda *a: approvals.append(a) or True, threading.Event())
    result = runner.execute(
        call("write_file", path="hello.py", content="print('hello')\n", expected_sha256="new")
    )
    assert result["verified"]
    assert "print('hello')" in approvals[0][1]["diff"]
    sha = ws.read("hello.py")["sha256"]

    def concurrent_change(*args):
        (tmp_path / "hello.py").write_text("someone else's update")
        return True

    runner.approve = concurrent_change
    with pytest.raises(ValueError, match="changed"):
        runner.execute(call("write_file", path="hello.py", content="changed", expected_sha256=sha))
    assert (tmp_path / "hello.py").read_text() == "someone else's update"


def test_tool_permissions_and_schema_validation(tmp_path):
    runner = ToolRunner(Workspace(tmp_path), Agent(allow_commands=False), lambda *a: True, threading.Event())
    with pytest.raises(PermissionError):
        runner.execute(call("run_command", argv=[sys.executable, "-V"]))
    with pytest.raises(ValidationError):
        runner.execute(call("read_file", path="x", unknown=True))
    with pytest.raises(PermissionError):
        runner.execute(call("invented"))


def test_command_execution_failure_timeout_output_limit_and_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_API_KEY", "should-never-inherit")
    cancel = threading.Event()
    result = run_command(
        tmp_path,
        CommandArgs(argv=[sys.executable, "-c", "import os; print(os.getenv('MY_API_KEY', 'absent'))"]),
        cancel,
    )
    assert result["exit_code"] == 0 and "absent" in result["output"]
    result = run_command(tmp_path, CommandArgs(argv=[sys.executable, "-c", "raise SystemExit(7)"]), cancel)
    assert result["exit_code"] == 7
    result = run_command(
        tmp_path,
        CommandArgs(argv=[sys.executable, "-c", "import time; time.sleep(5)"], timeout_seconds=1),
        cancel,
    )
    assert result["reason"] == "timeout"
    result = run_command(tmp_path, CommandArgs(argv=[sys.executable, "-c", "print('x'*50000)"]), cancel)
    assert result["reason"] == "output_limit" and len(result["output"]) == 32000
    cancel.set()
    result = run_command(
        tmp_path, CommandArgs(argv=[sys.executable, "-c", "import time; time.sleep(5)"]), cancel
    )
    assert result["reason"] == "cancelled"


@pytest.mark.parametrize("kind", ["ollama", "openai"])
def test_real_adapter_protocol_with_http_fixture(credentials, kind):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith(("/tags", "/models")):
            return httpx.Response(
                200, json={"models": [{"name": "test"}]} if kind == "ollama" else {"data": [{"id": "test"}]}
            )
        if request.url.path.endswith("/show"):
            return httpx.Response(200, json={"capabilities": ["completion", "tools"]})
        msg = {
            "content": "",
            "tool_calls": [
                {"id": "a", "function": {"name": "list_files", "arguments": {} if kind == "ollama" else "{}"}}
            ],
        }
        return httpx.Response(
            200,
            json={"message": msg, "eval_count": 3}
            if kind == "ollama"
            else {"choices": [{"message": msg}], "usage": {"total_tokens": 3}},
        )

    provider = Provider(Profile(id="p", name="p", kind=kind), credentials, httpx.MockTransport(handler))
    assert provider.discover() == ["test"]
    assert provider.capabilities("test")["tools"]
    reply = provider.chat("test", [{"role": "user", "content": "list"}], [])
    assert reply.calls[0].name == "list_files"
    assert reply.usage
    assert json.loads(requests[-1].content)["stream"] is False


def test_adapter_rejects_malformed_calls_and_rate_limits(credentials):
    profile = Profile(id="p", name="p")
    provider = Provider(profile, credentials, httpx.MockTransport(lambda r: httpx.Response(429)))
    with pytest.raises(ProviderError) as error:
        provider.chat("test", [], [])
    assert error.value.retryable
    provider.transport = httpx.MockTransport(
        lambda r: httpx.Response(
            200,
            json={"message": {"tool_calls": [{"function": {"name": "read_file", "arguments": "not JSON"}}]}},
        )
    )
    with pytest.raises(ProviderError, match="Malformed"):
        provider.chat("test", [], [])


def scripted_factory(replies, fail_first=False):
    class Scripted:
        def __init__(self, profile, credentials):
            self.profile = profile

        def capabilities(self, model):
            return {"tools": True, "source": "test fixture"}

        def chat(self, model, messages, tools):
            if fail_first and self.profile.id == "primary":
                raise ProviderError("Rate limited", True)
            return replies.pop(0)

    return Scripted


def test_end_to_end_coding_workflow_and_evidence(store, credentials, tmp_path):
    store.save_profile(Profile(id="ollama", name="Ollama"))
    replies = [
        Reply(calls=[call("list_files")]),
        Reply(calls=[call("write_file", path="hello.py", content="print('hello')\n", expected_sha256="new")]),
        Reply(calls=[call("run_command", argv=[sys.executable, "hello.py"])]),
        Reply(content="The recorded command printed hello."),
    ]
    observed = []
    sid, state = Runtime(store, credentials, scripted_factory(replies)).run(
        Agent(allow_commands=True),
        tmp_path,
        "Build hello",
        lambda *args: True,
        emit=observed.append,
        capture=True,
    )
    assert state == "completed"
    assert (tmp_path / "hello.py").read_text() == "print('hello')\n"
    events = store.events(sid)
    tool_results = [e for e in events if e["kind"] == "tool.result"]
    assert len(tool_results) == 3
    assert tool_results[-1]["data"]["exit_code"] == 0
    assert tool_results[-1]["data"]["status"] == "succeeded"
    assert [e for e in events if e["kind"] == "permission.decided"]
    assert store.messages(sid)
    assert all(e["app_version"] and e["id"] and e["timestamp"] for e in events)


def test_fallback_and_denial_are_recorded(store, credentials, tmp_path):
    for name in ("primary", "fallback"):
        store.save_profile(Profile(id=name, name=name))
    agent = Agent(
        primary=ModelRef(profile_id="primary", model="a"),
        fallbacks=[ModelRef(profile_id="fallback", model="b")],
    )
    replies = [
        Reply(calls=[call("write_file", path="no.txt", content="no", expected_sha256="new")]),
        Reply(content="Denied"),
    ]
    sid, state = Runtime(store, credentials, scripted_factory(replies, True)).run(
        agent, tmp_path, "task", lambda *a: False
    )
    events = store.events(sid)
    assert state == "needs_review"
    assert not (tmp_path / "no.txt").exists()
    assert any(e["kind"] == "provider.fallback" for e in events)
    assert any(e["kind"] == "tool.result" and e["data"]["status"] == "failed" for e in events)


def test_cancellation_and_runtime_step_limit(store, credentials, tmp_path):
    store.save_profile(Profile(id="ollama", name="Ollama"))
    cancel = threading.Event()
    cancel.set()
    sid, state = Runtime(store, credentials).run(Agent(), tmp_path, "task", lambda *a: True, cancel)
    assert state == "cancelled"
    assert store.events(sid)[-1]["kind"] == "session.cancelled"
    sid, state = Runtime(store, credentials, scripted_factory([Reply(calls=[call("list_files")])])).run(
        Agent(max_steps=1), tmp_path, "task", lambda *a: True
    )
    assert state == "limit_reached"
    with pytest.raises(RunTimeout):
        cancellable_call(lambda: time.sleep(0.3), threading.Event(), time.monotonic() + 0.05)


def test_unsupported_capability_fails_without_tool_execution(store, credentials, tmp_path):
    store.save_profile(Profile(id="ollama", name="Ollama"))

    class Unsupported:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": False, "source": "fixture"}

        def chat(self, *args):
            raise AssertionError("Must never call unsupported model")

    sid, state = Runtime(store, credentials, Unsupported).run(Agent(), tmp_path, "task", lambda *a: True)
    assert state == "failed"
    assert not any(e["kind"] == "tool.requested" for e in store.events(sid))


def test_search_ignores_secrets(store, tmp_path):
    (tmp_path / ".env").write_text("NEEDLE=private")
    (tmp_path / "app.py").write_text("print('NEEDLE')")
    results = Workspace(tmp_path).search("NEEDLE", threading.Event())["matches"]
    assert [r["path"] for r in results] == ["app.py"]


def test_live_conversation_without_content_persistence(store, credentials, tmp_path):
    store.save_profile(Profile(id="ollama", name="Ollama"))
    seen = []

    class ContextProvider:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            seen.append(list(messages))
            return Reply(content="A response")

    runtime = Runtime(store, credentials, ContextProvider)
    first, _ = runtime.run(Agent(), tmp_path, "First task", lambda *a: True)
    assert store.messages(first) == []
    runtime.run(Agent(), tmp_path, "Follow up", lambda *a: True, parent=first)
    assert any(m.get("content") == "First task" for m in seen[-1])
    assert seen[-1][-1]["content"] == "Follow up"


def test_evidence_metrics_and_configuration_audit(store, credentials, tmp_path):
    agent = store.save_agent(Agent())
    store.save_profile(Profile(id="ollama", name="Ollama"))
    replies = [Reply(calls=[call("list_files")], usage={"eval_count": 4}), Reply(content="Done")]
    sid, state = Runtime(store, credentials, scripted_factory(replies)).run(
        agent, tmp_path, "Inspect", lambda *a: True
    )
    metrics = store.metrics()
    assert metrics["sessions_by_state"]["completed"] == 1
    assert metrics["tools"]["list_files"]["succeeded"] == 1
    assert metrics["models"]["ollama/qwen2.5-coder:7b"]["reported_usage"]["eval_count"] == 4
    assert any(e["kind"] == "configuration.agent_saved" for e in store.events(None))
    events = store.events(sid)
    requested = next(e["data"] for e in events if e["kind"] == "tool.requested")
    result = next(e["data"] for e in events if e["kind"] == "tool.result")
    assert requested["execution_id"] == result["execution_id"]
    assert requested["request_id"] == result["request_id"]


def test_utf8_byte_limits_and_windows_reserved_paths(tmp_path):
    from aigentics.tools import WriteArgs

    with pytest.raises(ValidationError):
        WriteArgs(path="big.txt", content="🧪" * 30000, expected_sha256="new")
    for path in ("file:stream", "CON.txt", "nul", "trailing.", ".env "):
        with pytest.raises(PermissionError):
            Workspace(tmp_path).path(path)


def test_ollama_tool_result_uses_native_tool_name(credentials):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "ok"}})

    provider = Provider(Profile(id="ollama", name="Ollama"), credentials, httpx.MockTransport(handler))
    provider.chat(
        "test", [{"role": "tool", "name": "read_file", "tool_call_id": "c1", "content": "result"}], []
    )
    sent = requests[0]["messages"][0]
    assert sent["tool_name"] == "read_file"
    assert "name" not in sent and "tool_call_id" not in sent


def test_schema_upgrade_preserves_evidence_and_user_assessments(store, credentials, tmp_path):
    sid = store.start(Agent(), tmp_path)
    store.finish(sid, "completed", "Model completed")
    # Reconstruct the immediately previous schema; reopening must migrate without losing events.
    with store.db:
        store.db.execute("DROP TABLE assessments")
        store.db.execute("PRAGMA user_version=1")
    reopened = Store(store.path, credentials, recover=False)
    assert reopened.db.execute("PRAGMA user_version").fetchone()[0] == 4
    assert reopened.events(sid)
    reopened.assess(sid, "needs_work", "The command passed, but the feature is incomplete.")
    assert reopened.assessment(sid)["label"] == "needs_work"
    assert reopened.metrics()["user_assessments"] == {"needs_work": 1}
    output = tmp_path / "assessed.json"
    reopened.export(sid, output)
    assert json.loads(output.read_text())["user_assessment"]["label"] == "needs_work"
    reopened.delete_session(sid)
    assert reopened.assessment(sid) is None
    reopened.close()


def test_redaction_preserves_nested_json_and_escaped_secrets(store, credentials, tmp_path):
    secret = 'secret-with-quote"and\\slash'
    credentials._values["TEST_KEY"] = secret
    sid = store.start(Agent(), tmp_path, True)
    store.event(
        sid,
        "nested",
        {"message": "api_key=unregistered", "nested": {"authorization": "unknown", "error": secret}},
    )
    store.messages(sid, [{"role": "user", "content": "password=unregistered " + secret}])
    event = store.events(sid)[-1]["data"]
    assert event["nested"]["authorization"] == "[REDACTED]"
    assert secret not in event["nested"]["error"]
    assert "REDACTED" in store.messages(sid)[0]["content"]
    out = tmp_path / "safe.json"
    store.export(sid, out)
    assert json.loads(out.read_text())["events"]
    assert secret not in out.read_text()


def test_loaded_credentials_are_removed_from_model_task(store, credentials, tmp_path):
    credentials._values["TEST_KEY"] = "private-loaded-key-12345"
    store.save_profile(Profile(id="ollama", name="Ollama"))
    seen = []

    class InspectProvider:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            seen.extend(messages)
            return Reply(content="Done")

    Runtime(store, credentials, InspectProvider).run(
        Agent(), tmp_path, "Never send private-loaded-key-12345", lambda *a: True
    )
    assert "private-loaded-key-12345" not in json.dumps(seen)


def test_dotenv_nonsecret_settings_do_not_corrupt_model_configuration(store, credentials, tmp_path):
    source = tmp_path / "settings.env"
    source.write_text(
        "OLLAMA_MODEL=qwen2.5-coder:14b\nCUSTOM_CREDENTIAL=opaque-credential-value\n", encoding="utf-8"
    )
    credentials.load_env(source)
    agent = Agent(primary=ModelRef(profile_id="ollama", model="qwen2.5-coder:14b"))
    assert store.save_agent(agent).primary.model == "qwen2.5-coder:14b"
    assert credentials.get("CUSTOM_CREDENTIAL") == "opaque-credential-value"
    assert credentials.redact("opaque-credential-value") == "[REDACTED]"
