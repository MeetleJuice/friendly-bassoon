"""Useful, consented and browser-sized evidence for the expanded suite."""

import json
from urllib.parse import parse_qs, urlsplit
import pytest
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.runtime import Runtime
from aigentics.evidence import base_report, report_guidance, run_report
from aigentics.reporting import issue_body, prepare_browser_draft, public_report
from aigentics.regression_checks import validation_recovery_check, checkpoint_recovery_check


@pytest.mark.parametrize("count", [10, 18, 24])
def test_large_reports_keep_all_cases_budgets_recovery_and_no_private_values(credentials, count):
    report = base_report("agent_suite", "agent-suite-4", "Metadata")
    report["planned_cases"] = count
    report["checks"] = [
        {
            "id": f"case_{i}",
            "status": "failed",
            "code": "REQUIRED_OPERATIONS_NOT_VERIFIED",
            "message": "Application acceptance",
            "duration_ms": 123456,
            "evidence": {
                "runtime_state": "needs_review",
                "native_calls_total": 8,
                "file_matches": False,
                "max_output_tokens": 4096,
                "request_timeout_seconds": 120,
                "session_budget_seconds": 180,
                "tool_error_types": {"ValidationError": 2, "PermissionError": 1},
                "validation_issue_counts": {"UNEXPECTED_ARGUMENT": 2, "PRIVATE": 9},
                "execution_counts": {
                    "writes_verified": 1,
                    "failed": 3,
                    "recovered_validation_errors": 2,
                    "unchanged_writes": 1,
                    "recovered_edit_errors": 1,
                },
                "failure_usage": {
                    "eval_count": 4096,
                    "prompt_eval_count": 1000,
                    "total_duration": 1234567,
                    "secret": "PRIVATE",
                },
                "task_checks": {"status": "needs_attention"},
                "final_response_status": "present",
                "request_traces": [
                    {
                        "step": j,
                        "native_call_count": 1,
                        "content_chars": 500,
                        "request_chars": 10000,
                        "tool_schema_chars": 1000,
                        "response_shape": {"thinking_chars": 100},
                        "usage": {"prompt_eval_count": 1000, "eval_count": 1000},
                        "PRIVATE": "PRIVATE",
                    }
                    for j in range(8)
                ],
                "source": "PRIVATE",
                "path": "PRIVATE",
            },
        }
        for i in range(count)
    ]
    title, body = issue_body(report, credentials)
    url = prepare_browser_draft(title, body)
    assert len(url) <= 7500
    shared = parse_qs(urlsplit(url).query)["body"][0]
    assert "PRIVATE" not in shared
    assert all(f"case_{i}|" in shared for i in range(count))
    assert "recovered-validation" in shared and "UNEXPECTED_ARGUMENT" in shared
    assert "ValidationError" in shared and "4096/120/180" in shared
    assert shared.count("|F|") == count


def test_cancelled_partial_suite_never_claims_completed_denominator():
    report = base_report("agent_suite", "agent-suite-4", "Metadata")
    report["planned_cases"] = 18
    report["state"] = "cancelled"
    report["checks"] = [{"status": "passed"}] * 2
    assert "2/18" in report_guidance(report)


def test_run_review_preserves_original_validation_and_narrow_recovery(store, credentials, tmp_path):
    store.save_profile(Profile(id="ollama", name="Fixture"))

    class Correcting:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, model, messages, tools):
            n = sum(m["role"] == "tool" for m in messages)
            if n == 2:
                return Reply(content="Verified map")
            return Reply(
                calls=[
                    ToolCall(
                        id=str(n), name="project_map", arguments={"PRIVATE": "PRIVATE"} if n == 0 else {}
                    )
                ]
            )

    sid, state = Runtime(store, credentials, Correcting).run(
        Agent(tools=["project_map"]), tmp_path, "Map project", lambda *a: False
    )
    assert state == "completed"
    safe = public_report(run_report(store, sid))
    e = safe["checks"][0]["evidence"]
    assert e["execution_counts"]["failed"] == 1 and e["execution_counts"]["recovered_validation_errors"] == 1
    assert e["validation_issue_counts"] == {"UNEXPECTED_ARGUMENT": 1}
    assert "PRIVATE" not in json.dumps(safe)


def test_packaged_new_checks_are_real_offline_regressions(credentials):
    assert validation_recovery_check(credentials)["validation_recovery_verified"]
    assert checkpoint_recovery_check(credentials)["checkpoint_recovery_verified"]


