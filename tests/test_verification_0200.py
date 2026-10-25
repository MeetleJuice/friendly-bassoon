"""Final-proof feedback cannot create a second write attempt or erase failures."""

import json
import threading
import pytest
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.runtime import Runtime
from aigentics.task_checks import TaskChecks


def call(name, **arguments):
    return Reply(calls=[ToolCall(id="proof", name=name, arguments=arguments)])


def exercise(
    store,
    credentials,
    tmp_path,
    after=None,
    *,
    prefix=None,
    acceptance=None,
    approve=lambda *args: True,
    max_steps=8,
    before_final=lambda: None,
    cancel_on_feedback=False,
    checks_extra=None,
):
    sequence = list(
        prefix
        or [
            call("write_file", path="output.json", content='{"ok":true}'),
            call("write_file", path="output.json", content='{"ok":true}', expected_sha256="new"),
        ]
    ) + [
        Reply(content="Finished."),
        after or call("read_file", path="output.json"),
        Reply(content="Verified."),
    ]
    seen = []
    cancel = threading.Event()

    def emit(event):
        if cancel_on_feedback and event["kind"] == "completion.feedback_requested":
            cancel.set()

    class Model:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, model, messages, tools):
            seen.append([t["function"]["name"] for t in tools])
            response = sequence.pop(0) if sequence else Reply(content="Done.")
            if response.content == "Finished.":
                before_final()
            return response

    store.save_profile(Profile(id="ollama", name="Synthetic"))
    sid, state = Runtime(store, credentials, Model).run(
        Agent(max_steps=max_steps),
        tmp_path,
        "Create and verify output.json",
        approve,
        cancel=cancel,
        emit=emit,
        task_checks=TaskChecks(
            write_targets=["output.json"],
            json_outputs={"output.json": "object"},
            completion_feedback=True,
            **(checks_extra or {}),
        ),
        acceptance=acceptance,
    )
    events = store.events(sid)
    summary = next(e["data"] for e in events if e["kind"] == "run.summary")
    return state, summary, events, seen


def test_valid_corrected_write_gets_one_read_only_proof_turn(store, credentials, tmp_path):
    state, summary, events, seen = exercise(store, credentials, tmp_path)
    assert state == "completed"
    assert summary["tools"]["failed"] == 1
    assert summary["tools"]["recovered_proposal_errors"] == 1
    assert summary["completion_feedback_count"] == summary["verification_feedback_count"] == 1
    assert summary["unresolved_tool_errors"] == 0
    assert seen[-2:] == [["read_file"], ["read_file"]]
    feedback = [e for e in events if e["kind"] == "completion.feedback_requested"]
    assert len(feedback) == 1 and feedback[0]["data"]["verification_only"] is True


@pytest.mark.parametrize("operation", ["write", "other_read", "command", "no_read"])
def test_proof_turn_rejects_mutation_unrelated_reads_and_unproven_done(
    store, credentials, tmp_path, operation
):
    (tmp_path / "other.txt").write_text("unrelated", encoding="utf-8")
    attempts = {
        "write": call("write_file", path="output.json", content="{}", expected_sha256="last_read"),
        "other_read": call("read_file", path="other.txt"),
        "command": call("run_command", command="echo should-not-run"),
        "no_read": Reply(content="Done."),
    }
    approvals = []
    state, summary, _, _ = exercise(
        store,
        credentials,
        tmp_path,
        attempts[operation],
        approve=lambda kind, details: approvals.append(kind) or True,
    )
    assert state == "needs_review"
    assert approvals == ["write_file"]
    assert json.loads((tmp_path / "output.json").read_text(encoding="utf-8")) == {"ok": True}
    assert summary["tools"]["recovered_proposal_errors"] == 0
    assert summary["unresolved_tool_errors"] > 0
    assert summary["completion_feedback_count"] == 1


