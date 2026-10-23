"""Regressions from observed editing, validation and approved-report workflows."""

import json
import threading
import pytest
from aigentics.models import Agent, Reply, ToolCall, Profile
from aigentics.tools import Workspace, ToolRunner, StaleFileError
from aigentics.verification import check_python
from aigentics.runtime import Runtime
from aigentics.evidence import python_report, run_report, report_guidance
from aigentics.reporting import public_report, issue_body, prepare_browser_draft, recent_run_counts


def call(name, **arguments):
    return ToolCall(id="fixture", name=name, arguments=arguments)


@pytest.mark.parametrize(
    "source,code",
    [
        ("raise RuntimeError('never execute this')\n", "PYTHON_STATIC_OK"),
        ("return 3\n", "PYTHON_SYNTAX_ERROR"),
        ("def invalid(:\n", "PYTHON_SYNTAX_ERROR"),
        ("WIDTH, HEIGHT = 800, 60, 600\n", "LITERAL_UNPACK_MISMATCH"),
        ("first, *rest = 1, 2, 3\n", "PYTHON_STATIC_OK"),
        ("a, b = *values, 2\n", "PYTHON_STATIC_OK"),
    ],
)
def test_python_check_never_executes(tmp_path, source, code):
    (tmp_path / "game.py").write_text(source)
    result = check_python(Workspace(tmp_path), "game.py")
    assert result["code"] == code
    assert result["executed"] is False
    assert "content" not in result


def test_check_boundaries_and_no_side_effects(tmp_path):
    marker = tmp_path / "should-not-exist"
    (tmp_path / "game.py").write_text(f"open({str(marker)!r}, 'w').write('bad')\n")
    assert check_python(Workspace(tmp_path), "game.py")["status"] == "passed"
    assert not marker.exists()
    with pytest.raises(PermissionError):
        check_python(Workspace(tmp_path), "../outside.py")
    with pytest.raises(ValueError):
        check_python(Workspace(tmp_path), "readme.txt")


def test_last_read_requires_this_run_and_preserves_review_race_check(tmp_path):
    (tmp_path / "game.py").write_bytes(b"value = 1\r\n")
    ws = Workspace(tmp_path)
    approvals = []
    runner = ToolRunner(ws, Agent(), lambda *args: approvals.append(args) or True, threading.Event())
    write = call("write_file", path="game.py", content="value = 2\n", expected_sha256="last_read")
    with pytest.raises(StaleFileError):
        runner.execute(write)
    assert approvals == []
    runner.execute(call("read_file", path="./game.py"))
    result = runner.execute(write)
    assert result["verified"] and result["python_check"]["status"] == "passed"
    assert len(approvals) == 1
    # A successful write never silently refreshes the prior read revision.
    with pytest.raises(StaleFileError):
        runner.execute(write)
    runner.execute(call("read_file", path="game.py"))

    def race(*args):
        (tmp_path / "game.py").write_text("external = True\n")
        return True

    runner.approve = race
    with pytest.raises(StaleFileError):
        runner.execute(write)
    assert (tmp_path / "game.py").read_text() == "external = True\n"
    other = ToolRunner(ws, Agent(), lambda *args: True, threading.Event())
    with pytest.raises(StaleFileError):
        other.execute(write)


def scripted_runtime(store, credentials, tmp_path, steps, agent=None):
    store.save_profile(Profile(id="ollama", name="Fixture"))

    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            assert "Your agent name is George" in messages[0]["content"]
            index = sum(m["role"] == "tool" for m in messages)
            return (
                Reply(calls=[steps[index]])
                if index < len(steps)
                else Reply(content="Finished; behavior not tested.")
            )

    return Runtime(store, credentials, Fixture).run(
        agent or Agent(name="George"), tmp_path, "Edit the fixture", lambda *args: True
    )


