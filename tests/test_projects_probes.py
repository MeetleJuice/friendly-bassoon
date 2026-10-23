import json
import re
import threading
from contextlib import closing
import httpx
import pytest
from aigentics.models import Agent, Profile, ModelRef
from aigentics.providers import Provider, ProviderError
from aigentics.probes import ToolProbe, connection_signature
from aigentics.projects import Projects
from aigentics.store import Store


def setup(store, *, remote=False, **changes):
    profile = Profile(
        id="test",
        name="Test provider",
        kind="openai" if remote else "ollama",
        base_url="https://api.example/v1" if remote else "http://127.0.0.1:11434",
        **changes,
    )
    store.save_profile(profile)
    agent = store.save_agent(Agent(primary=ModelRef(profile_id=profile.id, model="fixture-model")))
    return profile, agent


def provider_factory(handler):
    return lambda p, c: Provider(p, c, httpx.MockTransport(handler))


def answer(request, *, prose=False, mismatch=False):
    body = json.loads(request.content)
    nonce = re.search(r"challenge '([^']+)'", body["messages"][-1]["content"])[1]
    args = {"challenge": "wrong" if mismatch else nonce}
    function = {"name": "report_probe", "arguments": args}
    native = request.url.path == "/api/chat"
    message = (
        {"content": json.dumps(function)}
        if prose
        else {
            "content": "",
            "tool_calls": [
                {
                    "id": "test-call",
                    "type": "function",
                    "function": function if native else function | {"arguments": json.dumps(args)},
                }
            ],
        }
    )
    if body["stream"]:
        if native:
            content = json.dumps({"message": message, "done": True, "done_reason": "stop"}) + "\n"
        else:
            delta = message.copy()
            if "tool_calls" in delta:
                delta["tool_calls"][0]["index"] = 0
            content = (
                "data: "
                + json.dumps({"choices": [{"delta": delta, "finish_reason": "stop"}]})
                + "\n\ndata: [DONE]\n\n"
            )
        return httpx.Response(200, content=content)
    return httpx.Response(
        200,
        json={"message": message, "done_reason": "stop"}
        if native
        else {"choices": [{"message": message, "finish_reason": "stop"}]},
    )


def test_remote_probe_requires_consent_before_any_call_or_record(store, credentials):
    _, agent = setup(store, remote=True)
    calls = []
    runner = ToolProbe(store, credentials, provider_factory(lambda r: calls.append(r) or answer(r)))
    with pytest.raises(PermissionError):
        runner.run(agent.id)
    assert not calls and not store.diagnostic_reports()
    report = runner.run(agent.id, allow_cloud=True)
    assert len(calls) == 1 and report["state"] == "passed"
    body = json.loads(calls[0].content)
    assert body["max_tokens"] == 96 and len(body["tools"]) == 1
    assert body["tools"][0]["function"]["name"] == "report_probe"
    assert report["checks"][0]["evidence"]["generation_requests"] == 1
    assert not store.sessions()


def test_local_matrix_matches_parameters_and_preserves_native_semantics(store, credentials):
    profile, agent = setup(store)
    calls = []

    def handle(request):
        calls.append(request)
        body = json.loads(request.content)
        assert (body.get("options", {}).get("temperature", body.get("temperature"))) == 0.2
        assert (body.get("options", {}).get("num_predict", body.get("max_tokens"))) == 96
        return answer(request)

    report = ToolProbe(store, credentials, provider_factory(handle)).run(agent.id, compare_routes=True)
    assert report["summary"]["passed"] == 4 and len(calls) == 4
    assert {c["id"] for c in report["checks"]} == {
        "native_tool_probe",
        "native_stream_tool_probe",
        "compatible_tool_probe",
        "compatible_stream_tool_probe",
    }
    assert all(
        c["evidence"]["http_status"] == 200 and c["evidence"]["challenge_verified"] for c in report["checks"]
    )
    assert store.profiles()[0].ollama_api == profile.ollama_api and not store.profiles()[0].ollama_stream


