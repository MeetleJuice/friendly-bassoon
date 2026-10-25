import json
from aigentics.crew_cases import CASES, evaluate_content


def test_large_valid_json_integer_is_a_failed_contract_not_a_grader_crash(tmp_path):
    case = next(c for c in CASES if c.id == "vera_shipping")
    for name, data in case.files.items():
        (tmp_path / name).write_bytes(data)
    value = {
        "cases": [
            {"input": 49, "expected": 10**1000},
            {"input": 50, "expected": 0},
            {"input": 51, "expected": 0},
        ]
    }
    (tmp_path / "cases.json").write_text(json.dumps(value))
    assert evaluate_content(case, tmp_path, "Done")["OUTPUT_CONTENT"] is False
