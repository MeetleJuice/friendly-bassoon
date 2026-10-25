"""Installed offline team smoke: actual harness, permissions, files and evidence."""

from contextlib import closing
from pathlib import Path
import json
import tempfile

from .coordination import Coordinator
from .crew import make_agent
from .models import ModelRef, Profile, Reply, ToolCall
from .store import Store
from .task_checks import TaskChecks


def team_pilot_check(credentials):
    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True}

        def chat(self, model, messages, tools, **kwargs):
            previous = [m for m in messages if m["role"] == "tool"]
            if any(t["function"]["name"] == "dispatch_worker" for t in tools):
                if not previous:
                    name, args = "team_status", {}
                elif not json.loads(previous[-1]["content"])["evidence"]:
                    name, args = (
                        "dispatch_worker",
                        {"role": "ada", "revision": json.loads(previous[-1]["content"])["revision"]},
                    )
                else:
                    return Reply(content="Recorded evidence only.")
            elif not previous:
                name, args = (
                    "write_file",
                    {"path": "result.txt", "content": "verified\n", "expected_sha256": "new"},
                )
            elif len(previous) == 1:
                name, args = "read_file", {"path": "result.txt"}
            else:
                return Reply(content="Saved output read back.")
            return Reply(calls=[ToolCall(id="fixture", name=name, arguments=args)])

    with tempfile.TemporaryDirectory(prefix="aigentics-team-check-") as directory:
        root = Path(directory)
        with closing(Store(root / "fixture.sqlite3", credentials)) as store:
            store.save_profile(Profile(id="ollama", name="Offline fixture"))
            project = root / "project"
            project.mkdir()
            agent = make_agent("orion", ModelRef(profile_id="ollama", model="fixture"))
            runtime = Coordinator(store, credentials, Fixture)
            checks = TaskChecks(write_targets=["result.txt"])
            sid, state = runtime.run(
                agent, project, "Create result.txt", lambda *args: True, task_checks=checks
            )
            if state != "completed" or (project / "result.txt").read_bytes() != b"verified\n":
                raise AssertionError("Native team completion fixture failed")
            summary = next(e["data"] for e in store.events(sid) if e["kind"] == "team.summary")
            if summary["budget"]["calls"] != 6 or len(summary["children"]) != 1:
                raise AssertionError("Aggregate team budget/evidence mismatch")
            (project / "result.txt").unlink()
            _, denied = runtime.run(
                agent, project, "Create result.txt", lambda *args: False, task_checks=checks
            )
            if denied == "completed" or (project / "result.txt").exists():
                raise AssertionError("Team bypassed denied write")
    return {"team_pilot_fixture_verified": True, "denial_blocked": True, "external_requests": 0}
