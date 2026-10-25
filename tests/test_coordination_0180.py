"""Actual native dispatch, files, approvals, SQLite recovery and total-budget regressions."""

import json
import threading
import pytest
from pydantic import ValidationError

from aigentics.coordination import Coordinator, RootBudget
from aigentics.crew import make_agent, ensure_roster
from aigentics.models import Agent, Profile, ModelRef, Reply, ToolCall
from aigentics.runtime import Runtime
from aigentics.store import Store
from aigentics.task_checks import TaskChecks


def call(name, **arguments):
    return Reply(calls=[ToolCall(id="native", name=name, arguments=arguments)], usage={"eval_count": 1})


class PilotModel:
    fault = ""
    review = True
    calls = 0

    def __init__(self, profile, credentials):
        self.profile = profile

    def capabilities(self, model):
        return {
            "tools": True,
            "thinking_support": "reported",
            "thinking_values": [False, True],
            "thinking_default": True,
        }

    def chat(self, model, messages, tools, **kwargs):
        type(self).calls += 1
        previous = [m for m in messages if m["role"] == "tool"]
        names = {t["function"]["name"] for t in tools}
        if "dispatch_worker" in names:
            if self.fault == "prose":
                return Reply(content="Everything passed!")
            if self.fault == "recursion":
                return call("dispatch_worker", role="orion", revision="a" * 64)
            if not previous:
                return call("team_status")
            status = json.loads(previous[-1]["content"])
            if self.fault == "stale":
                return call("dispatch_worker", role="ada", revision="a" * 64)
            if not status["evidence"]:
                return call("dispatch_worker", role="ada", revision=status["revision"])
            if self.fault == "duplicate":
                return call("dispatch_worker", role="ada", revision=status["revision"])
            if self.review and len(status["evidence"]) == 1 and status["evidence"][0]["verified"]:
                return call("dispatch_worker", role="sentinel", revision=status["revision"])
            return Reply(content="Recorded work completed. Review is advisory.", usage={"eval_count": 1})
        reviewer = "Your agent name is Sentinel" in messages[0]["content"]
        actions = [("read_file", {"path": "brief.txt"})]
        if not reviewer:
            if self.fault == "empty_worker":
                return Reply(content="")
            actions.append(
                ("write_file", {"path": "answer.txt", "content": "ready\n", "expected_sha256": "new"})
            )
        actions.append(("read_file", {"path": "answer.txt"}))
        if len(previous) < len(actions):
            name, args = actions[len(previous)]
            return call(name, **args)
        return Reply(content="Verified recorded sources.", usage={"eval_count": 1})


@pytest.fixture
def pilot(store, tmp_path):
    store.save_profile(Profile(id="ollama", name="Local"))
    root = tmp_path / "project"
    root.mkdir()
    (root / "brief.txt").write_text(
        "Create answer.txt containing ready followed by newline.", encoding="utf-8"
    )
    agent = make_agent("orion", ModelRef(profile_id="ollama", model="fixture:8b"))
    checks = TaskChecks(write_targets=["answer.txt"], required_reads=["brief.txt"], require_tools=True)
    return agent, root, checks


def execute(store, credentials, pilot, factory=PilotModel, **kwargs):
    agent, root, checks = pilot
    return Coordinator(store, credentials, factory).run(
        agent,
        root,
        "Create answer.txt from brief.txt",
        kwargs.pop("approve", lambda *args: True),
        task_checks=checks,
        **kwargs,
    )


def test_real_build_review_and_linked_evidence(store, credentials, pilot):
    events = []
    approvals = []
    sid, state = execute(
        store,
        credentials,
        pilot,
        emit=events.append,
        approve=lambda kind, details: approvals.append(kind) or True,
    )
    assert state == "completed", store.sessions()
    assert (pilot[1] / "answer.txt").read_bytes() == b"ready\n"
    children = [s for s in store.sessions() if s["parent"] == sid]
    assert len(children) == 2 and all(s["state"] == "completed" for s in children)
    assert approvals == ["write_file"]
    summary = next(e["data"] for e in store.events(sid) if e["kind"] == "team.summary")
    assert summary["budget"]["calls"] == 11
    assert summary["budget"]["output_reserved"] == 11 * 4096
    assert all(stage["verified"] for stage in summary["stages"])
    assert summary["goal_verification"] == "operational_checks_only"
    assert any(e["kind"] == "team.owner" for e in events)
    assert not any(e["kind"] == "tool.requested" for e in store.events(sid))
    assert store.messages(sid) == []


