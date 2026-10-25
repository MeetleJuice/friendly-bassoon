"""Unambiguous JSON structure without leaking fixture solution values."""

import json
import pytest
from aigentics.contracts import structural_schema, evaluate_contract
from aigentics.crew_cases import CASES
from aigentics.measurement import ARCHIVED_MANIFESTS, manifest_id, measurement_plan, summarize_trials
from aigentics.bundles import clean_report
from aigentics.evidence import base_report


@pytest.mark.parametrize(
    "value,kind",
    [
        (True, "boolean"),
        (1, "number"),
        (1.5, "number"),
        (None, "null"),
        ("private-solution", "string"),
        ([], "array"),
    ],
)
def test_schema_advertises_types_not_values(value, kind):
    result = structural_schema(value)
    assert result["type"] == kind
    assert "private-solution" not in json.dumps(result)
    assert not ({"const", "enum", "default", "maximum", "minimum"} & set(result))


def test_strict_grader_still_rejects_wrong_wrapper_and_booleans(tmp_path):
    case = next(c for c in CASES if c.id == "vera_exclusive")
    for name, data in case.files.items():
        (tmp_path / name).write_bytes(data)
    expected = case.output_json["cases.json"]
    (tmp_path / "cases.json").write_text(json.dumps(expected["cases"]))
    assert not evaluate_contract(case, tmp_path, "")["checks"]["OUTPUT_CONTENT"]
    (tmp_path / "cases.json").write_text(json.dumps(expected))
    assert evaluate_contract(case, tmp_path, "")["checks"]["OUTPUT_CONTENT"]
    wrong = json.loads(json.dumps(expected))
    wrong["cases"][2]["expected"] = False
    (tmp_path / "cases.json").write_text(json.dumps(wrong))
    assert not evaluate_contract(case, tmp_path, "")["checks"]["OUTPUT_CONTENT"]


def test_old_frozen_manifest_and_export_coverage_remain_intact(credentials):
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    old = json.loads((root / "docs/benchmarks/crew-measurement-1.json").read_text(encoding="utf-8"))
    digest = manifest_id(old)
    assert digest == ARCHIVED_MANIFESTS["crew-measurement-1"]
    assert len(measurement_plan("crew-measurement-1")) == 30
    assert len(summarize_trials([], version="crew-measurement-1")["groups"]) == 12
    report = base_report("crew_campaign", "crew-campaign-4", "Synthetic")
    report.update(
        mode="measurement", manifest_id=digest, measurement_manifest=old, planned_cases=30, checks=[]
    )
    exported = clean_report(report, credentials)
    assert exported["measurement_manifest"] == old
    assert exported["measurement_summary"]["measurement_version"] == "crew-measurement-1"
    assert len(exported["measurement_summary"]["groups"]) == 12
