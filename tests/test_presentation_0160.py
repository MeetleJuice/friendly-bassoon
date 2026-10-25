"""Real navigation, constrained layouts and unchanged task/approval state."""

from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QDialog

from aigentics.crew import ensure_roster
from aigentics.models import Agent
from aigentics.presentation import CommandPalette, STYLE
from aigentics.ui import Window
from test_campaign_ui_0120 import cleanup


@pytest.fixture
def window(qtbot, store, credentials):
    view = Window(store, credentials)
    qtbot.addWidget(view, before_close_func=cleanup)
    view.show()
    return view


@pytest.mark.parametrize("index", [0, 1, 2])
def test_sidebar_and_existing_page_routes_stay_synchronized(window, qtbot, index):
    qtbot.mouseClick(window.navigation_buttons[index], Qt.LeftButton)
    assert window.tabs.currentIndex() == index
    assert sum(b.isChecked() for b in window.navigation_buttons.values()) == 1
    assert window.navigation_buttons[index].isChecked()
    window.tabs.setCurrentIndex((index + 1) % 3)
    assert window.navigation_buttons[(index + 1) % 3].isChecked()


def test_command_palette_search_requires_selection_and_never_runs_a_model(qtbot, window, monkeypatch):
    calls = []
    monkeypatch.setattr(window, "start_run", lambda *args: calls.append("run"))
    window.open_command_palette()
    palette = window.command_palette
    qtbot.addWidget(palette)
    palette.search.setText("no matching command")
    palette.execute()
    assert palette.results.count() == 0 and not calls
    palette.search.setText("credential")
    assert palette.results.count() == 1
    qtbot.keyClick(palette.search, Qt.Key_Return)
    assert window.tabs.currentIndex() == 0 and window.agent_sections.currentIndex() == 1
    assert not calls and window.worker is None


def test_command_palette_escape_does_not_dispatch(qtbot, window):
    calls = []
    dialog = CommandPalette(window, [("Only action", "Synthetic", lambda: calls.append(True))])
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.keyClick(dialog.search, Qt.Key_Escape)
    assert not calls and dialog.result() == QDialog.DialogCode.Rejected


def test_context_options_preserve_state_and_keep_write_scope_visible(window, qtbot):
    window.tabs.setCurrentIndex(1)
    window.expected_files.setText("result.py")
    window.task_options.set_expanded(True)
    window.capture.setChecked(True)
    window.require_task_tools.setChecked(True)
    window.task_options.set_expanded(False)
    assert window.capture.isChecked() and window.require_task_tools.isChecked()
    assert window.expected_files.text() == "result.py" and window.expected_files.isVisible()
    assert not window.task_options.content.isVisible()
    assert window.require_task_readback.isChecked()


def test_panel_preferences_reopen_and_file_preview_opens_the_actual_inspector(
    window, qtbot, store, credentials, tmp_path
):
    (tmp_path / "preview.txt").write_text("Visible synthetic file")
    window.select_workspace(tmp_path)
    window.tabs.setCurrentIndex(1)
    window.files_toggle.setChecked(True)
    window.inspector_toggle.setChecked(False)
    window.inspector_toggle.setChecked(True)
    second = Window(store, credentials)
    qtbot.addWidget(second, before_close_func=cleanup)
    second.show()
    second.tabs.setCurrentIndex(1)
    assert second.files_toggle.isChecked() and second.inspector_toggle.isChecked()
    window.inspector_toggle.setChecked(False)
    item = next(
        window.tree.topLevelItem(i)
        for i in range(window.tree.topLevelItemCount())
        if window.tree.topLevelItem(i).text(0) == "preview.txt"
    )
    window.preview_file(item, 0)
    assert window.inspector_tabs.count() == 2
    assert window.inspector_toggle.isChecked()
    assert window.inspector_tabs.currentWidget() is window.file_preview
    assert "Visible synthetic file" in window.file_preview.toPlainText()


@pytest.mark.parametrize("width,height", [(900, 650), (1000, 740), (1440, 900)])
def test_workbench_remains_within_requested_window_size(window, qtbot, width, height):
    QApplication.instance().setStyleSheet(STYLE)
    window.resize(width, height)
    window.tabs.setCurrentIndex(1)
    qtbot.wait(20)
    assert window.width() == width and window.height() == height
    assert window.work_run.mapTo(window, window.work_run.rect().bottomRight()).x() < width
    assert window.work_run.mapTo(window, window.work_run.rect().bottomRight()).y() < height
    window.task_options.set_expanded(True)
    qtbot.wait(20)
    assert window.width() == width and window.height() == height
    assert window.workspace_scroll.widget() is not None
    assert window.explorer_panel.isVisible() == (width >= 1200)


