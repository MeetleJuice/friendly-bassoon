"""Correlated schema failures remain diagnosable without leaking input values."""

import hashlib
import json

import pytest

from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.runtime import Runtime
from aigentics.tool_diagnostics import (
    argument_metadata,
    public_tool_diagnostics,
    schema_fingerprint,
    tool_diagnostics,
)
from aigentics.tools import SCHEMAS


def event(kind, **data):
    return {"kind": kind, "data": data}


def test_argument_metadata_contains_known_types_not_private_values_or_unknown_names():
    value = argument_metadata(
        "write_file",
        {
            "path": "private/user.txt",
            "content": "PRIVATE-CODE",
            "expected_sha256": "PRIVATE-HASH",
            "PRIVATE-UNKNOWN-KEY": "PRIVATE-KEY",
        },
    )
    assert value["argument_types"] == {"path": "string", "content": "string", "expected_sha256": "string"}
    assert value["unexpected_argument_count"] == 1
    assert "PRIVATE" not in str(value) and "private/user.txt" not in str(value)
    assert value["allowed_fields"] == sorted(SCHEMAS["write_file"].model_fields)
    assert set(value["required_fields"]) == {"path", "content", "expected_sha256"}


@pytest.mark.parametrize(
    "argument,kind",
    [
        (None, "null"),
        (True, "boolean"),
        (7, "integer"),
        (1.25, "number"),
        ("secret", "string"),
        ([], "array"),
        ({}, "object"),
        (object(), "other"),
    ],
)
def test_known_input_type_is_preserved_without_its_value(argument, kind):
    assert argument_metadata("read_file", {"path": argument})["argument_types"] == {"path": kind}