def test_stale_edit_recovers_without_hiding_failure_history(store, credentials, tmp_path):
    (tmp_path / "game.py").write_text("value = 1\n")
    steps = [
        call("write_file", path="game.py", content="value = 2\n", expected_sha256="0" * 64),
        call("read_file", path="game.py"),
        call("write_file", path="game.py", content="value = 2\n", expected_sha256="last_read"),
    ]
    sid, state = scripted_runtime(store, credentials, tmp_path, steps)
    assert state == "completed"
    data = next(e["data"] for e in store.events(sid) if e["kind"] == "run.summary")
    assert data["tools"]["failed"] == data["tools"]["recovered_edit_errors"] == 1
    assert data["unresolved_tool_errors"] == 0
    assert data["tools"]["python_checks_passed"] == 1
    assert data["goal_verification"] == "not_evaluated"
    report = run_report(store, sid)
    assert report["checks"][0]["evidence"]["tool_error_codes"] == {"STALE_FILE": 1}


def test_invalid_python_saved_but_needs_review(store, credentials, tmp_path):
    sid, state = scripted_runtime(
        store,
        credentials,
        tmp_path,
        [call("write_file", path="game.py", content="WIDTH, HEIGHT = 800, 60, 600\n", expected_sha256="new")],
    )
    assert state == "needs_review"
    data = next(e["data"] for e in store.events(sid) if e["kind"] == "run.summary")
    assert data["tools"]["writes_verified"] == 1
    assert data["python_files_needing_attention"] == 1
    assert data["tools"]["commands_passed"] == 0


def test_unresolved_edit_not_cleared_by_other_file(store, credentials, tmp_path):
    (tmp_path / "existing.txt").write_text("original")
    _, state = scripted_runtime(
        store,
        credentials,
        tmp_path,
        [
            call("write_file", path="existing.txt", content="changed", expected_sha256="0" * 64),
            call("write_file", path="other.txt", content="new", expected_sha256="new"),
        ],
    )
    assert state == "needs_review"
    assert (tmp_path / "existing.txt").read_text() == "original"


def test_project_check_and_run_reports_exclude_content_paths_notes(store, credentials, tmp_path):
    (tmp_path / "private-name.py").write_text("private_name = 'private source'\n")
    report = python_report(store, Workspace(tmp_path), "private-name.py")
    public = json.dumps(public_report(report))
    assert "private-name" not in public and "private source" not in public
    assert report["local_sha256"] not in public
    sid, _ = scripted_runtime(store, credentials, tmp_path, [call("read_file", path="private-name.py")])
    store.assess(sid, "needs_work", "private assessment note")
    report = run_report(store, sid)
    public = json.dumps(public_report(report))
    assert "private" not in public and sid not in public and str(tmp_path) not in public
    assert report["state"] == "needs_attention"
    assert report["checks"][0]["evidence"]["user_assessment"] == "needs_work"
    assert "not_evaluated" not in report_guidance(report)  # reader-facing guidance
    title, body = issue_body(report, credentials)
    assert len(prepare_browser_draft(title, body)) <= 7500


def test_new_counters_strict_types_and_fixed_keys():
    result = recent_run_counts(
        {
            "execution_counts": {"writes_verified": 9, "failed": True, "private_name": 2},
            "tool_error_codes": {"STALE_FILE": 2, "private_code": 2},
            "user_assessments": {"goal_met": 1, "private_note": 1},
        }
    )
    assert result["execution_counts"] == {"writes_verified": 9}
    assert result["tool_error_codes"] == {"STALE_FILE": 2}
    assert result["user_assessments"] == {"goal_met": 1}


