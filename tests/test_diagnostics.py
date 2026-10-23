import json
import threading
import httpx
import pytest
from aigentics.diagnostics import DiagnosticRunner, ScriptedProvider
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.runtime import Runtime, looks_like_text_tool_call
from aigentics.store import Store
from aigentics.reporting import (
    GitHubReporter,
    ReportingError,
    SubmissionUnknown,
    issue_body,
    public_report,
    browser_draft,
    prepare_browser_draft,
)


def setup_profile(store):
    store.save_profile(Profile(id="ollama", name="Local Ollama"))
    store.save_agent(Agent())


def test_observed_text_tool_response_is_never_executed(store, credentials, tmp_path):
    setup_profile(store)
    responses = []

    class TextOnly:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            responses.append(messages[-1]["content"])
            return Reply(content='{"name": "list_files", "arguments": {"path": ""}}')

    sid, state = Runtime(store, credentials, TextOnly).run(
        Agent(), tmp_path, "Create hello.py", lambda *args: True
    )
    assert state == "protocol_error"
    assert len(responses) == 3
    assert "Runtime feedback:" in responses[1]
    events = store.events(sid)
    assert len([e for e in events if e["kind"] == "protocol.retry_requested"]) == 2
    assert not any(e["kind"] == "tool.requested" for e in events)
    assert not (tmp_path / "hello.py").exists()
    request = next(e["data"] for e in events if e["kind"] == "model.requested")
    assert "write_file" in request["tools_advertised"]
    assert request["tool_schema_sha256"] and request["message_roles"] == ["system", "user"]


def test_recovery_uses_native_calls_and_preserves_approval(store, credentials, tmp_path):
    setup_profile(store)

    class Recover:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            if not any(m["role"] == "assistant" for m in messages):
                return Reply(content='{"name":"write_file","arguments":{"path":"hello.py","content":"fake"}}')
            if not any(m["role"] == "tool" for m in messages):
                return Reply(
                    calls=[
                        ToolCall(
                            id="native",
                            name="write_file",
                            arguments={
                                "path": "hello.py",
                                "content": "print('real')\n",
                                "expected_sha256": "new",
                            },
                        )
                    ]
                )
            return Reply(content="Finished")

    approvals = []
    sid, state = Runtime(store, credentials, Recover).run(
        Agent(), tmp_path, "Create hello.py", lambda kind, details: approvals.append(details["diff"]) or False
    )
    assert state == "needs_review"
    assert len(approvals) == 1 and "print('real')" in approvals[0]
    assert not (tmp_path / "hello.py").exists()
    assert any(e["kind"] == "permission.decided" and not e["data"]["approved"] for e in store.events(sid))


def test_plain_conversation_is_response_only_not_verified_coding(store, credentials, tmp_path):
    setup_profile(store)

    class Chat:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, *args):
            return Reply(content="A Python function groups reusable statements.")

    sid, state = Runtime(store, credentials, Chat).run(
        Agent(), tmp_path, "Explain functions", lambda *a: True
    )
    assert state == "response_only"
    assert not any(e["kind"] == "protocol.retry_requested" for e in store.events(sid))


@pytest.mark.parametrize(
    "text,expected",
    [
        ('{"name":"list_files","arguments":{}}', True),
        ('```json\n{"name":"read_file","arguments":{"path":"x"}}\n```', True),
        ('<tool_call>{"function":{"name":"read_file","arguments":{}}}</tool_call>', True),
        ('{"name":"Alice","arguments":{}}', False),
        ('Here is an example: {"name":"read_file","arguments":{}}', False),
        ("[1, 2, 3]", False),
    ],
)
def test_protocol_shape_detection_is_narrow_and_non_executing(text, expected):
    assert looks_like_text_tool_call(text) is expected


def test_packaged_health_suite_runs_without_pytest_or_user_project(store, credentials, tmp_path):
    setup_profile(store)
    project = tmp_path / "user-project"
    project.mkdir()
    (project / "private.txt").write_text("private project data")
    report = DiagnosticRunner(store, credentials).run(threading.Event(), include_network=False)
    assert report["state"] == "passed"
    assert report["summary"] == {"passed": 19, "failed": 0, "warning": 0, "skipped": 0}
    assert (project / "private.txt").read_text() == "private project data"
    payload = store.diagnostic_reports()[0]["payload"]
    assert payload["id"] == report["id"]
    assert "private project data" not in json.dumps(payload)
    assert str(tmp_path) not in json.dumps(payload)
    assert any(
        r["id"] == "text_tool_regression" and r["evidence"]["text_never_executed"] for r in report["checks"]
    )
    for identity, flag in (
        ("tool_registry_fixture", "registry_fixture_verified"),
        ("project_retrieval_fixture", "project_retrieval_fixture_verified"),
        ("native_probe_fixture", "probe_fixture_verified"),
    ):
        assert any(row["id"] == identity and row["evidence"][flag] for row in report["checks"])


