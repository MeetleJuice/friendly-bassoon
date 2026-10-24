"""Requirement-level evidence must distinguish correct bytes from complete work."""

import threading

import pytest

from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.test_suite import REQUIREMENT_LABELS, requirement_failures, run_suite
from test_suite_080 import Scripted


def response(name, **arguments):
    return Reply(calls=[ToolCall(id=name, name=name, arguments=arguments)])


def provider(replies):
    class Provider(Scripted):
        def chat(self, model, messages, tools):
            index = sum(message["role"] == "tool" for message in messages)
            return replies[index] if index < len(replies) else Reply(content="Finished.")

    return Provider


def run(store, credentials, cases, factory=Scripted):
    store.save_profile(Profile(id="ollama", name="Fixture"))
    return run_suite(
        store,
        credentials,
        Agent(),
        threading.Event(),
        lambda event: None,
        factory,
        case_ids=cases,
    )


def test_all_baseline_requirements_have_fixed_boolean_evidence(store, credentials):
    report = run(store, credentials, None)
    assert report["summary"]["passed"] == 18
    for row in report["checks"]:
        checks = row["evidence"]["requirement_checks"]
        assert checks and set(checks) <= REQUIREMENT_LABELS.keys()
        assert all(value is True for value in checks.values()), row
        assert row["evidence"]["unmet_requirements"] == []


@pytest.mark.parametrize("case", ["edit", "stale"])
def test_correct_bytes_without_post_read_explain_missing_requirement(store, credentials, case):
    read = response("read_file", path="output.txt")
    write = response("write_file", path="output.txt", content="lighthouse\n", expected_sha256="last_read")
    replies = [read, write]
    if case == "stale":
        rejected = response("write_file", path="output.txt", content="lighthouse\n", expected_sha256="0" * 64)
        replies = [read, rejected, read, write]
    row = run(store, credentials, [case], provider(replies))["checks"][0]
    assert row["status"] == "failed"
    assert row["evidence"]["file_matches"] is True
    assert row["evidence"]["requirement_checks"]["VERIFIED_WRITE"] is True
    assert row["evidence"]["requirement_checks"]["POST_WRITE_READBACK"] is False
    assert row["evidence"]["task_checks"]["missing_readbacks"] == 1
    assert "POST_WRITE_READBACK" in row["evidence"]["unmet_requirements"]
    assert row["evidence"]["requirement_checks"]["STALE_ORDER" if case == "stale" else "EDIT_ORDER"] is False


def test_edit_cannot_skip_original_read_with_a_known_hash(store, credentials):
    import hashlib

    replies = [
        response(
            "write_file",
            path="output.txt",
            content="lighthouse\n",
            expected_sha256=hashlib.sha256(b"old\n").hexdigest(),
        ),
        response("read_file", path="output.txt"),
    ]
    row = run(store, credentials, ["edit"], provider(replies))["checks"][0]
    assert row["status"] == "failed"
    assert row["evidence"]["task_checks"]["status"] == "passed"
    assert row["evidence"]["requirement_checks"]["EDIT_ORDER"] is False


@pytest.mark.parametrize("cases", [["missing"], ["edit", "edit"], []])
def test_invalid_selection_rejected_before_creating_reports(store, credentials, cases):
    with pytest.raises(ValueError, match="unique known"):
        run(store, credentials, cases)
    assert store.diagnostic_reports() == []


def test_selected_cases_run_in_requested_order_and_have_correct_denominator(store, credentials):
    report = run(store, credentials, ["stale", "edit"])
    assert report["state"] == "passed"
    assert report["planned_cases"] == 2
    assert report["case_ids"] == ["stale", "edit"]
    assert [row["id"] for row in report["checks"]] == ["stale", "edit"]
    assert len(store.diagnostic_reports()) == 1


def test_unknown_private_requirements_cannot_become_failure_codes():
    assert requirement_failures({"PRIVATE_KEY": False, "POST_WRITE_READBACK": False}) == [
        "POST_WRITE_READBACK"
    ]


def test_wrong_noop_order_has_specific_evidence(store, credentials):
    row = run(
        store,
        credentials,
        ["noop"],
        provider(
            [
                response("read_file", path="output.txt"),
                response(
                    "write_file", path="output.txt", content="lighthouse\n", expected_sha256="last_read"
                ),
            ]
        ),
    )["checks"][0]
    assert row["status"] == "failed"
    assert row["evidence"]["requirement_checks"]["NOOP_NO_WRITE"] is True
    assert row["evidence"]["requirement_checks"]["NOOP_ORDER"] is False


def test_campaign_child_runs_do_not_persist_or_prune(store, credentials, monkeypatch):
    store.save_profile(Profile(id="ollama", name="Fixture"))
    writes = []
    monkeypatch.setattr(store, "save_diagnostic", lambda report: writes.append(report))
    monkeypatch.setattr(store, "prune", lambda: pytest.fail("Child must not prune campaign records"))
    report = run_suite(
        store,
        credentials,
        Agent(),
        threading.Event(),
        lambda event: None,
        Scripted,
        case_ids=["create"],
        persist=False,
    )
    assert report["state"] == "passed"
    assert report["checks"][0]["evidence"]["execution_counts"]["writes_verified"] == 1
    assert not writes and not store.diagnostic_reports()


def test_tool_timeline_is_bounded_and_contains_no_raw_inputs():
    from aigentics.test_suite import bounded_tool_timeline

    row = {
        "tool": "write_file",
        "status": "failed",
        "duration_ms": 999999999,
        "verified": False,
        "error_type": "PermissionError",
        "path": "PRIVATE",
        "arguments": {"content": "PRIVATE"},
        "message": "PRIVATE",
    }
    timeline = bounded_tool_timeline([row] * 100)
    assert len(timeline) == 32
    assert all(
        item
        == {
            "tool": "write_file",
            "status": "failed",
            "duration_ms": 300000,
            "verified": False,
            "error_type": "PermissionError",
        }
        for item in timeline
    )
    assert "PRIVATE" not in str(timeline)
    assert bounded_tool_timeline([{"tool": "PRIVATE", "status": "failed"}]) == []


def test_actual_native_tool_timeline_reports_order(store, credentials):
    report = run(store, credentials, ["edit"])
    timeline = report["checks"][0]["evidence"]["tool_timeline"]
    assert [row["tool"] for row in timeline] == ["read_file", "write_file", "read_file"]
    assert all(row["status"] == "succeeded" for row in timeline)
    assert timeline[1]["verified"] is True
