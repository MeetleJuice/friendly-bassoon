"""Actual Qt worker campaigns, preserved personal definitions and reviewed sharing."""

import threading

from PySide6.QtCore import QThread
import pytest

from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from aigentics import campaign_ui
from aigentics.campaign import run_campaign
from aigentics.diagnostics import OFFLINE_CHECK_COUNT
from aigentics.models import Agent, Profile
from aigentics.ui import Window
from test_campaign_0120 import CrewScripted


def setup_dialog(qtbot, store, credentials, monkeypatch, stop_after_first=False):
    store.save_profile(Profile(id="ollama", name="Local fixture"))
    personal = store.save_agent(Agent(name="George", instructions="My personal instructions stay intact."))
    window = Window(store, credentials)
    qtbot.addWidget(window, before_close_func=cleanup)
    errors = []
    monkeypatch.setattr(window, "error", errors.append)
    dialog = campaign_ui.CampaignDialog(window)
    qtbot.addWidget(dialog)

    def execute(*args, **kwargs):
        if stop_after_first:
            positional = list(args)
            emit, cancel = positional[4], positional[3]

            def bounded_emit(event):
                emit(event)
                if event["kind"] == "campaign.result":
                    cancel.set()

            positional[4] = bounded_emit
            return run_campaign(*positional, **kwargs, provider_factory=CrewScripted)
        return run_campaign(*args, **kwargs, provider_factory=CrewScripted)

    monkeypatch.setattr(campaign_ui, "run_campaign", execute)
    return window, dialog, personal, errors


def finish(qtbot, dialog):
    qtbot.waitUntil(lambda: dialog.worker is not None and not dialog.worker.isRunning(), timeout=90000)
    qtbot.waitUntil(lambda: dialog.go.isEnabled() and len(dialog.urls) == 2, timeout=5000)


def cleanup(window):
    """Run even after assertions/timeouts, before Qt can destroy worker parents.

    Forty-two real SQLite-backed cases can exceed 20 seconds on Windows CI.
    The completion deadline remains finite; teardown cancellation must not turn a
    normal assertion failure into a fatal QThread-destroyed-while-running abort.
    """
    workers = window.findChildren(QThread)
    for worker in workers:
        if worker.isRunning():
            worker.cancel.set()
    for worker in workers:
        assert worker.wait(30000), "Synthetic campaign did not stop after cancellation"
    window.lab_dir.cleanup()


def test_full_gui_real_66_attempt_worker_and_two_approved_previews(qtbot, store, credentials, monkeypatch):
    window, dialog, personal, errors = setup_dialog(qtbot, store, credentials, monkeypatch)
    opened = []
    monkeypatch.setattr(campaign_ui.webbrowser, "open", lambda url: opened.append(url) or True)
    dialog.show()
    dialog.start()
    finish(qtbot, dialog)
    assert not errors
    assert dialog.progress.value() == dialog.progress.maximum() == OFFLINE_CHECK_COUNT + 66
    assert dialog.results.rowCount() == len(dialog.rows) == 66
    assert all(dialog.results.item(index, 1).text() == "Passed immediately" for index in range(66))
    assert len(store.diagnostic_reports()) == 2
    saved = {agent.id: agent for agent in store.agents()}
    assert len(saved) == 7
    assert saved[personal.id] == personal
    assert all(
        saved[f"midnight-{role}-v1"].primary == personal.primary
        for role in ("george", "scout", "ada", "vera", "sentinel", "atlas")
    )
    previews = dialog.output.toPlainText()
    assert previews.count("EXACT PUBLIC PREVIEW") == 2
    assert dialog.approval.isEnabled() and not dialog.share.isEnabled()
    assert not opened
    dialog.open_drafts()
    assert not opened
    for url in dialog.urls:
        body = parse_qs(urlsplit(url).query)["body"][0]
        assert len(url) <= 7500
        assert "My personal instructions" not in body
        assert personal.primary.model not in body
    dialog.inspect(0, 0)
    assert "DETAIL:" in dialog.output.toPlainText()
    dialog.approval.setChecked(True)
    dialog.open_drafts()
    dialog.open_drafts()
    assert len(opened) == 2 and not dialog.urls
    assert not dialog.approval.isEnabled() and not dialog.share.isEnabled()
    assert not store.sessions()
    cleanup(window)