def test_new_task_during_work_does_not_clear_context_or_output(window):
    window.parent_session = "synthetic-session"
    window.work_output.setPlainText("Recorded evidence")
    window.worker = SimpleNamespace(isRunning=lambda: True)
    window.focus_new_task()
    assert window.parent_session == "synthetic-session"
    assert window.work_output.toPlainText() == "Recorded evidence"
    window.worker = None


def test_agent_visual_identity_does_not_rewrite_saved_definitions(window, store):
    personal = store.save_agent(Agent(name="George", instructions="Personal instructions"))
    roster = ensure_roster(store, personal.primary)
    before = {a.id: a.model_dump() for a in store.agents()}
    window.refresh_agents()
    assert all(not window.agent_list.item(i).icon().isNull() for i in range(window.agent_list.count()))
    window.display_agent(roster["sentinel"])
    assert window.agent_heading.text() == "Sentinel" and not window.allow_writes.isChecked()
    assert {a.id: a.model_dump() for a in store.agents()} == before


def test_run_shortcut_requires_composer_focus_and_enabled_run(window, monkeypatch, qtbot):
    calls = []
    monkeypatch.setattr(window, "start_run", lambda *args: calls.append(True))
    window.tabs.setCurrentIndex(1)
    window.task.setFocus()
    qtbot.wait(20)
    window.run_from_shortcut()
    assert calls == [True]
    window.work_run.setEnabled(False)
    window.run_from_shortcut()
    window.work_run.setEnabled(True)
    window.tabs.setCurrentIndex(0)
    window.run_from_shortcut()
    assert calls == [True]


def test_empty_project_screen_and_recent_workspace_transition(window, tmp_path):
    assert not window.project_panel.empty_state.isHidden()
    window.select_workspace(tmp_path)
    assert window.project_panel.empty_state.isHidden()
    assert not window.project_panel.project_splitter.isHidden()
    assert window.project_panel.row()["path"] == str(tmp_path)


def test_button_help_and_literal_ampersands_remain_accessible(window):
    from aigentics.ui import button
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    holder = QWidget(window)
    result = button("Review & save", lambda: None, QVBoxLayout(holder))
    assert result.text() == "Review && save" and result.accessibleName() == "Review & save"
    assert all(b.toolTip() for b in window.sidebar.findChildren(QPushButton))


def test_test_center_distinguishes_repairs_failures_and_unknowns(window, qtbot):
    from aigentics.campaign_ui import CampaignDialog

    dialog = CampaignDialog(window)
    qtbot.addWidget(dialog)
    assert dialog.details.content.isHidden() and dialog.github_sharing.content.isHidden()
    for identity, status, code, evidence in zip(
        dialog.identities[:4],
        ["passed", "passed", "failed", "failed"],
        ["OK", "OK", "ROLE_REQUIREMENTS_NOT_MET", "CANCELLED"],
        [{}, {"completion_feedback_count": 1}, {}, {"runtime_state": "cancelled"}],
    ):
        dialog.activity(
            {
                "kind": "campaign.result",
                "data": {
                    "id": identity,
                    "status": status,
                    "code": code,
                    "duration_ms": 100,
                    "evidence": evidence,
                },
            }
        )
    assert {k: v.text() for k, v in dialog.metric_values.items()} == {
        "immediate": "1",
        "corrected": "1",
        "failed": "1",
        "unknown": "1",
    }
    assert dialog.results.item(3, 1).text() == "Not completed"
    dialog.inspect(2, 0)
    assert not dialog.details.content.isHidden()
    assert "DETAIL:" in dialog.output.toPlainText()
    assert dialog.github_sharing.content.isHidden() and not dialog.share.isEnabled()


def test_invalid_view_preferences_fall_back_without_touching_agent_configuration(qtbot, store, credentials):
    store.set_setting("ui_files_visible", "invalid")
    store.set_setting("ui_inspector_visible", {"bad": True})
    view = Window(store, credentials)
    qtbot.addWidget(view, before_close_func=cleanup)
    view.show()
    view.resize(900, 650)
    view.tabs.setCurrentIndex(1)
    qtbot.wait(20)
    assert not view.files_toggle.isChecked() and not view.inspector_toggle.isChecked()
    assert view.require_task_readback.isChecked() and not view.capture.isChecked()
