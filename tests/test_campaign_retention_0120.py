"""A completed continuation stays available without rewriting its historical origin."""

from datetime import datetime, timedelta, timezone
import threading

from aigentics.campaign import run_campaign
from aigentics.evidence import base_report
from aigentics.models import Agent, Profile
from aigentics.store import Store
from test_campaign_0120 import CrewScripted


def test_explicit_refresh_preserves_original_payload_creation_and_id(store):
    report = base_report("health", "test", "Synthetic")
    report["created"] = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    report["state"] = "passed"
    store.save_diagnostic(report)
    store.save_diagnostic(report, refresh_retention=True)
    saved = store.diagnostic_reports()[0]
    assert saved["id"] == report["id"]
    assert saved["payload"]["created"] == report["created"]
    assert saved["created"] > report["created"]
    refreshed = saved["created"]
    report["summary"] = {"passed": 1}
    store.save_diagnostic(report)
    assert store.diagnostic_reports()[0]["created"] == refreshed
    store.prune()
    assert store.diagnostic_reports()[0]["payload"] == report


def test_unrequested_refresh_keeps_existing_age_retention_behavior(store):
    report = base_report("health", "test", "Synthetic")
    report["created"] = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    report["state"] = "passed"
    store.save_diagnostic(report)
    store.save_diagnostic(report)
    assert store.diagnostic_reports()[0]["created"] == report["created"]
    store.prune()
    assert not store.diagnostic_reports()


def test_completed_real_campaign_survives_full_retention_cap_and_reopen(tmp_path, credentials):
    path = tmp_path / "campaign.sqlite3"
    store = Store(path, credentials)
    try:
        store.save_profile(Profile(id="ollama", name="Local"))
        store.set_setting("max_reports", 5)
        stop = threading.Event()

        def emit(event):
            if event["kind"] == "campaign.result":
                stop.set()

        original = run_campaign(store, credentials, Agent(), stop, emit, provider_factory=CrewScripted)[1]
        assert original["state"] == "cancelled" and len(original["checks"]) == 1
        origin, first_result = original["created"], original["checks"][0]
        for _ in range(4):
            report = base_report("health", "test", "Synthetic")
            report["state"] = "passed"
            store.save_diagnostic(report)
        completed = run_campaign(
            store,
            credentials,
            Agent(),
            threading.Event(),
            lambda event: None,
            resume=True,
            provider_factory=CrewScripted,
        )[1]
        assert completed["id"] == original["id"]
        assert completed["created"] == origin
        assert completed["checks"][0] == first_result
        assert completed["summary"]["passed"] == 42
        retained = {row["id"]: row for row in store.diagnostic_reports()}
        assert completed["id"] in retained
        assert len(retained) == 5
        assert retained[completed["id"]]["payload"]["created"] == origin
        assert retained[completed["id"]]["created"] > origin
    finally:
        store.close()
    reopened = Store(path, credentials)
    try:
        reopened.prune()
        retained = {row["id"]: row["payload"] for row in reopened.diagnostic_reports()}
        assert retained[completed["id"]]["state"] == "passed"
        assert retained[completed["id"]]["created"] == origin
        assert retained[completed["id"]]["checks"][0] == first_result
        assert len(retained) == 5
    finally:
        reopened.close()
