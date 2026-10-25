"""Definition drift, missing trials and outcome flips must remain visible."""

from collections import Counter
from copy import deepcopy
from dataclasses import FrozenInstanceError
import pytest

from aigentics.measurement import (
    MEASUREMENT_VERSION,
    manifest_id,
    measurement_manifest,
    measurement_plan,
    paired_diff,
    summarize_trials,
)


def trial(case="george_workflow", arm="reference", repeat=1):
    return next(t for t in measurement_plan() if (t.case_id, t.arm, t.repeat) == (case, arm, repeat))


def row(case="george_workflow", arm="reference", repeat=1, status="passed", code="OK", **evidence):
    return {
        "id": trial(case, arm, repeat).id,
        "status": status,
        "code": code,
        "duration_ms": 20,
        "evidence": evidence,
    }


def group(summary, case="george_workflow", arm="reference"):
    return next(g for g in summary["groups"] if (g["case_id"], g["arm"]) == (case, arm))


def report(rows, **changes):
    return {"manifest_id": "a" * 64, "configuration_sha256": "b" * 64, "checks": rows, **changes}


def test_plan_has_64_fresh_unique_attempts_covering_all_six_locals():
    plan = measurement_plan()
    assert len(plan) == len({t.id for t in plan}) == 64
    counts = Counter((t.case_kind, t.case_id, t.arm) for t in plan)
    assert len(counts) == 29
    assert all(
        count
        == (
            1
            if identity in ("scout_comment", "sentinel_shifted", "sentinel_clean")
            else 3
            if kind == "role"
            else 2
        )
        for (kind, identity, _), count in counts.items()
    )
    assert sum(t.case_kind == "role" for t in plan) == 42
    assert sum(t.case_kind == "baseline" for t in plan) == 16
    assert all(t.max_output_tokens in (1024, 4096) for t in plan)
    assert all(t.request_timeout_seconds <= t.session_budget_seconds <= 180 for t in plan)
    assert plan == measurement_plan()
    with pytest.raises(FrozenInstanceError):
        plan[0].repeat = 99


def test_budget_arms_separate_output_only_from_coordinated_policy():
    reference, output, coordinated = (
        trial(case="unicode", arm=a) for a in ("reference", "output_only", "coordinated")
    )
    assert reference.budget == {
        "max_output_tokens": 1024,
        "request_timeout_seconds": 85,
        "session_budget_seconds": 90,
    }
    assert output.budget == {**reference.budget, "max_output_tokens": 4096}
    assert coordinated.budget == {
        "max_output_tokens": 4096,
        "request_timeout_seconds": 120,
        "session_budget_seconds": 180,
    }
    assert coordinated.effective_budget(profile_seconds=40, agent_seconds=30) == {
        "max_output_tokens": 4096,
        "request_timeout_seconds": 30,
        "session_budget_seconds": 30,
    }
    with pytest.raises(ValueError):
        coordinated.effective_budget(profile_seconds=True)
    with pytest.raises(ValueError):
        coordinated.effective_budget(agent_seconds=0)


def test_manifest_is_stable_complete_and_excludes_connection_identity():
    manifest = measurement_manifest()
    assert manifest_id(manifest) == manifest_id(measurement_manifest())
    assert len(manifest_id(manifest)) == 64
    assert manifest["measurement_version"] == MEASUREMENT_VERSION
    assert len(manifest["trials"]) == 64 and len(manifest["cases"]) == 12
    assert set(manifest["agent_definitions"]) == {
        "george",
        "orion",
        "scout",
        "ada",
        "vera",
        "sentinel",
        "atlas",
    }
    assert all(
        "primary" not in agent and "fallbacks" not in agent
        for agent in manifest["agent_definitions"].values()
    )
    assert manifest["sampling"]["deterministic_model_outputs"] is False
    assert manifest["sampling"]["seed"] is None
    assert "explicitly_advertises_support" in manifest["policy"]["reasoning_control"]
    assert manifest["policy"]["context_policy"] == "no_num_ctx_override"
    unicode_case = next(c for c in manifest["cases"] if c["case_id"] == "unicode")
    assert bytes.fromhex(unicode_case["outputs_hex"]["unicode.txt"]) == "café 🌊\n".encode()
    assert manifest["tool_schemas"]["project_map"]["additionalProperties"] is False
    assert "completion_feedback" in manifest["task_check_schema"]["properties"]


