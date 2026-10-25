"""Wire-level sampling, parser privacy, archived identities and evidence retention."""

import io
import json
import zipfile
import httpx
import pytest
from pydantic import ValidationError

from aigentics.models import Profile
from aigentics.providers import Provider
from aigentics.inference import sampling_options, public_sampling, public_run_details
from aigentics.contracts import parse_diagnostic, public_mismatches
from aigentics.measurement import measurement_plan, measurement_manifest, manifest_id, ARCHIVED_MANIFESTS


@pytest.mark.parametrize(
    "key,value",
    [
        ("temperature", -0.1),
        ("temperature", 2.1),
        ("temperature", float("nan")),
        ("temperature", float("inf")),
        ("temperature", True),
        ("top_p", 0),
        ("top_p", 1.1),
        ("top_p", "0.9"),
        ("top_k", 0),
        ("top_k", 1001),
        ("top_k", True),
        ("top_k", 2.0),
    ],
)
def test_invalid_sampling_rejected(key, value):
    with pytest.raises(ValidationError):
        Profile(id="local", name="Local", **{key: value})


@pytest.mark.parametrize("native", [True, False])
def test_requested_sampling_sent_on_actual_http_wire(native, credentials):
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(
            200,
            json={"message": {"content": "ok"}} if native else {"choices": [{"message": {"content": "ok"}}]},
        )

    profile = Profile(
        id="local",
        name="Local",
        ollama_api="native" if native else "compatible",
        temperature=0.7,
        top_p=0.9,
        top_k=30 if native else None,
    )
    Provider(profile, credentials, transport=httpx.MockTransport(handler)).chat(
        "fixture", [{"role": "user", "content": "test"}], []
    )
    options = seen[0]["options"] if native else seen[0]
    assert options["temperature"] == 0.7 and options["top_p"] == 0.9
    if native:
        assert options["top_k"] == 30 and options["num_predict"] == 4096
    assert "num_ctx" not in json.dumps(seen) and "keep_alive" not in json.dumps(seen)


def test_inherited_sampling_omitted_and_old_defaults_preserved(credentials):
    old = Profile.model_validate({"id": "local", "name": "Local"})
    assert sampling_options(old) == {"temperature": 0.2}
    assert sampling_options(old.model_copy(update={"temperature": None})) == {}
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "ok"}})

    Provider(
        old.model_copy(update={"temperature": None}), credentials, transport=httpx.MockTransport(handler)
    ).chat("fixture", [], [])
    assert seen[0]["options"] == {"num_predict": 4096}
    assert public_sampling({"temperature": True, "top_p": "PRIVATE", "SECRET": "PRIVATE"}) == {}


@pytest.mark.parametrize(
    "raw,reason",
    [
        ("{" + '"PRIVATE":}', "syntax"),
        ('{"PRIVATE":1,"PRIVATE":2}', "duplicate_key_or_nonfinite"),
        ('{"PRIVATE":NaN}', "duplicate_key_or_nonfinite"),
        (b"\xff", "encoding"),
    ],
)
def test_parser_reports_location_without_sensitive_error_text(raw, reason):
    result = parse_diagnostic(raw)
    assert result["reason"] == reason
    assert "PRIVATE" not in json.dumps(result)
    if reason == "syntax":
        assert result["line"] == 1 and result["column"] > 0
    safe = public_mismatches(
        [{"code": "JSON_PARSE", "target": "cases.json", "parser": result | {"secret": "PRIVATE"}}]
    )
    assert safe[0]["parser"]["reason"] == reason
    assert "PRIVATE" not in json.dumps(safe)


def test_all_role_mode_pairs_and_total_budget_workflows_are_predeclared():
    trials = measurement_plan()
    assert len(trials) == len({t.id for t in trials}) == 56
    assert len([t for t in trials if t.case_kind == "role" and t.arm == "thinking_off"]) == 18
    assert len([t for t in trials if t.case_kind == "workflow"]) == 4
    assert [t.case_id for t in trials[:4]] == [
        "scout_symbol",
        "scout_symbol",
        "vera_exclusive",
        "vera_exclusive",
    ]
    workflows = [t for t in trials if t.case_kind == "workflow"]
    assert all(t.budget == workflows[0].budget and t.thinking_mode == "off" for t in workflows)
    manifest = measurement_manifest()
    assert manifest["agent_definitions"]["orion"]["kind"] == "coordinator"
    assert manifest["team_pilot"]["max_total_calls"] == 12


def test_archived_manifests_keep_original_bytes_and_identities():
    from pathlib import Path

    for version, digest in ARCHIVED_MANIFESTS.items():
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "docs/benchmarks" / (version + ".json")).read_text(encoding="utf-8"))
        assert manifest_id(data) == digest
        assert len(measurement_plan(version)) == (30 if version.endswith("1") else 34)


def test_bundle_preserves_new_diagnostics_and_old_benchmark(store, credentials):
    from aigentics.evidence import base_report
    from aigentics.bundles import build_bundle
    from pathlib import Path

    for version in ("crew-measurement-2", "crew-measurement-3"):
        manifest = json.loads(
            (Path(__file__).resolve().parents[1] / "docs/benchmarks" / (version + ".json")).read_text(
                encoding="utf-8"
            )
        )
        report = base_report("crew_campaign", "crew-campaign-6", "Synthetic")
        report.update(
            mode="measurement",
            measurement_manifest=manifest,
            manifest_id=manifest_id(manifest),
            planned_cases=len(measurement_plan(version)),
            crew_version="midnight-crew-2",
        )
        report["checks"] = [
            {
                "id": "measure-vera_exclusive-reference-r1",
                "status": "failed",
                "code": "ROLE_REQUIREMENTS_NOT_MET",
                "duration_ms": 1,
                "message": "PRIVATE",
                "evidence": {
                    "terminal_response_status": "not_accepted",
                    "target_reads": [
                        {
                            "category": "output",
                            "ordinal": 1,
                            "after_latest_write": True,
                            "private_path": "PRIVATE",
                        }
                    ],
                    "request_traces": [{"sampling": {"temperature": 0.2, "PRIVATE": "PRIVATE"}}],
                    "mismatches": [
                        {
                            "code": "JSON_PARSE",
                            "target": "cases.json",
                            "parser": {"reason": "syntax", "line": 1, "column": 2},
                        }
                    ],
                },
            }
        ]
        data, preview = build_bundle([report], credentials)
        assert "PRIVATE" not in preview
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            exported = json.loads(archive.read("reports/01.json"))
        assert exported["measurement_manifest"] == manifest
        assert exported["crew_version"] == "midnight-crew-2"
        evidence = exported["checks"][0]["evidence"]
        assert evidence["terminal_response_status"] == "not_accepted"
        assert evidence["target_reads"][0]["ordinal"] == 1
        assert evidence["request_traces"][0]["sampling"] == {"temperature": 0.2}
        assert evidence["mismatches"][0]["parser"]["line"] == 1


def test_untrusted_new_evidence_stays_allowlisted():
    safe = public_run_details(
        {
            "terminal_response_status": "PRIVATE",
            "target_reads": [{"category": "PRIVATE", "ordinal": True, "after_latest_write": True}],
            "team_metrics": {"dispatches": -1, "managed": "PRIVATE", "PRIVATE": "PRIVATE"},
        }
    )
    assert safe == {"target_reads": [], "team_metrics": {}}
