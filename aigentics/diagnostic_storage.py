"""Bounded lossless diagnostic persistence; legacy JSON remains readable.

Only JSON and zlib/base64 are used. The decompression bound applies before JSON
parsing, and envelopes require exact byte length, checksum and stream completion.
"""

import base64
import binascii
import hashlib
import json
import re
import zlib

GENERIC_BYTES = 250_000
STORED_BYTES = 1_000_000
RAW_BYTES = 3_000_000
MAX_CASES = 66
MARKER = "_aigentics_payload"
ENCODING = "zlib-v1"


def _error():
    return ValueError("Diagnostic storage payload is invalid or exceeds its limit")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _error()
        result[key] = value
    return result


def _constant(value):
    raise _error()


def _json(raw):
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise _error() from None
    if not isinstance(value, dict):
        raise _error()
    return value


def encode_report(report, credentials):
    """Serialize scrubbed data; compress campaigns only when plain JSON exceeds1MB."""
    if not isinstance(report, dict):
        raise ValueError("Diagnostic report must be a JSON object")
    if MARKER in report:
        raise ValueError("Diagnostic report contains a reserved storage field")
    campaign = report.get("kind") == "crew_campaign"
    if campaign and (not isinstance(report.get("checks"), list) or len(report["checks"]) > MAX_CASES):
        raise ValueError("Campaign report exceeds the case limit")
    try:
        text = credentials.json(report, separators=(",", ":"), allow_nan=False)
        raw = text.encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise ValueError("Diagnostic report is not valid JSON") from None
    if len(raw) > (RAW_BYTES if campaign else GENERIC_BYTES):
        raise ValueError("Diagnostic report exceeds the storage limit")
    if not campaign or len(raw) <= STORED_BYTES:
        return text
    envelope = {
        MARKER: ENCODING,
        "raw_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "data": base64.b64encode(zlib.compress(raw)).decode("ascii"),
    }
    packed = json.dumps(envelope, separators=(",", ":"))
    if len(packed.encode("utf-8")) > STORED_BYTES:
        raise ValueError("Diagnostic report exceeds the stored payload limit")
    return packed


def decode_report(raw):
    """Decode a legacy report or a strictly bounded, integrity-checked envelope."""
    if not isinstance(raw, str):
        raise _error()
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError:
        raise _error() from None
    if size > RAW_BYTES:
        raise _error()
    value = _json(raw)
    if MARKER not in value:
        return value
    if (
        size > STORED_BYTES
        or set(value) != {MARKER, "raw_bytes", "sha256", "data"}
        or value[MARKER] != ENCODING
        or type(value["raw_bytes"]) is not int
        or not 0 < value["raw_bytes"] <= RAW_BYTES
        or not isinstance(value["sha256"], str)
        or not re.fullmatch(r"[a-f0-9]{64}", value["sha256"])
        or not isinstance(value["data"], str)
    ):
        raise _error()
    try:
        compressed = base64.b64decode(value["data"], validate=True)
        decoder = zlib.decompressobj()
        unpacked = decoder.decompress(compressed, RAW_BYTES + 1)
        if (
            len(unpacked) > RAW_BYTES
            or not decoder.eof
            or decoder.unused_data
            or decoder.unconsumed_tail
            or len(unpacked) != value["raw_bytes"]
            or hashlib.sha256(unpacked).hexdigest() != value["sha256"]
        ):
            raise _error()
    except (ValueError, TypeError, UnicodeError, binascii.Error, zlib.error):
        raise _error() from None
    report = _json(unpacked)
    # Compression is reserved for bounded campaigns, never arbitrary nested envelopes.
    if (
        MARKER in report
        or report.get("kind") != "crew_campaign"
        or not isinstance(report.get("checks"), list)
        or len(report["checks"]) > MAX_CASES
    ):
        raise _error()
    return report