def test_plan_mode_removes_write_advertisement_and_blocks_native_write(qtbot, store, credentials, tmp_path):
    from aigentics.ui import Window

    window = Window(store, credentials, startup=False)
    qtbot.addWidget(window)
    window.select_workspace(tmp_path)
    window.task_mode.setCurrentIndex(1)
    window.task.setPlainText("Plan a game, without making changes")
    advertised = []

    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            advertised.extend(t["function"]["name"] for t in tools)
            assert "PLAN ONLY" in messages[0]["content"]
            if not any(m["role"] == "tool" for m in messages):
                return Reply(
                    calls=[call("write_file", path="forbidden.txt", content="no", expected_sha256="new")]
                )
            return Reply(content="Plan only; write was denied.")

    window.runtime = Runtime(store, credentials, Fixture)
    window.start_run()
    qtbot.waitUntil(
        lambda: bool(store.sessions()) and store.sessions()[0]["state"] != "running", timeout=5000
    )
    qtbot.waitUntil(lambda: not window.worker.isRunning(), timeout=5000)
    assert "write_file" not in advertised and "run_command" not in advertised
    assert not (tmp_path / "forbidden.txt").exists()
    assert store.agents()[0].allow_writes  # one-run mode never mutates saved agent
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_manual_python_check_opens_readable_report_without_provider(
    qtbot, store, credentials, tmp_path, monkeypatch
):
    from aigentics.ui import Window, QFileDialog

    window = Window(store, credentials, startup=False)
    qtbot.addWidget(window)
    window.select_workspace(tmp_path)
    source = tmp_path / "game.py"
    source.write_text("WIDTH, HEIGHT = 800, 60, 600\n")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(source), "Python (*.py)"))
    window.check_python_file()
    assert not store.sessions()
    assert window.diagnostics_dialog.report["kind"] == "python_check"
    assert "different number of values" in window.diagnostics_dialog.output.toPlainText()
    assert window.diagnostics_dialog.technical.isChecked() is False
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_read_reference_never_overrides_wrong_explicit_hash_or_denied_approval(tmp_path):
    (tmp_path / "file.txt").write_text("original")
    runner = ToolRunner(Workspace(tmp_path), Agent(), lambda *args: False, threading.Event())
    runner.execute(call("read_file", path="file.txt"))
    with pytest.raises(StaleFileError):
        runner.execute(call("write_file", path="file.txt", content="changed", expected_sha256="0" * 64))
    with pytest.raises(PermissionError):
        runner.execute(call("write_file", path="file.txt", content="changed", expected_sha256="last_read"))
    assert (tmp_path / "file.txt").read_text() == "original"


def test_corrected_python_check_keeps_history_but_clears_current_failure(store, credentials, tmp_path):
    sid, state = scripted_runtime(
        store,
        credentials,
        tmp_path,
        [
            call(
                "write_file", path="game.py", content="WIDTH, HEIGHT = 800, 60, 600\n", expected_sha256="new"
            ),
            call("read_file", path="game.py"),
            call(
                "write_file",
                path="game.py",
                content="WIDTH, HEIGHT = 800, 600\n",
                expected_sha256="last_read",
            ),
        ],
    )
    assert state == "completed"
    report = run_report(store, sid)
    assert report["state"] == "needs_attention"  # user has not yet assessed behavior
    evidence = public_report(report)["checks"][0]["evidence"]
    assert evidence["python_check_codes"] == {"LITERAL_UNPACK_MISMATCH": 1, "PYTHON_STATIC_OK": 1}
    assert evidence["execution_counts"]["python_files_needing_attention"] == 0
    assert evidence["user_goal_met"] is False
    store.assess(sid, "goal_met")
    assert run_report(store, sid)["state"] == "passed"


def test_python_check_report_does_not_expose_secret_via_exception(tmp_path, store):
    (tmp_path / "private.py").write_text("PRIVATE_SECRET = 'unterminated\n")
    payload = json.dumps(public_report(python_report(store, Workspace(tmp_path), "private.py")))
    assert "PRIVATE_SECRET" not in payload and "unterminated" not in payload
    assert "PYTHON_SYNTAX_ERROR" in payload


def test_manual_reports_apply_retention_immediately(store, tmp_path):
    store.set_setting("max_reports", 5)
    (tmp_path / "game.py").write_text("value = 1\n")
    for _ in range(8):
        python_report(store, Workspace(tmp_path), "game.py")
    assert len(store.diagnostic_reports()) == 5
