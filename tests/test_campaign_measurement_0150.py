import threading
import pytest
from aigentics.campaign import run_campaign, plan
from aigentics.measurement import measurement_plan, measurement_manifest, manifest_id
from aigentics.models import Agent, Profile
from aigentics.bundles import build_bundle
from test_campaign_0120 import CrewScripted


def test_all_six_roles_repeated_measurement_and_zip(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local fixture"))
    health, r = run_campaign(
        store,
        credentials,
        Agent(),
        threading.Event(),
        lambda e: None,
        mode="measurement",
        provider_factory=CrewScripted,
    )
    assert len(r["checks"]) == r["planned_cases"] == 30
    assert r["summary"]["passed"] == 30, [
        (x["id"], x["code"]) for x in r["checks"] if x["status"] != "passed"
    ]
    assert r["track"] == "measurement" and r["manifest_verified"] is True
    assert r["manifest_id"] == manifest_id(measurement_manifest())
    assert len(r["measurement_summary"]["groups"]) == 12
    trials = {t.id: t for t in measurement_plan()}
    for row in r["checks"]:
        t = trials[row["id"]]
        e = row["evidence"]
        assert e["repeat"] == t.repeat and e["arm"] == t.arm
        assert e["max_output_tokens"] == t.max_output_tokens
    data, preview = build_bundle([r, health], credentials)
    assert data and "measurement_manifest" in preview and "tool_diagnostics" in preview
    assert "configuration_sha256" in preview
    assert plan("measurement") == list(trials)


@pytest.mark.parametrize("trigger", [1, 30])
def test_benchmark_change_stops_before_next_attempt(store, credentials, monkeypatch, trigger):
    import aigentics.campaign as campaign

    store.save_profile(Profile(id="ollama", name="Local fixture"))
    real = campaign.measurement_manifest
    changed = [False]
    emitted = [0]

    def manifest():
        result = real()
        if changed[0]:
            result["policy"]["mutation"] = "deliberate calibration fault"
        return result

    monkeypatch.setattr(campaign, "measurement_manifest", manifest)

    def emit(event):
        if event["kind"] == "campaign.result":
            emitted[0] += 1
            if emitted[0] == trigger:
                changed[0] = True

    report = run_campaign(
        store,
        credentials,
        Agent(),
        threading.Event(),
        emit,
        mode="measurement",
        provider_factory=CrewScripted,
    )[1]
    assert report["stop_reason"] == "benchmark_changed"
    assert report["manifest_verified"] is False
    assert len(report["checks"]) == trigger and report["state"] == "needs_attention"


def test_measurement_quick_stop_preserves_unknown_without_replay(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local fixture"))
    cancel = threading.Event()

    def emit(e):
        if e["kind"] == "campaign.result":
            cancel.set()

    first = run_campaign(
        store, credentials, Agent(), cancel, emit, mode="measurement", provider_factory=CrewScripted
    )[1]
    second = run_campaign(
        store,
        credentials,
        Agent(),
        threading.Event(),
        lambda e: None,
        mode="measurement",
        resume=True,
        provider_factory=CrewScripted,
    )[1]
    assert second["id"] == first["id"] and second["checks"][0] == first["checks"][0]
    assert second["summary"]["passed"] == 30
