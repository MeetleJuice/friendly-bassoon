"""Task-specific acceptance, wrong-target protection and missing-final regressions."""

import json
import threading
import pytest
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.runtime import Runtime
from aigentics.tools import Workspace, ToolRunner
from aigentics.task_checks import TaskChecks, TaskEvidence, suggested_targets, public_task_checks
from aigentics.evidence import run_report
from aigentics.reporting import public_report, issue_body, prepare_browser_draft


def call(name, **arguments):
    return ToolCall(id=name, name=name, arguments=arguments)


def exercise(store, credentials, tmp_path, replies, checks=None):
    store.save_profile(Profile(id="ollama", name="Fixture"))
    requests, approvals = [], []

    class Fixture:
        def __init__(self, *args):
            self.last_http_status = 200

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            requests.append(messages)
            result = replies[len(requests) - 1]
            return result() if callable(result) else result

    runtime = Runtime(store, credentials, Fixture)
    sid, state = runtime.run(
        Agent(), tmp_path, "Synthetic task", lambda *args: approvals.append(args) or True, task_checks=checks
    )
    summary = next(e["data"] for e in store.events(sid) if e["kind"] == "run.summary")
    return sid, state, summary, requests, approvals


@pytest.mark.parametrize(
    "task,expected",
    [
        ("Create output.py containing a square function.", ["output.py"]),
        ("Create output.py containing a square function. Read it back. Do not run commands.", ["output.py"]),
        ("Create a new file named `new_file.py` containing valid code.", ["new_file.py"]),
        ("Please update src/main.py.", ["src/main.py"]),
        ("Create output.py using input.py", []),
        ("Create a.py and b.py", []),
        ("Read source.py and explain it", []),
        ("Plan only: create source.py", []),
        ("Create source.py but do not modify any files", []),
        ("Explain why an old response said Create wrong.py", []),
    ],
)
def test_suggestions_are_narrow_visible_candidates(task, expected):
    assert suggested_targets(task) == expected


def test_wrong_existing_target_blocked_before_approval_even_if_unchanged(store, credentials, tmp_path):
    (tmp_path / "existing.py").write_text("value = 1\n")
    replies = [
        Reply(calls=[call("write_file", path="existing.py", content="value = 1\n", expected_sha256="new")]),
        Reply(content="The requested new file is verified."),
    ]
    sid, state, summary, requests, approvals = exercise(
        store, credentials, tmp_path, replies, TaskChecks(write_targets=["expected.py"])
    )
    assert state == "needs_review" and approvals == [] and len(requests) == 2
    assert (tmp_path / "existing.py").read_text() == "value = 1\n"
    assert not (tmp_path / "expected.py").exists()
    assert summary["task_checks"]["missing_writes"] == 1
    assert summary["tools"]["write_target_mismatches"] == 1
    assert any(e["data"].get("code") == "WRITE_TARGET_MISMATCH" for e in store.events(sid))


def test_matching_write_and_independent_read_pass_but_do_not_verify_user_goal(store, credentials, tmp_path):
    replies = [
        Reply(
            calls=[
                call("write_file", path="expected.py", content="value = 1\n", expected_sha256="new"),
                call("read_file", path="expected.py"),
            ]
        ),
        Reply(content="Saved and read back; not run."),
    ]
    sid, state, summary, requests, approvals = exercise(
        store,
        credentials,
        tmp_path,
        replies,
        TaskChecks(write_targets=["expected.py"], required_tools=["write_file", "read_file"]),
    )
    assert state == "completed" and len(approvals) == 1
    assert summary["task_checks"]["status"] == "passed"
    assert summary["task_checks"]["readback_files"] == 1
    assert summary["goal_verification"] == "not_evaluated"
    assert "Application task checks:" in requests[0][0]["content"]
    assert run_report(store, sid)["state"] == "needs_attention"  # user acceptance remains separate


def test_read_before_latest_write_is_not_readback(store, credentials, tmp_path):
    (tmp_path / "file.txt").write_text("before")
    replies = [
        Reply(
            calls=[
                call("read_file", path="file.txt"),
                call("write_file", path="file.txt", content="after", expected_sha256="last_read"),
            ]
        ),
        Reply(content="Everything verified."),
    ]
    _, state, summary, _, _ = exercise(
        store, credentials, tmp_path, replies, TaskChecks(write_targets=["file.txt"])
    )
    assert state == "needs_review"
    assert summary["task_checks"]["missing_readbacks"] == 1
    assert summary["tools"]["writes_verified"] == 1


def test_external_change_invalidates_completed_readback(store, credentials, tmp_path):
    def final():
        (tmp_path / "file.txt").write_text("external change")
        return Reply(content="Done")

    replies = [
        Reply(
            calls=[
                call("write_file", path="file.txt", content="saved", expected_sha256="new"),
                call("read_file", path="file.txt"),
            ]
        ),
        final,
    ]
    _, state, summary, _, _ = exercise(
        store, credentials, tmp_path, replies, TaskChecks(write_targets=["file.txt"])
    )
    assert state == "needs_review" and summary["task_checks"]["revision_mismatches"] == 1


