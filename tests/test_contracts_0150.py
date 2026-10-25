"""Contract diagnostics explain failures without leaking actual output or changing scores."""

from copy import deepcopy
import json

import pytest

from aigentics.contracts import (
    HINTS,
    MAX_MISMATCHES,
    contract_prompt,
    evaluate_contract,
    public_mismatches,
)
from aigentics.crew_cases import CASES, evaluate_content


def case_named(name):
    return next(case for case in CASES if case.id == name)


def prepare(case, root):
    for name, data in {**case.files, **case.outputs}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for name, data in case.output_json.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    return json.dumps(case.answer) if case.answer is not None else "Verified"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_correct_contract_diagnostics_preserve_all_original_scores(case, tmp_path):
    answer = prepare(case, tmp_path)
    result = evaluate_contract(case, tmp_path, answer)
    assert result["checks"] == evaluate_content(case, tmp_path, answer)
    assert all(result["checks"].values())
    assert result["mismatches"] == []


def test_equivalent_python_ast_is_labeled_format_only_without_regrading(tmp_path):
    case = case_named("george_workflow")
    answer = prepare(case, tmp_path)
    path = tmp_path / "price.py"
    path.write_bytes(path.read_bytes().replace(b"    return", b"  return"))
    result = evaluate_contract(case, tmp_path, answer)
    assert result["checks"]["OUTPUT_CONTENT"] is False
    assert result["mismatches"] == [
        {
            "code": "FORMAT_ONLY",
            "target": "price.py",
            "path": "",
            "expected_type": "string",
            "actual_type": "string",
            "hint": HINTS["FORMAT_ONLY"],
        }
    ]


@pytest.mark.parametrize("extra", ["PRIVATE-secret-key", "../../.env", "nested/PRIVATE"])
def test_extra_json_keys_never_enter_diagnostic_paths(tmp_path, extra):
    case = case_named("vera_clamp")
    answer = prepare(case, tmp_path)
    data = deepcopy(case.output_json["cases.json"])
    data[extra] = "PRIVATE-source-code"
    (tmp_path / "cases.json").write_text(json.dumps(data), encoding="utf-8")
    result = evaluate_contract(case, tmp_path, answer)
    assert result["checks"]["OUTPUT_CONTENT"] is False
    assert result["mismatches"][0]["code"] == "JSON_KEYS"
    assert result["mismatches"][0]["path"] == ""
    assert extra not in str(result) and "PRIVATE" not in str(result)


@pytest.mark.parametrize(
    "actual,code,actual_type",
    [
        (True, "JSON_TYPE", "boolean"),
        (999, "JSON_VALUE", "number"),
        ("PRIVATE-wrong-value", "JSON_TYPE", "string"),
    ],
)
def test_numeric_differences_name_schema_path_and_types_without_values(tmp_path, actual, code, actual_type):
    case = case_named("vera_shipping")
    answer = prepare(case, tmp_path)
    data = deepcopy(case.output_json["cases.json"])
    data["cases"][0]["expected"] = actual
    (tmp_path / "cases.json").write_text(json.dumps(data), encoding="utf-8")
    result = evaluate_contract(case, tmp_path, answer)
    mismatch = result["mismatches"][0]
    assert mismatch["code"] == code
    assert mismatch["path"] == "/cases/0/expected"
    assert mismatch["expected_type"] == "number" and mismatch["actual_type"] == actual_type
    if isinstance(actual, str):
        assert actual not in json.dumps(result)
    assert "999" not in str(result) and "PRIVATE" not in str(result)


@pytest.mark.parametrize(
    "data", [b'{"cases":', b"```json\n{}\n```", b'{"cases": [], "cases": []}', b"PRIVATE"]
)
def test_invalid_json_has_static_parse_diagnostic(tmp_path, data):
    case = case_named("vera_clamp")
    answer = prepare(case, tmp_path)
    (tmp_path / "cases.json").write_bytes(data)
    result = evaluate_contract(case, tmp_path, answer)
    assert result["mismatches"][0]["code"] == "JSON_PARSE"
    assert "PRIVATE" not in str(result)


def test_missing_file_and_known_input_change_are_separate(tmp_path):
    case = case_named("ada_two_files")
    answer = prepare(case, tmp_path)
    missing = next(iter(case.outputs))
    (tmp_path / missing).unlink()
    source = next(n for n in case.files if n not in case.outputs)
    (tmp_path / source).write_text("PRIVATE", encoding="utf-8")
    result = evaluate_contract(case, tmp_path, answer)
    assert {m["code"] for m in result["mismatches"]} == {"MISSING_OUTPUT", "SOURCE_CHANGED"}
    assert next(m for m in result["mismatches"] if m["code"] == "SOURCE_CHANGED")["target"] == source
    assert "PRIVATE" not in str(result)


