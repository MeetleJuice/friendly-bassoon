"""Public campaign evidence stays complete, bounded and free of generated text."""

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from aigentics.campaign import PLAN_IDS as CURRENT_PLAN_IDS, REQUIREMENT_LABELS

from aigentics.evidence import base_report
from aigentics.reporting import issue_body, prepare_browser_draft, public_report

PLAN_IDS = CURRENT_PLAN_IDS[:42]


def campaign_report():
    report = base_report("crew_campaign", "crew-campaign-1", "Counters only")
    report.update(state="needs_attention", planned_cases=len(PLAN_IDS))
    report["checks"] = [
        {
            "id": identity,
            "status": "failed",
            "code": "REQUIRED_OPERATIONS_NOT_VERIFIED",
            "message": "PRIVATE generated answer and source",
            "duration_ms": 179999,
            "evidence": {
                "role": "george" if identity.startswith(("baseline-", "repeat-")) else identity.split("-")[0],
                "attempt": 2 if identity.startswith("repeat-") else 1,
                "runtime_state": "needs_review",
                "native_calls_total": 10,
                "file_matches": True,
                "max_output_tokens": 4096,
                "request_timeout_seconds": 120,
                "session_budget_seconds": 180,
                "provider_error_code": "OUTPUT_LIMIT",
                "execution_counts": {"writes_verified": 2, "failed": 2},
                "task_checks": {"status": "needs_attention", "missing_readbacks": 1},
                "requirement_checks": {**{key: False for key in REQUIREMENT_LABELS}, "PRIVATE": False},
                "failure_usage": {"prompt_eval_count": 1000, "eval_count": 4096},
                "request_traces": [{"usage": {"prompt_eval_count": 2000, "eval_count": 4096}}] * 8,
                "source": "PRIVATE",
                "final_answer": "PRIVATE",
                "path": "PRIVATE",
                "model": "PRIVATE",
            },
        }
        for identity in PLAN_IDS
    ]
    return report


def test_full_campaign_browser_contains_every_row_and_no_source(credentials):
    report = campaign_report()
    title, body = issue_body(report, credentials)
    url = prepare_browser_draft(title, body)
    assert len(url) <= 7500
    shared = parse_qs(urlsplit(url).query)["body"][0]
    assert all(f"{identity}|" in shared for identity in PLAN_IDS)
    assert f"Recorded/planned: {len(PLAN_IDS)}/{len(PLAN_IDS)}" in shared
    assert "PRIVATE" not in shared
    assert "POST_WRITE_READBACK" in shared
    assert "OUTPUT_LIMIT" in shared
    assert "4096/120/180" in shared
    assert shared.count("|F|") == len(PLAN_IDS)


def test_public_campaign_filters_unknown_case_codes_and_generated_text():
    report = campaign_report()
    row = report["checks"][0]
    row["code"] = "PRIVATE"
    row["evidence"].update(
        role="PRIVATE", attempt="PRIVATE", runtime_state="PRIVATE", provider_error_code="PRIVATE"
    )
    report["checks"].append({**row, "id": "PRIVATE"})
    safe = public_report(report)
    assert len(safe["checks"]) == len(PLAN_IDS)
    assert safe["checks"][0]["code"] == "UNKNOWN"
    assert "PRIVATE" not in json.dumps(safe)


@pytest.mark.parametrize("state", ("cancelled", "interrupted", "needs_attention"))
def test_partial_campaign_keeps_planned_denominator(credentials, state):
    report = campaign_report()
    report["state"] = state
    report["checks"] = report["checks"][:2]
    _, body = issue_body(report, credentials)
    assert f"Recorded/planned: 2/{len(PLAN_IDS)}" in body
    assert state in body


def test_baseline_report_retains_exact_missing_task_requirements(credentials):
    report = base_report("agent_suite", "agent-suite-4", "Counters")
    report["checks"] = [
        {
            "id": "edit",
            "status": "failed",
            "code": "REQUIRED_OPERATIONS_NOT_VERIFIED",
            "message": "Criteria",
            "duration_ms": 1000,
            "evidence": {
                "task_checks": {
                    "status": "needs_attention",
                    "missing_writes": 0,
                    "missing_readbacks": 1,
                    "missing_tools": 0,
                    "revision_mismatches": 0,
                },
                "requirement_checks": {"POST_WRITE_READBACK": False, "PRIVATE": False},
            },
        }
    ]
    from aigentics.reporting import compact_suite_body

    body = compact_suite_body(public_report(report))
    assert "0/1/0/0" in body and "POST_WRITE_READBACK" in body
    assert "PRIVATE" not in body


def test_campaign_header_uses_only_fixed_mode_and_crew_version(credentials):
    from aigentics.crew import CREW_VERSION

    report = campaign_report()
    report.update(mode="deep", crew_version=CREW_VERSION)
    _, body = issue_body(report, credentials)
    assert f"Crew/mode: {CREW_VERSION}/deep" in body
    report.update(mode="PRIVATE", crew_version="PRIVATE")
    _, body = issue_body(report, credentials)
    assert "PRIVATE" not in body and "Crew/mode: ?/?" in body


