"""Wrong-root proposals must never reach approval; recovery requires fresh proof."""

import json
import pytest
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.runtime import Runtime
from aigentics.task_checks import TaskChecks


def native(name, **args):
    return Reply(calls=[ToolCall(id="proposal", name=name, arguments=args)])


class CorrectedProposal:
    def __init__(self, *args):
        pass

    def capabilities(self, *args):
        return {"tools": True}

    def chat(self, model, messages, tools):
        count = sum(m["role"] == "tool" for m in messages)
        if count == 0:
            return native("write_file", path="cases.json", content="[]", expected_sha256="last_read")
        if count == 1:
            return native("read_file", path="cases.json")
        if count == 2:
            return native("write_file", path="cases.json", content='{"cases":[]}', expected_sha256="new")
        if count == 3:
            return native("read_file", path="cases.json")
        return Reply(content="Saved object and read current revision.")


def run(store, credentials, tmp_path, factory=CorrectedProposal, approve=lambda *args: True, **overrides):
    store.save_profile(Profile(id="ollama", name="Local fixture"))
    checks = TaskChecks(
        write_targets=["cases.json"], json_outputs={"cases.json": "object"}, completion_feedback=True
    )
    agent = Agent(max_steps=8)
    sid, state = Runtime(store, credentials, factory).run(
        agent, tmp_path, "Create cases.json as an object", approve, task_checks=checks, **overrides
    )
    summary = next(e["data"] for e in store.events(sid) if e["kind"] == "run.summary")
    return sid, state, summary


def test_wrong_root_and_missing_output_recover_after_approved_write_and_read(store, credentials, tmp_path):
    approved = []
    sid, state, summary = run(
        store, credentials, tmp_path, approve=lambda kind, detail: approved.append(detail) or True
    )
    assert state == "completed", summary
    assert json.loads((tmp_path / "cases.json").read_text()) == {"cases": []}
    assert len(approved) == 1 and "[]" not in approved[0]["diff"].splitlines()[0]
    assert summary["tools"]["failed"] == 2
    assert summary["tools"]["recovered_proposal_errors"] == 2
    assert summary["unresolved_tool_errors"] == 0


def test_denial_never_recovered(store, credentials, tmp_path):
    _, state, summary = run(store, credentials, tmp_path, approve=lambda *args: False)
    assert state != "completed" and summary["unresolved_tool_errors"] > 0
    assert not (tmp_path / "cases.json").exists()


@pytest.mark.parametrize(
    "content,expected",
    [
        ("[]", "object"),
        ('{"x":1,"x":2}', "object"),
        ('{"x":NaN}', "object"),
        ('{"x":1e999}', "object"),
        ("```json\n{}\n```", "object"),
        ("[1,2,]", "array"),
    ],
)
def test_json_rejection_has_no_values_or_side_effects(content, expected):
    from aigentics.json_proposals import validate_proposal, JsonProposalError

    with pytest.raises(JsonProposalError) as error:
        validate_proposal(content, expected)
    assert content not in str(error.value)


def test_missing_revision_argument_recovers_only_after_current_readback(store, credentials, tmp_path):
    class Model(CorrectedProposal):
        def chat(self, model, messages, tools):
            count = sum(m["role"] == "tool" for m in messages)
            if count == 0:
                return native("write_file", path="cases.json", content='{"cases":[]}')
            if count == 1:
                return native("write_file", path="cases.json", content='{"cases":[]}', expected_sha256="new")
            if count == 2:
                return native("read_file", path="cases.json")
            return Reply(content="Verified.")

    _, state, summary = run(store, credentials, tmp_path, Model)
    assert state == "completed" and summary["tools"]["failed"] == 1
    assert summary["tools"]["recovered_proposal_errors"] == 1


def test_same_correction_without_final_read_stays_unverified(store, credentials, tmp_path):
    class NoRead(CorrectedProposal):
        def chat(self, model, messages, tools):
            count = sum(m["role"] == "tool" for m in messages)
            if count >= 3:
                return Reply(content="Done.")
            return super().chat(model, messages, tools)

    _, state, summary = run(store, credentials, tmp_path, NoRead)
    assert state != "completed" and summary["tools"]["recovered_proposal_errors"] == 0


def test_missing_unrelated_input_is_never_cleared(store, credentials, tmp_path):
    class InputError(CorrectedProposal):
        def chat(self, model, messages, tools):
            count = sum(m["role"] == "tool" for m in messages)
            if count == 0:
                return native("read_file", path="missing-input.txt")
            if count == 1:
                return native("write_file", path="cases.json", content='{"cases":[]}', expected_sha256="new")
            if count == 2:
                return native("read_file", path="cases.json")
            return Reply(content="Verified.")

    _, state, summary = run(store, credentials, tmp_path, InputError)
    assert state == "needs_review" and summary["tools"]["recovered_proposal_errors"] == 0


def test_contract_must_be_inside_declared_scope(store, credentials, tmp_path):
    from aigentics.task_checks import TaskEvidence
    from aigentics.tools import Workspace

    with pytest.raises(ValueError, match="declared"):
        TaskEvidence(
            Workspace(tmp_path), TaskChecks(write_targets=["a.json"], json_outputs={"b.json": "object"})
        )
    assert not store.sessions()


def test_ordinal_evidence_normalizes_both_sides_on_windows(store, credentials, tmp_path, monkeypatch):
    import ntpath
    import aigentics.task_checks as checks

    monkeypatch.setattr(checks.os.path, "normcase", ntpath.normcase)
    _, state, summary = run(store, credentials, tmp_path)
    assert state == "completed"
    # The old normalized-key versus raw-path emitter produced zero rows here.
    evidence = [e for e in store.events(store.sessions()[0]["id"]) if e["kind"] == "tool.target_read"]
    assert evidence and evidence[-1]["data"]["ordinal"] == 1
    assert evidence[-1]["data"]["after_latest_write"] is True


def test_absent_last_read_hint_requests_new_without_relaxing_revision_guard(store, credentials, tmp_path):
    from aigentics.tools import ToolRunner, Workspace, StaleFileError

    runner = ToolRunner(Workspace(tmp_path), Agent(), lambda *args: True, __import__("threading").Event())
    with pytest.raises(StaleFileError, match="expected_sha256='new'"):
        runner.execute(
            ToolCall(
                id="new",
                name="write_file",
                arguments={"path": "missing.json", "content": "{}", "expected_sha256": "last_read"},
            )
        )
    assert not (tmp_path / "missing.json").exists()


def test_valid_json_shape_does_not_bypass_semantic_checker(store, credentials, tmp_path):
    _, state, summary = run(
        store, credentials, tmp_path, acceptance=lambda ws, text: {"VALUES_CORRECT": False}
    )
    assert state == "needs_review"
    assert summary["acceptance_checks"] == {"VALUES_CORRECT": False}
    assert summary["completion_feedback_count"] == 1
    assert summary["tools"]["recovered_proposal_errors"] == 2