def test_probe_prose_is_distinct_never_executed(store, credentials, monkeypatch):
    from aigentics.tools import ToolRunner

    _, agent = setup(store)
    monkeypatch.setattr(
        ToolRunner, "execute", lambda *a: pytest.fail("A probe must not execute host/project tools")
    )
    report = ToolProbe(store, credentials, provider_factory(lambda r: answer(r, prose=True))).run(agent.id)
    check = report["checks"][0]
    assert check["code"] == "TEXT_TOOL_RESPONSE" and check["evidence"]["text_tool_response"]
    assert not check["evidence"]["challenge_verified"]
    assert "challenge '" not in json.dumps(report)


def test_native_argument_mismatch_is_not_a_pass(store, credentials):
    _, agent = setup(store)
    check = ToolProbe(store, credentials, provider_factory(lambda r: answer(r, mismatch=True))).run(agent.id)[
        "checks"
    ][0]
    assert check["code"] == "NATIVE_ARGUMENT_MISMATCH" and check["evidence"]["native_calls_total"] == 1


@pytest.mark.parametrize("stream", [False, True])
def test_protocol_failure_keeps_actual_http_200(store, credentials, stream):
    _, agent = setup(store, ollama_stream=stream)
    report = ToolProbe(
        store,
        credentials,
        provider_factory(lambda r: httpx.Response(200, content="private invalid response")),
    ).run(agent.id)
    evidence = report["checks"][0]["evidence"]
    assert evidence["http_status"] == 200 and evidence["generation_requests"] == 1
    assert "private invalid response" not in json.dumps(report)


@pytest.mark.parametrize("blocked", ["tools", "credential"])
def test_preflight_failures_do_not_count_a_dispatched_generation(store, credentials, monkeypatch, blocked):
    _, agent = setup(
        store,
        supports_tools=blocked != "tools",
        credential_ref="MISSING_KEY" if blocked == "credential" else "",
    )
    monkeypatch.setattr(
        credentials, "get", lambda ref: (_ for _ in ()).throw(ValueError("private credential detail"))
    )
    calls = []
    report = ToolProbe(store, credentials, provider_factory(lambda r: calls.append(r) or answer(r))).run(
        agent.id
    )
    assert report["checks"][0]["evidence"]["generation_requests"] == 0 and not calls
    assert "private credential detail" not in json.dumps(report)


def test_cancelled_probe_makes_no_request_and_remote_matrix_is_forbidden(store, credentials):
    _, agent = setup(store)
    cancel = threading.Event()
    cancel.set()
    calls = []
    report = ToolProbe(store, credentials, provider_factory(lambda r: calls.append(r))).run(agent.id, cancel)
    assert report["state"] == "cancelled" and not calls
    _, remote = setup(store, remote=True)
    with pytest.raises(ValueError):
        ToolProbe(store, credentials).run(remote.id, allow_cloud=True, compare_routes=True)


def test_native_response_type_and_truncation_are_rejected(credentials):
    for payload in (
        {"message": {"tool_calls": [{"type": "other", "function": {"name": "read_file", "arguments": {}}}]}},
        {
            "done_reason": "length",
            "message": {"tool_calls": [{"function": {"name": "read_file", "arguments": {}}}]},
        },
    ):
        p = Provider(
            Profile(id="local", name="Local"),
            credentials,
            httpx.MockTransport(lambda r: httpx.Response(200, json=payload)),
        )
        with pytest.raises(ProviderError):
            p.chat("fixture", [], [])


def test_active_ollama_parser_metadata_is_retained_without_template_contents(credentials):
    payload = {
        "capabilities": ["tools"],
        "template": "private template",
        "parser": "qwen3",
        "renderer": "",
        "template_source": "gguf_chat_template",
    }
    p = Provider(
        Profile(id="local", name="Local"),
        credentials,
        httpx.MockTransport(lambda r: httpx.Response(200, json=payload)),
    )
    evidence = p.capabilities("fixture")
    assert evidence["parser"] == "qwen3" and evidence["template_source"] == "gguf_chat_template"
    assert "private template" not in json.dumps(evidence)


