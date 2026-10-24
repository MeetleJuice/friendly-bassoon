import pytest
import threading
import httpx
from aigentics.harness import suite_budget
from aigentics.task_plans import TaskPlans, Step
from aigentics.models import Agent, Profile
from aigentics.providers import Provider, ProviderError


@pytest.mark.parametrize("kind", ["edit", "retrieve", "read", "python"])
@pytest.mark.parametrize("mode", ["balanced", "legacy"])
@pytest.mark.parametrize("seconds", [5, 30, 60, 300])
def test_budget_matrix_is_bounded_and_respects_user_limits(kind, mode, seconds):
    b = suite_budget(kind, mode, seconds, 120)
    assert 1 <= b["request_timeout_seconds"] <= min(120, b["session_budget_seconds"])
    assert 5 <= b["session_budget_seconds"] <= seconds
    assert b["max_output_tokens"] in (1024, 2048, 4096)
    if kind == "edit" and mode == "balanced" and seconds == 300:
        assert b["request_timeout_seconds"] == 120 and b["session_budget_seconds"] == 180


def test_length_response_keeps_only_numeric_usage(credentials):
    profile = Profile(id="ollama", name="Local")

    def response(req):
        return httpx.Response(
            200,
            json={
                "done_reason": "length",
                "message": {"content": "PRIVATE", "thinking": "SECRET"},
                "prompt_eval_count": 123,
                "eval_count": 1024,
                "total_duration": 456,
                "secret": "PRIVATE",
            },
        )

    provider = Provider(profile, credentials, httpx.MockTransport(response))
    with pytest.raises(ProviderError) as error:
        provider.chat("fixture", [], [])
    assert error.value.code == "OUTPUT_LIMIT"
    assert error.value.usage == {"prompt_eval_count": 123, "eval_count": 1024, "total_duration": 456}
    assert "PRIVATE" not in str(error.value) and error.value.http_status == 200


def finish_session(store, root):
    sid = store.start(Agent(), root, False, None)
    store.finish(sid, "completed", "Synthetic fixture")
    return sid


