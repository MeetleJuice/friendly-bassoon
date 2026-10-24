"""Batch/late-revision regressions supporting trustworthy campaign measurements."""

import threading

import pytest

from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.runtime import Runtime
from aigentics.task_checks import TaskChecks


def native(name, **arguments):
    # Some providers reuse call IDs; execution IDs must still correlate actual effects.
    return ToolCall(id="reused-provider-id", name=name, arguments=arguments)


def run(store, credentials, root, replies, targets, approve=None, cancel=None):
    store.save_profile(Profile(id="ollama", name="Synthetic local"))
    requests = []

    class Scripted:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "fixture"}

        def chat(self, model, messages, tools):
            requests.append(1)
            return replies[len(requests) - 1]

    sid, state = Runtime(store, credentials, Scripted).run(
        Agent(),
        root,
        "Complete only the explicit synthetic task.",
        approve or (lambda *args: True),
        cancel,
        task_checks=TaskChecks(write_targets=targets),
    )
    events = store.events(sid)
    summary = next(row["data"] for row in events if row["kind"] == "run.summary")
    return state, summary, events, len(requests)


@pytest.mark.parametrize("final_read", [False, True])
@pytest.mark.parametrize("separate_turns", [False, True])
def test_second_write_needs_its_own_current_readback(
    store, credentials, tmp_path, final_read, separate_turns
):
    first = [
        native("write_file", path="output.txt", content="first\n", expected_sha256="new"),
        native("read_file", path="output.txt"),
    ]
    second = [native("write_file", path="output.txt", content="second\n", expected_sha256="last_read")]
    if final_read:
        second.append(native("read_file", path="output.txt"))
    replies = (
        [Reply(calls=first), Reply(calls=second)] if separate_turns else [Reply(calls=first + second)]
    ) + [Reply(content="Both writes and the current revision are verified.")]
    state, summary, events, _ = run(store, credentials, tmp_path, replies, ["output.txt"])
    assert state == ("completed" if final_read else "needs_review")
    assert summary["task_checks"]["missing_readbacks"] == (0 if final_read else 1)
    assert summary["tools"]["writes_verified"] == 2
    assert (tmp_path / "output.txt").read_bytes() == b"second\n"
    requested = [row["data"] for row in events if row["kind"] == "tool.requested"]
    assert len({row["execution_id"] for row in requested}) == len(requested)
    assert len({row["call_id"] for row in requested}) == 1
    assert {row["execution_id"] for row in requested} == {
        row["data"]["execution_id"] for row in events if row["kind"] == "tool.result"
    }


@pytest.mark.parametrize("read_first", [False, True])
def test_correct_other_file_read_cannot_verify_expected_file(store, credentials, tmp_path, read_first):
    (tmp_path / "similar.txt").write_bytes(b"saved\n")
    calls = [native("read_file", path="similar.txt")] if read_first else []
    calls.append(native("write_file", path="output.txt", content="saved\n", expected_sha256="new"))
    calls.append(native("read_file", path="similar.txt"))
    state, summary, _, _ = run(
        store,
        credentials,
        tmp_path,
        [Reply(calls=calls), Reply(content="Verified identical contents in the similarly named file.")],
        ["output.txt"],
    )
    assert state == "needs_review"
    assert summary["task_checks"]["written_files"] == 1
    assert summary["task_checks"]["readback_files"] == 0
    assert summary["task_checks"]["missing_readbacks"] == 1


def test_success_later_in_batch_does_not_erase_denied_write(store, credentials, tmp_path):
    calls = [
        native("write_file", path="denied.txt", content="denied\n", expected_sha256="new"),
        native("write_file", path="allowed.txt", content="saved\n", expected_sha256="new"),
        native("read_file", path="allowed.txt"),
    ]
    state, summary, events, _ = run(
        store,
        credentials,
        tmp_path,
        [Reply(calls=calls), Reply(content="One write was denied; the other succeeded.")],
        ["denied.txt", "allowed.txt"],
        approve=lambda kind, details: details["path"] == "allowed.txt",
    )
    assert state == "needs_review"
    assert summary["tools"]["failed"] == summary["unresolved_tool_errors"] == 1
    assert summary["task_checks"]["missing_writes"] == 1
    assert summary["task_checks"]["readback_files"] == 1
    assert not (tmp_path / "denied.txt").exists()
    assert (tmp_path / "allowed.txt").read_bytes() == b"saved\n"
    assert [row["data"]["approved"] for row in events if row["kind"] == "permission.decided"] == [
        False,
        True,
    ]


def test_cancel_during_approval_stops_the_rest_of_batch(store, credentials, tmp_path):
    cancel = threading.Event()
    approvals = []

    def approve(kind, details):
        approvals.append(details["path"])
        cancel.set()
        return True

    calls = [
        native("write_file", path="first.txt", content="one\n", expected_sha256="new"),
        native("write_file", path="second.txt", content="two\n", expected_sha256="new"),
    ]
    state, summary, _, requests = run(
        store,
        credentials,
        tmp_path,
        [Reply(calls=calls)],
        ["first.txt", "second.txt"],
        approve=approve,
        cancel=cancel,
    )
    assert state == "cancelled" and requests == 1 and approvals == ["first.txt"]
    assert not (tmp_path / "first.txt").exists() and not (tmp_path / "second.txt").exists()
    assert summary["tools"]["writes_verified"] == 0


@pytest.mark.parametrize("post_read", [False, True])
def test_stale_recovery_is_separate_from_final_readback(store, credentials, tmp_path, post_read):
    (tmp_path / "output.txt").write_bytes(b"before\n")
    calls = [
        native("read_file", path="output.txt"),
        native("write_file", path="output.txt", content="after\n", expected_sha256="0" * 64),
        native("read_file", path="output.txt"),
        native("write_file", path="output.txt", content="after\n", expected_sha256="last_read"),
    ]
    if post_read:
        calls.append(native("read_file", path="output.txt"))
    state, summary, _, _ = run(
        store,
        credentials,
        tmp_path,
        [
            Reply(calls=calls),
            Reply(content="Recovered the stale write; current verification reported separately."),
        ],
        ["output.txt"],
    )
    assert state == ("completed" if post_read else "needs_review")
    assert summary["tools"]["failed"] == summary["tools"]["recovered_edit_errors"] == 1
    assert summary["unresolved_tool_errors"] == 0
    assert summary["task_checks"]["missing_readbacks"] == (0 if post_read else 1)
    assert (tmp_path / "output.txt").read_bytes() == b"after\n"