def test_remember_projects_briefs_forget_and_upgrade_preserves_existing_records(store, credentials, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "source.py").write_text("print('hello')")
    project = Projects(store).remember(root, brief="Build a small app and check its files.")
    assert Projects(store).remember(root)["id"] == project["id"]
    assert Projects(store).recent()[0]["brief"].startswith("Build")
    sid = store.start(Agent(), root)
    store.finish(sid, "completed", "done")
    assert Projects(store).sessions(root)[0]["id"] == sid
    Projects(store).forget(project["id"])
    assert not Projects(store).recent() and (root / "source.py").exists() and store.sessions()
    with store.db:
        store.db.execute("DROP TABLE projects")
        store.db.execute("PRAGMA user_version=4")
    with closing(Store(store.path, credentials, recover=False)) as migrated:
        assert migrated.db.execute("PRAGMA user_version").fetchone()[0] == 5
        assert migrated.sessions()[0]["id"] == sid
        assert Projects(migrated).recent() == []


def test_project_brief_rejects_known_credentials(store, credentials, tmp_path):
    credentials._values["EXAMPLE_API_KEY"] = "fixture-secret-value"
    with pytest.raises(ValueError):
        Projects(store).remember(tmp_path, brief="use fixture-secret-value")


def test_project_ui_preview_switching_and_unchanged_source_add(qtbot, store, credentials, tmp_path):
    from aigentics.ui import Window

    root = tmp_path / "a"
    root.mkdir()
    (root / "source.py").write_text("def discover_models():\n    return 'catalog'\n")
    other = tmp_path / "b"
    other.mkdir()
    window = Window(store, credentials)
    qtbot.addWidget(window)
    window.select_workspace(root)
    panel = window.project_panel
    panel.query.setText("discover_models")
    panel.preview(True)
    qtbot.waitUntil(lambda: panel.last_context is not None, timeout=5000)
    qtbot.waitUntil(lambda: not window.worker.isRunning(), timeout=5000)
    qtbot.waitUntil(lambda: window.work_run.isEnabled(), timeout=5000)
    panel.add_to_task()
    assert "source.py:" in window.task.toPlainText()
    window.select_workspace(other)
    assert panel.last_context is None
    assert window.project_history.isChecked()
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_probe_ui_reuses_scoped_results_and_confirms_route_change(qtbot, store, credentials, monkeypatch):
    from aigentics.ui import Window
    from aigentics.probe_ui import ProbeDialog
    from PySide6.QtWidgets import QMessageBox

    profile, agent = setup(store, ollama_stream=True)
    report = ToolProbe(store, credentials, provider_factory(answer)).run(agent.id)
    window = Window(store, credentials)
    qtbot.addWidget(window)
    dialog = ProbeDialog(window)
    qtbot.addWidget(dialog)
    assert dialog.report and dialog.report["id"] == report["id"]
    assert "Retained probe" in dialog.status.text()
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *args: asked.append(args) or QMessageBox.No)
    dialog.apply_route()
    assert asked and connection_signature(store.profiles()[0]) == connection_signature(profile)
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_retained_probe_does_not_apply_to_an_alias_profile_or_different_model(qtbot, store, credentials):
    from aigentics.ui import Window
    from aigentics.probe_ui import ProbeDialog
    from aigentics.diagnostics_ui import DiagnosticsDialog

    profile, agent = setup(store)
    report = ToolProbe(store, credentials, provider_factory(answer)).run(agent.id)
    alias = profile.model_copy(update={"id": "alias", "name": "Alias"})
    store.save_profile(alias)
    other = store.save_agent(
        Agent(name="Other", primary=ModelRef(profile_id="alias", model=agent.primary.model))
    )
    window = Window(store, credentials)
    qtbot.addWidget(window)
    dialog = ProbeDialog(window)
    qtbot.addWidget(dialog)
    dialog.agents.setCurrentIndex(dialog.agents.findData(other.id))
    assert dialog.report is None and not dialog.apply_button.isEnabled()
    assert not dialog.cloud.isEnabled()
    history = DiagnosticsDialog(window, prompts=False)
    qtbot.addWidget(history)
    history.rows = [{"payload": report}]
    changed = report | {"id": "later", "created": "2099-01-01T00:00:00+00:00", "model": "another-model"}
    assert "No earlier comparable report" in history.comparison(changed)
    window.lab_dir.cleanup()
    window.store.close = lambda: None
