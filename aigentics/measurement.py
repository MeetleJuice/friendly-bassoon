"""Content-addressed local measurement definitions and honest repeated-run metrics.

This module never calls a model, executes generated code, or persists user data.
The manifest is an application-owned benchmark definition, not model context.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from math import comb
from typing import Literal

MEASUREMENT_VERSION = "crew-measurement-1"
GRADER_VERSION = "strict-contract-2"
REFERENCE_CASES = (
    ("role", "george_workflow"),
    ("role", "scout_symbol"),
    ("role", "ada_repair"),
    ("role", "vera_exclusive"),
    ("role", "sentinel_bug"),
    ("role", "atlas_stale"),
    ("baseline", "unicode"),
    ("baseline", "noop"),
)

UNKNOWN_CODES = frozenset(
    ("INTERRUPTED_CASE_NOT_REPLAYED", "CANCELLED", "CAMPAIGN_BUDGET_EXHAUSTED", "TOOL_DISABLED")
)
USAGE_KEYS = ("prompt_eval_count", "eval_count")


@dataclass(frozen=True)
class Trial:
    id: str
    case_kind: Literal["baseline", "role"]
    case_id: str
    arm: Literal["reference", "output_only", "coordinated"]
    repeat: int
    max_output_tokens: int
    request_timeout_seconds: int
    session_budget_seconds: int

    @property
    def budget(self):
        return {
            "max_output_tokens": self.max_output_tokens,
            "request_timeout_seconds": self.request_timeout_seconds,
            "session_budget_seconds": self.session_budget_seconds,
        }

    def effective_budget(self, profile_seconds=120, agent_seconds=300):
        """Respect the caller's existing provider and session ceilings."""
        if type(profile_seconds) is not int or type(agent_seconds) is not int:
            raise ValueError("Budget ceilings must be positive integers")
        if profile_seconds < 1 or agent_seconds < 1:
            raise ValueError("Budget ceilings must be positive integers")
        total = min(self.session_budget_seconds, agent_seconds)
        return {
            "max_output_tokens": self.max_output_tokens,
            "request_timeout_seconds": min(self.request_timeout_seconds, profile_seconds, total),
            "session_budget_seconds": total,
        }


def measurement_plan():
    """30 fresh attempts covering all six locals and two budget-sensitive cases.

    Each role receives three reference repeats. Unicode/no-op each receive two
    repeats of reference, output-only and coordinated budgets. Round order is
    fixed and recorded, not randomized; added arms reverse in round two. This
    does not control hardware load, model state or stochastic sampling.
    """
    trials = []
    for repeat in range(1, 4):
        for kind, identity in REFERENCE_CASES:
            if kind != "role":
                continue
            trials.append(
                Trial(
                    f"measure-{identity}-reference-r{repeat}",
                    kind,
                    identity,
                    "reference",
                    repeat,
                    4096,
                    120,
                    180,
                )
            )
        if repeat <= 2:
            arms = (
                ("reference", "output_only", "coordinated")
                if repeat == 1
                else ("coordinated", "output_only", "reference")
            )
            for identity in ("unicode", "noop"):
                for arm in arms:
                    trials.append(
                        Trial(
                            f"measure-{identity}-{arm}-r{repeat}",
                            "baseline",
                            identity,
                            arm,
                            repeat,
                            1024 if arm == "reference" else 4096,
                            120 if arm == "coordinated" else 85,
                            180 if arm == "coordinated" else 90,
                        )
                    )
    return tuple(trials)


def manifest_id(manifest):
    """Canonical JSON SHA256; list order is meaningful, mapping order is not."""
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _bytes_map(value):
    return {name: data.hex() for name, data in sorted(value.items())}


