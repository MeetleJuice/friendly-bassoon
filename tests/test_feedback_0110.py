"""Native argument repair evidence without coercion, replay or privilege expansion."""

import json
import pytest
from pydantic import ValidationError
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.runtime import Runtime
from aigentics.task_checks import TaskChecks
from aigentics.tools import SCHEMAS, validation_feedback, VALIDATION_ISSUE_CODES, ToolRunner, Workspace


def call(name, **arguments):
    return ToolCall(id=name, name=name, arguments=arguments)


def run_replies(store, credentials, root, replies, agent=None, checks=None, allowed=False):
    store.save_profile(Profile(id="ollama", name="Synthetic local"))
    requests, approvals = [], []

    class Scripted:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            requests.append(json.loads(json.dumps(messages)))
            return replies[len(requests) - 1]

    sid, state = Runtime(store, credentials, Scripted).run(
        agent or Agent(),
        root,
        "Synthetic native repair acceptance",
        lambda kind, details: approvals.append(kind) or allowed,
        task_checks=checks,
    )
    events = store.events(sid)
    summary = next(e["data"] for e in events if e["kind"] == "run.summary")
    return sid, state, summary, events, requests, approvals


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_unknown_argument_names_and_values_never_enter_repair_feedback(name):
    arguments = {"PRIVATE_KEY_NAME": "PRIVATE_VALUE"}
    with pytest.raises(ValidationError) as error:
        SCHEMAS[name].model_validate(arguments)
    feedback = validation_feedback(name, error.value)
    serialized = json.dumps(feedback)
    assert "PRIVATE_KEY_NAME" not in serialized and "PRIVATE_VALUE" not in serialized
    assert feedback["code"] == "TOOL_ARGUMENT_VALIDATION"
    assert set(feedback["allowed_fields"]) == set(SCHEMAS[name].model_fields)
    assert all(issue["code"] in VALIDATION_ISSUE_CODES for issue in feedback["validation_issues"])
    assert any(issue["code"] == "UNEXPECTED_ARGUMENT" for issue in feedback["validation_issues"])


@pytest.mark.parametrize(
    "name,args,code,field",
    [
        ("read_file", {}, "MISSING_ARGUMENT", "path"),
        ("read_file", {"path": 1}, "ARGUMENT_TYPE", "path"),
        ("search", {"query": ""}, "ARGUMENT_BOUNDS", "query"),
        (
            "write_file",
            {"path": "a.txt", "content": "safe", "expected_sha256": "wrong"},
            "ARGUMENT_PATTERN",
            "expected_sha256",
        ),
        ("run_command", {"argv": ["python"], "timeout_seconds": 121}, "ARGUMENT_BOUNDS", "timeout_seconds"),
        (
            "write_file",
            {"path": "a.txt", "content": "\0PRIVATE", "expected_sha256": "new"},
            "ARGUMENT_INVALID",
            "content",
        ),
    ],
)
def test_static_issue_classification(name, args, code, field):
    with pytest.raises(ValidationError) as error:
        SCHEMAS[name].model_validate(args)
    issues = validation_feedback(name, error.value)["validation_issues"]
    assert {"location": [field], "code": code} in issues
    assert "PRIVATE" not in json.dumps(issues)


def test_map_correction_is_native_bounded_and_records_failed_attempt(store, credentials, tmp_path):
    result = run_replies(
        store,
        credentials,
        tmp_path,
        [
            Reply(calls=[call("project_map", path="PRIVATE_EXTRA")]),
            Reply(calls=[call("project_map")]),
            Reply(content="Inspected using actual map."),
        ],
        checks=TaskChecks(required_tools=["project_map"]),
    )
    _, state, summary, events, requests, approvals = result
    assert state == "completed" and len(requests) == 3 and not approvals
    assert summary["tools"]["failed"] == summary["tools"]["recovered_validation_errors"] == 1
    assert summary["unresolved_tool_errors"] == 0
    assert summary["task_checks"]["status"] == "passed"
    first_feedback = next(m["content"] for m in requests[1] if m["role"] == "tool")
    assert "PRIVATE_EXTRA" not in first_feedback and "exactly {}" in first_feedback
    results = [e["data"] for e in events if e["kind"] == "tool.result"]
    assert [r["status"] for r in results] == ["failed", "succeeded"]
    assert results[0]["validation_issues"] == [{"location": ["<unexpected>"], "code": "UNEXPECTED_ARGUMENT"}]
    assert any(e["kind"] == "validation.recovered" for e in events)


