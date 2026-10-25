"""Real native runtime/tools across the full crew; no live model or secret calls."""

import json
import threading
import pytest
from aigentics import campaign
from aigentics.crew_cases import CASES
from aigentics.diagnostics import OFFLINE_CHECK_COUNT
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.reporting import issue_body, prepare_browser_draft
from test_suite_080 import Scripted


class CrewScripted(Scripted):
    def chat(self, model, messages, tools):
        prompt = next(m["content"] for m in messages if m["role"] == "user")
        from aigentics.contracts import contract_prompt

        case = next((c for c in CASES if c.prompt == prompt or contract_prompt(c) == prompt), None)
        if case is None:
            return super().chat(model, messages, tools)
        calls = [("read_file", {"path": name}) for name in case.required_reads]
        for name, data in {
            **case.outputs,
            **{n: json.dumps(v).encode() for n, v in case.output_json.items()},
        }.items():
            calls.append(
                (
                    "write_file",
                    {
                        "path": name,
                        "content": data.decode(),
                        "expected_sha256": "last_read" if name in case.files else "new",
                    },
                )
            )
            calls.append(("read_file", {"path": name}))
        index = sum(m["role"] == "tool" for m in messages)
        if index < len(calls):
            name, args = calls[index]
            return Reply(calls=[ToolCall(id=str(index), name=name, arguments=args)])
        return Reply(content=json.dumps(case.answer) if case.answer is not None else "Verified.")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_specialist_native_actions_and_oracle(case, store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    row = campaign.role_case(store, credentials, Agent().primary, case, threading.Event(), CrewScripted)
    assert row["status"] == "passed", row
    assert all(row["evidence"]["requirement_checks"].values())
    assert row["evidence"]["native_calls_total"] >= len(case.required_reads)
    assert not store.sessions()


def test_full_campaign_has_66_distinct_results_two_shareable_reports(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    events = []
    reports = campaign.run_campaign(
        store, credentials, Agent(), threading.Event(), events.append, provider_factory=CrewScripted
    )
    health, report = reports
    assert health["summary"]["passed"] == OFFLINE_CHECK_COUNT
    assert report["summary"]["passed"] == report["planned_cases"] == 66, report
    assert len({r["id"] for r in report["checks"]}) == 66
    assert report["state"] == "passed"
    assert len([e for e in events if e["kind"] == "campaign.result"]) == 66
    from aigentics.diagnostic_storage import encode_report, decode_report

    stored = encode_report(report, credentials)
    assert len(stored.encode()) <= 1_000_000
    assert decode_report(stored) == credentials.scrub(report)
    assert not store.sessions()
    assert all(len(prepare_browser_draft(*issue_body(r, credentials))) <= 7500 for r in reports)
    saved = {r["id"]: r["payload"] for r in store.diagnostic_reports()}
    assert report["id"] in saved and health["id"] in saved
    assert len(saved) == 2


def test_cancel_then_continue_retains_original_results(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    cancel = threading.Event()

    def emit(e):
        if e["kind"] == "campaign.result":
            cancel.set()

    first = campaign.run_campaign(store, credentials, Agent(), cancel, emit, provider_factory=CrewScripted)[1]
    assert first["state"] == "cancelled" and len(first["checks"]) == 1
    second = campaign.run_campaign(
        store,
        credentials,
        Agent(),
        threading.Event(),
        lambda e: None,
        resume=True,
        provider_factory=CrewScripted,
    )[1]
    assert second["id"] == first["id"]
    assert second["checks"][0] == first["checks"][0]
    assert second["summary"]["passed"] == 66


def test_unknown_inflight_case_marked_never_replayed(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    cancel = threading.Event()
    cancel.set()
    report = campaign.run_campaign(
        store, credentials, Agent(), cancel, lambda e: None, provider_factory=CrewScripted
    )[1]
    report["state"] = "interrupted"
    report["active_case"] = campaign.PLAN_IDS[0]
    store.save_diagnostic(report)
    result = campaign.run_campaign(
        store,
        credentials,
        Agent(),
        threading.Event(),
        lambda e: None,
        resume=True,
        provider_factory=CrewScripted,
    )[1]
    assert result["id"] == report["id"]
    assert result["checks"][0]["code"] == "INTERRUPTED_CASE_NOT_REPLAYED"
    assert result["summary"] == {"passed": 65, "failed": 1, "skipped": 0, "warning": 0}


def test_quick_has_no_model_calls(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))

    def forbidden(*args):
        raise AssertionError("No model request allowed")

    health, report = campaign.run_campaign(
        store,
        credentials,
        Agent(),
        threading.Event(),
        lambda e: None,
        mode="quick",
        provider_factory=forbidden,
    )
    assert health["state"] == "passed" and report["checks"] == []
    assert report["state"] == "passed"


def test_model_change_cannot_resume_old_configuration(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    stop = threading.Event()
    stop.set()
    first = campaign.run_campaign(
        store, credentials, Agent(), stop, lambda e: None, provider_factory=CrewScripted
    )[1]
    other = Agent(primary={"profile_id": "ollama", "model": "different"})
    second = campaign.run_campaign(
        store, credentials, other, stop, lambda e: None, resume=True, provider_factory=CrewScripted
    )[1]
    assert first["id"] != second["id"]


def test_prose_without_reads_never_passes_specialist(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    case = next(c for c in CASES if c.answer is not None)

    class Prose(CrewScripted):
        def chat(self, *args):
            return Reply(content=json.dumps(case.answer))

    row = campaign.role_case(store, credentials, Agent().primary, case, threading.Event(), Prose)
    assert row["status"] == "failed"
    assert row["evidence"]["requirement_checks"]["FINAL_ANSWER"]
    assert not row["evidence"]["requirement_checks"]["SOURCE_READS"]
