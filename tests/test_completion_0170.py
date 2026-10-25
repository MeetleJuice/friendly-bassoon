"""Regressions derived from synthetic reproductions, never raw user outputs."""

import threading
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.test_suite import run_suite, baseline_files
from aigentics.crew_cases import CASES
from aigentics.contracts import contract_prompt


def test_noop_missing_final_read_receives_bounded_feedback_and_completes(store, credentials):
    store.save_profile(Profile(id="ollama", name="Synthetic local model"))
    content = baseline_files("noop")["output.txt"].decode()

    class Provider:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, model, messages, tools):
            results = sum(m["role"] == "tool" for m in messages)
            correction = any(
                "Application verification" in m.get("content", "") for m in messages if m["role"] == "user"
            )
            if results == 0 or (results == 2 and correction):
                return Reply(calls=[ToolCall(id="read", name="read_file", arguments={"path": "output.txt"})])
            if results == 1:
                return Reply(
                    calls=[
                        ToolCall(
                            id="same",
                            name="write_file",
                            arguments={
                                "path": "output.txt",
                                "content": content,
                                "expected_sha256": "last_read",
                            },
                        )
                    ]
                )
            return Reply(content="The file remains unchanged.")

    row = run_suite(
        store,
        credentials,
        Agent(),
        threading.Event(),
        lambda e: None,
        provider_factory=Provider,
        case_ids=["noop"],
        persist=False,
        completion_feedback=True,
    )["checks"][0]
    assert row["status"] == "passed"
    assert row["evidence"]["completion_feedback_count"] == 1
    assert row["evidence"]["execution_counts"]["unchanged_writes"] == 1
    assert row["evidence"]["execution_counts"]["writes_verified"] == 0
    assert row["evidence"]["requirement_checks"]["NOOP_ORDER"] is True


def test_vera_prompt_explicitly_advertises_root_and_item_schema():
    case = next(case for case in CASES if case.id == "vera_exclusive")
    prompt = contract_prompt(case)
    assert '"cases"' in prompt and '"properties"' in prompt
    assert '"input"' in prompt and '"expected"' in prompt


def test_unchanged_proof_is_invalidated_by_external_change_and_multiple_requests(tmp_path):
    from aigentics.task_checks import TaskChecks, TaskEvidence
    from aigentics.tools import Workspace, ToolRunner

    path = tmp_path / "file.txt"
    path.write_text("same")
    workspace = Workspace(tmp_path)
    evidence = TaskEvidence(workspace, TaskChecks(unchanged_targets=["file.txt"]))
    runner = ToolRunner(workspace, Agent(), lambda *args: True, threading.Event())
    for name, args in [
        ("read_file", {"path": "file.txt"}),
        ("write_file", {"path": "file.txt", "content": "same", "expected_sha256": "last_read"}),
        ("read_file", {"path": "file.txt"}),
    ]:
        call = ToolCall(id="native", name=name, arguments=args)
        evidence.record(call, runner.execute(call), "succeeded")
    assert evidence.evaluate()[0]["status"] == "passed"
    path.write_text("external")
    assert evidence.evaluate()[0]["status"] == "needs_attention"
    path.write_text("same")
    call = ToolCall(
        id="again",
        name="write_file",
        arguments={"path": "file.txt", "content": "same", "expected_sha256": "last_read"},
    )
    evidence.record(call, runner.execute(call), "succeeded")
    read = ToolCall(id="last", name="read_file", arguments={"path": "file.txt"})
    evidence.record(read, runner.execute(read), "succeeded")
    assert evidence.evaluate()[0]["status"] == "needs_attention"


def test_actual_write_cannot_satisfy_unchanged_file_contract(tmp_path):
    from aigentics.task_checks import TaskChecks, TaskEvidence
    from aigentics.tools import Workspace, ToolRunner

    (tmp_path / "file.txt").write_text("original")
    workspace = Workspace(tmp_path)
    evidence = TaskEvidence(workspace, TaskChecks(unchanged_targets=["file.txt"]))
    runner = ToolRunner(workspace, Agent(), lambda *args: True, threading.Event())
    for name, args in [
        ("read_file", {"path": "file.txt"}),
        ("write_file", {"path": "file.txt", "content": "changed", "expected_sha256": "last_read"}),
        ("read_file", {"path": "file.txt"}),
        ("write_file", {"path": "file.txt", "content": "changed", "expected_sha256": "last_read"}),
        ("read_file", {"path": "file.txt"}),
    ]:
        call = ToolCall(id="native", name=name, arguments=args)
        evidence.record(call, runner.execute(call), "succeeded")
    assert evidence.evaluate()[0]["status"] == "needs_attention"


def test_unchanged_target_preflight_preserves_permissions(store, credentials, tmp_path):
    import pytest
    from aigentics.runtime import Runtime
    from aigentics.task_checks import TaskChecks

    with pytest.raises(ValueError, match="Unchanged-file"):
        Runtime(store, credentials).run(
            Agent(allow_writes=False),
            tmp_path,
            "Check",
            lambda *args: True,
            task_checks=TaskChecks(unchanged_targets=["file.txt"]),
        )
    assert not store.sessions()
