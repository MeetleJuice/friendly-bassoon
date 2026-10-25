"""Bounded, reviewed diagnostic archives. Never upload or package the data directory."""

import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile
from uuid import UUID

from . import __version__
from .reporting import public_report, public_shape
from .test_suite import bounded_tool_timeline

MAX_BUNDLE_BYTES = 3_000_000
MAX_BUNDLE_UNCOMPRESSED_BYTES = 8_000_000


def clean_report(report, credentials):
    if report.get("kind") not in ("crew_campaign", "health"):
        raise ValueError("Select a campaign or app-health report for ZIP export")
    try:
        safe = public_report(report, include_model=False)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Report format is incomplete or invalid; choose another saved report") from exc
    safe = {
        k: v
        for k, v in safe.items()
        if k
        in (
            "schema_version",
            "suite_version",
            "kind",
            "id",
            "created",
            "app_version",
            "state",
            "environment",
            "checks",
            "planned_cases",
            "mode",
            "crew_version",
            "stop_reason",
            "budget_used_ms",
            "duration_ms",
            "manifest_id",
            "manifest_verified",
            "track",
        )
    }
    safe["schema_version"] = 1
    scope = report.get("local_scope")
    if isinstance(scope, str) and re.fullmatch(r"[a-f0-9]{64}", scope):
        safe["configuration_sha256"] = scope
    for key in ("duration_ms", "budget_used_ms"):
        if key in safe and (type(safe[key]) is not int or safe[key] < 0):
            safe.pop(key)

    try:
        safe["id"] = str(UUID(str(safe.get("id"))))
    except ValueError:
        raise ValueError("Report identifier is invalid") from None
    patterns = {
        "app_version": r"\d+\.\d+\.\d+",
        "suite_version": r"(?:crew-campaign-\d+|\d+)",
        "created": r"\d{4}-\d{2}-\d{2}T[0-9:.+-]+(?:Z)?",
    }
    for key in ("app_version", "suite_version", "created"):
        value = safe.get(key, "")
        if not isinstance(value, str) or (len(value) > 64 or not re.fullmatch(patterns[key], value)):
            safe[key] = "unknown"
    safe["environment"] = {
        k: v
        for k, v in safe.get("environment", {}).items()
        if k in ("os", "os_release", "architecture", "python")
        and isinstance(v, str)
        and re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", v)
    }
    if safe.get("state") not in (
        "running",
        "interrupted",
        "cancelled",
        "passed",
        "needs_attention",
        "failed",
    ):
        safe["state"] = "unknown"
    # Original reports may contain local configuration; only extend the public
    # allowlist with bounded numeric trace structure and argument-free actions.
    originals = {r.get("id"): r for r in report.get("checks", [])}
    for row in safe["checks"]:
        row["message"] = "Application-owned diagnostic criteria"
        if report["kind"] == "health":
            identity = row.get("id", "")
            allowed = {
                "database",
                "definitions",
                "file_boundaries",
                "permission_denial",
                "file_write_read_and_stale_edit",
                "cancellation",
                "command_execution",
                "command_timeout",
                "redaction",
                "provider_protocol_fixtures",
                "text_tool_regression",
                "native_agent_workflow",
                "model_catalog_fixture",
                "report_retention_fixture",
                "tool_registry_fixture",
                "project_retrieval_fixture",
                "native_probe_fixture",
                "python_check_fixture",
                "revision_fixture",
                "task_checks_fixture",
                "empty_final_fixture",
                "validation_recovery_fixture",
                "checkpoint_recovery_fixture",
                "crew_evaluation_fixture",
                "correctness_fixture",
                "update_connection",
                "selected_local_model",
            }
            if identity not in allowed:
                raise ValueError("Unknown health check identifier")
            row["code"] = row["code"] if row["code"] in ("OK", identity.upper() + "_FAILED") else "UNKNOWN"
            row["evidence"] = {
                k: v
                for k, v in row.get("evidence", {}).items()
                if type(v) in (bool, int) and (type(v) is bool or 0 <= v <= 10**15)
            }
            continue
        original = originals.get(row["id"], {}).get("evidence", {})
        traces = []
        for trace in original.get("request_traces", [])[:8]:
            entry = {
                k: min(v, 10**15)
                for k, v in trace.items()
                if k
                in (
                    "step",
                    "duration_ms",
                    "native_call_count",
                    "content_chars",
                    "advertised_tool_count",
                    "request_chars",
                    "tool_schema_chars",
                )
                and type(v) is int
                and v >= 0
            }
            entry["response_shape"] = public_shape(trace.get("response_shape", {}))
            entry["usage"] = {
                k: min(v, 10**15)
                for k, v in trace.get("usage", {}).items()
                if k in ("prompt_eval_count", "eval_count", "total_duration") and type(v) is int and v >= 0
            }
            traces.append(entry)
        row["evidence"]["request_traces"] = traces
        row["evidence"]["tool_timeline"] = bounded_tool_timeline(original.get("tool_timeline", []))
    if report.get("mode") == "measurement":
        from .measurement import measurement_manifest, manifest_id, summarize_trials

        expected = measurement_manifest()
        if report.get("measurement_manifest") == expected and report.get("manifest_id") == manifest_id(
            expected
        ):
            safe["measurement_manifest"] = expected
        safe["measurement_summary"] = summarize_trials(safe["checks"])
    return credentials.scrub(safe)


def build_bundle(reports, credentials):
    if not 1 <= len(reports) <= 2:
        raise ValueError("Select one or two diagnostic reports")
    files, index = {}, []
    for number, report in enumerate(reports, 1):
        safe = clean_report(report, credentials)
        name = f"reports/{number:02d}.json"
        raw = json.dumps(safe, indent=2, ensure_ascii=True).encode()
        files[name] = raw
        index.append(
            {
                "file": name,
                "report_id": safe["id"],
                "state": safe.get("state"),
                "recorded_cases": len(safe["checks"]),
                "planned_cases": safe.get("planned_cases"),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    files["README.txt"] = (
        "Aigentics diagnostic bundle v1\nLocal export; no automatic upload.\n"
        "Includes sanitized results, bounded numeric request traces, correctness checks and argument-free tool timelines.\n"
        "Excludes credentials, environment files, private project content/paths, private prompts, raw thinking and local connection configuration.\n"
        "Measurement bundles include the application-owned synthetic benchmark definition when it matches the current manifest.\n"
        "Partial reports are useful. Recorded cases do not prove all planned cases completed.\n"
        "An unsaved attempt cannot be reconstructed; interrupted attempts are never silently replayed.\n"
        "Usage is known-only, not a complete billing total. Model names are omitted.\n"
        "Reports are independent timestamped records; inclusion does not establish a shared run.\n"
    ).encode()
    manifest = {
        "bundle_schema": 1,
        "exporter_app_version": __version__,
        "reports": index,
        "files": [
            {"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in files.items()
        ],
    }
    files["manifest.json"] = json.dumps(manifest, indent=2).encode()
    if sum(map(len, files.values())) > MAX_BUNDLE_UNCOMPRESSED_BYTES:
        raise ValueError("Diagnostic bundle exceeds its 8 MB uncompressed limit")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    raw = stream.getvalue()
    if len(raw) > MAX_BUNDLE_BYTES:
        raise ValueError("Diagnostic ZIP exceeds its size limit")
    preview = "\n\n".join(n + "\n" + b.decode() for n, b in files.items())
    return raw, preview


def save_bundle(path, data):
    """Write precisely the approved bytes, replacing a destination atomically."""
    destination = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
