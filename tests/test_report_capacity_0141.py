import copy
import json
import pytest
from aigentics.evidence import base_report
from aigentics.store import Store


def large_campaign():
    r = base_report("crew_campaign", "crew-campaign-3", "Synthetic counters")
    r.update(state="running", planned_cases=66, active_case=None)
    trace = {
        "step": 1,
        "duration_ms": 123456,
        "native_call_count": 1,
        "content_chars": 1234,
        "request_chars": 45000,
        "tool_schema_chars": 3000,
        "tool_schema_sha256": "a" * 64,
        "advertised_tool_count": 6,
        "text_tool_response": False,
        "response_shape": {
            "thinking_chars": 15000,
            "content_chars": 200,
            "native_call_count": 1,
            "tool_calls_field_present": True,
            "content_field_present": True,
            "finish_reason": "stop",
            "stream": False,
        },
        "usage": {"prompt_eval_count": 12000, "eval_count": 4096, "total_duration": 123456789000},
    }
    for i in range(66):
        r["checks"].append(
            {
                "id": str(i),
                "status": "failed",
                "code": "ROLE_REQUIREMENTS_NOT_MET",
                "duration_ms": 180000,
                "evidence": {
                    "request_traces": [copy.deepcopy(trace) for _ in range(8)],
                    "initial_task_checks": {"missing_readbacks": 1, "content_failures": 1},
                    "task_checks": {"missing_readbacks": 0, "content_failures": 1},
                },
            }
        )
    assert len(json.dumps(r).encode()) > 250000
    return r


def test_long_campaign_evidence_survives_each_save_restart_and_recovery(tmp_path, credentials):
    path = tmp_path / "reports.sqlite3"
    full = large_campaign()
    partial = copy.deepcopy(full)
    partial["checks"] = []
    with_store = Store(path, credentials)
    for row in full["checks"]:
        partial["checks"].append(row)
        with_store.save_diagnostic(partial)
    with_store.close()
    reopened = Store(path, credentials)
    try:
        recovered = reopened.diagnostic_reports()[0]["payload"]
        assert recovered["state"] == "interrupted"
        assert recovered["checks"] == full["checks"]
        recovered["state"] = "needs_attention"
        reopened.save_diagnostic(recovered, refresh_retention=True)
        assert reopened.diagnostic_reports()[0]["payload"] == recovered
    finally:
        reopened.close()


@pytest.mark.parametrize("kind,size", [("health", 250001), ("crew_campaign", 1000001)])
def test_caps_still_reject_oversize_without_replacing_last_saved_record(store, kind, size):
    r = base_report(kind, "test", "Synthetic")
    store.save_diagnostic(r)
    before = store.diagnostic_reports()[0]["payload"]
    r["padding"] = "x" * size
    with pytest.raises(ValueError, match="storage limit"):
        store.save_diagnostic(r)
    assert store.diagnostic_reports()[0]["payload"] == before


def test_campaign_case_count_remains_bounded(store):
    r = large_campaign()
    r["checks"].append(r["checks"][0])
    with pytest.raises(ValueError, match="case limit"):
        store.save_diagnostic(r)
