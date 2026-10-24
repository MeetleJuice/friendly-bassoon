"""Exhaustive permission subsets, envelope limits and public diagnostic fidelity."""

import json
import pytest
from aigentics.harness import exercise_tools, request_size, output_budget
from aigentics.registry import TOOLS
from aigentics.models import Agent, Profile, Reply
from aigentics.runtime import Runtime
from aigentics.reporting import public_report, issue_body, prepare_browser_draft
from aigentics.evidence import base_report


@pytest.mark.parametrize("mask", range(128))
def test_disclosure_never_grants_permissions_and_preserves_order(mask):
    allowed = [t for i, t in enumerate(TOOLS) if mask & (1 << i)]
    required = TOOLS[mask % len(TOOLS)]
    for writing in (False, True):
        selected = exercise_tools(allowed, required, writing)
        assert set(selected) <= set(allowed)
        assert "run_command" not in selected
        assert selected == [t for t in allowed if t in selected]
        assert all(t == required or (writing and t == "read_file") for t in selected)
        assert (required in selected) == (required in allowed and required != "run_command")


@pytest.mark.parametrize("text", ["", "hello", "é", "你好", "\\n", "\n", "🔐", "x" * 10000])
def test_envelope_counts_schemas_and_unicode_without_losing_state(text):
    messages = [{"role": "user", "content": text}]
    before = json.dumps(messages)
    assert request_size(messages, [{"schema": "x" * 1000}]) > request_size(messages, []) + 900
    assert json.dumps(messages) == before
    assert request_size(messages, []) >= len(before)


@pytest.mark.parametrize(
    "case",
    ["edit", "python", "read", "discover", "search", "map", "retrieve", "create", "readonly", "denial"],
)
def test_budget_is_bounded_and_multi_step_is_distinguished(case):
    assert output_budget(case) in (1024, 2048)
    assert (output_budget(case) == 2048) == (case in ("edit", "python"))


def test_runtime_blocks_schema_overflow_before_dispatch(store, credentials, tmp_path):
    store.save_profile(Profile(id="ollama", name="Fixture"))
    requests = []

    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True}

        def chat(self, model, messages, tools):
            requests.append((messages, tools))
            return Reply(content="No operation.")

    runtime = Runtime(store, credentials, Fixture)
    sid, _ = runtime.run(Agent(context_chars=200000), tmp_path, "x" * 5000, lambda *a: False)
    meta = next(e["data"] for e in store.events(sid) if e["kind"] == "model.requested")
    assert meta["request_chars"] > meta["context_chars"]
    cap = meta["request_chars"] - 1
    assert cap >= 4000
    count = len(requests)
    _, state = runtime.run(Agent(context_chars=cap), tmp_path, "x" * 5000, lambda *a: False)
    assert state == "failed" and len(requests) == count


def test_typed_errors_survive_compaction_but_private_text_does_not(credentials):
    report = base_report("agent_suite", "agent-suite-2", "Metadata only")
    report["checks"] = [
        dict(
            id=f"case{i}",
            status="failed",
            code="ACCEPTANCE_NOT_MET",
            message="Synthetic",
            duration_ms=100,
            evidence={
                "tool_error_types": {"ValidationError": 1, "secret-path": 1},
                "max_output_tokens": 2048,
                "request_traces": [
                    {"step": j, "content_chars": 100, "response_shape": {}, "usage": {}} for j in range(8)
                ],
            },
        )
        for i in range(10)
    ]
    safe = public_report(report)
    assert safe["checks"][0]["evidence"]["tool_error_types"] == {"ValidationError": 1}
    url = prepare_browser_draft(*issue_body(report, credentials))
    assert len(url) <= 7500 and "ValidationError" in url and "secret-path" not in url


def test_three_identical_failures_stop_without_a_fourth_execution(store, credentials, tmp_path):
    from aigentics.models import ToolCall

    store.save_profile(Profile(id="ollama", name="Fixture"))
    requests = []

    class Repeating:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True}

        def chat(self, *args):
            requests.append(1)
            return Reply(
                calls=[ToolCall(id=str(len(requests)), name="read_file", arguments={"path": "missing.txt"})]
            )

    sid, state = Runtime(store, credentials, Repeating).run(
        Agent(), tmp_path, "Read a missing file", lambda *a: False
    )
    events = store.events(sid)
    assert state == "needs_review"
    assert len([e for e in events if e["kind"] == "tool.result"]) == 3
    assert any(e["data"].get("code") == "NO_PROGRESS" for e in events)


def test_successful_progress_resets_failed_request_breaker(store, credentials, tmp_path):
    from aigentics.models import ToolCall

    store.save_profile(Profile(id="ollama", name="Fixture"))
    count = []

    class Recovering:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True}

        def chat(self, *args):
            count.append(1)
            step = len(count)
            if step == 6:
                return Reply(content="Recovered.")
            if step == 4:
                return Reply(
                    calls=[
                        ToolCall(
                            id="write",
                            name="write_file",
                            arguments={"path": "missing.txt", "content": "ready", "expected_sha256": "new"},
                        )
                    ]
                )
            return Reply(calls=[ToolCall(id=str(step), name="read_file", arguments={"path": "missing.txt"})])

    sid, _ = Runtime(store, credentials, Recovering).run(Agent(), tmp_path, "Recover", lambda *a: True)
    events = store.events(sid)
    assert not any(e["data"].get("code") == "NO_PROGRESS" for e in events)
    assert (
        len([e for e in events if e["kind"] == "tool.result" and e["data"].get("status") == "succeeded"]) == 2
    )
