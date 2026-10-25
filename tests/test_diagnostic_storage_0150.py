"""Storage bounds and corruption must never discard or reinterpret evidence."""

import base64
import copy
import hashlib
import json
import zlib

import pytest

from aigentics.diagnostic_storage import (
    MARKER,
    RAW_BYTES,
    STORED_BYTES,
    decode_report,
    encode_report,
)
from aigentics.evidence import base_report


def envelope(data):
    return {
        MARKER: "zlib-v1",
        "raw_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "data": base64.b64encode(zlib.compress(data)).decode(),
    }


def dense_campaign():
    # Mirrors supported upper-bound telemetry: 66rows,8traces,16calls,8mismatches.
    r = base_report("crew_campaign", "crew-campaign-4", "Synthetic counters")
    trace = {
        "step": 7,
        "request_chars": 48000,
        "duration_ms": 123456,
        "usage": {"prompt_eval_count": 12000, "eval_count": 4096},
        "response_shape": {
            "thinking_chars": 15000,
            "content_chars": 200,
            "native_call_count": 1,
            "finish_reason": "stop",
        },
    }
    call = {
        "tool": "write_file",
        "status": "failed",
        "schema_sha256": "a" * 64,
        "argument_types": {"path": "string", "content": "string", "expected_sha256": "string"},
        "allowed_fields": ["path", "content", "expected_sha256"],
        "required_fields": ["path", "content", "expected_sha256"],
        "validation_issues": [{"location": ["<unexpected>"], "code": "UNEXPECTED_ARGUMENT"}] * 8,
    }
    mismatch = {
        "code": "JSON_TYPE",
        "target": "cases.json",
        "path": "/cases/0/expected",
        "expected_type": "number",
        "actual_type": "boolean",
        "hint": "Use the required JSON type; booleans are distinct from numbers.",
    }
    for i in range(66):
        r["checks"].append(
            {
                "id": str(i),
                "status": "failed",
                "evidence": {
                    "request_traces": [copy.deepcopy(trace) for _ in range(8)],
                    "tool_diagnostics": [dict(copy.deepcopy(call), call_index=j + 1) for j in range(16)],
                    "initial_mismatches": [copy.deepcopy(mismatch) for _ in range(8)],
                    "mismatches": [copy.deepcopy(mismatch) for _ in range(8)],
                },
            }
        )
    return r


def test_dense_supported_campaign_roundtrips_all_evidence(credentials):
    report = dense_campaign()
    compact = credentials.json(report, separators=(",", ":")).encode()
    assert STORED_BYTES < len(compact) < RAW_BYTES
    stored = encode_report(report, credentials)
    assert len(stored.encode()) <= STORED_BYTES
    assert json.loads(stored)[MARKER] == "zlib-v1"
    assert decode_report(stored) == report
    assert len(decode_report(stored)["checks"]) == 66


@pytest.mark.parametrize("kind", ["health", "crew_campaign"])
def test_small_reports_remain_plain_legacy_compatible_json(credentials, kind):
    report = base_report(kind, "1", "Synthetic")
    stored = encode_report(report, credentials)
    assert MARKER not in json.loads(stored)
    assert decode_report(stored) == report
    assert decode_report(json.dumps(report, indent=2)) == report


def test_credentials_are_scrubbed_before_compression(credentials):
    credentials._values["KEY"] = "private-fixture-secret"
    report = base_report("crew_campaign", "crew-campaign-4", "Synthetic")
    report["padding"] = "repeated " * 120000
    report["local_value"] = "private-fixture-secret"
    saved = decode_report(encode_report(report, credentials))
    assert "private-fixture-secret" not in json.dumps(saved)
    assert saved["local_value"] == "[REDACTED]"


@pytest.mark.parametrize("kind,bytes_limit", [("health", 250000), ("crew_campaign", RAW_BYTES)])
def test_kind_specific_raw_caps_remain_enforced(credentials, kind, bytes_limit):
    report = base_report(kind, "1", "Synthetic")
    report["padding"] = "x" * bytes_limit
    with pytest.raises(ValueError, match="storage limit"):
        encode_report(report, credentials)


def test_campaign_case_cap_remains_enforced(credentials):
    report = base_report("crew_campaign", "1", "Synthetic")
    report["checks"] = [{}] * 67
    with pytest.raises(ValueError, match="case limit"):
        encode_report(report, credentials)


@pytest.mark.parametrize(
    "mutation", ["digest", "length", "truncated", "trailing", "base64", "encoding", "extra", "bool_length"]
)
def test_corrupt_envelopes_fail_with_static_errors(mutation):
    raw = json.dumps(base_report("crew_campaign", "1", "Synthetic")).encode()
    packed = envelope(raw)
    if mutation == "digest":
        packed["sha256"] = "0" * 64
    elif mutation == "length":
        packed["raw_bytes"] += 1
    elif mutation == "truncated":
        packed["data"] = base64.b64encode(zlib.compress(raw)[:-2]).decode()
    elif mutation == "trailing":
        packed["data"] = base64.b64encode(zlib.compress(raw) + b"PRIVATE").decode()
    elif mutation == "base64":
        packed["data"] = "PRIVATE!"
    elif mutation == "encoding":
        packed[MARKER] = "PRIVATE"
    elif mutation == "extra":
        packed["PRIVATE"] = "PRIVATE"
    else:
        packed["raw_bytes"] = True
    with pytest.raises(ValueError) as caught:
        decode_report(json.dumps(packed))
    assert "PRIVATE" not in str(caught.value)


def test_decompression_expansion_is_bounded_before_json_parse():
    packed = envelope(b"x" * (RAW_BYTES + 1))
    packed["raw_bytes"] = 1  # Advertised length cannot weaken the actual expansion bound.
    with pytest.raises(ValueError):
        decode_report(json.dumps(packed))


def test_multiple_zlib_streams_are_rejected():
    raw = json.dumps(base_report("crew_campaign", "1", "Synthetic")).encode()
    packed = envelope(raw)
    packed["data"] = base64.b64encode(zlib.compress(raw) + zlib.compress(raw)).decode()
    with pytest.raises(ValueError):
        decode_report(json.dumps(packed))


@pytest.mark.parametrize("raw", ["[]", "null", "not-json", '{"a":1,"a":2}', '{"x":NaN}'])
def test_nonobject_or_ambiguous_json_rejected(raw):
    with pytest.raises(ValueError):
        decode_report(raw)


def test_envelope_stored_size_bound_is_enforced():
    raw = json.dumps(base_report("crew_campaign", "1", "Synthetic")).encode()
    packed = envelope(raw)
    packed["data"] = "A" * (STORED_BYTES + 1)
    with pytest.raises(ValueError):
        decode_report(json.dumps(packed))


def test_nested_envelopes_and_compressed_generic_reports_are_rejected():
    for report in [base_report("health", "1", "Synthetic"), {MARKER: "zlib-v1"}]:
        with pytest.raises(ValueError):
            decode_report(json.dumps(envelope(json.dumps(report).encode())))


def test_reserved_marker_and_invalid_reports_rejected(credentials):
    with pytest.raises(ValueError):
        encode_report({MARKER: "zlib-v1"}, credentials)
    with pytest.raises(ValueError):
        encode_report([], credentials)
    with pytest.raises(ValueError):
        encode_report({"bad": float("nan")}, credentials)
