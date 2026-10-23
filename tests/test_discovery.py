import json
import threading
import pytest
from aigentics.discovery import desktop_locations, find_desktop_env, discover, DiscoveryResult
from aigentics.models import Profile


@pytest.mark.parametrize("filename", [".env", ".env.txt"])
def test_notepad_desktop_keys_create_profiles_without_cloud_calls(tmp_path, credentials, filename):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    secret = "fake-local-key-for-fixture-123"
    (desktop / filename).write_text(
        "\ufeffGROQ_API_KEY=" + secret + "\nOLLAMA_MODEL=qwen2.5-coder:14b\n", encoding="utf-8"
    )
    observed = []

    class LocalOllama:
        def __init__(self, profile, creds):
            observed.append(profile.base_url)
            assert profile.timeout_seconds == 3

        def discover(self):
            return ["qwen2.5-coder:14b", "llama3.2:3b"]

    result = discover(credentials, [desktop], threading.Event(), provider_factory=LocalOllama)
    assert result.models == ["qwen2.5-coder:14b", "llama3.2:3b"]
    assert result.env_found == 1 and result.variables_loaded == 2
    assert result.profiles[0].id == "groq"
    assert result.profiles[0].credential_ref == "GROQ_API_KEY"
    assert observed == ["http://127.0.0.1:11434"]
    assert secret not in json.dumps(result.evidence())
    assert credentials.get("GROQ_API_KEY") == secret


def test_desktop_search_is_bounded_and_handles_onedrive(tmp_path):
    actual = tmp_path / "RedirectedDesktop"
    home = tmp_path / "Home"
    onedrive = tmp_path / "OneDrive"
    locations = desktop_locations(
        actual, {"OneDrive": str(onedrive), "OneDriveConsumer": str(onedrive)}, home
    )
    assert locations == [actual, home / "Desktop", onedrive / "Desktop"]
    actual.mkdir()
    (actual / ".env").write_text("GROQ_API_KEY=fake")
    (actual / "unrelated.env").write_text("OTHER=not-loaded")
    (tmp_path / ".env").write_text("OUTSIDE=never-loaded")
    assert find_desktop_env(locations) == [actual / ".env"]


def test_discovery_disabled_does_not_read_files_or_contact_ollama(tmp_path, credentials):
    (tmp_path / ".env").write_text("GROQ_API_KEY=private-value")

    def prohibited(*args):
        raise AssertionError("Network must not be used")

    result = discover(
        credentials,
        [tmp_path],
        threading.Event(),
        load_desktop_env=False,
        find_ollama=False,
        provider_factory=prohibited,
    )
    assert result.models == [] and not credentials.names()
    assert result.variables_loaded == 0


def test_unavailable_ollama_and_unreadable_env_remain_actionable(tmp_path, credentials):
    (tmp_path / ".env").write_bytes(b"\xff\xfe\x00not-utf8")

    class Broken:
        def __init__(self, *args):
            pass

        def discover(self):
            raise ConnectionError("not running")

    result = discover(credentials, [tmp_path], threading.Event(), provider_factory=Broken)
    assert "unavailable" in result.ollama_status
    assert "Could not read" in result.env_status
    assert result.errors == ["UnicodeDecodeError", "ConnectionError"]


def test_no_secret_interpolation_and_oversized_env_rejected(tmp_path, credentials, monkeypatch):
    monkeypatch.setenv("PRIVATE_SYSTEM_TOKEN", "must-not-expand")
    path = tmp_path / ".env"
    path.write_text("CUSTOM_TOKEN=${PRIVATE_SYSTEM_TOKEN}\n", encoding="utf-8")
    credentials.load_env(path)
    assert credentials.get("CUSTOM_TOKEN") == "${PRIVATE_SYSTEM_TOKEN}"
    path.write_bytes(b"x" * 1_000_001)
    with pytest.raises(ValueError, match="1 MB"):
        credentials.load_env(path)


def test_discovered_profiles_never_overwrite_existing_configuration(qtbot, store, credentials):
    from aigentics.ui import Window

    custom = Profile(
        id="groq",
        name="My endpoint",
        kind="openai",
        base_url="https://example.com/v1",
        credential_ref="CUSTOM_KEY",
    )
    store.save_profile(custom)
    window = Window(store, credentials)
    qtbot.addWidget(window)
    result = DiscoveryResult(
        models=["qwen2.5-coder:14b"],
        profiles=[
            Profile(
                id="groq",
                name="Default",
                kind="openai",
                base_url="https://api.groq.com/openai/v1",
                credential_ref="GROQ_API_KEY",
            )
        ],
        env_status="Loaded into memory",
        ollama_status="Connected",
    )
    window.discovery_completed(result)
    assert next(p for p in store.profiles() if p.id == "groq").base_url == "https://example.com/v1"
    assert window.agent_model.count() == 1
    assert window.agent_model.text() == "qwen2.5-coder:14b"
    assert store.agents()[0].primary.model == "qwen2.5-coder:14b"
    window.open_setup()
    assert window.setup_dialog.models.currentText() == "qwen2.5-coder:14b"
    assert window.setup_dialog.auto_env.isChecked()
    window.setup_dialog.auto_env.setChecked(False)
    assert store.setting("auto_desktop_env", True) is False
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_consistent_database_backup_and_retention(store, tmp_path):
    from aigentics.models import Agent

    sid = store.start(Agent(), tmp_path)
    store.finish(sid, "completed", "Done")
    for _ in range(4):
        path = store.backup()
    import sqlite3

    with sqlite3.connect(path) as backup:
        assert backup.execute("SELECT state FROM sessions WHERE id=?", (sid,)).fetchone()[0] == "completed"
    assert len(list(path.parent.glob("*.sqlite3"))) == 3
