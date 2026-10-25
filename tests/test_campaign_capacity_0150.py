import copy
import json
import zipfile
import io
from aigentics.store import Store
from aigentics.campaign import PLAN_IDS
from aigentics.tool_diagnostics import argument_metadata, public_tool_diagnostics
from aigentics.contracts import public_mismatches
from aigentics.bundles import build_bundle
from test_report_capacity_0141 import large_campaign


def test_full_telemetry_survives_database_reopen_and_zip(tmp_path, credentials):
    report = large_campaign()
    metadata = argument_metadata(
        "write_file", {"path": "cases.json", "content": "{}", "expected_sha256": "last_read"}
    )
    calls = public_tool_diagnostics(
        [
            {
                "call_index": i + 1,
                "tool": "write_file",
                "status": "failed",
                **metadata,
                "validation_issues": [{"location": ["content"], "code": "ARGUMENT_TYPE"}] * 8,
            }
            for i in range(16)
        ]
    )
    mismatches = public_mismatches(
        [
            {
                "code": "JSON_TYPE",
                "target": "cases.json",
                "path": "/cases/0/expected",
                "expected_type": "number",
                "actual_type": "boolean",
            }
        ]
        * 8
    )
    for row, identity in zip(report["checks"], PLAN_IDS):
        row.update(id=identity, message="Synthetic")
        row["evidence"].update(
            tool_diagnostics=copy.deepcopy(calls),
            mismatches=copy.deepcopy(mismatches),
            initial_mismatches=copy.deepcopy(mismatches),
        )
    assert len(credentials.json(report, separators=(",", ":")).encode()) > 1_000_000
    path = tmp_path / "reports.sqlite3"
    with_store = Store(path, credentials)
    with_store.save_diagnostic(report)
    stored = with_store.db.execute("SELECT payload FROM diagnostics").fetchone()[0]
    assert "_aigentics_payload" in stored and len(stored.encode()) <= 1_000_000
    with_store.close()
    reopened = Store(path, credentials)
    try:
        actual = reopened.diagnostic_reports()[0]["payload"]
        assert actual["state"] == "interrupted" and actual["checks"] == report["checks"]
        data, _ = build_bundle([actual], credentials)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            exported = json.loads(archive.read("reports/01.json"))
            assert len(exported["checks"]) == 66
            assert all(len(row["evidence"]["tool_diagnostics"]) == 16 for row in exported["checks"])
            assert all(len(row["evidence"]["mismatches"]) == 8 for row in exported["checks"])
    finally:
        reopened.close()