@pytest.mark.parametrize("fault", ["prose", "recursion", "stale", "duplicate", "empty_worker"])
def test_bad_routes_or_missing_evidence_never_pass(fault, store, credentials, pilot):
    class Fault(PilotModel):
        pass

    Fault.fault = fault
    sid, state = execute(store, credentials, pilot, Fault)
    assert state != "completed"
    children = [s for s in store.sessions() if s["parent"] == sid]
    assert len(children) <= 1
    if fault in ("prose", "recursion", "stale"):
        assert not (pilot[1] / "answer.txt").exists()


def test_denied_write_cannot_be_overruled_by_manager(store, credentials, pilot):
    sid, state = execute(store, credentials, pilot, approve=lambda *args: False)
    assert state != "completed"
    assert not (pilot[1] / "answer.txt").exists()
    assert len([s for s in store.sessions() if s["parent"] == sid]) == 1


def test_total_request_limit_covers_manager_and_children(store, credentials, pilot):
    pilot[0].max_steps = 4
    sid, state = execute(store, credentials, pilot)
    assert state != "completed"
    summary = next(e["data"] for e in store.events(sid) if e["kind"] == "team.summary")
    assert summary["budget"]["calls"] == 4
    assert summary["budget"]["output_reserved"] == 4 * 4096


def test_cancelled_child_stops_team_and_keeps_saved_effects(store, credentials, pilot):
    stop = threading.Event()

    def activity(event):
        if event["kind"] == "tool.result" and event["data"].get("verified"):
            stop.set()

    sid, state = execute(store, credentials, pilot, cancel=stop, emit=activity)
    assert state == "cancelled"
    assert (pilot[1] / "answer.txt").read_bytes() == b"ready\n"
    assert not any(s["state"] == "running" for s in store.sessions())
    with pytest.raises(ValueError, match="fresh"):
        execute(store, credentials, pilot, parent=sid)


def test_crash_reopen_marks_root_and_child_interrupted_without_replay(store, credentials, pilot):
    root = store.start(pilot[0], pilot[1], False)
    child = store.start(make_agent("ada", pilot[0].primary), pilot[1], False, root)
    reopened = Store(store.path, credentials)
    try:
        assert {s["id"]: s["state"] for s in reopened.sessions()} == {
            root: "interrupted",
            child: "interrupted",
        }
        assert not (pilot[1] / "answer.txt").exists()
    finally:
        reopened.close()


def test_output_reservation_and_expired_budget_prevent_dispatch():
    budget = RootBudget(10, output=4096)
    budget.reserve(4096)
    with pytest.raises(Exception, match="budget"):
        budget.reserve(4096)
    budget.deadline = 0
    with pytest.raises(InterruptedError):
        budget.reserve(1)
    assert budget.calls == 1


def test_stock_migration_preserves_model_and_historical_snapshot(store, credentials):
    primary = ModelRef(profile_id="ollama", model="fixture:8b")
    george = store.save_agent(make_agent("george", primary))
    sid = store.start(george, "synthetic", False)
    store.finish(sid, "completed", "Historical generalist")
    roster = ensure_roster(store, primary)
    assert roster["orion"].name == "Orion" and roster["orion"].kind == "coordinator"
    assert roster["orion"].primary == primary and roster["orion"].id == george.id
    assert json.loads(store.sessions()[0]["agent"])["name"] == "George"
    assert len(store.agents()) == 6
    assert ensure_roster(store, primary) == roster


def test_custom_george_is_preserved_and_orion_added(store):
    primary = ModelRef(profile_id="ollama", model="fixture:8b")
    george = make_agent("george", primary)
    george.instructions = "My customized instructions"
    store.save_agent(george)
    roster = ensure_roster(store, primary)
    assert next(a for a in store.agents() if a.id == george.id) == george
    assert roster["orion"].id != george.id