def test_optional_real_model_check_verifies_files_with_controlled_provider(store, credentials):
    setup_profile(store)
    report = DiagnosticRunner(store, credentials, ScriptedProvider).run(
        threading.Event(), agent=store.agents()[0], include_model=True, include_network=False
    )
    row = next(r for r in report["checks"] if r["id"] == "selected_local_model")
    assert (
        row["status"] == "passed" and row["evidence"]["file_matches"] and row["evidence"]["readback_recorded"]
    )


def test_cloud_model_is_skipped_and_network_failures_are_warnings(store, credentials):
    from aigentics.models import ModelRef

    store.save_profile(Profile(id="cloud", name="Cloud", kind="openai", base_url="https://example.com/v1"))
    agent = Agent(primary=ModelRef(profile_id="cloud", model="paid-model"))
    store.save_agent(agent)

    class Unavailable:
        def check(self, *args):
            raise ConnectionError("sensitive private request content")

    report = DiagnosticRunner(store, credentials, updater=Unavailable()).run(
        threading.Event(), agent=agent, include_model=True, include_network=True
    )
    assert report["summary"]["warning"] == 1 and report["summary"]["skipped"] == 1
    assert "sensitive private request content" not in json.dumps(report)


def example_report():
    return {
        "schema_version": 1,
        "suite_version": "1",
        "id": "report-123",
        "created": "2026-10-23",
        "app_version": "0.3.0",
        "state": "needs_attention",
        "environment": {"os": "Windows", "python": "3.12", "workspace": "C:/Users/private/project"},
        "summary": {"failed": 1},
        "checks": [
            {
                "id": "selected_local_model",
                "status": "failed",
                "code": "MODEL_WORKFLOW_NOT_VERIFIED",
                "message": "The selected model did not complete the verified tool workflow.",
                "duration_ms": 100,
                "evidence": {
                    "model": "my-private-model",
                    "runtime_state": "protocol_error",
                    "file_content": "private code",
                },
            }
        ],
        "recent_runs": {
            "states": {"protocol_error": 1},
            "tool_error_types": {},
            "protocol_failures": 1,
            "messages": ["private conversation"],
        },
        "raw_credentials": "not-allowed",
    }


def test_public_report_is_allowlisted_and_model_names_require_opt_in(credentials):
    report = example_report()
    value = public_report(report)
    encoded = json.dumps(value)
    assert "my-private-model" not in encoded
    assert "private code" not in encoded and "private conversation" not in encoded
    assert "C:/Users" not in encoded and "raw_credentials" not in encoded
    assert public_report(report, True)["checks"][0]["evidence"]["model"] == "my-private-model"
    title, body = issue_body(report, credentials)
    assert "report-123" in body and "private code" not in body


def test_sharing_requires_approval_and_uses_only_issues_endpoint(credentials):
    credentials._values["GITHUB_TOKEN"] = "fake-test-github-token-123456"
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(
            201, json={"html_url": "https://github.com/MeetleJuice/friendly-bassoon/issues/42"}
        )

    reporter = GitHubReporter(credentials, httpx.MockTransport(handle))
    with pytest.raises(ReportingError, match="approval"):
        reporter.submit("Title", "Body")
    assert not calls
    assert reporter.submit("Title", "Body", approved=True).endswith("/issues/42")
    assert str(calls[0].url) == "https://api.github.com/repos/MeetleJuice/friendly-bassoon/issues"
    assert calls[0].method == "POST"
    assert json.loads(calls[0].content) == {"title": "Title", "body": "Body"}
    assert credentials._values["GITHUB_TOKEN"] not in calls[0].content.decode()
    assert calls[0].headers["authorization"].startswith("Bearer ")


def test_unknown_submission_never_retries_and_secret_body_is_blocked(credentials):
    credentials._values["GITHUB_TOKEN"] = "fake-test-github-token-123456"
    count = []

    def fail(request):
        count.append(1)
        raise httpx.ReadTimeout("potential private body")

    reporter = GitHubReporter(credentials, httpx.MockTransport(fail))
    with pytest.raises(SubmissionUnknown):
        reporter.submit("Title", "Body", approved=True)
    assert len(count) == 1
    with pytest.raises(ReportingError, match="credential"):
        reporter.submit("Title", credentials._values["GITHUB_TOKEN"], approved=True)
    assert len(count) == 1


def test_browser_draft_is_bounded_and_requires_approval(credentials):
    from urllib.parse import urlsplit, parse_qs

    title, body = issue_body(example_report(), credentials)
    with pytest.raises(ReportingError):
        browser_draft(title, body)
    url = browser_draft(title, body, approved=True)
    assert url.startswith("https://github.com/MeetleJuice/friendly-bassoon/issues/new?")
    assert parse_qs(urlsplit(url).query)["body"][0] == body
    report = example_report()
    report["checks"] *= 15
    title, body = issue_body(report, credentials)
    bounded = prepare_browser_draft(title, body)
    assert len(bounded) <= 7500 and "report-123" in parse_qs(urlsplit(bounded).query)["body"][0]


