"""Live-suite acceptance adversaries exercise real file tools and ordered evidence."""

import hashlib
import threading
import pytest
from aigentics import test_suite as suite
from aigentics.models import Agent, Profile, Reply, ToolCall
from test_suite_080 import Scripted


def exercise(monkeypatch, store, credentials, identity, provider=Scripted):
    monkeypatch.setattr(suite, "CASES", tuple(c for c in suite.CASES if c[0] == identity))
    store.save_profile(Profile(id="ollama", name="Fixture"))
    report = suite.run_suite(store, credentials, Agent(), threading.Event(), lambda e: None, provider)
    assert len(report["checks"]) == 1
    return report["checks"][0]


def response(name, **arguments):
    return Reply(calls=[ToolCall(id=name, name=name, arguments=arguments)])


def scripted(replies):
    class Provider(Scripted):
        def chat(self, model, messages, tools):
            index = sum(m["role"] == "tool" for m in messages)
            return replies[index] if index < len(replies) else Reply(content="Finished.")

    return Provider


@pytest.mark.parametrize(
    "identity,writes",
    [
        ("empty", 1),
        ("unicode", 1),
        ("multiline", 1),
        ("nested", 1),
        ("multi_file", 2),
        ("transform", 1),
        ("noop", 0),
        ("stale", 1),
    ],
)
def test_new_cases_verify_native_operations_and_exact_bytes(
    monkeypatch, store, credentials, identity, writes
):
    row = exercise(monkeypatch, store, credentials, identity)
    assert row["status"] == "passed", row
    assert row["evidence"]["file_matches"] is True
    assert row["evidence"]["execution_counts"]["writes_verified"] == writes
    assert not store.sessions()  # Synthetic trial sessions never enter user history.


@pytest.mark.parametrize(
    "case", ["empty", "unicode", "multiline", "nested", "multi_file", "transform", "noop", "stale"]
)
def test_claimed_success_without_tools_fails_every_new_case(monkeypatch, store, credentials, case):
    row = exercise(monkeypatch, store, credentials, case, scripted([]))
    assert row["status"] == "failed"


@pytest.mark.parametrize("read_actual_output", [False, True])
def test_noop_requires_correct_file_reads_before_and_after(
    monkeypatch, store, credentials, read_actual_output
):
    replies = [
        response("read_file", path="output.txt" if read_actual_output else "input.txt"),
        response(
            "write_file",
            path="output.txt",
            content="lighthouse\n",
            expected_sha256=hashlib.sha256(b"lighthouse\n").hexdigest(),
        ),
    ]
    row = exercise(monkeypatch, store, credentials, "noop", scripted(replies))
    assert row["evidence"]["execution_counts"]["unchanged_writes"] == 1
    assert row["evidence"]["runtime_state"] == "completed"
    assert row["status"] == "failed"  # Correct bytes/no-op alone cannot stand in for ordered read-back.


@pytest.mark.parametrize("incorrect_mode", ["no_first_read", "no_reread", "wrong_hash"])
def test_stale_requires_the_specific_rejection_and_ordered_recovery(
    monkeypatch, store, credentials, incorrect_mode
):
    read = response("read_file", path="output.txt")
    bad = response(
        "write_file",
        path="output.txt",
        content="lighthouse\n",
        expected_sha256="last_read"
        if incorrect_mode == "no_first_read"
        else "1" * 64
        if incorrect_mode == "wrong_hash"
        else "0" * 64,
    )
    good = response("write_file", path="output.txt", content="lighthouse\n", expected_sha256="last_read")
    replies = (
        [bad, read, good, read]
        if incorrect_mode == "no_first_read"
        else [read, bad, good, read]
        if incorrect_mode == "no_reread"
        else [read, bad, read, good, read]
    )
    row = exercise(monkeypatch, store, credentials, "stale", scripted(replies))
    assert row["evidence"]["execution_counts"]["recovered_edit_errors"] == 1
    assert row["evidence"]["runtime_state"] == "completed"
    assert row["status"] == "failed"


def test_transform_requires_input_reads_before_the_saved_output(monkeypatch, store, credentials):
    replies = [
        response("write_file", path="combined.txt", content="lighthouse\nharbor\n", expected_sha256="new"),
        response("read_file", path="combined.txt"),
        response("read_file", path="input.txt"),
        response("read_file", path="second_input.txt"),
    ]
    row = exercise(monkeypatch, store, credentials, "transform", scripted(replies))
    assert row["evidence"]["file_matches"] is True and row["evidence"]["task_checks"]["status"] == "passed"
    assert row["status"] == "failed"


def test_both_new_outputs_require_readback(monkeypatch, store, credentials):
    replies = [
        response("write_file", path="first.txt", content="alpha\n", expected_sha256="new"),
        response("write_file", path="second.txt", content="beta\n", expected_sha256="new"),
        response("read_file", path="first.txt"),
    ]
    row = exercise(monkeypatch, store, credentials, "multi_file", scripted(replies))
    assert row["evidence"]["execution_counts"]["writes_verified"] == 2
    assert row["evidence"]["task_checks"]["missing_readbacks"] == 1
    assert row["status"] == "failed"


@pytest.mark.parametrize(
    "case,wrong_content",
    [
        ("empty", "not empty"),
        ("unicode", "cafe\n"),
        ("multiline", "def square(number):\\n    return number * number\\n"),
        ("nested", "wrong\n"),
    ],
)
def test_approximate_output_is_not_exact_output(monkeypatch, store, credentials, case, wrong_content):
    class Wrong(Scripted):
        def chat(self, *args):
            reply = super().chat(*args)
            for call in reply.calls:
                if call.name == "write_file":
                    call.arguments["content"] = wrong_content
            return reply

    row = exercise(monkeypatch, store, credentials, case, Wrong)
    assert row["evidence"]["file_matches"] is False
    assert row["status"] == "failed"


@pytest.mark.parametrize(
    "case", ["read", "create", "denial", "noop", "stale", "transform", "multi_file", "nested"]
)
def test_equivalent_dot_paths_are_real_authorized_targets(monkeypatch, store, credentials, case):
    class Equivalent(Scripted):
        def chat(self, *args):
            reply = super().chat(*args)
            for call in reply.calls:
                if "path" in call.arguments and call.arguments["path"] not in ("", "."):
                    call.arguments["path"] = "./" + call.arguments["path"]
            return reply

    row = exercise(monkeypatch, store, credentials, case, Equivalent)
    assert row["status"] == "passed", row