def test_array_length_and_missing_expected_field_are_precise(tmp_path):
    case = case_named("vera_clamp")
    answer = prepare(case, tmp_path)
    data = deepcopy(case.output_json["cases.json"])
    data["cases"].pop()
    del data["cases"][0]["expected"]
    (tmp_path / "cases.json").write_text(json.dumps(data), encoding="utf-8")
    result = evaluate_contract(case, tmp_path, answer)
    assert any(m["code"] == "JSON_LENGTH" and m["path"] == "/cases" for m in result["mismatches"])
    assert any(m["code"] == "JSON_MISSING" and m["path"] == "/cases/0/expected" for m in result["mismatches"])


def test_relative_citation_is_labeled_without_silently_accepting_it(tmp_path):
    case = case_named("sentinel_bug")
    prepare(case, tmp_path)
    answer = deepcopy(case.answer)
    answer["findings"][0]["file"] = "./access.py"
    result = evaluate_contract(case, tmp_path, json.dumps(answer))
    assert result["checks"]["FINAL_ANSWER"] is False
    assert result["mismatches"][0]["code"] == "PATH_SPELLING"
    assert result["mismatches"][0]["target"] == "final_answer"
    assert result["mismatches"][0]["path"] == "/findings/0/file"
    assert "./access.py" not in str(result)


def test_unexpected_file_does_not_disclose_discovered_name(tmp_path):
    case = case_named("sentinel_clean")
    answer = prepare(case, tmp_path)
    (tmp_path / "PRIVATE-sensitive-file.txt").write_text("PRIVATE", encoding="utf-8")
    result = evaluate_contract(case, tmp_path, answer)
    assert result["checks"]["NO_UNEXPECTED_FILES"] is False
    assert result["mismatches"][0]["code"] == "UNEXPECTED_FILE"
    assert "PRIVATE" not in str(result)


def test_malformed_answer_does_not_expose_text(tmp_path):
    case = case_named("sentinel_clean")
    prepare(case, tmp_path)
    result = evaluate_contract(case, tmp_path, "PRIVATE wrong answer")
    assert result["mismatches"][0]["code"] == "ANSWER_PARSE"
    assert "PRIVATE" not in str(result)


@pytest.mark.parametrize("mutation", ["target", "path", "code", "hint", "actual_type"])
def test_public_diagnostics_reject_private_or_malformed_fields(mutation):
    row = {
        "code": "JSON_VALUE",
        "target": "cases.json",
        "path": "/cases/0/expected",
        "expected_type": "number",
        "actual_type": "number",
        "hint": "not trusted",
    }
    row[mutation] = ["PRIVATE"] if mutation == "actual_type" else "PRIVATE"
    result = public_mismatches([row])
    assert "PRIVATE" not in str(result)
    if mutation == "hint":
        assert result[0]["hint"] == HINTS["JSON_VALUE"]


def test_mismatch_count_is_bounded(tmp_path):
    case = case_named("vera_clamp")
    answer = prepare(case, tmp_path)
    (tmp_path / "cases.json").write_text('{"cases":[{}, {}, {}, {}, {}, {}, {}, {}]}', encoding="utf-8")
    result = evaluate_contract(case, tmp_path, answer)
    assert 1 <= len(result["mismatches"]) <= MAX_MISMATCHES
    assert len(public_mismatches(result["mismatches"] * 20)) <= MAX_MISMATCHES


def test_symlink_output_is_not_followed(tmp_path):
    case = case_named("george_target")
    answer = prepare(case, tmp_path)
    target_name = next(iter(case.outputs))
    (tmp_path / target_name).unlink()
    outside = tmp_path.parent / "outside-contract-private.txt"
    outside.write_text("PRIVATE", encoding="utf-8")
    try:
        (tmp_path / target_name).symlink_to(outside)
    except OSError:
        pytest.skip("Symbolic links unavailable")
    result = evaluate_contract(case, tmp_path, answer)
    assert not result["checks"]["OUTPUT_CONTENT"]
    assert "PRIVATE" not in str(result)
    assert any(m["code"] == "UNREADABLE_OUTPUT" for m in result["mismatches"])


@pytest.mark.parametrize("name", ["george_workflow", "vera_clamp", "sentinel_bug"])
def test_measurement_prompt_clarifies_without_changing_legacy_or_revealing_answers(name):
    case = case_named(name)
    original = case.prompt
    prompt = contract_prompt(case)
    assert prompt.startswith(original + "\nExplicit acceptance contract:")
    assert case.prompt == original
    for content in case.outputs.values():
        assert content.decode() not in prompt
    if case.output_json:
        assert "duplicate or extra keys" in prompt
    if case.answer is not None:
        assert json.dumps(case.answer) not in prompt
