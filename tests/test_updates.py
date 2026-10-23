import hashlib
import threading
import httpx
import pytest
from aigentics.updates import (
    API_URL,
    REPOSITORY,
    Updater,
    UpdateError,
    version_tuple,
    checked_url,
    verify_download,
    launch_installer,
)

BINARY = b"fixture executable bytes; never execute this"
SHA = hashlib.sha256(BINARY).hexdigest()
PREFIX = f"https://github.com/{REPOSITORY}/releases/download/v0.3.0/"
NAME = "Aigentics-Setup-0.3.0.exe"


def metadata():
    return {
        "tag_name": "v0.3.0",
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": NAME,
                "browser_download_url": PREFIX + NAME,
                "size": len(BINARY),
                "digest": "sha256:" + SHA,
            },
            {"name": "SHA256SUMS.txt", "browser_download_url": PREFIX + "SHA256SUMS.txt"},
        ],
    }


def transport(data=None, content=BINARY, checksum=None, redirect=None):
    def handle(request):
        # An updater request must never carry provider authentication.
        assert "authorization" not in request.headers
        if str(request.url) == API_URL:
            return httpx.Response(200, json=metadata() if data is None else data)
        if request.url.path.endswith("SHA256SUMS.txt"):
            return httpx.Response(200, text=checksum or f"{SHA}  {NAME}\n")
        if redirect:
            return httpx.Response(302, headers={"Location": redirect})
        return httpx.Response(200, content=content)

    return httpx.MockTransport(handle)


def test_version_order_and_downgrade_prevention(tmp_path):
    assert version_tuple("v0.10.0") > version_tuple("0.9.9")
    updater = Updater(tmp_path, "0.3.0", transport())
    assert updater.check(threading.Event()) is None
    updater.current_version = "0.4.0"
    assert updater.check(threading.Event()) is None
    for version in ("latest", "v1.2.3-beta", "1.2", "../1.2.3", "01.2.3"):
        with pytest.raises(UpdateError):
            version_tuple(version)


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/file",
        "https://evil.example/file",
        "https://github.com.evil.example/file",
        "https://user:pass@github.com/file",
        "https://github.com:444/file",
    ],
)
def test_reject_untrusted_update_destinations(url):
    with pytest.raises(UpdateError):
        checked_url(url)


def test_update_check_and_verified_download_are_real_file_operations(tmp_path):
    updater = Updater(tmp_path, "0.2.0", transport())
    release = updater.check(threading.Event())
    assert release.version == "0.3.0"
    progress = []
    update = updater.download(release, threading.Event(), lambda n, total: progress.append((n, total)))
    assert update.path.read_bytes() == BINARY
    assert progress[-1] == (len(BINARY), len(BINARY))
    verify_download(update)
    # A valid cached download is checked before reuse.
    assert updater.download(release, threading.Event()).sha256 == SHA
    update.path.write_bytes(b"tampered" + BINARY)
    with pytest.raises(UpdateError):
        verify_download(update)


@pytest.mark.parametrize(
    "data",
    [
        {"tag_name": "v0.3.0", "draft": True},
        {"tag_name": "v0.3.0", "prerelease": True},
    ],
)
def test_draft_and_prerelease_never_install(tmp_path, data):
    assert Updater(tmp_path, "0.2.0", transport(data)).check(threading.Event()) is None


def test_missing_foreign_and_oversized_release_assets_are_rejected(tmp_path):
    data = metadata()
    data["assets"] = []
    with pytest.raises(UpdateError, match="no complete"):
        Updater(tmp_path, "0.2.0", transport(data)).check(threading.Event())
    data = metadata()
    data["assets"][0]["browser_download_url"] = (
        "https://github.com/other/repo/releases/download/v0.3.0/" + NAME
    )
    with pytest.raises(UpdateError, match="do not belong"):
        Updater(tmp_path, "0.2.0", transport(data)).check(threading.Event())
    data = metadata()
    data["assets"][0]["size"] = 2**31
    with pytest.raises(UpdateError, match="size"):
        Updater(tmp_path, "0.2.0", transport(data)).check(threading.Event())