def test_claimed_required_tools_without_calls_cannot_pass(store, credentials, tmp_path):
    _, state, summary, requests, _ = exercise(
        store,
        credentials,
        tmp_path,
        [Reply(content="I inspected the files using list_files and project_map. All verified.")],
        TaskChecks(require_tools=True, required_tools=["list_files", "project_map"]),
    )
    assert state == "needs_review" and len(requests) == 1
    assert summary["task_checks"]["missing_tools"] == 2
    assert summary["tools"]["requested"] == 0


def test_empty_final_preserves_success_without_replay_or_thinking_substitution(store, credentials, tmp_path):
    replies = [
        Reply(
            calls=[
                call("write_file", path="saved.py", content="value = 1\n", expected_sha256="new"),
                call("read_file", path="saved.py"),
            ]
        ),
        Reply(evidence={"thinking_chars": 500, "finish_reason": "stop"}),
    ]
    sid, state, summary, requests, approvals = exercise(
        store, credentials, tmp_path, replies, TaskChecks(write_targets=["saved.py"])
    )
    assert state == "incomplete_response" and len(requests) == 2 and len(approvals) == 1
    assert summary["task_checks"]["status"] == "passed"
    assert summary["tools"]["writes_verified"] == 1
    assert summary["tools"]["empty_final_responses"] == 1
    assert summary["final_response_status"] == "missing"
    assert (tmp_path / "saved.py").read_text() == "value = 1\n"
    report = run_report(store, sid)
    evidence = public_report(report)["checks"][0]["evidence"]
    assert evidence["final_response_status"] == "missing"
    assert report["recent_runs"]["failure_stages"] == {"final_response": 1}


def test_empty_final_without_actions_is_explicit_partial_not_success(store, credentials, tmp_path):
    _, state, summary, requests, _ = exercise(store, credentials, tmp_path, [Reply()])
    assert state == "incomplete_response" and len(requests) == 1
    assert summary["tools"]["requested"] == 0
    assert summary["final_response_status"] == "missing"


def test_unchanged_write_does_not_rewrite_or_ask_approval(tmp_path):
    source = tmp_path / "same.py"
    source.write_bytes(b"value = 1\r\n")
    before = source.stat().st_mtime_ns
    approvals = []
    runner = ToolRunner(
        Workspace(tmp_path), Agent(), lambda *args: approvals.append(args) or False, threading.Event()
    )
    runner.execute(call("read_file", path="same.py"))
    result = runner.execute(
        call("write_file", path="same.py", content="value = 1\r\n", expected_sha256="last_read")
    )
    assert result["unchanged"] and result["python_check"]["status"] == "passed"
    assert approvals == [] and source.stat().st_mtime_ns == before


def test_unchanged_write_does_not_satisfy_expected_write(store, credentials, tmp_path):
    (tmp_path / "same.txt").write_text("same")
    replies = [
        Reply(
            calls=[
                call("read_file", path="same.txt"),
                call("write_file", path="same.txt", content="same", expected_sha256="last_read"),
            ]
        ),
        Reply(content="Done"),
    ]
    _, state, summary, _, approvals = exercise(
        store, credentials, tmp_path, replies, TaskChecks(write_targets=["same.txt"])
    )
    assert state == "needs_review" and approvals == []
    assert summary["tools"]["unchanged_writes"] == 1
    assert summary["tools"]["writes_verified"] == 0


def test_contracts_preserve_protected_paths_and_permission_checks(tmp_path):
    ws = Workspace(tmp_path)
    for target in ("../escape.py", ".env", ".git/config"):
        with pytest.raises(PermissionError):
            TaskEvidence(ws, TaskChecks(write_targets=[target]))
    runner = ToolRunner(ws, Agent(allow_writes=False), lambda *args: True, threading.Event(), ["allowed.py"])
    with pytest.raises(PermissionError):
        runner.execute(call("write_file", path="allowed.py", content="x=1", expected_sha256="new"))
    assert not (tmp_path / "allowed.py").exists()


def test_public_contracts_and_reports_never_include_target_names(store, credentials, tmp_path):
    sid, _, _, _, _ = exercise(
        store,
        credentials,
        tmp_path,
        [Reply(content="No action")],
        TaskChecks(write_targets=["private_target.py"], required_tools=["read_file"]),
    )
    report = run_report(store, sid)
    payload = json.dumps(public_report(report))
    assert "private_target" not in payload and str(tmp_path) not in payload and sid not in payload
    title, body = issue_body(report, credentials)
    assert len(prepare_browser_draft(title, body)) <= 7500
    assert public_task_checks(
        {"unmet_targets": ["private"], "status": "PRIVATE", "expected_files": True}
    ) == {"status": "not_recorded"}


