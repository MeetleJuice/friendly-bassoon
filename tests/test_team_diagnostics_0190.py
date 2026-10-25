"""Bounded schema feedback and argument-free evidence for actual native dispatch."""

import json
import pytest
from aigentics.diagnostics import model_evidence
from aigentics.inference import public_run_details
from test_coordination_0180 import PilotModel, execute, call
import test_coordination_0180 as base


class MalformedOnce(PilotModel):
    def chat(self, model, messages, tools, **kwargs):
        if any(t["function"]["name"] == "dispatch_worker" for t in tools):
            previous = [m for m in messages if m["role"] == "tool"]
            if previous and "Arguments rejected" in previous[-1]["content"]:
                status = next(
                    json.loads(m["content"]) for m in reversed(previous[:-1]) if m["content"].startswith("{")
                )
                return call("dispatch_worker", role="ada", handoff=status["handoff"])
            if len(previous) == 1:
                return call("dispatch_worker", role="ADA", revision="PRIVATE")
        return super().chat(model, messages, tools, **kwargs)


def test_one_schema_correction_within_shared_budget(store, credentials, team_case):
    sid, state = execute(store, credentials, team_case, MalformedOnce)
    assert state == "completed"
    summary = next(e["data"] for e in store.events(sid) if e["kind"] == "team.summary")
    assert summary["format_feedback_count"] == 1 and summary["budget"]["calls"] == 12
    assert len(summary["children"]) == 2
    failed = [row for row in summary["diagnostics"] if row["status"] == "failed"]
    assert len(failed) == 1 and failed[0]["code"] == "ARGUMENT_VALIDATION"
    safe = public_run_details({"team_diagnostics": summary["diagnostics"]})
    assert "PRIVATE" not in json.dumps(safe) and "revision" not in json.dumps(safe)


def test_persistent_bad_arguments_stop_before_dispatch_and_export_reason(store, credentials, team_case):
    class Repeated(MalformedOnce):
        def chat(self, model, messages, tools, **kwargs):
            if any(t["function"]["name"] == "dispatch_worker" for t in tools) and any(
                m["role"] == "tool" for m in messages
            ):
                return call("dispatch_worker", role="ADA", revision="PRIVATE")
            return super().chat(model, messages, tools, **kwargs)

    sid, state = execute(store, credentials, team_case, Repeated)
    assert state == "needs_review"
    events = store.events(sid)
    data = public_run_details(model_evidence(events))
    assert data["team_error_code"] == "ARGUMENT_VALIDATION"
    assert len(data["team_diagnostics"]) == 3
    assert "PRIVATE" not in json.dumps(data)
    assert len(store.sessions()) == 1


def test_old_handle_after_build_cannot_start_review(store, credentials, team_case):
    class Stale(PilotModel):
        def chat(self, model, messages, tools, **kwargs):
            if any(t["function"]["name"] == "dispatch_worker" for t in tools):
                previous = [m for m in messages if m["role"] == "tool"]
                if previous and json.loads(previous[-1]["content"])["evidence"]:
                    return call("dispatch_worker", role="sentinel", handoff="h1")
            return super().chat(model, messages, tools, **kwargs)

    sid, state = execute(store, credentials, team_case, Stale)
    assert state == "needs_review"
    evidence = model_evidence(store.events(sid))
    assert evidence["team_error_code"] == "STALE_HANDOFF"
    assert len([s for s in store.sessions() if s["parent"] == sid]) == 1


def test_chronological_actor_totals_include_manager_and_omitted_trace_tail(store, credentials, team_case):
    sid, state = execute(store, credentials, team_case)
    assert state == "completed"
    children = [s["id"] for s in store.sessions() if s["parent"] == sid]
    events = sorted(
        store.events(sid) + [e for child in children for e in store.events(child)],
        key=lambda e: e["sequence"],
    )
    evidence = model_evidence(events)
    actors = {row["actor"]: row for row in evidence["actor_statistics"]}
    assert {key: row["requests"] for key, row in actors.items()} == {"orion": 4, "ada": 4, "sentinel": 3}
    assert sum(row["eval_count"] for row in actors.values()) == 11
    assert evidence["trace_coverage"] == {"responses_recorded": 11, "traces_retained": 8}
    assert evidence["request_traces"][2]["actor"] == "ada"


def test_malformed_export_cannot_copy_private_actor_or_tool_fields():
    data = public_run_details(
        {
            "actor_statistics": [{"actor": {"PRIVATE": 1}, "requests": 4}],
            "team_diagnostics": [
                {
                    "tool": "dispatch_worker",
                    "stage": "build",
                    "status": "failed",
                    "argument_types": {"role": "PRIVATE", "SECRET": "str"},
                    "code": "PRIVATE",
                    "raw": "PRIVATE",
                }
            ],
        }
    )
    assert "PRIVATE" not in json.dumps(data)
    assert data["actor_statistics"] == []


@pytest.fixture
def team_case(store, tmp_path):
    return base.pilot.__wrapped__(store, tmp_path)


def test_self_dispatch_stops_without_format_repair(store, credentials, team_case):
    class SelfRoute(PilotModel):
        fault = "recursion"

    sid, state = execute(store, credentials, team_case, SelfRoute)
    assert state == "needs_review"
    summary = next(e["data"] for e in store.events(sid) if e["kind"] == "team.summary")
    assert summary["format_feedback_count"] == 0 and not summary["children"]
    assert model_evidence(store.events(sid))["team_error_code"] == "ROUTE_REJECTED"