def test_changed_read_target_does_not_hide_original_invalid_call(store, credentials, tmp_path):
    (tmp_path / "second.txt").write_bytes(b"safe")
    _, state, summary, *_ = run_replies(
        store,
        credentials,
        tmp_path,
        [
            Reply(calls=[call("read_file", path="first.txt", extra="PRIVATE")]),
            Reply(calls=[call("read_file", path="second.txt")]),
            Reply(content="Read another file."),
        ],
    )
    assert state == "needs_review"
    assert summary["tools"]["recovered_validation_errors"] == 0
    assert summary["unresolved_tool_errors"] == 1


def test_schema_corrected_write_still_requires_approval_and_review(store, credentials, tmp_path):
    _, state, summary, _, requests, approvals = run_replies(
        store,
        credentials,
        tmp_path,
        [
            Reply(
                calls=[
                    call("write_file", path="out.txt", content="safe", expected_sha256="new", extra="PRIVATE")
                ]
            ),
            Reply(calls=[call("write_file", path="out.txt", content="safe", expected_sha256="new")]),
            Reply(content="Saved reviewed proposal."),
        ],
        allowed=True,
    )
    assert len(approvals) == 1 and (tmp_path / "out.txt").read_bytes() == b"safe"
    assert state == "needs_review" and summary["tools"]["recovered_validation_errors"] == 0
    assert len(requests) == 3


def test_corrected_write_cannot_expand_permissions_or_create_a_file(store, credentials, tmp_path):
    _, state, summary, _, _, approvals = run_replies(
        store,
        credentials,
        tmp_path,
        [
            Reply(
                calls=[
                    call("write_file", path="out.txt", content="safe", expected_sha256="new", extra="PRIVATE")
                ]
            ),
            Reply(calls=[call("write_file", path="out.txt", content="safe", expected_sha256="new")]),
            Reply(content="Cannot write."),
        ],
        agent=Agent(allow_writes=False),
        allowed=True,
    )
    assert state == "needs_review" and not approvals and not (tmp_path / "out.txt").exists()
    assert summary["unresolved_tool_errors"] == 2


def test_permission_failures_never_resolve_when_a_map_succeeds(store, credentials, tmp_path):
    _, state, summary, *_ = run_replies(
        store,
        credentials,
        tmp_path,
        [
            Reply(calls=[call("read_file", path="../outside.txt")]),
            Reply(calls=[call("project_map")]),
            Reply(content="Mapped."),
        ],
    )
    assert state == "needs_review" and summary["unresolved_tool_errors"] == 1
    assert summary["tools"]["recovered_validation_errors"] == 0


def test_repeated_schema_failure_retains_existing_circuit_breaker(store, credentials, tmp_path):
    replies = [Reply(calls=[call("project_map", path="PRIVATE")]) for _ in range(4)]
    _, state, summary, events, requests, _ = run_replies(store, credentials, tmp_path, replies)
    assert state == "needs_review" and len(requests) == 4
    assert summary["tools"]["failed"] == 3 and summary["unresolved_tool_errors"] == 3
    assert any(e["data"].get("code") == "NO_PROGRESS" for e in events)


def test_invalid_map_never_invokes_the_executor(credentials, tmp_path, monkeypatch):
    import aigentics.tools as tool_module

    invoked = []
    monkeypatch.setitem(tool_module.EXECUTORS, "project_map", lambda *a: invoked.append(1))
    runner = ToolRunner(Workspace(tmp_path), Agent(), lambda *a: True, __import__("threading").Event())
    with pytest.raises(ValidationError):
        runner.execute(call("project_map", path="PRIVATE"))
    assert not invoked