@pytest.mark.parametrize("content", [b"bad executable", BINARY + b"too long"])
def test_corrupt_downloads_never_become_installable_files(tmp_path, content):
    updater = Updater(tmp_path, "0.2.0", transport(content=content))
    release = updater.check(threading.Event())
    with pytest.raises(UpdateError):
        updater.download(release, threading.Event())
    assert not list(tmp_path.glob("*.exe"))
    assert not list(tmp_path.glob("*.part"))


def test_digest_disagreement_and_untrusted_redirect_rejected(tmp_path):
    updater = Updater(tmp_path, "0.2.0", transport(checksum="0" * 64 + "  " + NAME))
    release = updater.check(threading.Event())
    with pytest.raises(UpdateError, match="disagree"):
        updater.download(release, threading.Event())
    updater.transport = transport(redirect="https://evil.example/setup.exe")
    with pytest.raises(UpdateError, match="trusted"):
        updater.download(release, threading.Event())
    assert not list(tmp_path.glob("*.exe"))


def test_cancelled_download_cleans_partial_file(tmp_path):
    updater = Updater(tmp_path, "0.2.0", transport())
    release = updater.check(threading.Event())
    cancel = threading.Event()
    with pytest.raises(InterruptedError):
        updater.download(release, cancel, lambda *args: cancel.set())
    # Cancellation at the last chunk must still stop promotion of the file.
    assert not list(tmp_path.glob("*.part"))


def test_missing_release_and_rate_limited_updates_are_actionable(tmp_path):
    updater = Updater(tmp_path, "0.2.0", httpx.MockTransport(lambda request: httpx.Response(404)))
    assert updater.check(threading.Event()) is None
    updater.transport = httpx.MockTransport(lambda request: httpx.Response(429))
    with pytest.raises(UpdateError, match="429"):
        updater.check(threading.Event())


def test_installer_launch_reverifies_and_preserves_argument_boundaries(tmp_path, monkeypatch):
    import aigentics.updates as module

    updater = Updater(tmp_path / "folder with spaces", "0.2.0", transport())
    update = updater.download(updater.check(threading.Event()), threading.Event())
    calls = []
    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(module.sys, "executable", str(tmp_path / "Installed App" / "Aigentics.exe"))
    monkeypatch.setattr(module.subprocess, "Popen", lambda argv, **kw: calls.append((argv, kw)))
    launch_installer(update)
    assert calls[0][0] == [str(update.path), "/UPDATE=1", "/DIR=" + str(tmp_path / "Installed App")]
    assert calls[0][1] == {"close_fds": True}
    update.path.write_bytes(b"tampered")
    with pytest.raises(UpdateError):
        launch_installer(update)
    assert len(calls) == 1


def test_ui_update_status_and_local_evidence(qtbot, store, credentials, tmp_path):
    from aigentics.ui import Window

    window = Window(store, credentials)
    qtbot.addWidget(window)
    updater = Updater(tmp_path / "cache", "0.2.0", transport())
    window.updater = updater
    window.open_setup()
    window.check_updates()
    qtbot.waitUntil(
        lambda: window.update_worker is not None and not window.update_worker.isRunning(), timeout=5000
    )
    qtbot.waitUntil(lambda: window.available_release is not None, timeout=5000)
    window.download_update()
    qtbot.waitUntil(
        lambda: window.downloaded_update is not None and not window.update_worker.isRunning(), timeout=5000
    )
    assert window.downloaded_update.path.read_bytes() == BINARY
    assert "SHA-256 verified" in window.setup_dialog.update.text()
    kinds = [e["kind"] for e in store.events(None)]
    assert "update.check_completed" in kinds and "update.download_verified" in kinds
    window.lab_dir.cleanup()
    window.store.close = lambda: None
