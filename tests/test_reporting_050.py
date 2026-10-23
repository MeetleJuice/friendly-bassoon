import json
import platform
from urllib.parse import parse_qs, urlsplit

import pytest

from aigentics.catalog import CatalogRunner
from aigentics.diagnostics import safe_recent_summary
from aigentics.models import Agent, Profile
from aigentics.reporting import issue_body, prepare_browser_draft, public_report


def report_fixture(kind="tool_probe"):
    return {
        "schema_version": 1,
        "suite_version": "tool-probe-1",
        "kind": kind,
        "id": "synthetic-report-050",
        "created": "2026-10-23T00:00:00+00:00",
        "app_version": "0.5.0",
        "state": "needs_attention",
        "environment": {"os": "SyntheticOS", "os_release": "1", "architecture": "test", "python": "3.12"},
        "checks": [],
    }


def check_fixture(identity="selected_model_probe", **evidence):
    return {
        "id": identity,
        "status": "failed",
        "code": "PROBE_NOT_VERIFIED",
        "message": "Synthetic native tool-call probe was not verified.",
        "duration_ms": 1,
        "evidence": evidence,
    }


@pytest.mark.parametrize("recent", [None, [], "private-record", {}, {"states": [], "tool_error_types": None}])
def test_recent_counts_have_typed_defaults(recent):
    report = report_fixture()
    report["recent_runs"] = recent
    counts = public_report(report)["recent_runs"]
    assert counts == {
        "states": {},
        "tool_error_types": {},
        "runtime_error_codes": {},
        "runtime_error_types": {},
        "failure_stages": {},
        "protocol_failures": 0,
        "legacy_text_tool_responses": 0,
        "execution_counts": {},
        "tool_error_codes": {},
        "user_assessments": {},
    }
    assert type(counts["protocol_failures"]) is int
    assert type(counts["legacy_text_tool_responses"]) is int


def test_public_recent_counts_reject_private_keys_and_invalid_values():
    report = report_fixture()
    report["recent_runs"] = {
        "states": {"failed": 2000, "completed": True, "cancelled": -1, "PrivateSessionIdentifier": 1},
        "tool_error_types": {"ValueError": 2, "TypeError": False, "PrivateCustomerSecret": 1},
        "runtime_error_codes": {"HTTP_ERROR": 1, "TIMEOUT": -1, "PRIVATE_SECRET_CODE": 1},
        "runtime_error_types": {"ProviderError": 1, "TypeError": "1", "PrivateClassName": 1},
        "failure_stages": {"provider": 1, "runtime": True, "/private/workspace": 1},
        "protocol_failures": True,
        "legacy_text_tool_responses": -1,
        "session_ids": ["PrivateSessionIdentifier"],
    }
    counts = public_report(report)["recent_runs"]
    assert counts == {
        "states": {"failed": 20},
        "tool_error_types": {"ValueError": 2},
        "runtime_error_codes": {"HTTP_ERROR": 1},
        "runtime_error_types": {"ProviderError": 1},
        "failure_stages": {"provider": 1},
        "protocol_failures": 0,
        "legacy_text_tool_responses": 0,
        "execution_counts": {},
        "tool_error_codes": {},
        "user_assessments": {},
    }


def test_recent_failures_count_sessions_once_and_exclude_successful_fallback(store, tmp_path):
    failed = store.start(Agent(name="PrivateAgentName"), tmp_path / "private-project", capture=True)
    store.messages(
        failed,
        [
            {"role": "user", "content": "PrivatePromptText"},
            {"role": "assistant", "content": '{"name":"list_files","arguments":{"path":"private"}}'},
        ],
    )
    for _ in range(2):
        store.event(
            failed,
            "provider.failed",
            {"code": "HTTP_ERROR", "error": "PrivateProviderError", "profile": "PrivateProfileId"},
        )
        store.event(
            failed,
            "runtime.error",
            {"type": "ProviderError", "code": "HTTP_ERROR", "message": "PrivateRuntimeMessage"},
        )
    store.event(failed, "runtime.error", {"type": "PrivateErrorClass", "code": "PRIVATE_ERROR_CODE"})
    store.event(
        failed,
        "tool.result",
        {"status": "failed", "error_type": "PrivateToolErrorClass", "error": "PrivateToolMessage"},
    )
    store.event(failed, "protocol.invalid_response", {"content": "PrivateModelResponse"})
    store.finish(failed, "failed", "PrivateOutcomeText")

    completed = store.start(Agent(), tmp_path)
    store.event(completed, "provider.failed", {"code": "TIMEOUT", "error": "PrivateRecoveredError"})
    store.finish(completed, "completed", "Fallback succeeded")

    counts = safe_recent_summary(store)
    assert counts["states"] == {"completed": 1, "failed": 1}
    assert counts["runtime_error_codes"] == {"HTTP_ERROR": 1, "UNKNOWN_ERROR": 1}
    assert counts["runtime_error_types"] == {"ProviderError": 1, "OtherError": 1}
    assert counts["failure_stages"] == {"provider": 1, "runtime": 1}
    assert counts["tool_error_types"] == {"OtherError": 1}
    assert counts["protocol_failures"] == 1
    assert counts["legacy_text_tool_responses"] == 1
    encoded = json.dumps(counts)
    assert "Private" not in encoded and "PRIVATE" not in encoded
    assert failed not in encoded and completed not in encoded and str(tmp_path) not in encoded