def test_campaign_optional_model_name_uses_credential_redaction(credentials):
    report = campaign_report()
    report["checks"] = report["checks"][:1]
    credentials._values["TEST_TOKEN"] = "synthetic-token-for-redaction"
    e = report["checks"][0]["evidence"]
    e["model"] = "model-synthetic-token-for-redaction"
    e["model_metadata"] = {"template_sha256": "a" * 64, "parser": "PRIVATE"}
    _, hidden = issue_body(report, credentials)
    assert "model-synthetic" not in hidden
    assert "a" * 64 in hidden
    _, included = issue_body(report, credentials, include_model=True)
    assert "synthetic-token-for-redaction" not in included
    assert "[REDACTED]" in included
    assert "PRIVATE" not in included


def test_campaign_preserves_unknown_usage_and_adds_only_known_rejected_usage(credentials):
    report = campaign_report()
    report["checks"] = report["checks"][:2]
    report["checks"][0]["evidence"].update(request_traces=[], failure_usage={})
    report["checks"][1]["evidence"].update(
        request_traces=[{"usage": {"prompt_eval_count": 3, "eval_count": 5}}],
        failure_usage={"prompt_eval_count": 7, "eval_count": 11},
    )
    _, body = issue_body(report, credentials)
    assert "|?/?|" in body and "|10/16|" in body


def test_campaign_hex_mask_preserves_every_failed_requirement(credentials):
    report = campaign_report()
    report["checks"] = report["checks"][:1]
    e = report["checks"][0]["evidence"]
    e["requirement_checks"] = {"POST_WRITE_READBACK": False, "EXACT_OUTPUT": False, "TASK_VERIFIED": True}
    _, body = issue_body(report, credentials)
    row = next(line for line in body.splitlines() if line.startswith(report["checks"][0]["id"] + "|"))
    assert row.split("|")[-1] == "3"
    assert "0=EXACT_OUTPUT" in body and "1=POST_WRITE_READBACK" in body
    assert "TASK_VERIFIED" not in body


def test_quick_campaign_zero_planned_is_not_unknown(credentials):
    report = campaign_report()
    report.update(planned_cases=0, checks=[], mode="quick", state="passed")
    _, body = issue_body(report, credentials)
    assert "Recorded/planned: 0/0" in body


def test_health_browser_retains_packaged_crew_fixture_without_source(credentials):
    report = base_report("diagnostics", "7", "Synthetic fixtures only")
    report.update(state="passed")
    report["checks"] = [
        {
            "id": "crew_evaluation_fixture",
            "status": "passed",
            "code": "OK",
            "message": "Synthetic fixture",
            "duration_ms": 1,
            "evidence": {"crew_fixture_verified": True, "external_requests": 0, "source": "PRIVATE"},
        }
    ]
    # Force the same compact path used by the complete diagnostic report.
    report["privacy"] = "Synthetic fixture metadata. " * 500
    safe = public_report(report)
    assert safe["checks"][0]["evidence"] == {"crew_fixture_verified": True, "external_requests": 0}
    title, body = issue_body(report, credentials)
    shared = parse_qs(urlsplit(prepare_browser_draft(title, body)).query)["body"][0]
    assert "crew_fixture_verified" in shared and "PRIVATE" not in shared


def test_interrupted_campaign_distinguishes_unknown_time_from_budget_charge(credentials):
    report = campaign_report()
    report.update(stop_reason="campaign_budget", budget_used_ms=7_300_000)
    report["checks"] = report["checks"][:1]
    row = report["checks"][0]
    row.update(code="INTERRUPTED_CASE_NOT_REPLAYED", duration_ms=0)
    row["evidence"]["timing_unknown"] = True
    safe = public_report(report)
    assert safe["budget_used_ms"] == 7_300_000
    assert safe["checks"][0]["evidence"]["timing_unknown"] is True
    _, body = issue_body(report, credentials)
    line = next(line for line in body.splitlines() if line.startswith(row["id"] + "|"))
    assert line.split("|")[3] == "?"
    assert "Stop: campaign_budget; budget charged ms: 7300000" in body
    report.update(stop_reason="PRIVATE", budget_used_ms=True)
    safe = public_report(report)
    assert "stop_reason" not in safe and "budget_used_ms" not in safe


def test_packaged_crew_fixture_flag_is_strict_boolean():
    report = base_report("diagnostics", "7", "Counters")
    report["checks"] = [
        {
            "id": "crew_evaluation_fixture",
            "status": "passed",
            "code": "OK",
            "message": "Fixture",
            "duration_ms": 1,
            "evidence": {"crew_fixture_verified": "PRIVATE"},
        }
    ]
    assert "crew_fixture_verified" not in public_report(report)["checks"][0]["evidence"]
