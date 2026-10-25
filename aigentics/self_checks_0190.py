"""Installed JSON-proposal guard and proof-based recovery, without external calls."""

from contextlib import closing
from pathlib import Path
import tempfile

from .models import Agent, Profile, Reply, ToolCall
from .runtime import Runtime
from .store import Store
from .task_checks import TaskChecks


def json_proposal_check(credentials):
    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, model, messages, tools):
            count = sum(message["role"] == "tool" for message in messages)
            operations = [
                ("write_file", {"path": "result.json", "content": "[]", "expected_sha256": "new"}),
                ("read_file", {"path": "result.json"}),
                (
                    "write_file",
                    {"path": "result.json", "content": '{"ready":true}', "expected_sha256": "new"},
                ),
                ("read_file", {"path": "result.json"}),
            ]
            if count < len(operations):
                name, args = operations[count]
                return Reply(calls=[ToolCall(id=str(count), name=name, arguments=args)])
            return Reply(content="Verified the saved object.")

    with tempfile.TemporaryDirectory(prefix="aigentics-json-check-") as folder:
        root = Path(folder) / "project"
        root.mkdir()
        with closing(Store(Path(folder) / "check.sqlite3", credentials)) as store:
            store.save_profile(Profile(id="ollama", name="Synthetic fixture"))
            approvals = []
            sid, state = Runtime(store, credentials, Fixture).run(
                Agent(),
                root,
                "Create object result.json",
                lambda kind, details: approvals.append(kind) or True,
                task_checks=TaskChecks(write_targets=["result.json"], json_outputs={"result.json": "object"}),
            )
            summary = next(e["data"] for e in store.events(sid) if e["kind"] == "run.summary")
            if (
                state != "completed"
                or approvals != ["write_file"]
                or summary["tools"]["recovered_proposal_errors"] != 2
                or (root / "result.json").read_text(encoding="utf-8") != '{"ready":true}'
            ):
                raise AssertionError("JSON proposal guard/recovery fixture failed")
    return {"json_proposal_fixture_verified": True, "external_requests": 0}
