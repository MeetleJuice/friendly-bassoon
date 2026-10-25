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


def crew_evaluation_check(credentials):
    """Packaged role/tool/evaluator integration; no model server or pytest needed."""
    import json

    from .campaign import role_case
    from .crew import ROLES, make_agent
    from .crew_cases import CASES, evaluate_content
    from .models import ModelRef

    primary = ModelRef(profile_id="ollama", model="offline-crew-fixture")
    agents = [make_agent(role, primary) for role in ROLES]
    require(len(agents) == 6 and len({agent.id for agent in agents}) == 6)
    require(
        all(agent.primary == primary and not agent.fallbacks and not agent.allow_commands for agent in agents)
    )
    require(all("run_command" not in agent.tools for agent in agents))
    require(not agents[1].allow_writes and not agents[4].allow_writes)
    case = next(case for case in CASES if case.id == "scout_symbol")

    class NativeFixture:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True, "source": "offline_fixture"}

        def chat(self, model, messages, tools):
            require(all(tool["function"]["name"] != "write_file" for tool in tools))
            if not any(message["role"] == "tool" for message in messages):
                return Reply(
                    calls=[
                        ToolCall(id=str(index), name="read_file", arguments={"path": name})
                        for index, name in enumerate(case.required_reads)
                    ]
                )
            return Reply(content=json.dumps(case.answer))

    with tempfile.TemporaryDirectory(prefix="aigentics-crew-fixture-") as directory:
        folder = Path(directory)
        with closing(Store(folder / "fixture.sqlite3", credentials)) as store:
            store.save_profile(Profile(id="ollama", name="Offline crew fixture"))
            row = role_case(store, credentials, primary, case, __import__("threading").Event(), NativeFixture)
            require(row["status"] == "passed")
            require(row["evidence"]["native_calls_total"] == 2)
            require(all(row["evidence"]["requirement_checks"].values()))
        root = folder / "negative"
        root.mkdir()
        for name, data in case.files.items():
            (root / name).write_bytes(data)
        wrong = evaluate_content(case, root, '{"file":"billing_notes.py","symbol":"calculate_total"}')
        require(wrong["FINAL_ANSWER"] is False)
        (root / "unexpected.txt").write_bytes(b"not allowed")
        require(evaluate_content(case, root, json.dumps(case.answer))["NO_UNEXPECTED_FILES"] is False)
    return {"crew_fixture_verified": True, "external_requests": 0}


def correctness_check(credentials):
    """A successful native write/readback must not certify incorrect content."""
    from .task_checks import TaskChecks

    class NativeFixture:
        def __init__(self, *args):
            pass

        def capabilities(self, model):
            return {"tools": True}

        def chat(self, model, messages, tools):
            count = sum(m["role"] == "tool" for m in messages)
            if count == 0:
                return Reply(
                    calls=[
                        ToolCall(
                            id="save",
                            name="write_file",
                            arguments={"path": "result.txt", "content": "wrong", "expected_sha256": "new"},
                        )
                    ]
                )
            if count == 1:
                return Reply(
                    calls=[ToolCall(id="inspect", name="read_file", arguments={"path": "result.txt"})]
                )
            return Reply(content="Done")

    with tempfile.TemporaryDirectory(prefix="aigentics-correctness-") as folder:
        root = Path(folder) / "project"
        root.mkdir()
        with closing(Store(Path(folder) / "state.sqlite3", credentials)) as store:
            store.save_profile(Profile(id="ollama", name="Offline fixture"))
            sid, state = Runtime(store, credentials, NativeFixture).run(
                Agent(max_steps=5),
                root,
                "Save the required correct result",
                lambda *args: True,
                task_checks=TaskChecks(write_targets=["result.txt"], completion_feedback=True),
                acceptance=lambda ws, text: {"EXACT_OUTPUT": ws.read("result.txt")["content"] == "right"},
            )
            summary = next(e["data"] for e in store.events(sid) if e["kind"] == "run.summary")
            require(state == "needs_review" and summary["tools"]["writes_verified"] == 1)
            require(summary["task_checks"]["missing_readbacks"] == 0)
            require(summary["task_checks"]["content_failures"] == 1)
            require(summary["completion_feedback_count"] == 1)
    return {"correctness_fixture_verified": True, "external_requests": 0}
