"""0.20 targeted evidence: real review dispatch, budgets and grounded citations."""

# Imported pytest fixture is deliberately named by its consumer arguments.
# ruff: noqa: F811

import json
import threading
from pathlib import Path

from aigentics.bundles import clean_report
from aigentics.campaign import role_case
from aigentics.crew_cases import MEASUREMENT_CASES
from aigentics.evidence import base_report
from aigentics.measurement import focused_plan, manifest_id, measurement_plan, summarize_trials
from aigentics.models import Agent, Profile, Reply
from aigentics.team_evaluation import run_trial
from test_campaign_0120 import CrewScripted
from test_coordination_0180 import PilotModel, execute, pilot  # noqa: F401


def test_direct_reservations_are_measured_not_placeholder_zero(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local fixture"))
    trial = next(t for t in focused_plan() if t.arm == "direct")
    row = run_trial(store, credentials, Agent().primary, trial, threading.Event(), CrewScripted)
    assert row["status"] == "passed"
    metrics = row["evidence"]["team_metrics"]
    assert metrics["total_calls"] > 0
    assert metrics["output_reserved"] == metrics["total_calls"] * 4096
    assert metrics["output_reserved"] <= metrics["output_limit"]
    assert metrics["review_required"] is metrics["review_completed"] is False


def test_required_review_rejects_early_manager_final_but_optional_review_still_works(
    store, credentials, pilot
):
    class BuildOnly(PilotModel):
        review = False

    sid, state = execute(store, credentials, pilot, BuildOnly, require_review=True)
    assert state == "needs_review"
    assert (pilot[1] / "answer.txt").read_bytes() == b"ready\n"
    assert any(
        e["kind"] == "team.error" and e["data"]["code"] == "REVIEW_REQUIRED" for e in store.events(sid)
    )
    assert len([s for s in store.sessions() if s["parent"] == sid]) == 1
    (pilot[1] / "answer.txt").unlink()
    sid, state = execute(store, credentials, pilot, BuildOnly)
    assert state == "completed"


def test_required_review_cannot_be_satisfied_by_reviewer_prose_without_reads(store, credentials, pilot):
    class ProseReview(PilotModel):
        def chat(self, model, messages, tools, **kwargs):
            if "Your agent name is Sentinel" in messages[0]["content"]:
                return Reply(content="Everything is correct; trust me.")
            return super().chat(model, messages, tools, **kwargs)

    sid, state = execute(store, credentials, pilot, ProseReview, require_review=True)
    assert state != "completed"
    summary = next(e["data"] for e in store.events(sid) if e["kind"] == "team.summary")
    assert len(summary["children"]) == 2
    assert summary["stages"][-1]["role"] == "sentinel"
    assert summary["stages"][-1]["verified"] is False


def test_mandatory_review_trials_include_real_sentinel_and_shared_budget(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local fixture"))
    trial = next(t for t in focused_plan() if t.case_id == "ada_review")
    row = run_trial(store, credentials, Agent().primary, trial, threading.Event(), CrewScripted)
    assert row["status"] == "passed", row
    e = row["evidence"]
    assert e["requirement_checks"]["REVIEW_COMPLETED"] is True
    assert e["team_metrics"]["review_required"] is e["team_metrics"]["review_completed"] is True
    assert e["team_metrics"]["dispatches"] == e["team_metrics"]["stages_verified"] == 2
    assert {a["actor"] for a in e["actor_statistics"]} == {"ada", "sentinel", "orion"}
    assert e["team_metrics"]["total_calls"] <= 12
    report = base_report("crew_campaign", "crew-campaign-8", "Synthetic")
    report["checks"] = [row]
    safe = clean_report(report, credentials)["checks"][0]["evidence"]["team_metrics"]
    assert safe["review_required"] is safe["review_completed"] is True


def test_shifted_line_citation_requires_native_search_not_just_correct_guess(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local fixture"))
    case = next(c for c in MEASUREMENT_CASES if c.id == "sentinel_shifted")

    class GuessWithoutSearch(CrewScripted):
        def chat(self, model, messages, tools, **kwargs):
            result = super().chat(model, messages, tools, **kwargs)
            if any(call.name == "search" for call in result.calls):
                return Reply(content=json.dumps(case.answer))
            return result

    good = role_case(
        store, credentials, Agent().primary, case, threading.Event(), CrewScripted, clarified=True
    )
    assert good["status"] == "passed"
    missing = role_case(
        store, credentials, Agent().primary, case, threading.Event(), GuessWithoutSearch, clarified=True
    )
    assert missing["status"] == "failed"
    assert missing["evidence"]["requirement_checks"]["SOURCE_READS"] is True
    assert missing["evidence"]["requirement_checks"]["FINAL_ANSWER"] is True
    assert missing["evidence"]["requirement_checks"]["TASK_VERIFIED"] is False


def test_archived_focused4_export_does_not_gain_new_cases_or_change_summary(credentials):
    manifest = json.loads(
        (Path(__file__).parents[1] / "docs/benchmarks/crew-measurement-4.json").read_text(encoding="utf-8")
    )
    rows = [
        {
            "id": t.id,
            "status": "failed",
            "code": "ROLE_REQUIREMENTS_NOT_MET",
            "message": "Synthetic failed trial",
            "duration_ms": 7,
            "evidence": {},
        }
        for t in focused_plan("crew-measurement-4")
    ]
    report = base_report("crew_campaign", "crew-campaign-7", "Synthetic")
    report.update(
        mode="focused", measurement_manifest=manifest, manifest_id=manifest_id(manifest), checks=rows
    )
    exported = clean_report(report, credentials)
    assert exported["measurement_manifest"] == manifest
    assert exported["measurement_summary"] == summarize_trials(
        rows, version="crew-measurement-4", mode="focused"
    )
    assert sum(g["recorded_repetitions"] for g in exported["measurement_summary"]["groups"]) == 24
    assert len(measurement_plan("crew-measurement-4")) == 56


def test_actor_totals_override_truncated_preview_for_current_measurement_only():
    trial = next(t for t in focused_plan() if t.arm == "managed")
    row = {
        "id": trial.id,
        "status": "passed",
        "evidence": {
            "actor_statistics": [{"actor": "ada", "eval_count": 60, "eval_samples": 10}],
            "request_traces": [{"usage": {"eval_count": 7}}],
        },
    }
    current = next(
        g
        for g in summarize_trials([row])["groups"]
        if g["case_kind"] == "workflow" and g["arm"] == "managed" and g["case_id"] == "ada_repair"
    )
    archived = next(
        g
        for g in summarize_trials([row], version="crew-measurement-4")["groups"]
        if g["case_kind"] == "workflow" and g["arm"] == "managed"
    )
    assert current["known_usage"]["eval_count"] == 60
    assert archived["known_usage"]["eval_count"] == 7
