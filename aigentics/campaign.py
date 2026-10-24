"""Bounded, resumable evaluation of independent same-model crew members.

Only completed case evidence persists. Each attempt gets a fresh disposable project;
unknown in-flight effects are marked interrupted, never silently replayed.
"""

from contextlib import closing
from pathlib import Path
import tempfile
import time
import threading

from .crew import CREW_VERSION, make_agent
from .crew_cases import CASES as ROLE_CASES, evaluate_content
from .diagnostics import DiagnosticRunner, model_evidence
from .evidence import base_report
from .runtime import Runtime
from .store import Store
from .task_checks import TaskChecks
from .test_suite import (
    CASES,
    REQUIREMENT_LABELS as BASE_LABELS,
    local_profile,
    matching_results,
    run_suite,
    bounded_tool_timeline,
)
from .tools import Workspace

CAMPAIGN_VERSION = "crew-campaign-2"
MAX_SECONDS = 7200
REPEAT_CASES = ("edit", "unicode", "transform", "noop", "stale", "map")
REQUIREMENT_LABELS = {
    **BASE_LABELS,
    "OUTPUT_CONTENT": "Output contents satisfy the independent contract",
    "FINAL_ANSWER": "Final JSON answer matches source evidence",
    "INPUTS_UNCHANGED": "Unrelated input files remain unchanged",
    "NO_UNEXPECTED_FILES": "No unexpected files were created",
    "SOURCE_READS": "Every required source was actually read",
    "READ_BEFORE_WRITE": "Required source reads precede the first saved change",
    "TASK_VERIFIED": "Saved outputs were verified and read back",
    "RUN_COMPLETED": "Runtime completed without unresolved errors",
}
PLAN_IDS = tuple(
    [f"baseline-{c[0]}" for c in CASES]
    + [f"{c.role}-{c.id}" for c in ROLE_CASES]
    + [f"repeat-{identity}" for identity in REPEAT_CASES]
)


def plan(mode):
    if mode not in ("quick", "standard", "deep"):
        raise ValueError("Unknown campaign mode")
    return [] if mode == "quick" else list(PLAN_IDS[:36] if mode == "standard" else PLAN_IDS)


def latest_resumable(store, scope):
    newest = next(
        (
            r["payload"]
            for r in store.diagnostic_reports()
            if r["payload"].get("kind") == "crew_campaign"
            and r["payload"].get("local_scope") == scope
            and r["payload"].get("suite_version") == CAMPAIGN_VERSION
        ),
        None,
    )
    if newest and newest.get("state") in ("running", "interrupted", "cancelled"):
        completed = {r["id"] for r in newest.get("checks", [])}
        if set(plan(newest.get("mode", "deep"))) - completed:
            return newest
    return None


def campaign_scope(store, agent, mode):
    profile = local_profile(store, agent) if mode != "quick" else None
    return store.fingerprint(
        {
            "model": agent.primary.model_dump() if profile else None,
            "profile": profile.model_dump() if profile else None,
            "crew": CREW_VERSION,
            "campaign": CAMPAIGN_VERSION,
            "mode": mode,
        }
    )