def test_schema_digest_is_canonical_and_matches_actual_model_schema():
    expected = hashlib.sha256(
        json.dumps(
            SCHEMAS["project_map"].model_json_schema(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()
    assert schema_fingerprint("project_map") == expected
    assert len(expected) == 64


def test_per_call_validation_and_recovery_are_correlated_and_ordered():
    records = [
        event(
            "tool.requested",
            execution_id="PRIVATE-ID1",
            tool="project_map",
            **argument_metadata("project_map", {"PRIVATE-ARG": "PRIVATE-VALUE"}),
        ),
        event(
            "tool.result",
            execution_id="PRIVATE-ID1",
            tool="project_map",
            status="failed",
            error_type="ValidationError",
            code="TOOL_ARGUMENT_VALIDATION",
            error="PRIVATE-RAW-ERROR",
            validation_issues=[{"location": ["PRIVATE-ARG"], "code": "UNEXPECTED_ARGUMENT"}],
        ),
        event(
            "tool.requested",
            execution_id="PRIVATE-ID2",
            tool="project_map",
            **argument_metadata("project_map", {}),
        ),
        event("tool.result", execution_id="PRIVATE-ID2", tool="project_map", status="succeeded"),
    ]
    safe = tool_diagnostics(records)
    assert [r["call_index"] for r in safe] == [1, 2]
    assert [r["status"] for r in safe] == ["failed", "succeeded"]
    assert safe[0]["validation_issues"] == [{"location": ["<unexpected>"], "code": "UNEXPECTED_ARGUMENT"}]
    assert safe[0]["unexpected_argument_count"] == 1 and safe[1]["unexpected_argument_count"] == 0
    assert all(r["schema_source"] == "runtime" for r in safe)
    assert "PRIVATE" not in json.dumps(safe)


def test_legacy_schema_fallback_does_not_claim_arguments_were_recorded():
    records = [
        event("tool.requested", execution_id="1", tool="read_file", argument_keys=["PRIVATE"]),
        event(
            "tool.result",
            execution_id="1",
            tool="read_file",
            status="failed",
            error_type="FileNotFoundError",
            error="PRIVATE-PATH",
        ),
    ]
    safe = tool_diagnostics(records)
    assert safe[0]["schema_source"] == "current_registry"
    assert "argument_types" not in safe[0] and "unexpected_argument_count" not in safe[0]
    assert safe[0]["error_type"] == "FileNotFoundError"
    assert "PRIVATE" not in str(safe)


def test_export_preserves_historical_schema_digest_without_rewriting_it():
    value = [
        {
            "call_index": 1,
            "tool": "read_file",
            "status": "failed",
            "schema_sha256": "a" * 64,
            "schema_source": "runtime",
        }
    ]
    assert public_tool_diagnostics(value)[0]["schema_sha256"] == "a" * 64


def test_malicious_nested_values_and_unrecognized_fields_are_discarded():
    r = {
        "call_index": 1,
        "tool": "read_file",
        "status": "failed",
        "error": "PRIVATE",
        "code": "PRIVATE",
        "error_type": "PRIVATE",
        "schema_sha256": "PRIVATE",
        "schema_source": "PRIVATE",
        "argument_types": {"path": "PRIVATE", "PRIVATE": "string"},
        "allowed_fields": ["path", "PRIVATE"],
        "required_fields": ["PRIVATE"],
        "unexpected_argument_count": True,
        "validation_issues": [
            {"location": ["path", "PRIVATE"], "code": "ARGUMENT_TYPE"},
            {"location": ["path", 9999], "code": "ARGUMENT_BOUNDS"},
            {"location": ["PRIVATE"], "code": ["PRIVATE"]},
        ],
        "PRIVATE": "PRIVATE",
    }
    safe = public_tool_diagnostics([r])
    assert "PRIVATE" not in json.dumps(safe)
    assert safe[0]["validation_issues"] == [
        {"location": ["path", "<unexpected>"], "code": "ARGUMENT_TYPE"},
        {"location": ["path", 40], "code": "ARGUMENT_BOUNDS"},
    ]
    assert "unexpected_argument_count" not in safe[0]


@pytest.mark.parametrize(
    "value", [None, {}, "PRIVATE", [None], [{"tool": ["PRIVATE"], "call_index": 1, "status": "failed"}]]
)
def test_malformed_top_level_evidence_fails_closed(value):
    assert public_tool_diagnostics(value) == []


def test_call_limit_keeps_original_ordinals_and_never_leaks_orphan_results():
    records = []
    for index in range(32):
        records += [
            event("tool.requested", execution_id=str(index), tool="read_file"),
            event("tool.result", execution_id=str(index), tool="read_file", status="succeeded"),
        ]
    records += [
        event("tool.result", execution_id="orphan", tool="read_file", status="failed", error="PRIVATE")
    ]
    safe = tool_diagnostics(records)
    assert len(safe) == 16 and [r["call_index"] for r in safe] == list(range(17, 33))


def test_actual_native_schema_failure_is_visible_without_raw_arguments(store, credentials, tmp_path):
    store.save_profile(Profile(id="ollama", name="Fixture"))

    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, model, messages, tools):
            count = sum(m["role"] == "tool" for m in messages)
            if count < 2:
                return Reply(
                    calls=[
                        ToolCall(
                            id=str(count),
                            name="project_map",
                            arguments={"path": "PRIVATE-PATH", "PRIVATE-NAME": "PRIVATE-VALUE"}
                            if count == 0
                            else {},
                        )
                    ]
                )
            return Reply(content="Inspected")

    sid, state = Runtime(store, credentials, Fixture).run(
        Agent(tools=["project_map"], allow_writes=False, max_steps=5),
        tmp_path,
        "Inspect",
        lambda *args: False,
    )
    assert state == "completed"
    safe = tool_diagnostics(store.events(sid))
    assert safe[0]["code"] == "TOOL_ARGUMENT_VALIDATION"
    assert safe[0]["validation_issues"][0]["code"] == "UNEXPECTED_ARGUMENT"
    assert safe[1]["status"] == "succeeded"
    assert safe[0]["schema_source"] == "runtime"
    assert safe[0]["argument_types"] == {}
    assert safe[0]["unexpected_known_argument_types"] == {"path": "string"}
    assert safe[0]["unexpected_argument_count"] == 2
    assert safe[1]["unexpected_known_argument_types"] == {}
    assert "PRIVATE" not in str(safe)


@pytest.mark.parametrize(
    "argument,kind",
    [
        (None, "null"),
        (True, "boolean"),
        (7, "integer"),
        (1.25, "number"),
        ("PRIVATE", "string"),
        ([], "array"),
        ({}, "object"),
        (object(), "other"),
    ],
)
def test_globally_known_but_disallowed_argument_retains_type_only(argument, kind):
    value = argument_metadata("project_map", {"path": argument, "PRIVATE-NAME": "PRIVATE-SECRET"})
    assert value["argument_types"] == {}
    assert value["unexpected_known_argument_types"] == {"path": kind}
    assert value["unexpected_argument_count"] == 2
    assert "PRIVATE" not in str(value)


def test_unexpected_known_field_export_uses_only_registry_vocabulary_and_type_enum():
    value = [
        {
            "call_index": 1,
            "tool": "read_file",
            "status": "failed",
            "unexpected_known_argument_types": {
                "query": "string",
                "path": "string",
                "argv": "PRIVATE",
                "PRIVATE": "string",
                "content": ["PRIVATE"],
            },
        }
    ]
    safe = public_tool_diagnostics(value)
    assert safe[0]["unexpected_known_argument_types"] == {"query": "string"}
    assert "PRIVATE" not in str(safe)


def test_unexpected_known_field_capture_and_export_remain_bounded_by_finite_schema():
    from aigentics.tool_diagnostics import MAX_FIELDS

    names = {name for schema in SCHEMAS.values() for name in schema.model_fields}
    value = argument_metadata(
        "project_map",
        {**{name: "PRIVATE" for name in names}, **{f"PRIVATE-{i}": "PRIVATE" for i in range(100)}},
    )
    assert set(value["unexpected_known_argument_types"]) == names
    assert len(value["unexpected_known_argument_types"]) <= MAX_FIELDS
    assert value["unexpected_argument_count"] == len(names) + 100
    assert "PRIVATE" not in str(value)
