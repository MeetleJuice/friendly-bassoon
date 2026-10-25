"""Focused coverage must be predeclared, versioned and distinct from full results."""

import json
import threading
from aigentics.campaign import plan, run_campaign
from aigentics.measurement import focused_plan, measurement_plan, summarize_trials
from aigentics.models import Agent, Profile
from aigentics.diagnostics import OFFLINE_CHECK_COUNT
from aigentics.bundles import clean_report
from test_campaign_0120 import CrewScripted


def test_focused_workload_is_explicit_and_does_not_pretend_full_coverage():
    focused = focused_plan()
    assert len(focused) == 32 and len({t.id for t in focused}) == 32
    assert {t.id for t in focused} < {t.id for t in measurement_plan()}
    assert all(t.case_kind == "workflow" for t in focused[:6])
    assert all(t.case_id == "vera_exclusive" for t in focused[6:12])
    assert sum(t.thinking_mode == "off" for t in focused) == 20
    assert not any(t.case_id == "noop" and t.thinking_mode != "off" for t in focused)
    summary = summarize_trials([], mode="focused")
    assert sum(group["unrecorded"] for group in summary["groups"]) == 32
    assert summary["plan_scope"] == "focused" and len(summary["thinking_pairs"]) == 12
    assert plan("focused") == [t.id for t in focused]


def test_native_focused_campaign_and_complete_reviewed_export(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local fixture"))
    health, report = run_campaign(
        store,
        credentials,
        Agent(),
        threading.Event(),
        lambda e: None,
        mode="focused",
        provider_factory=CrewScripted,
    )
    assert health["summary"]["passed"] == OFFLINE_CHECK_COUNT
    assert report["planned_cases"] == len(report["checks"]) == report["summary"]["passed"] == 32, [
        (r["id"], r["status"]) for r in report["checks"] if r["status"] != "passed"
    ]
    assert report["manifest_verified"] and report["stop_reason"] == "finished"
    exported = clean_report(report, credentials)
    assert exported["mode"] == "focused" and exported["measurement_summary"]["plan_scope"] == "focused"
    assert sum(g["unrecorded"] for g in exported["measurement_summary"]["groups"]) == 0
    manager = [r for r in exported["checks"] if r["evidence"].get("role") == "orion"]
    assert len(manager) == 4
    assert manager[0]["evidence"]["team_diagnostics"]
    actors = {s["actor"] for s in manager[0]["evidence"]["actor_statistics"]}
    assert actors == {"orion", "ada", "sentinel"}
    assert "raw_arguments" not in json.dumps(exported)


def test_direct_and_managed_approve_only_equivalent_declared_output_paths(store, credentials):
    from aigentics.team_evaluation import run_trial

    class Aliases(CrewScripted):
        def chat(self, model, messages, tools, **kwargs):
            reply = super().chat(model, messages, tools, **kwargs)
            for call in reply.calls:
                if call.name in ("read_file", "write_file") and "path" in call.arguments:
                    call.arguments["path"] = "./" + call.arguments["path"]
            return reply

    store.save_profile(Profile(id="ollama", name="Local fixture"))
    for arm in ("direct", "managed"):
        trial = next(t for t in focused_plan() if t.case_kind == "workflow" and t.arm == arm)
        row = run_trial(store, credentials, Agent().primary, trial, threading.Event(), Aliases)
        assert row["status"] == "passed", row
