from aigentics.ui import Window
from aigentics.models import Reply, ToolCall
from aigentics.runtime import Runtime


def test_native_desktop_agent_crud_and_shared_workbench(qtbot, store, credentials, tmp_path):
    window = Window(store, credentials)
    qtbot.addWidget(window)
    window.show()
    assert window.tabs.tabText(0) == "AGENTS"
    assert window.tabs.tabText(1) == "WORKBENCH"
    window.new_agent()
    window.agent_name.setText("Desktop test")
    window.save_agent()
    assert window.run_agent.findData(window.agent_id) >= 0
    assert window.lab_agent.findData(window.agent_id) >= 0
    window.duplicate_agent()
    assert any(a.name == "Desktop test copy" for a in store.agents())
    (tmp_path / "hello.txt").write_text("hello desktop")
    window.select_workspace(tmp_path)
    assert window.tree.topLevelItemCount() > 0
    assert window.project_label.text().startswith(tmp_path.name)
    # Store fixture owns the connection in tests.
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_desktop_worker_runs_real_tools_and_populates_history(qtbot, store, credentials, tmp_path):
    window = Window(store, credentials)
    qtbot.addWidget(window)
    window.show()

    class FixtureProvider:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            if not any(m["role"] == "tool" for m in messages):
                return Reply(calls=[ToolCall(id="1", name="list_files", arguments={})])
            return Reply(content="Actual project listing completed.")

    window.runtime = Runtime(store, credentials, FixtureProvider)
    window.select_workspace(tmp_path)
    window.task.setPlainText("Inspect the project")
    window.start_run()
    qtbot.waitUntil(
        lambda: bool(store.sessions()) and store.sessions()[0]["state"] != "running", timeout=5000
    )
    qtbot.waitUntil(lambda: not window.worker.isRunning(), timeout=5000)
    qtbot.waitUntil(lambda: window.work_run.isEnabled(), timeout=5000)
    assert "Actual project listing completed" in window.work_output.toPlainText()
    assert "tool.result" in window.work_output.toPlainText()
    assert window.history.count() == 1
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_desktop_diff_approval_flow(qtbot, store, credentials, tmp_path):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QDialog

    window = Window(store, credentials)
    qtbot.addWidget(window)
    window.show()

    class WriterProvider:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            if not any(m["role"] == "tool" for m in messages):
                return Reply(
                    calls=[
                        ToolCall(
                            id="write1",
                            name="write_file",
                            arguments={
                                "path": "approved.txt",
                                "content": "Reviewed edit\n",
                                "expected_sha256": "new",
                            },
                        )
                    ]
                )
            return Reply(content="Edit applied.")

    window.runtime = Runtime(store, credentials, WriterProvider)
    window.select_workspace(tmp_path)
    window.task.setPlainText("Create a file")
    approvals = []
    timer = QTimer()

    def approve_dialog():
        dialog = QApplication.activeModalWidget()
        if isinstance(dialog, QDialog):
            approvals.append(dialog.windowTitle())
            dialog.accept()

    timer.timeout.connect(approve_dialog)
    timer.start(10)
    window.start_run()
    qtbot.waitUntil(lambda: window.worker is not None and not window.worker.isRunning(), timeout=5000)
    qtbot.waitUntil(lambda: window.work_run.isEnabled(), timeout=5000)
    timer.stop()
    assert approvals == ["Review proposed write_file"]
    assert (tmp_path / "approved.txt").read_text() == "Reviewed edit\n"
    assert any(
        e["kind"] == "permission.decided" and e["data"]["approved"]
        for e in store.events(store.sessions()[0]["id"])
    )
    window.lab_dir.cleanup()
    window.store.close = lambda: None
