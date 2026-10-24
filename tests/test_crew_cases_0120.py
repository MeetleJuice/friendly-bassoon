"""Independent content evaluator rejects plausible but incorrect specialist outputs."""

from collections import Counter
import json
import pytest

from aigentics.crew_cases import CASES, evaluate_content


def prepare(case, root):
    for name, data in {**case.files, **case.outputs}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for name, data in case.output_json.items():
        (root / name).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return json.dumps(case.answer) if case.answer is not None else "Completed with file evidence."


def test_catalog_covers_all_six_roles_with_three_distinct_cases():
    assert Counter(case.role for case in CASES) == dict.fromkeys(
        ("george", "scout", "ada", "vera", "sentinel", "atlas"), 3
    )
    assert len({case.id for case in CASES}) == 18
    for case in CASES:
        assert set(case.required_reads) <= set(case.files)
        assert not (set(case.outputs) & set(case.output_json))
        assert bool(case.answer is not None) != bool(case.outputs or case.output_json)
        assert len(case.prompt) < 1000
        assert sum(map(len, case.files.values())) < 2000


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_correct_oracle_accepts_all_case_content(case, tmp_path):
    final = prepare(case, tmp_path)
    assert all(evaluate_content(case, tmp_path, final).values())


@pytest.mark.parametrize("case", [case for case in CASES if case.answer is not None], ids=lambda c: c.id)
def test_convincing_prose_cannot_replace_structured_evidence(case, tmp_path):
    prepare(case, tmp_path)
    result = evaluate_content(case, tmp_path, "All done. I inspected everything and found no problems.")
    assert result["FINAL_ANSWER"] is False


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_unrequested_file_is_never_accepted(case, tmp_path):
    final = prepare(case, tmp_path)
    (tmp_path / "unrequested.txt").write_bytes(b"unexpected\n")
    assert evaluate_content(case, tmp_path, final)["NO_UNEXPECTED_FILES"] is False


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_unrelated_source_change_is_rejected(case, tmp_path):
    final = prepare(case, tmp_path)
    unchanged = next(name for name in case.files if name not in case.outputs and name not in case.output_json)
    (tmp_path / unchanged).write_bytes(b"wrong content\n")
    assert evaluate_content(case, tmp_path, final)["INPUTS_UNCHANGED"] is False


@pytest.mark.parametrize("case", [c for c in CASES if c.outputs or c.output_json], ids=lambda c: c.id)
def test_wrong_output_content_is_rejected(case, tmp_path):
    final = prepare(case, tmp_path)
    name = next(iter(case.outputs or case.output_json))
    (tmp_path / name).write_bytes(b'{"cases":[]}\n')
    assert evaluate_content(case, tmp_path, final)["OUTPUT_CONTENT"] is False


@pytest.mark.parametrize(
    "final",
    [
        '{"findings":[],"findings":[]}',
        '```json\n{"findings":[]}\n```',
        '{"findings":[],"confidence":1}',
        '{"findings":null}',
    ],
)
def test_reviewer_contract_rejects_duplicate_keys_fences_and_extra_claims(tmp_path, final):
    case = next(case for case in CASES if case.id == "sentinel_clean")
    prepare(case, tmp_path)
    assert evaluate_content(case, tmp_path, final)["FINAL_ANSWER"] is False


def test_boolean_does_not_pass_for_a_numeric_fact(tmp_path):
    case = next(case for case in CASES if case.id == "atlas_stale")
    prepare(case, tmp_path)
    final = json.dumps({**case.answer, "version": True})
    assert evaluate_content(case, tmp_path, final)["FINAL_ANSWER"] is False


def test_numeric_json_formatting_is_not_a_false_failure(tmp_path):
    case = next(case for case in CASES if case.id == "vera_empty")
    final = prepare(case, tmp_path)
    (tmp_path / "cases.json").write_text(
        '{"cases":[{"input":[],"expected":"empty"},{"input":[2],"expected":2.0},'
        '{"input":[2,4],"expected":3.0}]}',
        encoding="utf-8",
    )
    assert all(evaluate_content(case, tmp_path, final).values())


def test_missing_output_does_not_pass_on_a_completion_message(tmp_path):
    case = next(case for case in CASES if case.id == "ada_two_files")
    final = prepare(case, tmp_path)
    (tmp_path / "about.txt").unlink()
    result = evaluate_content(case, tmp_path, final)
    assert result["OUTPUT_CONTENT"] is False
    assert result["NO_UNEXPECTED_FILES"] is True
    assert result["INPUTS_UNCHANGED"] is True


def test_linked_source_is_rejected_before_read(tmp_path):
    case = next(case for case in CASES if case.id == "atlas_handoff")
    path = tmp_path / "progress.json"
    target = tmp_path.parent / "outside-crew-fixture.json"
    target.write_text(json.dumps(case.files["progress.json"].decode()), encoding="utf-8")
    try:
        path.symlink_to(target)
    except OSError:
        pytest.skip("Symbolic links unavailable on this platform")
    assert not any(evaluate_content(case, tmp_path, json.dumps(case.answer)).values())


def test_vera_vectors_distinguish_correct_rules_from_seeded_mutants():
    vectors = {case.id: case.output_json["cases.json"]["cases"] for case in CASES if case.role == "vera"}
    rules = {
        "vera_clamp": (lambda n: min(10, max(0, n)), lambda n: n),
        "vera_shipping": (lambda n: 0 if n >= 50 else 5, lambda n: 0 if n > 50 else 5),
        "vera_empty": (
            lambda xs: sum(xs) / len(xs) if xs else "empty",
            lambda xs: sum(xs) / len(xs) if xs else 0,
        ),
    }
    for identity, rows in vectors.items():
        correct, mutant = rules[identity]
        assert all(correct(row["input"]) == row["expected"] for row in rows)
        assert any(mutant(row["input"]) != row["expected"] for row in rows)
