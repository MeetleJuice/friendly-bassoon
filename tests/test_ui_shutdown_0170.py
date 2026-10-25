"""Queued worker failures must not open modal UI during deferred shutdown."""

import threading
from PySide6.QtWidgets import QMessageBox
from aigentics.ui import Window


def test_late_worker_error_is_suppressed_while_close_waits_for_worker(qtbot, store, credentials, monkeypatch):
    window = Window(store, credentials)
    qtbot.addWidget(window)
    # This fixture owns SQLite; closing the window must not close its connection.
    monkeypatch.setattr(store, "close", lambda: None)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    window.error("Visible before shutdown")
    assert warnings == ["Visible before shutdown"]
    release, entered = threading.Event(), threading.Event()

    def task(worker):
        entered.set()
        release.wait(3)
        return None

    completed = []
    window.start_worker(task, completed.append)
    try:
        qtbot.waitUntil(entered.is_set, timeout=3000)
        window.close()
        assert window.worker.cancel.is_set()
        assert window.start_worker(task, completed.append) is False
        window.worker.failed.emit("Late synthetic cancellation failure")
        qtbot.wait(1)
        assert warnings == ["Visible before shutdown"]
    finally:
        release.set()
        assert window.worker.wait(5000)
        qtbot.wait(1)
        window.close()

    assert completed == []