def test_visible_suggestion_can_be_overridden_and_fresh_context_is_default(
    qtbot, store, credentials, tmp_path
):
    from aigentics.ui import Window

    window = Window(store, credentials, startup=False)
    qtbot.addWidget(window)
    window.task.setPlainText("Create requested.py containing a function.")
    assert window.expected_files.text() == "requested.py"
    window.expected_files.setText("explicit.py")
    window.task.setPlainText("Create different.py containing a function.")
    assert window.expected_files.text() == "explicit.py"
    assert window.conversation_mode.currentData() == "fresh"
    window.new_conversation()
    assert window.expected_files.text() == "different.py"
    assert not window.required_task_tools
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_fresh_and_continued_context_are_explicit_in_runtime_evidence(store, credentials, tmp_path):
    store.save_profile(Profile(id="ollama", name="Fixture"))

    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            return Reply(content="Conversation response only.")

    runtime = Runtime(store, credentials, Fixture)
    first, _ = runtime.run(Agent(), tmp_path, "First", lambda *args: False)
    fresh, _ = runtime.run(Agent(), tmp_path, "Second", lambda *args: False)
    continued, _ = runtime.run(Agent(), tmp_path, "Third", lambda *args: False, parent=first)

    def context(sid):
        return next(e["data"] for e in store.events(sid) if e["kind"] == "task.context")

    assert context(fresh)["source"] == "fresh" and context(fresh)["history_messages"] == 0
    assert context(continued)["source"] == "continued" and context(continued)["history_messages"] == 2


def test_noop_write_preserves_scope_and_does_not_satisfy_readback_after_new_write(tmp_path):
    ws = Workspace(tmp_path)
    checks = TaskChecks(write_targets=["file.txt"])
    evidence = TaskEvidence(ws, checks)
    runner = ToolRunner(ws, Agent(), lambda *args: True, threading.Event(), checks.write_targets)
    for operation in [
        call("write_file", path="file.txt", content="first", expected_sha256="new"),
        call("read_file", path="file.txt"),
        call("write_file", path="file.txt", content="second", expected_sha256="last_read"),
    ]:
        evidence.record(operation, runner.execute(operation), "succeeded")
    assert evidence.evaluate()[0]["missing_readbacks"] == 1


def test_successful_http_status_is_retained_in_runtime_and_health_evidence(store, credentials, tmp_path):
    from aigentics.diagnostics import model_evidence

    sid, _, _, _, _ = exercise(store, credentials, tmp_path, [Reply(content="No tools requested")])
    assert model_evidence(store.events(sid))["http_status"] == 200


def test_impossible_checks_stop_before_any_provider_or_session(store, credentials, tmp_path):
    with pytest.raises(ValueError, match="disabled tool"):
        Runtime(store, credentials).run(
            Agent(allow_commands=False),
            tmp_path,
            "No generation",
            lambda *args: True,
            task_checks=TaskChecks(required_tools=["run_command"]),
        )
    assert not store.sessions()


def test_workbench_dispatches_fresh_by_default_and_continues_only_when_selected(
    qtbot, store, credentials, tmp_path
):
    from aigentics.ui import Window

    window = Window(store, credentials, startup=False)
    qtbot.addWidget(window)
    window.select_workspace(tmp_path)

    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            return Reply(content="A response without file operations.")

    window.runtime = Runtime(store, credentials, Fixture)

    def run(text):
        previous = len(store.sessions())
        window.task.setPlainText(text)
        window.start_run()
        qtbot.waitUntil(
            lambda: len(store.sessions()) > previous and store.sessions()[0]["state"] != "running",
            timeout=5000,
        )
        qtbot.waitUntil(lambda: not window.worker.isRunning() and window.work_run.isEnabled(), timeout=5000)
        return next(e["data"] for e in store.events(store.sessions()[0]["id"]) if e["kind"] == "task.context")

    assert run("First exchange")["source"] == "fresh"
    assert run("Second exchange")["history_messages"] == 0
    window.conversation_mode.setCurrentIndex(1)
    assert run("Third exchange")["source"] == "continued"
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_noop_static_check_cannot_certify_a_different_revision(tmp_path, monkeypatch):
    import aigentics.tools as tools

    (tmp_path / "same.py").write_bytes(b"value = 1\n")
    ws = Workspace(tmp_path)
    runner = ToolRunner(ws, Agent(), lambda *args: False, threading.Event())
    runner.execute(call("read_file", path="same.py"))
    monkeypatch.setattr(
        tools,
        "check_python",
        lambda *args: {"status": "passed", "code": "PYTHON_STATIC_OK", "sha256": "f" * 64},
    )
    result = runner.execute(
        call("write_file", path="same.py", content="value = 1\n", expected_sha256="last_read")
    )
    assert result["unchanged"] and result["python_check"]["code"] == "CHECK_REVISION_CHANGED"
    assert result["python_check"]["status"] == "failed"
