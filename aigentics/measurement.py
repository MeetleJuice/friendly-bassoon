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

MEASUREMENT_VERSION = "crew-measurement-5"
ARCHIVED_MANIFESTS = {
    "crew-measurement-1": "0dcfdb6158c959aa7ac6c6591b862031f7edb75813bccf9aafb3184431b9261d",
    "crew-measurement-2": "e5efea395071aff13862f9d943e5a9909b1e0a537e0727a2bc51e08bc51a847e",
    "crew-measurement-3": "2e90f43b81731250ffe9d77c4a17256ebdcb45bafa6d2109c9f33f1ba8749142",
    "crew-measurement-4": "158ad54343cc8565ca22544d71487a636281c2824c0a6efe8d322dc57e15068e",
}
GRADER_VERSION = "strict-contract-5"
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
EXPANDED_CASES = (("role", "scout_comment"), ("role", "sentinel_shifted"), ("role", "sentinel_clean"))

UNKNOWN_CODES = frozenset(
    (
        "INTERRUPTED_CASE_NOT_REPLAYED",
        "CANCELLED",
        "CAMPAIGN_BUDGET_EXHAUSTED",
        "TOOL_DISABLED",
        "THINKING_CONTROL_UNAVAILABLE",
        "THINKING_NOT_APPLICABLE",
        "THINKING_ROUTE_UNSUPPORTED",
    )
)
USAGE_KEYS = ("prompt_eval_count", "eval_count")


@dataclass(frozen=True)
class Trial:
    id: str
    case_kind: Literal["baseline", "role", "workflow"]
    case_id: str
    arm: Literal["reference", "output_only", "coordinated", "thinking_off", "direct", "managed"]
    repeat: int
    max_output_tokens: int
    request_timeout_seconds: int
    session_budget_seconds: int

    @property
    def thinking_mode(self):
        return "off" if self.arm == "thinking_off" or self.case_kind == "workflow" else "default"

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