def measurement_manifest(*, grader_version=GRADER_VERSION, policy=None):
    """Return a complete synthetic benchmark definition, never a user snapshot.

    Version semantic grader/harness changes explicitly. Filesystem source hashes
    are deliberately avoided: source files need not exist in frozen installers.
    Model/profile identity and actual server/hardware belong in a separate local
    configuration fingerprint and run evidence, not this public case definition.
    """
    from .crew import CREW_VERSION, make_agent
    from .contracts import HINTS, MAX_MISMATCHES, MAX_POINTER, contract_prompt
    from .crew_cases import CASES as ROLE_CASES
    from .models import ModelRef
    from .test_suite import CASES, CASE_OUTPUTS, COMPLEX_CASES, baseline_files
    from .runtime import RUNTIME_POLICY_VERSION
    from .harness import exercise_tools
    from .tools import SCHEMAS
    from .task_checks import TaskChecks

    if not isinstance(grader_version, str) or not grader_version or len(grader_version) > 100:
        raise ValueError("Choose a bounded grader version")
    by_id = {case[0]: case for case in CASES}
    selected = []
    primary = ModelRef(profile_id="measurement-definition", model="excluded-from-manifest")
    agents = {}
    for kind, identity in REFERENCE_CASES:
        if kind == "baseline":
            _, prompt, required = by_id[identity]
            files = baseline_files(identity)
            outputs = CASE_OUTPUTS.get(identity, {})
            writing = bool(outputs)
            agent = make_agent("george", primary)
            tools = exercise_tools(agent.tools, required, writing)
            descriptor = {
                "case_kind": kind,
                "case_id": identity,
                "prompt": prompt,
                "files_hex": _bytes_map(files),
                "outputs_hex": _bytes_map(outputs),
                "required_native_tool": required,
                "tools": tools,
                "max_steps": min(agent.max_steps, 8 if identity in COMPLEX_CASES else 5),
                "context_chars": min(agent.context_chars, 16000),
                "task_checks": {
                    "completion_feedback": True,
                    "write_targets": sorted(outputs) if identity != "noop" else [],
                    "require_readback": writing and identity != "noop",
                    "required_tools": ["read_file", "write_file"] if identity == "noop" else [],
                },
            }
            agents["george"] = agent
        else:
            case = next(case for case in ROLE_CASES if case.id == identity)
            agent = make_agent(case.role, primary)
            agents[case.role] = agent
            descriptor = {
                "case_kind": kind,
                "case_id": identity,
                "role": case.role,
                "prompt": contract_prompt(case),
                "strict_contract_clarified": True,
                "files_hex": _bytes_map(case.files),
                "outputs_hex": _bytes_map(case.outputs),
                "output_json": dict(case.output_json),
                "answer": case.answer,
                "required_reads": list(case.required_reads),
                "tools": list(agent.tools),
                "max_steps": 10,
                "context_chars": agent.context_chars,
                "task_checks": {
                    "completion_feedback": True,
                    "write_targets": sorted({*case.outputs, *case.output_json}),
                    "require_readback": True,
                    "require_tools": True,
                    "required_reads": list(case.required_reads),
                },
            }
        selected.append(descriptor)
    definitions = {}
    for role, agent in agents.items():
        definitions[role] = {
            key: value
            for key, value in agent.model_dump().items()
            if key not in ("id", "revision", "primary", "fallbacks")
        }
    manifest = {
        "measurement_version": MEASUREMENT_VERSION,
        "grader_version": grader_version,
        "runtime_policy_version": RUNTIME_POLICY_VERSION,
        "diagnostic_contract": {
            "hints": dict(HINTS),
            "max_mismatches": MAX_MISMATCHES,
            "max_pointer": MAX_POINTER,
        },
        "crew_version": CREW_VERSION,
        "cases": selected,
        "trials": [asdict(trial) for trial in measurement_plan()],
        "agent_definitions": definitions,
        "tool_schemas": {name: schema.model_json_schema() for name, schema in sorted(SCHEMAS.items())},
        "task_check_schema": TaskChecks.model_json_schema(),
        "sampling": {"temperature": 0.2, "seed": None, "deterministic_model_outputs": False},
        "policy": {
            "track": "measurement",
            "native_calls_only": True,
            "host_commands": False,
            "cloud_fallback": False,
            "fresh_workspace_each_attempt": True,
            "completion_feedback_limit": 1,
            "reasoning_control": "unchanged_no_toggle",
            "budget_ceilings": "clamp_to_profile_and_agent_limits",
            "comparison": "output_only isolates allowance; coordinated changes allowance_and_time",
            **(policy or {}),
        },
    }

    # Detach nested fixture/answer dictionaries from the global case definitions.
    return json.loads(json.dumps(manifest, ensure_ascii=True, allow_nan=False))


def _number(value):
    return min(value, 10**15) if type(value) is int and value >= 0 else None


def _usage(row, key):
    evidence = row.get("evidence", {})
    known = []
    for trace in evidence.get("request_traces", [])[:8]:
        value = _number(trace.get("usage", {}).get(key))
        if value is not None:
            known.append(value)
    value = _number(evidence.get("failure_usage", {}).get(key))
    if value is not None:
        known.append(value)
    return sum(known) if known else None


def _outcome(row):
    if row.get("code") in UNKNOWN_CODES or row.get("status") not in ("passed", "failed"):
        return None
    return row["status"] == "passed"