@pytest.mark.parametrize(
    "overrides",
    [
        {"allow_writes": True},
        {"tools": ["read_file"]},
        {"allow_commands": True},
        {"fallbacks": [{"profile_id": "x", "model": "x"}]},
    ],
)
def test_typed_coordinator_rejects_escalated_permissions(overrides):
    data = make_agent("orion", Agent().primary).model_dump() | overrides
    with pytest.raises(ValidationError):
        Agent.model_validate(data)


def test_worker_runtime_cannot_execute_a_coordinator(store, credentials, pilot):
    with pytest.raises(ValueError, match="pilot"):
        Runtime(store, credentials, PilotModel).run(pilot[0], pilot[1], "task", lambda *args: True)


def test_qt_workbench_runs_native_pilot_and_preserves_worker_lifecycle(
    qtbot, store, credentials, pilot, monkeypatch
):
    from aigentics.ui import Window
    from test_campaign_ui_0120 import cleanup
    import aigentics.coordination as module

    original = module.Coordinator
    monkeypatch.setattr(module, "Coordinator", lambda db, keys: original(db, keys, PilotModel))
    store.save_agent(pilot[0])
    window = Window(store, credentials)
    qtbot.addWidget(window, before_close_func=cleanup)
    window.store.close = lambda: None
    errors = []
    monkeypatch.setattr(window, "error", errors.append)

    def approve(request):
        request["allowed"] = True
        request["done"].set()

    monkeypatch.setattr(window, "on_approval", approve)
    window.select_workspace(pilot[1])
    window.run_agent.setCurrentIndex(window.run_agent.findData(pilot[0].id))
    window.task.setPlainText("Create answer.txt from brief.txt")
    window.expected_files.setText("answer.txt")
    try:
        window.start_run()
        qtbot.waitUntil(lambda: window.worker is not None and not window.worker.isRunning(), timeout=15000)
        qtbot.waitUntil(lambda: window.work_run.isEnabled(), timeout=5000)
        assert not errors
        assert (pilot[1] / "answer.txt").read_bytes() == b"ready\n"
        assert "TEAM" in window.work_output.toPlainText()
        assert "Ada" not in errors
        assert len(store.sessions()) == 3
    finally:
        cleanup(window)


def test_experimental_preset_edits_preview_without_changing_saved_profile(qtbot, store, credentials):
    from aigentics.ui import Window
    from test_campaign_ui_0120 import cleanup

    store.save_profile(Profile(id="ollama", name="Local"))
    window = Window(store, credentials)
    qtbot.addWidget(window, before_close_func=cleanup)
    window.store.close = lambda: None
    window.profile_select.setCurrentIndex(window.profile_select.findData("ollama"))
    before = store.profiles()[0]
    window.sampling_preset.setCurrentIndex(window.sampling_preset.findData("tools"))
    preview = Profile.model_validate_json(window.profile_json.toPlainText())
    assert preview.ollama_thinking == "off" and preview.temperature == 0.2
    assert store.profiles()[0] == before
    window.save_profile()
    assert store.profiles()[0] == preview
    cleanup(window)


def test_workbench_continue_cannot_silently_restart_a_team(qtbot, store, credentials, pilot, monkeypatch):
    from aigentics.ui import Window
    from test_campaign_ui_0120 import cleanup

    store.save_agent(pilot[0])
    window = Window(store, credentials)
    qtbot.addWidget(window, before_close_func=cleanup)
    window.store.close = lambda: None
    errors = []
    monkeypatch.setattr(window, "error", errors.append)
    window.select_workspace(pilot[1])
    window.run_agent.setCurrentIndex(window.run_agent.findData(pilot[0].id))
    window.conversation_mode.setCurrentIndex(window.conversation_mode.findData("continue"))
    window.parent_session = "previous-team"
    window.task.setPlainText("Create answer.txt from brief.txt")
    window.expected_files.setText("answer.txt")
    window.start_run()
    assert errors and "fresh" in str(errors[0])
    assert window.worker is None and not store.sessions()
    assert not (pilot[1] / "answer.txt").exists()
    cleanup(window)