def test_durable_checkpoint_and_changed_revision_block_continuation(store, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    plans = TaskPlans(store, root)
    plans.save([Step(task="Create a", outputs=["a.txt"]), Step(task="Build on a")])
    plans.begin(0)
    with pytest.raises(ValueError):
        TaskPlans(store, root).begin(0)
    (root / "a.txt").write_bytes(b"version1")
    plans.finish(0, finish_session(store, root))
    plans.checkpoint(0)
    (root / "a.txt").write_bytes(b"version2")
    with pytest.raises(ValueError, match="changed"):
        plans.begin(1)
    plans.reset(0)
    assert all(s.state == "planned" for s in plans.steps())


@pytest.mark.parametrize("path", ["../outside.txt", ".env", ".git/config"])
def test_plan_protected_paths_rejected(store, tmp_path, path):
    with pytest.raises(PermissionError):
        TaskPlans(store, tmp_path).save([Step(task="No escape", outputs=[path])])


def test_uncertain_attempt_and_missing_outputs_are_not_verified(store, tmp_path):
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Write", outputs=["missing.txt"])])
    plans.begin(0)
    with pytest.raises(ValueError):
        plans.checkpoint(0)
    plans.finish(0, finish_session(store, tmp_path))
    with pytest.raises(FileNotFoundError):
        plans.checkpoint(0)
    assert plans.steps()[0].state == "review"


def test_suite_balanced_and_legacy_are_separate_scopes(store, credentials):
    import runpy
    from aigentics.test_suite import run_suite

    fixture = runpy.run_path("tests/test_suite_080.py")["Scripted"]
    store.save_profile(Profile(id="ollama", name="Local"))
    a = run_suite(store, credentials, Agent(), threading.Event(), lambda e: None, fixture, "balanced")
    b = run_suite(store, credentials, Agent(), threading.Event(), lambda e: None, fixture, "legacy")
    assert a["suite_version"] == b["suite_version"] == "agent-suite-4"
    assert a["local_scope"] != b["local_scope"]
    edit = next(c for c in a["checks"] if c["id"] == "edit")
    assert edit["evidence"]["request_timeout_seconds"] > 45
    assert edit["evidence"]["max_output_tokens"] == 4096


def test_checkpoint_project_and_step_order_are_enforced(store, tmp_path):
    first = tmp_path / "a"
    second = tmp_path / "b"
    first.mkdir()
    second.mkdir()
    plans = TaskPlans(store, first)
    plans.save([Step(task="first"), Step(task="second")])
    with pytest.raises(ValueError):
        plans.begin(1)
    with pytest.raises(ValueError):
        plans.begin(-1)
    plans.begin(0)
    plans.finish(0, finish_session(store, second))
    with pytest.raises(ValueError):
        plans.checkpoint(0)
    assert TaskPlans(store, second).steps() == []


def test_task_plan_ui_launch_is_fresh_and_completion_attaches_session(
    qtbot, store, credentials, tmp_path, monkeypatch
):
    from aigentics.ui import Window
    from aigentics.task_plans_ui import TaskPlanDialog

    w = Window(store, credentials)
    qtbot.addWidget(w)
    w.select_workspace(tmp_path)
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Create result.txt", outputs=["result.txt"])])
    dialog = TaskPlanDialog(w)
    qtbot.addWidget(dialog)
    called = []
    monkeypatch.setattr(w, "start_run", lambda: called.append(w.conversation_mode.currentData()) or True)
    dialog.launch()
    assert called == ["fresh"] and w.expected_files.text() == "result.txt"
    sid = finish_session(store, tmp_path)
    w.run_completed((sid, "completed"), False)
    assert plans.steps()[0].session == sid and plans.steps()[0].state == "review"
    assert w.active_plan_step is None
    w.lab_dir.cleanup()
    w.store.close = lambda: None


def test_failure_usage_public_allowlist_and_browser_limit(credentials):
    from aigentics.evidence import base_report
    from aigentics.reporting import public_report, issue_body, prepare_browser_draft

    report = base_report("agent_suite", "agent-suite-3", "Metadata")
    report["checks"] = [
        {
            "id": str(i),
            "status": "failed",
            "code": "ACCEPTANCE_NOT_MET",
            "message": "Synthetic",
            "duration_ms": 45000,
            "evidence": {
                "failure_usage": {"eval_count": 2048, "secret": "PRIVATE", "total_duration": True},
                "max_output_tokens": 4096,
                "request_timeout_seconds": 120,
                "session_budget_seconds": 180,
                "request_traces": [{"step": i, "usage": {}, "response_shape": {}}] * 8,
            },
        }
        for i in range(10)
    ]
    safe = public_report(report)
    assert safe["checks"][0]["evidence"]["failure_usage"] == {"eval_count": 2048}
    url = prepare_browser_draft(*issue_body(report, credentials))
    assert len(url) <= 7500 and "PRIVATE" not in url and "rejected_usage" in url


def test_restart_keeps_uncertain_step_and_never_replays(tmp_path, credentials):
    from aigentics.store import Store

    root = tmp_path / "project"
    root.mkdir()
    path = tmp_path / "saved.sqlite3"
    first = Store(path, credentials)
    plan = TaskPlans(first, root)
    plan.save([Step(task="Uncertain attempt")])
    plan.begin(0)
    first.close()
    reopened = Store(path, credentials)
    try:
        plan = TaskPlans(reopened, root)
        assert plan.steps()[0].state == "started"
        with pytest.raises(ValueError):
            plan.begin(0)
        plan.reset(0)
        assert plan.begin(0).state == "started"
    finally:
        reopened.close()


def test_plan_capacity_never_silently_evicts_an_uncertain_plan(store, tmp_path):
    for i in range(32):
        root = tmp_path / str(i)
        root.mkdir()
        plan = TaskPlans(store, root)
        plan.save([Step(task="Step")])
        plan.begin(0)
    root = tmp_path / "extra"
    root.mkdir()
    with pytest.raises(ValueError, match="32"):
        TaskPlans(store, root).save([Step(task="Extra")])
    assert TaskPlans(store, tmp_path / "0").steps()[0].state == "started"
    TaskPlans(store, tmp_path / "0").save([])
    TaskPlans(store, root).save([Step(task="Extra")])


def test_failed_dispatch_does_not_attach_later_unrelated_run(
    qtbot, store, credentials, tmp_path, monkeypatch
):
    from aigentics.ui import Window
    from aigentics.task_plans_ui import TaskPlanDialog

    w = Window(store, credentials)
    qtbot.addWidget(w)
    w.select_workspace(tmp_path)
    plan = TaskPlans(store, tmp_path)
    plan.save([Step(task="Try")])
    d = TaskPlanDialog(w)
    qtbot.addWidget(d)
    monkeypatch.setattr(w, "start_run", lambda: False)
    d.launch()
    assert w.active_plan_step is None and plan.steps()[0].state == "started"
    w.lab_dir.cleanup()
    w.store.close = lambda: None