def role_case(store, credentials, primary, case, cancel, provider_factory=None):
    """Run native tools; grade structured data, never execute generated model code."""
    from .providers import Provider

    agent = make_agent(case.role, primary)
    observed, replies = [], []
    budget = {"max_output_tokens": 4096, "request_timeout_seconds": 120, "session_budget_seconds": 180}
    profile = local_profile(store, agent)
    budget["request_timeout_seconds"] = min(profile.timeout_seconds, 120)
    agent.max_seconds = 180
    agent.max_steps = 10
    before = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="aigentics-role-") as directory:
        root = Path(directory) / "project"
        root.mkdir()
        for name, data in case.files.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        workspace = Workspace(root)

        def same(path, target):
            try:
                return isinstance(path, str) and workspace.path(path) == workspace.path(target)
            except (ValueError, PermissionError, OSError):
                return False

        class BoundedProvider:
            def __init__(self, *args):
                self.inner = (provider_factory or Provider)(*args)

            def __getattr__(self, key):
                return getattr(self.inner, key)

            def chat(self, model, messages, tools):
                reply = (
                    self.inner.chat(model, messages, tools, max_output_tokens=4096)
                    if provider_factory is None
                    else self.inner.chat(model, messages, tools)
                )
                observed.extend(reply.calls)
                if not reply.calls:
                    replies.append(reply.content)
                return reply

        outputs = {*case.outputs, *case.output_json}
        with closing(Store(Path(directory) / "trial.sqlite3", credentials)) as trial:
            trial.save_profile(
                profile.model_copy(update={"timeout_seconds": budget["request_timeout_seconds"]})
            )
            sid, state = Runtime(trial, credentials, BoundedProvider).run(
                agent,
                root,
                case.prompt,
                lambda kind, detail: kind == "write_file"
                and any(same(detail.get("path"), p) for p in outputs),
                cancel,
                capture=False,
                task_checks=TaskChecks(
                    write_targets=sorted(outputs),
                    require_tools=True,
                    require_readback=True,
                    required_reads=list(case.required_reads),
                    completion_feedback=True,
                ),
            )
            events = trial.events(sid)
            summary = next((e["data"] for e in reversed(events) if e["kind"] == "run.summary"), {})
            requirements = evaluate_content(case, root, replies[-1] if replies else "")
            sources = [
                matching_results(
                    events, observed, trial, "read_file", lambda args, name=name: same(args.get("path"), name)
                )
                for name in case.required_reads
            ]
            writes = [
                i
                for i, e in enumerate(events)
                if e["kind"] == "tool.result"
                and e["data"].get("tool") == "write_file"
                and e["data"].get("status") == "succeeded"
                and e["data"].get("verified")
            ]
            requirements.update(
                {
                    "SOURCE_READS": all(sources),
                    "READ_BEFORE_WRITE": not writes
                    or all(any(i < min(writes) for i, _ in group) for group in sources),
                    "TASK_VERIFIED": summary.get("task_checks", {}).get("status") == "passed",
                    "RUN_COMPLETED": state == "completed",
                }
            )
            evidence = {
                **model_evidence(events),
                **budget,
                "role": case.role,
                "attempt": 1,
                "requirement_checks": requirements,
                "task_checks": summary.get("task_checks", {}),
                "execution_counts": summary.get("tools", {}),
                "tool_timeline": bounded_tool_timeline(
                    [e["data"] for e in events if e["kind"] == "tool.result"]
                ),
                "runtime_state": state,
                "final_response_status": summary.get("final_response_status", "not_reached"),
                "file_matches": requirements["OUTPUT_CONTENT"],
                "native_calls_total": sum(
                    e["data"].get("tool_calls", 0) for e in events if e["kind"] == "model.responded"
                ),
            }
    passed = all(requirements.values())
    return {
        "id": f"{case.role}-{case.id}",
        "status": "passed" if passed else "failed",
        "code": "OK"
        if passed
        else "MODEL_OR_RUNTIME_FAILED"
        if state == "failed"
        else "ROLE_REQUIREMENTS_NOT_MET",
        "message": case.title,
        "duration_ms": round((time.monotonic() - before) * 1000),
        "evidence": evidence,
    }