@pytest.mark.parametrize(
    "field", ["prompt", "fixture", "contract", "schema", "instructions", "budget", "grader", "policy"]
)
def test_manifest_changes_when_any_measured_condition_changes(field):
    original = measurement_manifest()
    changed = deepcopy(original)
    if field == "prompt":
        changed["cases"][0]["prompt"] += " Different instruction."
    elif field == "fixture":
        name = next(iter(changed["cases"][0]["files_hex"]))
        changed["cases"][0]["files_hex"][name] = b"different\n".hex()
    elif field == "contract":
        name = next(iter(changed["cases"][0]["outputs_hex"]))
        changed["cases"][0]["outputs_hex"][name] = b"different\n".hex()
    elif field == "schema":
        changed["tool_schemas"]["project_map"]["additionalProperties"] = True
    elif field == "instructions":
        changed["agent_definitions"]["george"]["instructions"] += " New behavior."
    elif field == "budget":
        changed["trials"][0]["max_output_tokens"] = 8192
    elif field == "grader":
        changed["grader_version"] = "other-grader"
    else:
        changed["policy"]["completion_feedback_limit"] = 2
    assert manifest_id(changed) != manifest_id(original)


def test_manifest_mapping_order_is_irrelevant_but_trial_order_matters():
    value = measurement_manifest()
    assert manifest_id(value) == manifest_id(dict(reversed(list(value.items()))))
    changed = deepcopy(value)
    changed["trials"] = list(reversed(changed["trials"]))
    assert manifest_id(value) != manifest_id(changed)


def test_empty_run_reports_unrecorded_coverage_without_fake_zeros():
    summary = summarize_trials([])
    assert len(summary["groups"]) == 29
    for g in summary["groups"]:
        assert g["recorded_repetitions"] == g["eligible_repetitions"] == 0
        assert g["unrecorded"] == g["planned_repetitions"]
        assert g["success_rate"] is None and g["flip_rate"] is None
        assert g["known_duration_ms"] is None
        assert g["known_usage"] == {"prompt_eval_count": None, "eval_count": None}


def test_unknown_interrupted_attempt_is_not_failure_or_zero_time():
    rows = [
        row(repeat=1),
        row(repeat=2, status="failed", code="INTERRUPTED_CASE_NOT_REPLAYED", timing_unknown=True),
    ]
    rows[1]["duration_ms"] = 0
    g = group(summarize_trials(rows))
    assert g["passed"] == g["eligible_repetitions"] == 1
    assert g["failed"] == 0 and g["interrupted_unknown"] == 1 and g["unrecorded"] == 1
    assert g["success_rate"] == 1 and g["mixed_outcomes"] is None
    assert g["known_duration_ms"] == 20 and g["duration_samples"] == 1


def test_repeated_flip_and_pair_disagreement_are_observed_not_pass_at_k():
    rows = [row(repeat=1), row(repeat=2, status="failed", code="MODEL_OR_RUNTIME_FAILED"), row(repeat=3)]
    g = group(summarize_trials(rows))
    assert g["passed"] == 2 and g["failed"] == 1
    assert g["success_rate"] == pytest.approx(2 / 3)
    assert g["mixed_outcomes"] is True
    assert g["adjacent_known_pairs"] == g["observed_flips"] == 2 and g["flip_rate"] == 1
    assert g["pair_disagreement_rate"] == pytest.approx(2 / 3)
    assert "pass@" not in str(g)


def test_unknown_gap_does_not_create_a_consecutive_flip():
    g = group(summarize_trials([row(repeat=1), row(repeat=3, status="failed")]))
    assert g["mixed_outcomes"] is True
    assert g["adjacent_known_pairs"] == g["observed_flips"] == 0 and g["flip_rate"] is None
    assert g["pair_disagreement_rate"] == 1


def test_metrics_retain_known_rejected_usage_without_treating_unknown_as_zero():
    rows = [
        row(
            request_traces=[{"usage": {"prompt_eval_count": 12, "eval_count": 5}}],
            failure_usage={"prompt_eval_count": 13, "eval_count": 1024},
        ),
        row(repeat=2),
    ]
    g = group(summarize_trials(rows))
    assert g["known_usage"] == {"prompt_eval_count": 25, "eval_count": 1029}
    assert g["usage_samples"] == {"prompt_eval_count": 1, "eval_count": 1}
    assert "not billing totals" in summarize_trials(rows)["usage_basis"]


def test_unknown_ids_ignored_and_duplicate_attempts_rejected():
    assert group(summarize_trials([{"id": "not-a-trial", "status": "passed"}]))["recorded_repetitions"] == 0
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_trials([row(), row()])


