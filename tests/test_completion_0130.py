import threading
import pytest
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.runtime import Runtime
from aigentics.task_checks import TaskChecks


def execute(store, credentials, root, replies, checks, approve=True, steps=8):
    store.save_profile(Profile(id="ollama", name="Fixture"))
    calls = []

    class Provider:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, model, messages, tools):
            calls.append(messages[-1]["content"])
            return replies[min(len(calls) - 1, len(replies) - 1)]

    sid, state = Runtime(store, credentials, Provider).run(
        Agent(max_steps=steps),
        root,
        "Do the bounded task.",
        lambda *args: approve,
        threading.Event(),
        task_checks=checks,
    )
    events = store.events(sid)
    summary = next(e["data"] for e in events if e["kind"] == "run.summary")
    return state, summary, events, calls


def tool(name, **args):
    return Reply(calls=[ToolCall(id="call", name=name, arguments=args)])


def test_missing_readback_gets_one_correction_without_rewriting(store, credentials, tmp_path):
    replies = [
        tool("write_file", path="output.txt", content="saved\n", expected_sha256="new"),
        Reply(content="Done"),
        tool("read_file", path="output.txt"),
        Reply(content="Verified"),
    ]
    state, summary, events, calls = execute(
        store,
        credentials,
        tmp_path,
        replies,
        TaskChecks(write_targets=["output.txt"], completion_feedback=True),
    )
    assert state == "completed"
    assert summary["completion_feedback_count"] == 1
    assert summary["tools"]["writes_verified"] == 1
    assert summary["task_checks"]["missing_readbacks"] == 0
    assert len([e for e in events if e["kind"] == "completion.feedback_requested"]) == 1


@pytest.mark.parametrize("repair", [False, True])
def test_required_source_read_is_enforced_and_bounded(store, credentials, tmp_path, repair):
    (tmp_path / "source.txt").write_text("evidence")
    replies = [Reply(content="I know the answer")]
    if repair:
        replies += [tool("read_file", path="source.txt"), Reply(content="Based on source")]
    state, summary, events, calls = execute(
        store,
        credentials,
        tmp_path,
        replies,
        TaskChecks(required_reads=["source.txt"], completion_feedback=True),
    )
    assert state == ("completed" if repair else "needs_review")
    assert summary["completion_feedback_count"] == 1
    assert summary["task_checks"]["missing_sources"] == (0 if repair else 1)
    assert len(calls) == (3 if repair else 2)


def test_denial_never_triggers_completion_repair(store, credentials, tmp_path):
    state, summary, events, calls = execute(
        store,
        credentials,
        tmp_path,
        [tool("write_file", path="output.txt", content="no", expected_sha256="new"), Reply(content="Denied")],
        TaskChecks(write_targets=["output.txt"], completion_feedback=True),
        approve=False,
    )
    assert state == "needs_review" and summary["completion_feedback_count"] == 0
    assert not (tmp_path / "output.txt").exists()


def test_no_remaining_steps_means_no_extra_request(store, credentials, tmp_path):
    state, summary, events, calls = execute(
        store,
        credentials,
        tmp_path,
        [Reply(content="Done")],
        TaskChecks(required_reads=["source.txt"], completion_feedback=True),
        steps=1,
    )
    assert len(calls) == 1 and summary["completion_feedback_count"] == 0


@pytest.mark.parametrize("filename", ["source.txt", "nested/source.txt", "café.txt"])
@pytest.mark.parametrize("spelling", ["exact", "relative"])
def test_native_source_identity_accepts_valid_relative_paths(
    store, credentials, tmp_path, filename, spelling
):
    target = tmp_path / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("fact")
    path = filename if spelling == "exact" else "./" + filename
    state, summary, events, calls = execute(
        store,
        credentials,
        tmp_path,
        [Reply(content="Premature"), tool("read_file", path=path), Reply(content="Observed")],
        TaskChecks(required_reads=[filename], completion_feedback=True),
    )
    assert state == "completed" and summary["task_checks"]["missing_sources"] == 0
    feedback = next(e["data"] for e in events if e["kind"] == "completion.feedback_requested")
    assert filename not in str(feedback)


def test_reading_wrong_source_never_passes(store, credentials, tmp_path):
    (tmp_path / "required.txt").write_text("fact")
    (tmp_path / "other.txt").write_text("fact")
    state, summary, events, calls = execute(
        store,
        credentials,
        tmp_path,
        [tool("read_file", path="other.txt"), Reply(content="Done")],
        TaskChecks(required_reads=["required.txt"], completion_feedback=True),
    )
    assert state == "needs_review" and summary["task_checks"]["missing_sources"] == 1
    assert summary["completion_feedback_count"] == 1


def test_public_feedback_counters_exclude_private_source_names():
    from aigentics.task_checks import public_task_checks

    safe = public_task_checks({"missing_sources": 1, "unread_sources": ["private.txt"]})
    assert safe["missing_sources"] == 1 and "private.txt" not in str(safe)


def test_campaign_report_retains_initial_counters_without_private_paths(credentials):
    from aigentics.evidence import base_report
    from aigentics.reporting import public_report, issue_body, prepare_browser_draft

    r = base_report("crew_campaign", "crew-campaign-2", "Synthetic")
    r["checks"] = [
        {
            "id": "baseline-edit",
            "status": "passed",
            "code": "OK",
            "message": "Synthetic",
            "duration_ms": 1,
            "evidence": {
                "completion_feedback_count": 1,
                "initial_task_checks": {
                    "missing_readbacks": 1,
                    "missing_sources": 2,
                    "unread_sources": ["private.txt"],
                },
            },
        }
    ]
    safe = public_report(r)
    assert safe["checks"][0]["evidence"]["completion_feedback_count"] == 1
    assert safe["checks"][0]["evidence"]["initial_task_checks"]["missing_sources"] == 2
    assert "private.txt" not in str(safe)
    assert len(prepare_browser_draft(*issue_body(r, credentials))) <= 7500
