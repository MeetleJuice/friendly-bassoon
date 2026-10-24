"""Installer queue is durable before process launch; explicit Update needs no second app prompt."""

from types import SimpleNamespace
import pytest
from aigentics.ui import Window


@pytest.mark.parametrize("fail", [False, True])
def test_guided_update_saves_restart_queue_before_launch(qtbot, store, credentials, monkeypatch, fail):
    window = Window(store, credentials)
    qtbot.addWidget(window)
    window.downloaded_update = SimpleNamespace(release=SimpleNamespace(version="99.0.0"))
    window.guided_update = True
    errors = []
    calls = []
    monkeypatch.setattr(window, "error", errors.append)
    monkeypatch.setattr(window, "close", lambda: calls.append("close"))
    monkeypatch.setattr(store, "backup", lambda: calls.append("backup"))

    def question(*args):
        raise AssertionError("Update click already authorized installation")

    monkeypatch.setattr("aigentics.ui.QMessageBox.question", question)

    def launch(update):
        assert store.setting("guided_tests_after_update", None) == {"version": "99.0.0"}
        assert store.setting("pending_update", None)["version"] == "99.0.0"
        calls.append("launch")
        if fail:
            raise RuntimeError("Synthetic launch failure")

    monkeypatch.setattr("aigentics.ui.launch_installer", launch)
    window.install_update()
    assert calls == (["backup", "launch"] if fail else ["backup", "launch", "close"])
    assert bool(errors) == fail
    if fail:
        assert store.setting("guided_tests_after_update", None) is None
        assert store.setting("pending_update", None) is None
    window.lab_dir.cleanup()
    window.store.close = lambda: None