def measurement_plan(version=MEASUREMENT_VERSION):
    """34 fresh attempts covering all six locals and two budget-sensitive cases.

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
                ("reference", "output_only", "coordinated", "thinking_off")
                if repeat == 1
                else ("thinking_off", "coordinated", "output_only", "reference")
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
                            120 if arm in ("coordinated", "thinking_off") else 85,
                            180 if arm in ("coordinated", "thinking_off") else 90,
                        )
                    )
    if version == "crew-measurement-1":
        return tuple(t for t in trials if t.arm != "thinking_off")
    if version == "crew-measurement-2":
        return tuple(trials)
    if version not in (MEASUREMENT_VERSION, "crew-measurement-3", "crew-measurement-4"):
        raise ValueError("Unknown measurement version")
    # Short paired calibration first: Scout and Vera expose the recent failure modes.
    # Preserve all 34 retained comparisons; add 18 per-role off trials and 4 team trials.
    for repeat in range(1, 4):
        for _, identity in (item for item in REFERENCE_CASES if item[0] == "role"):
            trials.append(
                Trial(
                    f"measure-{identity}-thinking_off-r{repeat}",
                    "role",
                    identity,
                    "thinking_off",
                    repeat,
                    4096,
                    120,
                    180,
                )
            )
    for repeat in (1, 2):
        for arm in ("direct", "managed") if repeat == 1 else ("managed", "direct"):
            trials.append(
                Trial(
                    f"measure-team_build-{arm}-r{repeat}",
                    "workflow",
                    "ada_repair",
                    arm,
                    repeat,
                    4096,
                    120,
                    180,
                )
            )
    if version == MEASUREMENT_VERSION:
        for kind, identity in EXPANDED_CASES:
            for arm in ("thinking_off", "reference"):
                trials.append(Trial(f"measure-{identity}-{arm}-r1", kind, identity, arm, 1, 4096, 120, 180))
        for repeat in (1, 2):
            trials.append(
                Trial(
                    f"measure-team_review-managed-r{repeat}",
                    "workflow",
                    "ada_review",
                    "managed",
                    repeat,
                    4096,
                    120,
                    180,
                )
            )
    priority = {"scout_symbol": 0, "vera_exclusive": 1}
    calibration = sorted(
        (t for t in trials if t.case_id in priority and t.repeat == 1),
        key=lambda t: (priority[t.case_id], t.arm != "thinking_off"),
    )
    trials = calibration + [t for t in trials if t not in calibration]
    return tuple(trials)


def focused_plan(version=MEASUREMENT_VERSION):
    """Declared focused subset; archived4 keeps24, current5 adds8 targeted probes."""
    if version not in ("crew-measurement-4", MEASUREMENT_VERSION):
        raise ValueError("Focused mode was introduced with measurement4")
    full = measurement_plan(version)

    def select(trial):
        return (
            trial.case_id == "vera_exclusive"
            or trial.case_kind == "workflow"
            or trial.case_id in ("scout_symbol", "sentinel_bug")
            and trial.repeat <= 2
            or trial.case_id == "unicode"
            and trial.arm in ("coordinated", "thinking_off")
            or trial.case_id == "noop"
            and trial.arm == "thinking_off"
            or trial.case_id in {identity for _, identity in EXPANDED_CASES}
        )

    selected = [trial for trial in full if select(trial)]
    return tuple(
        sorted(
            selected,
            key=lambda t: 0 if t.case_kind == "workflow" else 1 if t.case_id == "vera_exclusive" else 2,
        )
    )


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
    from .contracts import HINTS, MAX_MISMATCHES, MAX_POINTER, PARSE_REASONS, contract_prompt
    from .crew_cases import MEASUREMENT_CASES as ROLE_CASES
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
    for kind, identity in (*REFERENCE_CASES, *EXPANDED_CASES, ("workflow", "ada_review")):
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
                    "unchanged_targets": ["output.txt"] if identity == "noop" else [],
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
                "required_tools": list(case.required_tools),
                "tools": list(agent.tools),
                "max_steps": 12 if kind == "workflow" else 10,
                "context_chars": agent.context_chars,
                "task_checks": {
                    "json_outputs": {
                        name: "object" if isinstance(value, dict) else "array"
                        for name, value in case.output_json.items()
                    },
                    "completion_feedback": True,
                    "write_targets": sorted({*case.outputs, *case.output_json}),
                    "require_readback": True,
                    "require_tools": True,
                    "required_reads": list(case.required_reads),
                    "required_tools": list(case.required_tools),
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
    coordinator = make_agent("orion", primary)
    definitions["orion"] = {
        k: v
        for k, v in coordinator.model_dump().items()
        if k not in ("id", "revision", "primary", "fallbacks")
    }
    from .coordination import PILOT_VERSION, MAX_CALLS, MAX_OUTPUT_RESERVATION, TOOLS as TEAM_TOOLS
    from .json_proposals import PROPOSAL_POLICY_VERSION, JSON_TYPES, MAX_JSON_DEPTH, MAX_JSON_NODES

    manifest = {
        "measurement_version": MEASUREMENT_VERSION,
        "grader_version": grader_version,
        "runtime_policy_version": RUNTIME_POLICY_VERSION,
        "diagnostic_contract": {
            "hints": dict(HINTS),
            "max_mismatches": MAX_MISMATCHES,
            "max_pointer": MAX_POINTER,
            "parse_reasons": sorted(PARSE_REASONS),
        },
        "crew_version": CREW_VERSION,
        "cases": selected,
        "trials": [{**asdict(trial), "thinking_mode": trial.thinking_mode} for trial in measurement_plan()],
        "recommended_trial_ids": [trial.id for trial in focused_plan()],
        "agent_definitions": definitions,
        "tool_schemas": {name: schema.model_json_schema() for name, schema in sorted(SCHEMAS.items())},
        "task_check_schema": TaskChecks.model_json_schema(),
        "sampling": {"temperature": 0.2, "seed": None, "deterministic_model_outputs": False},
        "proposal_policy": {
            "version": PROPOSAL_POLICY_VERSION,
            "root_types": sorted(JSON_TYPES),
            "max_depth": MAX_JSON_DEPTH,
            "max_nodes": MAX_JSON_NODES,
            "recovery": "only_declared_json_outputs_no_effect_error_then_permitted_verified_write_and_current_readback",
            "historical_errors": "retained",
            "semantic_values": "independent_strict_checker_unchanged",
        },
        "team_pilot": {
            "version": PILOT_VERSION,
            "tools": TEAM_TOOLS,
            "max_dispatches": 2,
            "format_feedback_limit": 1,
            "handoff_binding": "current_run_stage_and_snapshot_rechecked_before_dispatch",
            "max_declared_paths": 16,
            "max_total_calls": MAX_CALLS,
            "max_total_output_reservation": MAX_OUTPUT_RESERVATION,
            "task_case": "ada_repair",
            "required_review_case": "ada_review",
            "thinking": "off_if_eligible_else_skip",
            "review": "advisory_and_read_only",
            "authority": "application_owned_checks",
            "serial": True,
        },
        "policy": {
            "track": "measurement",
            "native_calls_only": True,
            "host_commands": False,
            "cloud_fallback": False,
            "fresh_workspace_each_attempt": True,
            "completion_feedback_limit": 1,
            "reasoning_control": "native_boolean_off_only_when_api_show_explicitly_advertises_support_and_active_default",
            "reference_thinking": "model_default_omitted_request_field",
            "temperature": 0.2,
            "context_policy": "no_num_ctx_override",
            "server_environment": "unchanged",
            "unchanged_workflow": "read_identical_write_read_exactly_once_no_actual_write",
            "budget_ceilings": "clamp_to_profile_and_agent_limits",
            "comparison": "output_only isolates allowance; coordinated changes allowance_and_time",
            "interrupted_runtime": "unknown_not_model_failure",
            **(policy or {}),
        },
    }

    # Detach nested fixture/answer dictionaries from the global case definitions.
    return json.loads(json.dumps(manifest, ensure_ascii=True, allow_nan=False))


def _number(value):
    return min(value, 10**15) if type(value) is int and value >= 0 else None


def _usage(row, key, version=MEASUREMENT_VERSION):
    evidence = row.get("evidence", {})
    if version == MEASUREMENT_VERSION and isinstance(evidence.get("actor_statistics"), list):
        sample_key = "prompt_samples" if key == "prompt_eval_count" else "eval_samples"
        known = [
            _number(actor.get(key))
            for actor in evidence["actor_statistics"]
            if _number(actor.get(sample_key)) not in (None, 0)
        ]
        known = [value for value in known if value is not None]
        if known:
            rejected = _number(evidence.get("failure_usage", {}).get(key))
            return sum(known) + (rejected or 0)
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
    if (
        row.get("code") in UNKNOWN_CODES
        or row.get("evidence", {}).get("runtime_state") == "cancelled"
        or row.get("status") not in ("passed", "failed")
    ):
        return None
    return row["status"] == "passed"


def summarize_trials(rows, *, version=MEASUREMENT_VERSION, mode="measurement"):
    """Repeated outcomes, not pass@k; unknown attempts never become model failures."""
    planned = focused_plan(version) if mode == "focused" else measurement_plan(version)
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
        usage = {key: [_usage(row, key, version) for _, row in records] for key in USAGE_KEYS}
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
    summary = {
        "measurement_version": version,
        "groups": result,
        "usage_basis": "All-recorded actor known counters when available, otherwise retained traces plus rejected-response counters; not billing totals"
        if version == MEASUREMENT_VERSION
        else "Retained traces plus known rejected-response counters; not billing totals",
        "sampling_note": "Observed repetitions only; no deterministic model or pass@k estimate claimed",
    }
    if version in (MEASUREMENT_VERSION, "crew-measurement-4", "crew-measurement-3", "crew-measurement-2"):
        pairs = thinking_pairs(rows, version=version)
        if mode == "focused":
            planned_ids = {trial.id for trial in planned}
            pairs = [
                p
                for p in pairs
                if f"measure-{p['case_id']}-{p['reference_arm']}-r{p['repeat']}" in planned_ids
                and f"measure-{p['case_id']}-thinking_off-r{p['repeat']}" in planned_ids
            ]
            summary["plan_scope"] = "focused"
        summary["thinking_pairs"] = pairs
    return summary


def thinking_pairs(rows, *, version=MEASUREMENT_VERSION):
    """Matched settings, not a causal or hidden-compute guarantee."""
    from .ollama_settings import public_thinking, thinking_experiment_available

    index = {row.get("id"): row for row in rows}
    results = []
    cases = ("unicode", "noop") + (
        tuple(identity for kind, identity in REFERENCE_CASES if kind == "role")
        if version in (MEASUREMENT_VERSION, "crew-measurement-4", "crew-measurement-3")
        else ()
    )
    if version == MEASUREMENT_VERSION:
        cases += tuple(identity for _, identity in EXPANDED_CASES)
    for case in cases:
        reference_arm = "coordinated" if case in ("unicode", "noop") else "reference"
        repeats = (
            (1,)
            if case in {identity for _, identity in EXPANDED_CASES}
            else (1, 2)
            if case in ("unicode", "noop")
            else (1, 2, 3)
        )
        for repeat in repeats:
            left = index.get(f"measure-{case}-{reference_arm}-r{repeat}", {})
            right = index.get(f"measure-{case}-thinking_off-r{repeat}", {})
            a, b = left.get("evidence", {}), right.get("evidence", {})
            first, second = _outcome(left), _outcome(right)
            controls = public_thinking(a.get("model_metadata", {}))
            matched = bool(
                controls
                and controls == public_thinking(b.get("model_metadata", {}))
                and thinking_experiment_available(controls)
            )
            budgets_match = all(
                type(a.get(k)) is int and a[k] == b.get(k)
                for k in ("max_output_tokens", "request_timeout_seconds", "session_budget_seconds")
            )
            eligible = (
                first is not None
                and second is not None
                and matched
                and budgets_match
                and a.get("thinking_mode") == "default"
                and b.get("thinking_mode") == "off"
            )
            delta = None
            if (
                eligible
                and first
                and second
                and a.get("timing_unknown") is not True
                and b.get("timing_unknown") is not True
            ):
                da, db = _number(left.get("duration_ms")), _number(right.get("duration_ms"))
                if da is not None and db is not None:
                    delta = db - da
            results.append(
                {
                    "case_id": case,
                    "repeat": repeat,
                    "reference_arm": reference_arm,
                    "treatment_arm": "thinking_off",
                    "eligible": eligible,
                    "reference_passed": first,
                    "off_passed": second,
                    "both_passed_duration_delta_ms": delta,
                    "note": "Matched observed settings; no seed control or hidden-compute guarantee"
                    if eligible
                    else "Missing, skipped or mismatched controls/budgets",
                }
            )
    return results


def paired_diff(previous, current):
    """Compare only identical benchmark and local configuration identities."""
    if previous.get("manifest_verified") is False or current.get("manifest_verified") is False:
        return {"comparable": False, "reason": "manifest_integrity_failed"}
    for key in ("thinking_comparison", "ollama_observation"):
        before, after = previous.get(key), current.get(key)
        if key == "ollama_observation":
            before = (
                {k: v for k, v in (before or {}).items() if k not in ("observer_duration_ms",)}
                if isinstance(before, dict)
                else before
            )
            after = (
                {k: v for k, v in (after or {}).items() if k not in ("observer_duration_ms",)}
                if isinstance(after, dict)
                else after
            )
        if before != after:
            return {"comparable": False, "reason": "observed_settings_mismatch"}
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
