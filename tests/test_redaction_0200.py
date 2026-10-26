"""Redaction parity, bounded per-call work and coherent credential changes."""

import threading

import pytest


def legacy_scrub(credentials, value):
    """Original traversal, retained as an independent semantic reference."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if str(key).lower() in {"api_key", "apikey", "password", "secret", "token", "authorization"}
            else legacy_scrub(credentials, item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [legacy_scrub(credentials, item) for item in value]
    return credentials.redact(value) if isinstance(value, str) else value


def counted(credentials, monkeypatch):
    original = credentials.redact
    calls = []

    def redact(value):
        calls.append(len(value))
        return original(value)

    monkeypatch.setattr(credentials, "redact", redact)
    return calls


def test_nested_output_matches_original_redaction_for_secrets_regexes_and_unicode(credentials):
    credentials._values = {"API_KEY": "overlapping-secret-long", "TOKEN": "overlapping-secret"}
    data = {
        "API_KEY": {"nested": "never expose this"},
        "note": "overlapping-secret-long / overlapping-secret / naïve ☀",
        "more": [
            "Bearer abc.DEF-123",
            "sk-abcdef1234567890",
            "password=exposed-value",
            "ghp_abcdefghijklmnopqrstuvwxyz",
            "github_pat_abcdefghijklmnopqrstuvwxyz",
            "AIzaabcdefghijklmnopqrstuvwxyz",
            {"Authorization": "anything", "plain": (None, 0, 1.2, True, "naïve ☀")},
        ],
        7: ["overlapping-secret-long"] * 20,
    }
    assert credentials.scrub(data) == legacy_scrub(credentials, data)
    assert isinstance(data["more"][-1]["plain"], tuple)


def test_repeated_synthetic_report_strings_are_redacted_once_per_call(credentials, monkeypatch):
    payload = [{"message": "Bearer example-token", "status": "passed"} for _ in range(4000)]
    expected = legacy_scrub(credentials, payload)
    calls = counted(credentials, monkeypatch)
    assert credentials.scrub(payload) == expected
    assert len(calls) == 2
    assert credentials.scrub(payload) == expected
    assert len(calls) == 4  # No memo survives the first scrub.


@pytest.mark.parametrize("kind", ["entries", "characters", "long_strings"])
def test_redaction_memo_bounds_do_not_skip_remaining_work(kind, credentials, monkeypatch):
    if kind == "entries":
        values = [f"ordinary fixture value {i:04d}" for i in range(1040)]
        expected_calls = 1040 + 16
    elif kind == "characters":
        # 4,000 input + 4,000 output chars each: only32 fit the262,144 cap.
        values = [f"{i:04d}" + "x" * 3996 for i in range(40)]
        expected_calls = 40 + 8
    else:
        values = ["x" * 4097] * 4
        expected_calls = 8
    payload = values + values
    expected = legacy_scrub(credentials, payload)
    calls = counted(credentials, monkeypatch)
    assert credentials.scrub(payload) == expected
    assert len(calls) == expected_calls


def test_unhashable_string_subclasses_keep_original_behavior(credentials):
    class UnhashableString(str):
        __hash__ = None

    value = [UnhashableString("Bearer example-token")] * 3
    assert credentials.scrub(value) == legacy_scrub(credentials, value)


def test_later_env_load_cannot_reuse_an_old_scrub_memo(credentials, tmp_path):
    path = tmp_path / "fixture.env"
    payload = ["old-value-123", "new-value-456"] * 3
    path.write_text("SERVICE_KEY=old-value-123\n", encoding="utf-8")
    credentials.load_env(path)
    assert credentials.scrub(payload) == ["[REDACTED]", "new-value-456"] * 3
    path.write_text("SERVICE_KEY=new-value-456\n", encoding="utf-8")
    credentials.load_env(path)
    assert credentials.scrub(payload) == ["old-value-123", "[REDACTED]"] * 3


def test_later_vault_save_and_get_do_not_reuse_stale_redactions(credentials, monkeypatch):
    import keyring

    vault = {}
    monkeypatch.setattr(keyring, "set_password", lambda service, ref, value: vault.__setitem__(ref, value))
    monkeypatch.setattr(keyring, "get_password", lambda service, ref: vault[ref])
    payload = ["first-value-123", "second-value-456", "vault-value-789"] * 2
    credentials.save("service-ref", "first-value-123")
    assert credentials.scrub(payload) == ["[REDACTED]", "second-value-456", "vault-value-789"] * 2
    credentials.save("service-ref", "second-value-456")
    assert credentials.scrub(payload) == ["first-value-123", "[REDACTED]", "vault-value-789"] * 2
    vault["other-ref"] = "vault-value-789"
    assert credentials.get("other-ref") == "vault-value-789"
    assert credentials.scrub(payload) == ["first-value-123", "[REDACTED]", "[REDACTED]"] * 2


def test_public_credential_update_waits_for_a_coherent_scrub(credentials, monkeypatch, tmp_path):
    path = tmp_path / "fixture.env"
    path.write_text("SERVICE_KEY=old-value-123\n", encoding="utf-8")
    credentials.load_env(path)
    path.write_text("SERVICE_KEY=new-value-456\n", encoding="utf-8")
    entered, release, updating, updated = (threading.Event() for _ in range(4))
    results, errors = [], []
    original = credentials.redact

    def redact(value):
        entered.set()
        assert release.wait(5)
        return original(value)

    def scrub():
        try:
            results.append(credentials.scrub(["old-value-123", "new-value-456"] * 2))
        except Exception as exc:
            errors.append(type(exc).__name__)

    def update():
        try:
            updating.set()
            credentials.load_env(path)
            updated.set()
        except Exception as exc:
            errors.append(type(exc).__name__)

    monkeypatch.setattr(credentials, "redact", redact)
    reader, writer = threading.Thread(target=scrub), threading.Thread(target=update)
    reader.start()
    try:
        assert entered.wait(5)
        writer.start()
        assert updating.wait(5)
        assert not updated.wait(0.03)
    finally:
        release.set()
        reader.join(5)
        if writer.ident is not None:
            writer.join(5)
    assert not reader.is_alive() and not writer.is_alive() and not errors
    assert results == [["[REDACTED]", "new-value-456"] * 2]
    assert updated.is_set()
    assert credentials.scrub(["old-value-123", "new-value-456"]) == ["old-value-123", "[REDACTED]"]