def summarize_trials(rows):
    """Repeated outcomes, not pass@k; unknown attempts never become model failures."""
    planned = measurement_plan()
    known_ids = {trial.id for trial in planned}
    selected = {}
    for row in rows:
        identity = row.get("id")
        if identity in known_ids:
            if identity in selected:
                raise ValueError("Duplicate measurement attempt identifier")
            selected[identity] = row
    grouped = {}
    for trial in planned:
        key = (trial.case_kind, trial.case_id, trial.arm)
        grouped.setdefault(key, []).append(trial)
    result = []
    for (kind, identity, arm), trials in grouped.items():
        records = [(trial, selected[trial.id]) for trial in trials if trial.id in selected]
        outcomes = [(trial.repeat, _outcome(row)) for trial, row in records]
        known = [(repeat, passed) for repeat, passed in outcomes if passed is not None]
        passed = sum(value for _, value in known)
        pairs = [(a, b) for a, b in zip(known, known[1:]) if b[0] == a[0] + 1]
        flips = sum(a[1] != b[1] for a, b in pairs)
        durations = [
            duration
            for _, row in records
            if row.get("evidence", {}).get("timing_unknown") is not True
            and (duration := _number(row.get("duration_ms"))) is not None
        ]
        usage = {key: [_usage(row, key) for _, row in records] for key in USAGE_KEYS}
        result.append(
            {
                "case_kind": kind,
                "case_id": identity,
                "arm": arm,
                "planned_repetitions": len(trials),
                "recorded_repetitions": len(records),
                "eligible_repetitions": len(known),
                "passed": passed,
                "failed": len(known) - passed,
                "interrupted_unknown": len(records) - len(known),
                "unrecorded": len(trials) - len(records),
                "success_rate": passed / len(known) if known else None,
                "mixed_outcomes": bool(passed and passed < len(known)) if len(known) >= 2 else None,
                "adjacent_known_pairs": len(pairs),
                "observed_flips": flips,
                "flip_rate": flips / len(pairs) if pairs else None,
                "pair_disagreement_rate": passed * (len(known) - passed) / comb(len(known), 2)
                if len(known) >= 2
                else None,
                "known_duration_ms": sum(durations) if durations else None,
                "duration_samples": len(durations),
                "known_usage": {
                    key: sum(value for value in values if value is not None)
                    if any(value is not None for value in values)
                    else None
                    for key, values in usage.items()
                },
                "usage_samples": {
                    key: sum(value is not None for value in values) for key, values in usage.items()
                },
            }
        )
    return {
        "measurement_version": MEASUREMENT_VERSION,
        "groups": result,
        "usage_basis": "Retained traces plus known rejected-response counters; not billing totals",
        "sampling_note": "Observed repetitions only; no deterministic model or pass@k estimate claimed",
    }


def paired_diff(previous, current):
    """Compare only identical benchmark and local configuration identities."""
    if previous.get("manifest_verified") is False or current.get("manifest_verified") is False:
        return {"comparable": False, "reason": "manifest_integrity_failed"}
    manifest = current.get("manifest_id")
    configuration = current.get("configuration_sha256", current.get("local_scope"))
    previous_configuration = previous.get("configuration_sha256", previous.get("local_scope"))
    if (
        not isinstance(manifest, str)
        or not re.fullmatch(r"[a-f0-9]{64}", manifest)
        or manifest != previous.get("manifest_id")
    ):
        return {"comparable": False, "reason": "manifest_mismatch_or_missing"}
    if (
        not isinstance(configuration, str)
        or not re.fullmatch(r"[a-f0-9]{64}", configuration)
        or configuration != previous_configuration
    ):
        return {"comparable": False, "reason": "configuration_mismatch_or_missing"}
    known_ids = {trial.id for trial in measurement_plan()}

    def index(report):
        rows = {}
        for row in report.get("checks", []):
            identity = row.get("id")
            if identity in known_ids:
                if identity in rows:
                    raise ValueError("Duplicate measurement attempt identifier")
                rows[identity] = row
        return rows

    before, after = index(previous), index(current)
    result = {
        "comparable": True,
        "newly_passing": [],
        "newly_failing": [],
        "still_passing": [],
        "still_failing": [],
        "unknown_or_missing": [],
        "paired_known_duration_delta_ms": 0,
        "paired_duration_samples": 0,
        "paired_known_usage_delta": {key: 0 for key in USAGE_KEYS},
        "paired_usage_samples": {key: 0 for key in USAGE_KEYS},
    }
    for identity in sorted(before.keys() | after.keys()):
        a, b = before.get(identity), after.get(identity)
        old, new = _outcome(a) if a else None, _outcome(b) if b else None
        if old is None or new is None:
            result["unknown_or_missing"].append(identity)
            continue
        key = (
            "still_passing"
            if old and new
            else "still_failing"
            if not old and not new
            else "newly_passing"
            if new
            else "newly_failing"
        )
        result[key].append(identity)
        da, db = _number(a.get("duration_ms")), _number(b.get("duration_ms"))
        if (
            da is not None
            and db is not None
            and a.get("evidence", {}).get("timing_unknown") is not True
            and b.get("evidence", {}).get("timing_unknown") is not True
        ):
            result["paired_known_duration_delta_ms"] += db - da
            result["paired_duration_samples"] += 1
        for key in USAGE_KEYS:
            ua, ub = _usage(a, key), _usage(b, key)
            if ua is not None and ub is not None:
                result["paired_known_usage_delta"][key] += ub - ua
                result["paired_usage_samples"][key] += 1
    return result