def test_cancel_preserves_result_and_continue_finishes_without_replay(qtbot, store, credentials, monkeypatch):
    window, dialog, personal, errors = setup_dialog(
        qtbot, store, credentials, monkeypatch, stop_after_first=True
    )
    dialog.start()
    finish(qtbot, dialog)
    assert not errors
    assert len(dialog.rows) == 1
    assert dialog.resume.isEnabled()
    saved = next(
        row["payload"] for row in store.diagnostic_reports() if row["payload"].get("kind") == "crew_campaign"
    )
    assert saved["state"] == "cancelled"
    first = saved["checks"][0]
    monkeypatch.setattr(
        campaign_ui,
        "run_campaign",
        lambda *args, **kwargs: run_campaign(*args, **kwargs, provider_factory=CrewScripted),
    )
    dialog.start(True)
    finish(qtbot, dialog)
    assert not errors and len(dialog.rows) == 66
    assert dialog.progress.value() == OFFLINE_CHECK_COUNT + 66
    resumed = next(
        row["payload"] for row in store.diagnostic_reports() if row["payload"].get("kind") == "crew_campaign"
    )
    assert resumed["id"] == saved["id"] and resumed["checks"][0] == first
    assert resumed["summary"]["passed"] == 66
    assert not dialog.resume.isEnabled()
    cleanup(window)


def test_running_operation_blocks_campaign_without_creating_roster(qtbot, store, credentials, monkeypatch):
    window, dialog, personal, errors = setup_dialog(qtbot, store, credentials, monkeypatch)
    window.worker = SimpleNamespace(isRunning=lambda: True)
    dialog.start()
    assert errors == ["Finish the current operation first."]
    assert dialog.worker is None and len(store.agents()) == 1
    window.worker = None
    cleanup(window)


def test_obsolete_worker_signals_cannot_replace_new_campaign_state(qtbot, store, credentials, monkeypatch):
    window, dialog, personal, errors = setup_dialog(qtbot, store, credentials, monkeypatch)
    dialog.mode.setCurrentIndex(dialog.mode.findData("quick"))
    dialog.start()
    finish(qtbot, dialog)
    obsolete = dialog.worker
    report = store.diagnostic_reports()[0]["payload"]
    dialog.worker = object()  # A replacement owner exists; every previous signal is stale.
    dialog.urls = []
    dialog.go.setEnabled(False)
    progress = dialog.progress.value()
    obsolete.activity.emit({"kind": "diagnostic.result", "data": {"id": "obsolete", "status": "failed"}})
    obsolete.succeeded.emit([report, report])
    obsolete.failed.emit("Obsolete failure")
    obsolete.finished.emit()
    qtbot.wait(50)
    assert dialog.progress.value() == progress
    assert not dialog.urls and not dialog.go.isEnabled() and not errors
    dialog.worker = obsolete
    cleanup(window)


def test_test_cleanup_stops_active_worker_after_assertion_failure(qtbot, store, credentials, monkeypatch):
    window, dialog, personal, errors = setup_dialog(qtbot, store, credentials, monkeypatch)
    entered = threading.Event()

    def waiting_campaign(*args, **kwargs):
        entered.set()
        assert args[3].wait(10), "Test cleanup never cancelled the worker"
        return run_campaign(*args, **kwargs, provider_factory=CrewScripted)

    monkeypatch.setattr(campaign_ui, "run_campaign", waiting_campaign)
    dialog.start()
    qtbot.waitUntil(entered.is_set, timeout=5000)
    assert dialog.worker.isRunning()
    with pytest.raises(AssertionError, match="simulated test assertion"):
        try:
            raise AssertionError("simulated test assertion")
        finally:
            cleanup(window)
    assert not dialog.worker.isRunning()
    assert dialog.worker.cancel.is_set()


@pytest.mark.parametrize("available", [False, True])
def test_queued_update_uses_matching_interrupted_campaign(qtbot, store, credentials, monkeypatch, available):
    window, dialog, personal, errors = setup_dialog(qtbot, store, credentials, monkeypatch)
    monkeypatch.setattr(campaign_ui, "latest_resumable", lambda *args: {"id": "saved"} if available else None)
    observed = []
    monkeypatch.setattr(dialog, "start", lambda resume=False: observed.append(resume))
    dialog.start_queued()
    assert observed == [available]
    assert not errors
