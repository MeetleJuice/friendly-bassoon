"""Campaign lifecycle regressions: supersession, uncertain work and deadline isolation."""

import threading
from contextlib import closing
import pytest

from aigentics import campaign
from aigentics.evidence import base_report
from aigentics.models import Agent, Profile
from aigentics.regression_checks import crew_evaluation_check
from aigentics.store import Store


def saved(store, scope, state, created, checks=()):
    report = base_report("crew_campaign", campaign.CAMPAIGN_VERSION, "Synthetic counters only")
    report.update(
        local_scope=scope,
        state=state,
        created=created,
        mode="deep",
        planned_cases=len(campaign.PLAN_IDS),
        checks=list(checks),
        active_case=None,
    )
    store.save_diagnostic(report)
    return report


def test_completed_newer_campaign_supersedes_older_cancelled_campaign(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    scope = campaign.campaign_scope(store, Agent(), "deep")
    saved(store, scope, "cancelled", "2026-10-23T10:00:00+00:00")
    saved(store, scope, "passed", "2026-10-23T11:00:00+00:00")
    assert campaign.latest_resumable(store, scope) is None


def test_fully_recorded_cancelled_campaign_is_not_offered_as_unfinished(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    scope = campaign.campaign_scope(store, Agent(), "deep")
    rows = [{"id": identity, "status": "passed", "evidence": {}} for identity in campaign.PLAN_IDS]
    saved(store, scope, "cancelled", "2026-10-23T10:00:00+00:00", rows)
    assert campaign.latest_resumable(store, scope) is None


def test_newest_unfinished_campaign_is_resumable_despite_unrelated_newer_report(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    scope = campaign.campaign_scope(store, Agent(), "deep")
    expected = saved(store, scope, "interrupted", "2026-10-23T10:00:00+00:00")
    saved(store, "different-scope", "passed", "2026-10-23T11:00:00+00:00")
    assert campaign.latest_resumable(store, scope)["id"] == expected["id"]


def test_per_case_timer_cannot_poison_later_cases(store, credentials, monkeypatch):
    store.save_profile(Profile(id="ollama", name="Local"))
    requested = []

    class Health:
        def __init__(self, *args):
            pass

        def run(self, cancel, emit, include_network):
            report = base_report("diagnostic", "7", "Offline fixture")
            report["state"] = "passed"
            return report

    def exercise(store, credentials, agent, cancel, emit, **kwargs):
        name = kwargs["case_ids"][0]
        requested.append((name, cancel.is_set()))
        if len(requested) == 1:
            # Runtime timers set their own supplied event when one session expires.
            cancel.set()
        row = {
            "id": name,
            "status": "failed" if len(requested) == 1 else "passed",
            "code": "SESSION_BUDGET_EXHAUSTED" if len(requested) == 1 else "OK",
            "message": "Synthetic timer isolation",
            "duration_ms": 1,
            "evidence": {},
        }
        return {"checks": [row]}

    monkeypatch.setattr(campaign, "DiagnosticRunner", Health)
    monkeypatch.setattr(campaign, "plan", lambda mode: ["baseline-read", "baseline-map"])
    monkeypatch.setattr(campaign, "run_suite", exercise)
    report = campaign.run_campaign(store, credentials, Agent(), threading.Event(), lambda event: None)[1]
    assert requested == [("read", False), ("map", False)]
    assert report["state"] == "needs_attention"
    assert report["summary"]["passed"] == report["summary"]["failed"] == 1


def test_packaged_crew_fixture_runs_without_model_server(credentials):
    assert crew_evaluation_check(credentials) == {"crew_fixture_verified": True, "external_requests": 0}


class OfflineHealth:
    def __init__(self, *args):
        pass

    def run(self, cancel, emit, include_network):
        report = base_report("diagnostic", "7", "Offline fixture")
        row = {"id": "database", "status": "passed", "code": "OK", "duration_ms": 1, "evidence": {}}
        report.update(state="passed", checks=[row], summary={"passed": 1, "failed": 0})
        emit({"kind": "diagnostic.result", "data": row})
        return report


def case_result(identity, passed=True):
    return {
        "id": identity,
        "status": "passed" if passed else "failed",
        "code": "OK" if passed else "REQUIRED_OPERATIONS_NOT_VERIFIED",
        "message": "Synthetic isolated result",
        "duration_ms": 1,
        "evidence": {},
    }


def test_actual_store_restart_keeps_completed_and_does_not_replay_inflight(
    credentials, tmp_path, monkeypatch
):
    monkeypatch.setattr(campaign, "DiagnosticRunner", OfflineHealth)
    monkeypatch.setattr(campaign, "plan", lambda mode: ["baseline-read", "baseline-map", "baseline-search"])
    path = tmp_path / "restart.sqlite3"
    completed = case_result("baseline-read")
    with closing(Store(path, credentials)) as original:
        original.save_profile(Profile(id="ollama", name="Local"))
        scope = campaign.campaign_scope(original, Agent(), "deep")
        report = saved(original, scope, "running", "2026-10-24T10:00:00+00:00", [completed])
        report.update(active_case="baseline-map", duration_ms=240000)
        original.save_diagnostic(report)
    calls = []

    def exercise(store, credentials, agent, cancel, emit, **kwargs):
        name = kwargs["case_ids"][0]
        calls.append(name)
        return {"checks": [case_result(name)]}

    monkeypatch.setattr(campaign, "run_suite", exercise)
    events = []
    with closing(Store(path, credentials)) as reopened:
        recovered = next(r["payload"] for r in reopened.diagnostic_reports() if r["id"] == report["id"])
        assert recovered["state"] == "interrupted"
        health, result = campaign.run_campaign(
            reopened, credentials, Agent(), threading.Event(), events.append, resume=True
        )
    assert calls == ["search"]
    assert result["id"] == report["id"] and result["checks"][0] == completed
    assert result["checks"][1]["code"] == "INTERRUPTED_CASE_NOT_REPLAYED"
    assert result["summary"] == {"passed": 2, "failed": 1, "skipped": 0, "warning": 0}
    assert result["duration_ms"] >= 240000
    assert result["checks"][1]["evidence"]["timing_unknown"] is True
    assert result["checks"][1]["duration_ms"] == 0
    assert result["budget_used_ms"] >= result["duration_ms"] + 180000
    assert health["state"] == "passed" and result["state"] == "needs_attention"
    assert {row["id"] for row in result["checks"]} == {
        "baseline-read",
        "baseline-map",
        "baseline-search",
    }
    assert len([e for e in events if e["kind"] == "diagnostic.result"]) == 1
    assert len([e for e in events if e["kind"] == "campaign.result"]) == 3


def test_resumed_exhausted_budget_never_starts_model_work(store, credentials, monkeypatch):
    store.save_profile(Profile(id="ollama", name="Local"))
    scope = campaign.campaign_scope(store, Agent(), "deep")
    report = saved(store, scope, "cancelled", "2026-10-24T10:00:00+00:00")
    report["duration_ms"] = campaign.MAX_SECONDS * 1000
    store.save_diagnostic(report)
    monkeypatch.setattr(campaign, "DiagnosticRunner", OfflineHealth)

    def forbidden(*args, **kwargs):
        raise AssertionError("Exhausted campaign must not start a model request")

    monkeypatch.setattr(campaign, "run_suite", forbidden)
    monkeypatch.setattr(campaign, "role_case", forbidden)
    result = campaign.run_campaign(
        store, credentials, Agent(), threading.Event(), lambda event: None, resume=True
    )[1]
    assert result["id"] == report["id"] and result["checks"] == []
    assert result["state"] == "needs_attention"
    assert result["stop_reason"] == "campaign_budget"
    assert result["planned_cases"] == len(campaign.PLAN_IDS)
    assert result["summary"]["passed"] == 0
    assert campaign.latest_resumable(store, scope) is None


def test_elapsed_campaign_deadline_stops_remaining_cases_without_false_cancel(
    store, credentials, monkeypatch
):
    store.save_profile(Profile(id="ollama", name="Local"))
    monkeypatch.setattr(campaign, "DiagnosticRunner", OfflineHealth)
    monkeypatch.setattr(campaign, "plan", lambda mode: ["baseline-read", "baseline-map"])
    elapsed = [0]
    monkeypatch.setattr(campaign.time, "monotonic", lambda: elapsed[0])
    calls = []

    def exercise(store, credentials, agent, cancel, emit, **kwargs):
        name = kwargs["case_ids"][0]
        calls.append(name)
        elapsed[0] = campaign.MAX_SECONDS + 1
        return {"checks": [case_result(name)]}

    monkeypatch.setattr(campaign, "run_suite", exercise)
    external_cancel = threading.Event()
    result = campaign.run_campaign(store, credentials, Agent(), external_cancel, lambda event: None)[1]
    assert calls == ["read"] and not external_cancel.is_set()
    assert result["state"] == "needs_attention" and len(result["checks"]) == 1
    assert result["summary"]["passed"] == 1 and result["planned_cases"] == 2
    assert result["duration_ms"] >= campaign.MAX_SECONDS * 1000
    assert result["stop_reason"] == "campaign_budget"


def test_uncertain_budget_reservation_persists_before_resume_health(store, credentials, monkeypatch):
    store.save_profile(Profile(id="ollama", name="Local"))
    scope = campaign.campaign_scope(store, Agent(), "deep")
    report = saved(store, scope, "interrupted", "2026-10-24T10:00:00+00:00")
    report.update(
        active_case="baseline-read", active_case_budget_ms=180000, duration_ms=3000, budget_used_ms=3000
    )
    store.save_diagnostic(report)

    class CrashBeforeHealth:
        def __init__(self, *args):
            pass

        def run(self, *args, **kwargs):
            raise RuntimeError("Synthetic interruption before health completion")

    monkeypatch.setattr(campaign, "DiagnosticRunner", CrashBeforeHealth)
    with pytest.raises(RuntimeError, match="Synthetic interruption"):
        campaign.run_campaign(store, credentials, Agent(), threading.Event(), lambda event: None, resume=True)
    retained = next(row["payload"] for row in store.diagnostic_reports() if row["id"] == report["id"])
    assert retained["budget_used_ms"] == 183000
    assert retained["duration_ms"] == 3000
    assert retained["active_case"] is None and retained["active_case_budget_ms"] == 0
    assert retained["checks"][0]["code"] == "INTERRUPTED_CASE_NOT_REPLAYED"
    assert retained["checks"][0]["evidence"]["timing_unknown"] is True


def test_completed_case_budget_is_saved_before_result_delivery(store, credentials, monkeypatch):
    store.save_profile(Profile(id="ollama", name="Local"))
    monkeypatch.setattr(campaign, "DiagnosticRunner", OfflineHealth)
    monkeypatch.setattr(campaign, "plan", lambda mode: ["baseline-read", "baseline-map"])
    elapsed = [0]
    monkeypatch.setattr(campaign.time, "monotonic", lambda: elapsed[0])

    def exercise(store, credentials, agent, cancel, emit, **kwargs):
        elapsed[0] = 100
        return {"checks": [case_result(kwargs["case_ids"][0])]}

    def lost_delivery(event):
        if event["kind"] == "campaign.result":
            raise RuntimeError("Synthetic delivery interruption")

    monkeypatch.setattr(campaign, "run_suite", exercise)
    with pytest.raises(RuntimeError, match="Synthetic delivery interruption"):
        campaign.run_campaign(store, credentials, Agent(), threading.Event(), lost_delivery)
    report = next(
        row["payload"] for row in store.diagnostic_reports() if row["payload"].get("kind") == "crew_campaign"
    )
    assert report["checks"][0]["id"] == "baseline-read"
    assert report["duration_ms"] == report["budget_used_ms"] == 100000
    assert report["active_case"] is None and report["active_case_budget_ms"] == 0