def test_recent_failure_counters_are_limited_to_twenty_sessions():
    class ManySessions:
        def assessment(self, sid):
            return None

        def sessions(self):
            return [{"id": str(index), "state": "protocol_error"} for index in range(25)]

        def messages(self, sid):
            return []

        def events(self, sid):
            return [
                {
                    "kind": "runtime.error",
                    "data": {"type": "NativeToolProtocolError", "code": "NATIVE_TOOL_PROTOCOL"},
                }
            ] * 3

    counts = safe_recent_summary(ManySessions())
    assert counts["limit"] == 20
    assert counts["states"] == {"protocol_error": 20}
    assert counts["runtime_error_codes"] == {"NATIVE_TOOL_PROTOCOL": 20}
    assert counts["runtime_error_types"] == {"NativeToolProtocolError": 20}
    assert counts["failure_stages"] == {"native_protocol": 20}


def test_tool_probe_title_and_evidence_are_allowlisted_and_model_opt_in(credentials):
    evidence = {
        "provider": "ollama",
        "model": "private-selected-model",
        "route": "native",
        "stream": True,
        "http_status": 200,
        "native_calls_total": 1,
        "challenge_verified": True,
        "generation_requests": 1,
        "max_output_tokens": 128,
        "finish_reason": "tool_calls",
        "tool_calls_field_present": True,
        "text_tool_response": False,
        "provider_error_code": "NONE",
        "probe_fixture_verified": True,
        "project_retrieval_fixture_verified": True,
        "registry_fixture_verified": True,
    }
    report = report_fixture()
    report["checks"] = [
        check_fixture(**evidence, challenge="PrivateChallenge", prompt="PrivatePrompt", path="/private/file")
    ]
    safe = public_report(report)
    assert safe["checks"][0]["evidence"] == {key: value for key, value in evidence.items() if key != "model"}
    assert public_report(report, include_model=True)["checks"][0]["evidence"] == evidence
    title, body = issue_body(report, credentials)
    assert title == "Aigentics tool-call probe 0.5.0: needs_attention"
    assert "private-selected-model" not in body and "Private" not in body and "/private/file" not in body


def test_compact_browser_draft_keeps_probe_api_and_failure_evidence(credentials):
    report = report_fixture()
    api = check_fixture(
        "api_1", provider="custom_openai", http_status=206, request_count=1, generation_requests=0
    )
    probe_evidence = {
        "provider": "ollama",
        "route": "native",
        "stream": False,
        "http_status": 200,
        "native_calls_total": 0,
        "challenge_verified": False,
        "generation_requests": 1,
        "max_output_tokens": 128,
        "finish_reason": "stop",
        "tool_calls_field_present": False,
        "text_tool_response": True,
        "provider_error_code": "NONE",
    }
    probes = [
        check_fixture(identity, **(probe_evidence | {"route": route, "stream": stream}))
        for identity, route, stream in (
            ("native_tool_probe", "native", False),
            ("native_stream_tool_probe", "native", True),
            ("compatible_tool_probe", "compatible", False),
            ("compatible_stream_tool_probe", "compatible", True),
        )
    ]
    for check in [api, *probes]:
        check["message"] += " Synthetic details." * 300
    report["checks"] = [api, *probes]
    report["recent_runs"] = {
        "runtime_error_codes": {"HTTP_ERROR": 2},
        "runtime_error_types": {"ProviderError": 2},
        "failure_stages": {"provider": 2},
    }
    title, body = issue_body(report, credentials)
    url = prepare_browser_draft(title, body)
    assert len(url) <= 7500
    compact = parse_qs(urlsplit(url).query)["body"][0]
    assert "Full report retained locally" in compact and report["id"] in compact
    check_line = next(line for line in compact.splitlines() if line.startswith("Check evidence: "))
    checks = json.loads(check_line.removeprefix("Check evidence: "))
    assert checks["api_1"] == api["evidence"]
    for probe in probes:
        assert checks[probe["id"]] == probe["evidence"]
    counts_line = next(line for line in compact.splitlines() if line.startswith("Recent run counts: "))
    counts = json.loads(counts_line.removeprefix("Recent run counts: "))
    assert counts["runtime_error_codes"] == {"HTTP_ERROR": 2}
    assert counts["runtime_error_types"] == {"ProviderError": 2}
    assert counts["failure_stages"] == {"provider": 2}


