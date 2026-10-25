"""Frozen same-task direct versus managed trials, counting total team overhead."""

from contextlib import closing
from pathlib import Path
import tempfile
import time

from .coordination import Coordinator, RootBudget, MAX_CALLS, MAX_OUTPUT_RESERVATION
from .crew import make_agent
from .crew_cases import CASES
from .contracts import contract_prompt, evaluate_contract
from .diagnostics import model_evidence
from .runtime import Runtime
from .store import Store
from .task_checks import TaskChecks
from .tools import Workspace


def run_trial(store, credentials, primary, trial, cancel, provider_factory=None):
    from .providers import Provider
    from .test_suite import local_profile

    before = time.monotonic()
    case = next(c for c in CASES if c.id == trial.case_id)
    agent = make_agent("orion" if trial.arm == "managed" else "ada", primary)
    agent.max_seconds = trial.session_budget_seconds
    agent.max_steps = MAX_CALLS
    profile = local_profile(store, agent).model_copy(
        update={"ollama_thinking": "off", "temperature": 0.2, "top_p": None, "top_k": None}
    )
    checks = TaskChecks(
        write_targets=sorted(case.outputs),
        required_reads=list(case.required_reads),
        require_tools=True,
        completion_feedback=True,
    )
    with tempfile.TemporaryDirectory(prefix="aigentics-team-") as folder:
        root = Path(folder) / "project"
        root.mkdir()
        for name, data in case.files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        with closing(Store(Path(folder) / "evidence.sqlite3", credentials)) as db:
            db.save_profile(profile)
            factory = provider_factory or Provider
            runtime = (
                Coordinator(db, credentials, factory)
                if trial.arm == "managed"
                else Runtime(
                    db, credentials, RootBudget(trial.session_budget_seconds, cancel=cancel).factory(factory)
                )
            )
            sid, state = runtime.run(
                agent,
                root,
                contract_prompt(case),
                lambda kind, details: kind == "write_file" and details.get("path") in case.outputs,
                cancel,
                task_checks=checks,
                acceptance=lambda ws, content: evaluate_contract(case, ws.root, content),
            )
            events = db.events(sid)
            summary = next(
                e["data"] for e in reversed(events) if e["kind"] in ("team.summary", "run.summary")
            )
            passed = state == "completed" and all(evaluate_contract(case, root, "")["checks"].values())
            children = summary.get("children", [])
            child_events = [event for child in children for event in db.events(child)]
            evidence = model_evidence(events + child_events)
            evidence.update(
                runtime_state=state,
                terminal_response_status="accepted" if state == "completed" else "not_accepted",
                role="orion" if trial.arm == "managed" else "ada",
                thinking_mode="off",
                **trial.budget,
                team_metrics={
                    "dispatches": len(children),
                    "total_calls": summary.get("budget", {}).get(
                        "calls", sum(e["kind"] == "model.requested" for e in events)
                    ),
                    "call_limit": MAX_CALLS,
                    "output_limit": MAX_OUTPUT_RESERVATION,
                    "stages_verified": sum(stage["verified"] for stage in summary.get("stages", [])),
                    "managed": trial.arm == "managed",
                },
            )
            evidence["requirement_checks"] = evaluate_contract(case, Workspace(root).root, "")["checks"] | {
                "RUN_COMPLETED": state == "completed"
            }
    return {
        "id": trial.id,
        "status": "passed" if passed else "failed",
        "code": "OK" if passed else "ROLE_REQUIREMENTS_NOT_MET",
        "message": "Matched TOTAL-budget build workflow",
        "duration_ms": round((time.monotonic() - before) * 1000),
        "evidence": evidence,
    }