def test_plan_binds_first_activity_before_final_callback(qtbot, store, credentials, tmp_path):
    from aigentics.ui import Window
    from aigentics.task_plans import TaskPlans, Step

    w = Window(store, credentials)
    qtbot.addWidget(w)
    w.select_workspace(tmp_path)
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="First")])
    plans.begin(0)
    sid = store.start(Agent(), tmp_path)
    w.active_plan_step = (plans, 0)
    w.on_activity({"kind": "task.received", "data": {"chars": 5}, "session_id": sid})
    assert plans.steps()[0].session == sid and plans.steps()[0].state == "started"
    assert store.sessions()[0]["state"] == "running"
    store.finish(sid, "interrupted", "Synthetic interruption")
    plans.reconcile(0)
    with pytest.raises(ValueError):
        plans.checkpoint(0)
    w.active_plan_step = None
    w.lab_dir.cleanup()
    w.store.close = lambda: None


def test_finished_worker_queued_signals_cannot_rebind_a_new_job(qtbot, store, credentials):
    from aigentics.ui import Window

    w = Window(store, credentials)
    qtbot.addWidget(w)
    completed = []
    assert w.start_worker(lambda job: "obsolete", lambda result: completed.append(result))
    assert w.worker.wait(3000)  # Thread done; its queued UI callbacks have not run.
    assert w.start_worker(lambda job: "current", lambda result: completed.append(result))
    qtbot.waitUntil(lambda: not w.worker.isRunning(), timeout=3000)
    qtbot.waitUntil(lambda: completed == ["current"], timeout=3000)
    w.lab_dir.cleanup()
    w.store.close = lambda: None


def test_native_two_step_plan_uses_fresh_context_and_accepts_a_later_edit(
    qtbot, store, credentials, tmp_path, monkeypatch
):
    from aigentics.ui import Window
    from aigentics.task_plans import TaskPlans, Step
    from aigentics.task_plans_ui import TaskPlanDialog
    import runpy

    base = runpy.run_path("tests/test_suite_080.py")["Scripted"]

    class Native(base):
        def chat(self, model, messages, tools):
            reply = super().chat(model, messages, tools)
            task = next(m["content"] for m in messages if m["role"] == "user")
            if "seed" in task:
                for call in reply.calls:
                    if call.name == "write_file":
                        call.arguments["content"] = "old\n"
            return reply

    w = Window(store, credentials)
    qtbot.addWidget(w)
    w.select_workspace(tmp_path)
    w.runtime = Runtime(store, credentials, Native)

    def approve(request):
        request["allowed"] = True
        request["done"].set()

    monkeypatch.setattr(w, "on_approval", approve)
    plans = TaskPlans(store, tmp_path)
    plans.save(
        [
            Step(task="Create output.txt with seed contents, then read it back.", outputs=["output.txt"]),
            Step(
                task="Read output.txt, then replace its contents with exactly lighthouse followed by a newline. Then read it back.",
                outputs=["output.txt"],
            ),
            Step(task="Next task"),
        ]
    )
    contexts = []
    for index in (0, 1):
        dialog = TaskPlanDialog(w)
        qtbot.addWidget(dialog)
        dialog.rows.setCurrentRow(index)
        dialog.launch()
        qtbot.waitUntil(lambda: not w.worker.isRunning(), timeout=5000)
        qtbot.waitUntil(lambda: plans.steps()[index].state == "review", timeout=5000)
        sid = plans.steps()[index].session
        contexts.append(
            next(e["data"]["history_messages"] for e in store.events(sid) if e["kind"] == "task.context")
        )
        plans.checkpoint(index)
    assert contexts == [0, 0]
    assert (tmp_path / "output.txt").read_bytes() == b"lighthouse\n"
    assert plans.steps()[0].hashes != plans.steps()[1].hashes
    assert len({s.session for s in plans.steps()[:2]}) == 2
    plans.begin(2)
    assert w.active_plan_step is None
    w.lab_dir.cleanup()
    w.store.close = lambda: None


def test_checkpoint_session_binding_uses_directory_identity_not_spelling(store, tmp_path):
    from aigentics.task_plans import TaskPlans, Step

    root = tmp_path / "project"
    root.mkdir()
    plans = TaskPlans(store, root)
    plans.save([Step(task="Equivalent path")])
    plans.begin(0)
    sid = store.start(Agent(), str(root / ".." / "project"))
    plans.bind(0, sid)
    assert plans.steps()[0].session == sid
    plans.reset(0)
    plans.begin(0)
    sid = store.start(Agent(), tmp_path / "missing")
    with pytest.raises(ValueError):
        plans.bind(0, sid)