@pytest.mark.parametrize(
    "changed,reason",
    [
        ({"manifest_id": "c" * 64}, "manifest_mismatch_or_missing"),
        ({"manifest_id": None}, "manifest_mismatch_or_missing"),
        ({"manifest_id": "z" * 64}, "manifest_mismatch_or_missing"),
        ({"configuration_sha256": "c" * 64}, "configuration_mismatch_or_missing"),
        ({"configuration_sha256": None}, "configuration_mismatch_or_missing"),
    ],
)
def test_paired_diff_refuses_different_or_missing_conditions(changed, reason):
    assert paired_diff(report([row()]), report([row()], **changed)) == {"comparable": False, "reason": reason}


def test_paired_diff_uses_shared_known_outcomes_and_paired_measurements_only():
    before_rows = [
        row(repeat=1, status="failed", request_traces=[{"usage": {"eval_count": 10}}]),
        row(repeat=2),
        row(repeat=3),
    ]
    after_rows = [
        row(repeat=1, request_traces=[{"usage": {"eval_count": 15}}]),
        row(repeat=2, status="failed"),
        row(repeat=3, status="failed", code="INTERRUPTED_CASE_NOT_REPLAYED", timing_unknown=True),
    ]
    after_rows[0]["duration_ms"] = 30
    result = paired_diff(report(before_rows), report(after_rows))
    assert result["comparable"] is True
    assert result["newly_passing"] == [trial(repeat=1).id]
    assert result["newly_failing"] == [trial(repeat=2).id]
    assert result["unknown_or_missing"] == [trial(repeat=3).id]
    assert result["paired_known_duration_delta_ms"] == 10
    assert result["paired_duration_samples"] == 2
    assert result["paired_known_usage_delta"]["eval_count"] == 5
    assert result["paired_usage_samples"]["eval_count"] == 1
    assert result["paired_usage_samples"]["prompt_eval_count"] == 0


def test_paired_diff_rejects_duplicate_rows():
    with pytest.raises(ValueError, match="Duplicate"):
        paired_diff(report([row(), row()]), report([row()]))


def test_manifest_reads_current_prompt_and_schema_sources(monkeypatch):
    from aigentics import test_suite

    before = manifest_id(measurement_manifest())
    monkeypatch.setattr(
        test_suite,
        "CASES",
        tuple(
            (identity, prompt + " Changed instruction.", tool)
            if identity == "unicode"
            else (identity, prompt, tool)
            for identity, prompt, tool in test_suite.CASES
        ),
    )
    assert manifest_id(measurement_manifest()) != before


def test_manifest_covers_actual_diagnostic_hints_and_clarified_role_prompt(monkeypatch):
    from aigentics import contracts
    from aigentics.crew_cases import CASES

    manifest = measurement_manifest()
    role = next(c for c in manifest["cases"] if c["case_kind"] == "role")
    original = next(c for c in CASES if c.id == role["case_id"])
    assert role["prompt"] == contracts.contract_prompt(original)
    assert role["strict_contract_clarified"] is True
    before = manifest_id(manifest)
    monkeypatch.setattr(contracts, "HINTS", {**contracts.HINTS, "JSON_VALUE": "New correction guidance"})
    assert manifest_id(measurement_manifest()) != before
    assert manifest_id(manifest) == before


def test_manifest_nested_expected_values_are_detached_from_case_catalog():
    from aigentics.crew_cases import CASES

    manifest = measurement_manifest()
    role = next(c for c in manifest["cases"] if c["case_id"] == "vera_exclusive")
    expected = next(c for c in CASES if c.id == role["case_id"]).output_json["cases.json"]
    role["output_json"]["cases.json"]["cases"][0]["expected"] = "changed in caller snapshot"
    assert expected["cases"][0]["expected"] != "changed in caller snapshot"


def test_manifest_uses_shared_baseline_fixtures_and_runtime_policy(monkeypatch):
    from aigentics import runtime, test_suite

    original = measurement_manifest()
    before = manifest_id(original)
    fixtures = test_suite.baseline_files
    monkeypatch.setattr(
        test_suite,
        "baseline_files",
        lambda identity: {**fixtures(identity), "added.txt": b"fixture change\n"},
    )
    changed = measurement_manifest()
    assert manifest_id(changed) != before
    assert all("added.txt" in c["files_hex"] for c in changed["cases"] if c["case_kind"] == "baseline")
    monkeypatch.setattr(test_suite, "baseline_files", fixtures)
    monkeypatch.setattr(runtime, "RUNTIME_POLICY_VERSION", "other-runtime-policy")
    assert manifest_id(measurement_manifest()) != before
    assert original["runtime_policy_version"] != "other-runtime-policy"