def test_diagnostic_migration_retention_and_interrupted_recovery(store, credentials):
    report = example_report()
    report["state"] = "running"
    store.save_diagnostic(report)
    reopened = Store(store.path, credentials)
    assert reopened.diagnostic_reports()[0]["state"] == "interrupted"
    reopened.delete_diagnostic(report["id"])
    assert reopened.diagnostic_reports() == []
    reopened.close()
    for i in range(25):
        value = example_report()
        value["id"] = str(i)
        store.save_diagnostic(value)
    store.prune()
    assert len(store.diagnostic_reports()) == 20


def test_diagnostics_ui_completes_and_sharing_waits_for_approval(qtbot, store, credentials, monkeypatch):
    from aigentics.ui import Window
    from aigentics.diagnostics_ui import DiagnosticsDialog
    from PySide6.QtGui import QDesktopServices

    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)
    window = Window(store, credentials)
    qtbot.addWidget(window)
    dialog = DiagnosticsDialog(window, prompts=False)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.live.setChecked(False)
    dialog.network.setChecked(False)
    dialog.start()
    qtbot.waitUntil(lambda: dialog.report is not None and not dialog.busy(), timeout=10000)
    assert dialog.report["state"] == "passed"
    assert not opened and not dialog.approved.isChecked()
    dialog.review()
    dialog.submit()
    assert not opened
    dialog.approved.setChecked(True)
    dialog.submit()
    assert len(opened) == 1 and "issues/new?" in opened[0]
    row = store.diagnostic_reports()[0]
    assert row["submission_state"] == "draft_opened" and not row["submission_url"]
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_v2_database_migrates_without_losing_existing_history(store, credentials, tmp_path):
    from contextlib import closing

    store.save_profile(Profile(id="ollama", name="Local"))
    agent = store.save_agent(Agent())
    sid = store.start(agent, tmp_path, capture=True)
    store.messages(sid, [{"role": "user", "content": "preserve my history"}])
    store.finish(sid, "completed", "Original run")
    store.set_setting("keep", "original setting")
    with store.db:
        store.db.execute("DROP TABLE diagnostics")
        store.db.execute("PRAGMA user_version=2")
    with closing(Store(store.path, credentials)) as migrated:
        assert migrated.setting("keep", None) == "original setting"
        assert migrated.agents()[0].id == agent.id
        assert migrated.messages(sid)[0]["content"] == "preserve my history"
        assert migrated.diagnostic_reports() == []
        assert migrated.db.execute("PRAGMA user_version").fetchone()[0] == 5


def test_legacy_saved_text_tool_response_is_reported_as_count_not_content(store, tmp_path):
    from aigentics.diagnostics import safe_recent_summary

    sid = store.start(Agent(), tmp_path, capture=True)
    store.messages(
        sid,
        [
            {
                "role": "assistant",
                "content": '{"name":"list_files","arguments":{"path":"private-project-name"}}',
            }
        ],
    )
    store.finish(sid, "completed", "Legacy model turn ended")
    summary = safe_recent_summary(store)
    assert summary["legacy_text_tool_responses"] == 1
    assert "private-project-name" not in json.dumps(summary)


def test_github_token_value_cannot_be_used_as_a_reference(credentials):
    reporter = GitHubReporter(credentials)
    with pytest.raises(ReportingError, match="variable name"):
        reporter.submit("Title", "Body", token_ref="ghp_abcdefghijklmnopqrstuvwxyz", approved=True)


def test_report_edit_revokes_sharing_approval(qtbot, store, credentials):
    from aigentics.ui import Window
    from aigentics.diagnostics_ui import DiagnosticsDialog

    window = Window(store, credentials)
    qtbot.addWidget(window)
    dialog = DiagnosticsDialog(window, prompts=False)
    qtbot.addWidget(dialog)
    dialog.report = example_report()
    dialog.prepare_preview()
    dialog.approved.setChecked(True)
    dialog.preview.appendPlainText("A changed report needs fresh approval.")
    assert not dialog.approved.isChecked() and not dialog.send.isEnabled()
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_validator_failure_omits_private_input_and_stays_serializable(store, credentials, tmp_path):
    setup_profile(store)

    class InvalidWriter:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            if not any(m["role"] == "tool" for m in messages):
                return Reply(
                    calls=[
                        ToolCall(
                            id="invalid",
                            name="write_file",
                            arguments={
                                "path": "bad.txt",
                                "content": "private-content\x00",
                                "expected_sha256": "new",
                            },
                        )
                    ]
                )
            return Reply(content="The file was not written.")

    sid, state = Runtime(store, credentials, InvalidWriter).run(
        Agent(), tmp_path, "Write a file", lambda *args: True
    )
    assert state == "needs_review"
    assert not (tmp_path / "bad.txt").exists()
    events = store.events(sid)
    assert any(e["kind"] == "tool.result" and e["data"]["error_type"] == "ValidationError" for e in events)
    assert "private-content" not in json.dumps(events)
