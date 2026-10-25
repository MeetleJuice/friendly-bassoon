"""Bounded per-call schema evidence, without arguments, values or raw errors.

The runtime captures schema metadata at request time. Legacy events without that
snapshot are explicitly labelled as using the current registry, rather than
pretending the historical schema is known. Export retains the original digest.
"""

import hashlib
import json
import re

from .tools import SCHEMAS, VALIDATION_ISSUE_CODES

MAX_CALLS = 16
MAX_FIELDS = 16
TYPE_NAMES = frozenset(("null", "boolean", "integer", "number", "string", "array", "object", "other"))
ERROR_TYPES = frozenset(
    (
        "ValidationError",
        "ValueError",
        "FileNotFoundError",
        "PermissionError",
        "StaleFileError",
        "WriteTargetError",
        "OSError",
        "UnicodeDecodeError",
        "IsADirectoryError",
        "NotADirectoryError",
        "CommandFailure",
        "RuntimeError",
        "KeyError",
        "TypeError",
        "OtherError",
    )
)
ERROR_CODES = frozenset(("TOOL_ARGUMENT_VALIDATION", "STALE_FILE", "WRITE_TARGET_MISMATCH", "UNKNOWN_ERROR"))


def schema_fingerprint(tool):
    """Hash the actual Pydantic JSON schema using stable canonical serialization."""
    if not isinstance(tool, str) or tool not in SCHEMAS:
        raise ValueError("Unknown registered tool")
    raw = json.dumps(
        SCHEMAS[tool].model_json_schema(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _type_name(value):
    # bool must precede int; no repr(), str(), or model content enters metadata.
    return {
        type(None): "null",
        bool: "boolean",
        int: "integer",
        float: "number",
        str: "string",
        list: "array",
        dict: "object",
    }.get(type(value), "other")


def _registry_fields():
    """Finite schema vocabulary, never names learned from model arguments."""
    return frozenset(name for schema in SCHEMAS.values() for name in schema.model_fields)


def _argument_types(value, allowed):
    if not isinstance(value, dict):
        return {}
    return {
        name: value[name]
        for name in sorted(allowed)[:MAX_FIELDS]
        if name in value and isinstance(value[name], str) and value[name] in TYPE_NAMES
    }


def argument_metadata(tool, arguments):
    """Capture safe field/type/schema information before native dispatch."""
    if not isinstance(tool, str) or tool not in SCHEMAS or not isinstance(arguments, dict):
        return {}
    fields = SCHEMAS[tool].model_fields
    return {
        "argument_types": {name: _type_name(value) for name, value in arguments.items() if name in fields},
        "unexpected_known_argument_types": {
            name: _type_name(arguments[name])
            for name in sorted(_registry_fields() - fields.keys())[:MAX_FIELDS]
            if name in arguments
        },
        "unexpected_argument_count": min(sum(name not in fields for name in arguments), 32000),
        "schema_sha256": schema_fingerprint(tool),
        "allowed_fields": sorted(fields),
        "required_fields": sorted(name for name, field in fields.items() if field.is_required()),
    }


def _fields(value, known):
    return (
        sorted({name for name in value if isinstance(name, str) and name in known})
        if isinstance(value, list)
        else []
    )


def public_tool_diagnostics(value):
    """Revalidate stored evidence before export; never trust arbitrary JSON keys."""
    if not isinstance(value, list):
        return []
    result = []
    for row in value[-MAX_CALLS:]:
        if not isinstance(row, dict):
            continue
        tool = row.get("tool")
        index = row.get("call_index")
        if (
            not isinstance(tool, str)
            or tool not in SCHEMAS
            or type(index) is not int
            or not 1 <= index <= 32000
        ):
            continue
        if row.get("status") not in ("succeeded", "failed"):
            continue
        known = SCHEMAS[tool].model_fields
        safe = {"call_index": index, "tool": tool, "status": row["status"]}
        digest = row.get("schema_sha256")
        if isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest):
            safe["schema_sha256"] = digest
        if row.get("schema_source") in ("runtime", "current_registry"):
            safe["schema_source"] = row["schema_source"]
        for key in ("allowed_fields", "required_fields"):
            if isinstance(row.get(key), list):
                safe[key] = _fields(row[key], known)
        types = row.get("argument_types")
        if isinstance(types, dict):
            safe["argument_types"] = _argument_types(types, known)
        unexpected_types = row.get("unexpected_known_argument_types")
        if isinstance(unexpected_types, dict):
            safe["unexpected_known_argument_types"] = _argument_types(
                unexpected_types, _registry_fields() - known.keys()
            )
        count = row.get("unexpected_argument_count")
        if type(count) is int and count >= 0:
            safe["unexpected_argument_count"] = min(count, 32000)
        for key, allowed in (("error_type", ERROR_TYPES), ("code", ERROR_CODES)):
            item = row.get(key)
            if isinstance(item, str) and item in allowed:
                safe[key] = item
        issues = []
        values = row.get("validation_issues", [])
        for issue in values[:8] if isinstance(values, list) else []:
            if (
                not isinstance(issue, dict)
                or not isinstance(issue.get("code"), str)
                or issue["code"] not in VALIDATION_ISSUE_CODES
            ):
                continue
            location = []
            raw = issue.get("location")
            for number, item in enumerate(raw[:3] if isinstance(raw, list) else []):
                if number == 0 and isinstance(item, str) and item in known:
                    location.append(item)
                elif number == 0 and item in ("<unexpected>", "<arguments>"):
                    location.append(item)
                    break
                elif location and type(item) is int:
                    location.append(min(max(item, 0), 40))
                else:
                    location.append("<unexpected>")
                    break
            issues.append({"location": location or ["<arguments>"], "code": issue["code"]})
        if issues:
            safe["validation_issues"] = issues
        result.append(safe)
    return result


def tool_diagnostics(events):
    """Correlate completed calls, retaining the last16 with original call ordinals."""
    requests, rows, ordinal = {}, [], 0
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("data"), dict):
            continue
        data = event["data"]
        identity = data.get("execution_id")
        if event.get("kind") == "tool.requested":
            ordinal += 1
            if isinstance(identity, str) and 0 < len(identity) <= 128:
                requests.setdefault(identity, (ordinal, data))
            continue
        if event.get("kind") != "tool.result" or not isinstance(identity, str) or identity not in requests:
            continue
        index, request = requests.pop(identity)
        tool = request.get("tool")
        if not isinstance(tool, str) or tool not in SCHEMAS or data.get("tool") != tool:
            continue
        digest = request.get("schema_sha256")
        captured = isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest) is not None
        row = {
            "call_index": index,
            "tool": tool,
            "status": data.get("status"),
            "schema_sha256": digest if captured else schema_fingerprint(tool),
            "schema_source": "runtime" if captured else "current_registry",
        }
        # Metadata absent from legacy events stays absent; it must not imply zero bad fields.
        for key in (
            "argument_types",
            "unexpected_known_argument_types",
            "unexpected_argument_count",
            "allowed_fields",
            "required_fields",
        ):
            if key in request:
                row[key] = request[key]
        for key in ("validation_issues", "error_type", "code"):
            if key in data:
                row[key] = data[key]
        rows.append(row)
    return public_tool_diagnostics(rows)
