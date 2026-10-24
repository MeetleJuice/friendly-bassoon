"""Packaged, offline regressions for recovery and durable checkpoint state."""

from contextlib import closing
from pathlib import Path
import tempfile
from .models import Agent, Profile, Reply, ToolCall
from .runtime import Runtime
from .store import Store
from .task_plans import TaskPlans, Step


def require(value):
    if not value:
        raise AssertionError("Offline recovery acceptance criterion failed")


def validation_recovery_check(credentials):
    with tempfile.TemporaryDirectory(prefix="aigentics-validation-") as folder:
        root = Path(folder) / "project"
        root.mkdir()

        class NativeFixture:
            def __init__(self, *args):
                pass

            def capabilities(self, model):
                return {"tools": True, "source": "offline_fixture"}

            def chat(self, model, messages, tools):
                turns = sum(m["role"] == "tool" for m in messages)
                if turns < 2:
                    return Reply(
                        calls=[
                            ToolCall(
                                id=str(turns),
                                name="project_map",
                                arguments={"path": "."} if turns == 0 else {},
                            )
                        ]
                    )
                return Reply(content="Map completed after argument correction.")

        with closing(Store(Path(folder) / "state.sqlite3", credentials)) as store:
            store.save_profile(Profile(id="ollama", name="Offline fixture"))
            sid, state = Runtime(store, credentials, NativeFixture).run(
                Agent(tools=["project_map"], allow_writes=False),
                root,
                "Map the project.",
                lambda *args: False,
            )
            events = store.events(sid)
            summary = next(e["data"] for e in events if e["kind"] == "run.summary")
            require(state == "completed" and summary["tools"]["failed"] == 1)
            require(
                summary["tools"]["recovered_validation_errors"] == 1
                and summary["unresolved_tool_errors"] == 0
            )
            require(any(e["data"].get("code") == "TOOL_ARGUMENT_VALIDATION" for e in events))
            require(not list(root.iterdir()))
    return {"validation_recovery_verified": True, "external_requests": 0}


def checkpoint_recovery_check(credentials):
    with tempfile.TemporaryDirectory(prefix="aigentics-checkpoint-") as folder:
        root = Path(folder) / "project"
        root.mkdir()
        db = Path(folder) / "state.sqlite3"
        with closing(Store(db, credentials)) as store:
            plans = TaskPlans(store, root)
            plans.save([Step(task="Create output", outputs=["output.txt"]), Step(task="Next step")])
            plans.begin(0)
            sid = store.start(Agent(), root)
            plans.bind(0, sid)
        with closing(Store(db, credentials)) as store:
            plans = TaskPlans(store, root)
            require(plans.steps()[0].state == "started" and plans.steps()[0].session == sid)
            plans.reconcile(0)
            try:
                plans.checkpoint(0)
            except ValueError:
                pass
            else:
                raise AssertionError("An interrupted action was certified")
            plans.reset(0)
            plans.begin(0)
            sid = store.start(Agent(), root)
            store.finish(sid, "completed", "Synthetic completion")
            plans.finish(0, sid)
            (root / "output.txt").write_bytes(b"accepted")
            plans.checkpoint(0)
            (root / "output.txt").write_bytes(b"changed")
            try:
                plans.begin(1)
            except ValueError:
                pass
            else:
                raise AssertionError("A changed checkpoint was accepted")
    return {"checkpoint_recovery_verified": True, "external_requests": 0}