def test_catalog_report_records_actual_environment_and_success_status(store, credentials):
    store.save_profile(Profile(id="synthetic", name="Synthetic provider"))
    calls = []

    class MetadataProvider:
        last_http_status = 206

        def __init__(self, profile, credentials):
            pass

        def discover(self):
            calls.append("GET metadata")
            return ["synthetic-model"]

    report = CatalogRunner(store, credentials, MetadataProvider).run()
    assert calls == ["GET metadata"]
    assert report["environment"] == {
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
    }
    assert report["checks"][0]["evidence"]["http_status"] == 206
    assert report["checks"][0]["evidence"]["generation_requests"] == 0
    assert public_report(report)["environment"] == report["environment"]


def test_public_model_traces_keep_stream_and_validated_parser_metadata(credentials):
    report = report_fixture("health")
    metadata = {
        "tools": True,
        "source": "ollama /api/show",
        "parser": "qwen3",
        "renderer": "qwen3",
        "template_source": "model",
        "raw_template": "PrivateTemplateText",
    }
    report["checks"] = [
        check_fixture(
            "selected_local_model",
            model_metadata=metadata,
            request_traces=[
                {
                    "step": number,
                    "native_call_count": 0,
                    "text_tool_response": True,
                    "response_shape": {
                        "stream": True,
                        "tool_calls_field_present": False,
                        "finish_reason": "stop",
                    },
                }
                for number in range(1, 5)
            ],
        )
    ]
    report["checks"][0]["message"] += " Synthetic details." * 400
    safe = public_report(report)["checks"][0]["evidence"]
    assert safe["model_metadata"] == {key: value for key, value in metadata.items() if key != "raw_template"}
    assert all(row["response_shape"]["stream"] is True for row in safe["request_traces"])
    title, body = issue_body(report, credentials)
    compact = parse_qs(urlsplit(prepare_browser_draft(title, body)).query)["body"][0]
    assert '"stream":true' in compact
    assert "PrivateTemplateText" not in compact


def test_browser_sharing_hides_token_controls_and_switching_revokes_approval(qtbot, store, credentials):
    from aigentics.diagnostics_ui import DiagnosticsDialog
    from aigentics.ui import Window

    window = Window(store, credentials)
    qtbot.addWidget(window)
    dialog = DiagnosticsDialog(window, prompts=False)
    qtbot.addWidget(dialog)
    dialog.report = report_fixture()
    dialog.review()
    dialog.show()
    controls = (dialog.token_label, dialog.token_ref, dialog.token_hint)
    assert dialog.method.currentData() == "browser"
    assert all(control.isHidden() and not control.isEnabled() for control in controls)

    dialog.approved.setChecked(True)
    dialog.method.setCurrentIndex(dialog.method.findData("api"))
    assert all(not control.isHidden() and control.isEnabled() for control in controls)
    assert not dialog.approved.isChecked() and not dialog.send.isEnabled()
    assert store.setting("github_report_method", None) == "api"

    dialog.approved.setChecked(True)
    dialog.method.setCurrentIndex(dialog.method.findData("browser"))
    assert all(control.isHidden() and not control.isEnabled() for control in controls)
    assert not dialog.approved.isChecked() and not dialog.send.isEnabled()
    window.lab_dir.cleanup()
    window.store.close = lambda: None