def run_campaign(store, credentials, agent, cancel, emit, mode="deep", resume=False, provider_factory=None):
    """Two reports, no API checks, no orchestration, finite local model workload."""
    scope = campaign_scope(store, agent, mode)
    identities = plan(mode)
    report = latest_resumable(store, scope) if resume else None
    if report is None:
        report = base_report(
            "crew_campaign",
            CAMPAIGN_VERSION,
            "Synthetic requirement counters only; no source, prompts, credentials or private paths.",
        )
        report.update(
            local_scope=scope,
            planned_cases=len(identities),
            mode=mode,
            state="running",
            crew_version=CREW_VERSION,
            active_case=None,
            local_configuration={
                "model": agent.primary.model_dump() if mode != "quick" else None,
                "profile": local_profile(store, agent).model_dump() if mode != "quick" else None,
                "role_fingerprints": {
                    role: store.fingerprint(make_agent(role, agent.primary).model_dump())
                    for role in ("george", "scout", "ada", "vera", "sentinel", "atlas")
                }
                if mode != "quick"
                else {},
            },
        )
    if any(r["id"] not in identities for r in report["checks"]):
        raise ValueError("Saved campaign does not match its manifest")
    uncertain_ms = 0
    if report.get("active_case") in identities and not any(
        r["id"] == report["active_case"] for r in report["checks"]
    ):
        uncertain_ms = min(180000, max(0, report.get("active_case_budget_ms", 180000)))
        report["checks"].append(
            {
                "id": report["active_case"],
                "status": "failed",
                "code": "INTERRUPTED_CASE_NOT_REPLAYED",
                "message": "Interrupted attempt not replayed",
                "duration_ms": 0,
                "evidence": {"timing_unknown": True},
            }
        )
    prior_ms = report.get("duration_ms", 0)
    prior_budget_ms = max(report.get("budget_used_ms", 0), prior_ms) + uncertain_ms
    report["active_case"] = None
    report["active_case_budget_ms"] = 0
    report["budget_used_ms"] = prior_budget_ms
    report["state"] = "running"
    store.save_diagnostic(report)
    before = time.monotonic()

    class CampaignCancel:
        def __init__(self):
            self.local = threading.Event()

        def set(self):
            self.local.set()

        def is_set(self):
            return (
                self.local.is_set()
                or cancel.is_set()
                or prior_budget_ms / 1000 + time.monotonic() - before >= MAX_SECONDS
            )

    bounded_cancel = CampaignCancel()
    health = DiagnosticRunner(store, credentials).run(CampaignCancel(), emit, include_network=False)
    health.pop("recent_runs", None)
    store.save_diagnostic(health)
    done = {row["id"] for row in report["checks"]}
    for row in report["checks"]:
        emit({"kind": "campaign.result", "data": row})
    by_id = {f"{c.role}-{c.id}": c for c in ROLE_CASES}
    for identity in identities:
        if identity in done or bounded_cancel.is_set():
            continue
        report["active_case"] = identity
        report["duration_ms"] = prior_ms + round((time.monotonic() - before) * 1000)
        report["budget_used_ms"] = prior_budget_ms + round((time.monotonic() - before) * 1000)
        report["active_case_budget_ms"] = 180000
        store.save_diagnostic(report)
        emit({"kind": "campaign.started", "data": {"id": identity}})
        started = time.monotonic()
        try:
            if identity.startswith(("baseline-", "repeat-")):
                name = identity.split("-", 1)[1]
                baseline = run_suite(
                    store,
                    credentials,
                    make_agent("george", agent.primary),
                    CampaignCancel(),
                    lambda event: None,
                    provider_factory=provider_factory,
                    case_ids=[name],
                    persist=False,
                    completion_feedback=True,
                )
                if not baseline["checks"]:
                    break
                row = baseline["checks"][0]
                row["id"] = identity
                row["evidence"].update(role="george", attempt=2 if identity.startswith("repeat-") else 1)
            else:
                row = role_case(
                    store, credentials, agent.primary, by_id[identity], CampaignCancel(), provider_factory
                )
        except Exception as exc:
            row = {
                "id": identity,
                "status": "failed",
                "code": "SUITE_CASE_FAILED",
                "message": "Case failed; bounded exception class retained locally",
                "duration_ms": round((time.monotonic() - started) * 1000),
                "evidence": {"local_error_type": type(exc).__name__},
            }
        report["checks"].append(row)
        report["active_case"] = None
        report["active_case_budget_ms"] = 0
        report["duration_ms"] = prior_ms + round((time.monotonic() - before) * 1000)
        report["budget_used_ms"] = prior_budget_ms + round((time.monotonic() - before) * 1000)
        store.save_diagnostic(report)
        emit({"kind": "campaign.result", "data": row})
    report["duration_ms"] = prior_ms + round((time.monotonic() - before) * 1000)
    report["budget_used_ms"] = prior_budget_ms + round((time.monotonic() - before) * 1000)
    report["stop_reason"] = (
        "cancelled" if cancel.is_set() else "campaign_budget" if bounded_cancel.is_set() else "finished"
    )
    report["summary"] = {
        key: sum(row["status"] == key for row in report["checks"])
        for key in ("passed", "failed", "skipped", "warning")
    }
    report["state"] = (
        "cancelled"
        if cancel.is_set()
        else "needs_attention"
        if bounded_cancel.is_set()
        else "passed"
        if report["summary"]["passed"] == len(identities)
        else "needs_attention"
    )
    store.save_diagnostic(report, refresh_retention=True)
    store.prune()
    return [health, report]