@pytest.mark.parametrize(
    "reason", ["denial", "unrelated_error", "bad_values", "disk_changed", "step_limit", "no_write"]
)
def test_other_failures_do_not_qualify_for_verification_exception(store, credentials, tmp_path, reason):
    kwargs = {}
    if reason == "denial":
        kwargs["approve"] = lambda *args: False
    elif reason == "unrelated_error":
        kwargs["prefix"] = [
            call("read_file", path="absent.txt"),
            call("write_file", path="output.json", content="{}"),
            call("write_file", path="output.json", content="{}", expected_sha256="new"),
        ]
    elif reason == "bad_values":
        kwargs["acceptance"] = lambda ws, text: {"VALUES_CORRECT": False}
    elif reason == "disk_changed":
        kwargs["before_final"] = lambda: (tmp_path / "output.json").write_text("{}", encoding="utf-8")
    elif reason == "step_limit":
        kwargs["max_steps"] = 3
    elif reason == "no_write":
        kwargs["prefix"] = [call("write_file", path="output.json", content="{}")]
    state, summary, _, _ = exercise(store, credentials, tmp_path, **kwargs)
    assert state != "completed"
    assert summary["verification_feedback_count"] == summary["completion_feedback_count"] == 0
    assert summary["tools"]["recovered_proposal_errors"] == 0


def test_external_revision_change_after_feedback_does_not_count_as_readback(store, credentials, tmp_path):
    # Mutate between the feedback request and the native read without changing runtime evidence.
    original = Runtime.run

    def run_with_edit(self, *args, **kwargs):
        def emit(event):
            if event["kind"] == "completion.feedback_requested":
                (tmp_path / "output.json").write_text("{}", encoding="utf-8")

        kwargs["emit"] = emit
        return original(self, *args, **kwargs)

    from unittest.mock import patch

    with patch.object(Runtime, "run", run_with_edit):
        state, summary, _, _ = exercise(store, credentials, tmp_path)
    assert state == "needs_review"
    assert summary["tools"]["recovered_proposal_errors"] == 0
    assert summary["task_checks"]["revision_mismatches"] == 1


def test_verification_metric_survives_private_safe_export(store, credentials, tmp_path):
    from aigentics.diagnostics import model_evidence
    from aigentics.reporting import public_report

    _, _, events, _ = exercise(store, credentials, tmp_path)
    evidence = model_evidence(events)
    assert evidence["verification_feedback_count"] == 1
    report = {
        "kind": "health",
        "state": "passed",
        "checks": [
            {
                "id": "synthetic",
                "status": "passed",
                "code": "OK",
                "message": "Fixture",
                "duration_ms": 0,
                "evidence": evidence,
            }
        ],
    }
    assert public_report(report)["checks"][0]["evidence"]["verification_feedback_count"] == 1


def test_cancel_on_verification_feedback_stops_before_next_read(store, credentials, tmp_path):
    state, summary, _, seen = exercise(store, credentials, tmp_path, cancel_on_feedback=True)
    assert state == "cancelled"
    assert len(seen) == 3
    assert summary["tools"]["recovered_proposal_errors"] == 0


def test_denied_phase_action_cannot_be_erased_by_later_valid_read(store, credentials, tmp_path):
    response = Reply(
        calls=[
            ToolCall(id="bad", name="read_file", arguments={"path": "unrelated.txt"}),
            ToolCall(id="good", name="read_file", arguments={"path": "output.json"}),
        ]
    )
    state, summary, _, _ = exercise(store, credentials, tmp_path, response)
    assert state == "needs_review"
    assert summary["tools"]["recovered_proposal_errors"] == 1
    assert summary["unresolved_tool_errors"] == 1
    assert summary["completion_feedback_count"] == 1


@pytest.mark.parametrize(
    "extra",
    [
        {"required_reads": ["source.txt"]},
        {"required_tools": ["search"]},
        {"unchanged_targets": ["source.txt"]},
    ],
)
def test_other_missing_proof_blocks_verification_exception(store, credentials, tmp_path, extra):
    (tmp_path / "source.txt").write_text("source", encoding="utf-8")
    state, summary, _, _ = exercise(store, credentials, tmp_path, checks_extra=extra)
    assert state == "needs_review"
    assert summary["verification_feedback_count"] == summary["completion_feedback_count"] == 0
