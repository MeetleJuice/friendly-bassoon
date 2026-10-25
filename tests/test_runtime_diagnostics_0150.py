"""Functional regressions first exercised on the pre-update runtime."""

from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.runtime import Runtime
from aigentics.diagnostics import model_evidence
from aigentics.task_checks import TaskChecks


def test_failed_map_call_retains_typed_schema_evidence(store, credentials, tmp_path):
    store.save_profile(Profile(id="ollama", name="Fixture"))

    class Provider:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, model, messages, tools):
            count = sum(m["role"] == "tool" for m in messages)
            if count < 2:
                return Reply(
                    calls=[
                        ToolCall(
                            id="call", name="project_map", arguments={"path": "PRIVATE"} if count == 0 else {}
                        )
                    ]
                )
            return Reply(content="Done")

    sid, state = Runtime(store, credentials, Provider).run(
        Agent(), tmp_path, "Map project", lambda *args: True
    )
    evidence = model_evidence(store.events(sid))
    calls = evidence.get("tool_diagnostics", [])
    assert len(calls) == 2
    assert calls[0]["tool"] == "project_map"
    assert calls[0]["unexpected_argument_count"] == 1
    assert len(calls[0]["schema_sha256"]) == 64
    assert calls[0]["validation_issues"][0]["code"] == "UNEXPECTED_ARGUMENT"
    assert "PRIVATE" not in str(calls) and "path" not in str(calls[0]["argument_types"])
    assert calls[1]["status"] == "succeeded" and state == "completed"


def test_content_feedback_contains_safe_mismatch_before_final_acceptance(store, credentials, tmp_path):
    store.save_profile(Profile(id="ollama", name="Fixture"))
    seen = []

    class Provider:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, model, messages, tools):
            seen.append(messages[-1]["content"])
            return Reply(content="Premature completion")

    def contract(ws, text):
        return {
            "checks": {"OUTPUT_CONTENT": False},
            "mismatches": [
                {
                    "code": "JSON_TYPE",
                    "target": "final_answer",
                    "path": "/cases/0/expected",
                    "expected_type": "number",
                    "actual_type": "boolean",
                }
            ],
        }

    sid, state = Runtime(store, credentials, Provider).run(
        Agent(max_steps=3),
        tmp_path,
        "Produce valid JSON",
        lambda *args: True,
        task_checks=TaskChecks(completion_feedback=True),
        acceptance=contract,
    )
    assert len(seen) == 2
    assert "JSON_TYPE" in seen[1] and "/cases/0/expected" in seen[1]
    assert state == "needs_review"
    summary = next(e["data"] for e in store.events(sid) if e["kind"] == "run.summary")
    assert summary["mismatches"][0]["code"] == "JSON_TYPE"
