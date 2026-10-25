"""Installed final-proof recovery and mutation rejection, without network access."""

from contextlib import closing
from pathlib import Path
import tempfile

from .models import Agent, Profile, Reply, ToolCall
from .runtime import Runtime
from .store import Store
from .task_checks import TaskChecks


def verification_check(credentials):
    with tempfile.TemporaryDirectory(prefix="aigentics-proof-") as folder:
        with closing(Store(Path(folder) / "fixture.sqlite3", credentials)) as store:
            store.save_profile(Profile(id="ollama", name="Synthetic fixture"))
            for mutation in (False, True):
                root = Path(folder) / str(mutation)
                root.mkdir()
                operations = [
                    Reply(
                        calls=[
                            ToolCall(
                                id="bad",
                                name="write_file",
                                arguments={
                                    "path": "out.json",
                                    "content": "{}",
                                },
                            )
                        ]
                    ),
                    Reply(
                        calls=[
                            ToolCall(
                                id="save",
                                name="write_file",
                                arguments={
                                    "path": "out.json",
                                    "content": "{}",
                                    "expected_sha256": "new",
                                },
                            )
                        ]
                    ),
                    Reply(content="Finished."),
                    Reply(
                        calls=[
                            ToolCall(
                                id="proof",
                                name="write_file" if mutation else "read_file",
                                arguments={
                                    "path": "out.json",
                                    "content": "[]",
                                    "expected_sha256": "last_read",
                                }
                                if mutation
                                else {"path": "out.json"},
                            )
                        ]
                    ),
                    Reply(content="Verified."),
                ]

                class Fixture:
                    def __init__(self, *args):
                        pass

                    def capabilities(self, *args):
                        return {"tools": True}

                    def chat(self, model, messages, tools):
                        return operations.pop(0)

                approvals = []
                sid, state = Runtime(store, credentials, Fixture).run(
                    Agent(max_steps=6),
                    root,
                    "Create and verify out.json",
                    lambda kind, details: approvals.append(kind) or True,
                    task_checks=TaskChecks(
                        write_targets=["out.json"],
                        json_outputs={"out.json": "object"},
                        completion_feedback=True,
                    ),
                )
                summary = next(e["data"] for e in store.events(sid) if e["kind"] == "run.summary")
                if (
                    state != ("needs_review" if mutation else "completed")
                    or summary["verification_feedback_count"] != 1
                    or summary["tools"]["recovered_proposal_errors"] != (0 if mutation else 1)
                    or approvals != ["write_file"]
                    or (root / "out.json").read_text(encoding="utf-8") != "{}"
                ):
                    raise AssertionError("Verification-only recovery/permission fixture failed")
    return {"verification_fixture_verified": True, "external_requests": 0}
