"""Model-advertised thinking controls, exact requests and private metadata bounds."""

import json
import threading
import httpx
import pytest
from pydantic import ValidationError

from aigentics.models import Agent, Profile
from aigentics.providers import Provider, ProviderError
from aigentics.runtime import Runtime
from aigentics.ollama_settings import thinking_metadata, thinking_experiment_available, public_observation


@pytest.mark.parametrize(
    "value,available",
    [
        (None, False),
        ({"values": [False, True], "default": True}, True),
        ({"values": [False], "default": False}, False),
        ({"values": [False, True], "default": False}, False),
        ({"values": ["low", "medium", "high"], "default": "medium"}, False),
        ({"values": [False, "medium"], "default": "medium"}, True),
        ({"values": [0, 1], "default": 1}, False),
        ({"values": [False, True, "PRIVATE"], "default": True}, False),
        ({"values": [False, False], "default": False}, False),
        ({"values": [False, True]}, False),
        ({"values": []}, False),
    ],
)
def test_only_explicit_active_default_and_false_support_enable_comparison(value, available):
    metadata = thinking_metadata(value)
    assert thinking_experiment_available(metadata) is available
    assert "PRIVATE" not in json.dumps(metadata)


@pytest.mark.parametrize("mode", ["default", "on", "off"])
@pytest.mark.parametrize("streaming", [False, True])
def test_native_request_places_verified_control_at_top_level_without_context_override(
    credentials, mode, streaming
):
    calls, bodies = [], []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/api/show":
            return httpx.Response(
                200,
                json={
                    "capabilities": ["tools", "thinking"],
                    "thinking": {"values": [False, True], "default": True},
                },
            )
        body = json.loads(request.content)
        bodies.append(body)
        response = {
            "message": {"role": "assistant", "content": "done"},
            "done": True,
            "done_reason": "stop",
            "load_duration": 1234,
            "eval_duration": 4321,
        }
        return httpx.Response(200, content=(json.dumps(response) + "\n").encode())

    profile = Profile(id="fixture", name="Local", ollama_thinking=mode, ollama_stream=streaming)
    reply = Provider(profile, credentials, httpx.MockTransport(handler)).chat(
        "fixture", [], [], max_output_tokens=64
    )
    body = bodies[0]
    assert body["options"] == {"temperature": 0.2, "num_predict": 64}
    assert "num_ctx" not in body["options"] and "keep_alive" not in body
    assert ("think" in body) is (mode != "default")
    if mode != "default":
        assert body["think"] is (mode == "on")
    assert calls == (["/api/chat"] if mode == "default" else ["/api/show", "/api/chat"])
    assert reply.usage["load_duration"] == 1234 and reply.usage["eval_duration"] == 4321


@pytest.mark.parametrize(
    "metadata",
    [None, {"values": ["low", "medium", "high"], "default": "medium"}, {"values": [True], "default": True}],
)
def test_unverified_off_blocks_before_generation(credentials, metadata):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"capabilities": ["tools"], "thinking": metadata})

    provider = Provider(
        Profile(id="fixture", name="Local", ollama_thinking="off"), credentials, httpx.MockTransport(handler)
    )
    with pytest.raises(ProviderError) as raised:
        provider.chat("fixture", [], [])
    assert raised.value.code == "THINKING_CONTROL_UNAVAILABLE"
    assert calls == ["/api/show"]


@pytest.mark.parametrize("overrides", [{"kind": "openai"}, {"ollama_api": "compatible"}])
def test_explicit_controls_cannot_silently_move_to_other_routes(overrides):
    with pytest.raises(ValidationError):
        Profile(id="fixture", name="Local", ollama_thinking="off", **overrides)


def test_runtime_reuses_verified_capabilities_without_extra_show_per_turn(store, credentials, tmp_path):
    calls = []
    store.save_profile(Profile(id="ollama", name="Local", ollama_thinking="off"))

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/api/show":
            return httpx.Response(
                200,
                json={
                    "capabilities": ["tools", "thinking"],
                    "thinking": {"values": [False, True], "default": True},
                },
            )
        body = json.loads(request.content)
        assert body["think"] is False
        message = (
            {"content": "done"}
            if any(m["role"] == "tool" for m in body["messages"])
            else {"tool_calls": [{"function": {"name": "list_files", "arguments": {}}}]}
        )
        return httpx.Response(200, json={"message": message, "done_reason": "stop"})

    def factory(profile, keys):
        return Provider(profile, keys, httpx.MockTransport(handler))

    sid, state = Runtime(store, credentials, factory).run(
        Agent(tools=["list_files"]), tmp_path, "List files", lambda *a: True
    )
    assert state == "completed"
    assert calls == ["/api/show", "/api/chat", "/api/chat"]
    assert all(
        e["data"]["thinking_mode"] == "off" for e in store.events(sid) if e["kind"] == "model.requested"
    )


def test_context_observation_reports_actual_loaded_context_without_names(credentials):
    def handler(request):
        return httpx.Response(
            200,
            json={"version": "0.18.1"}
            if request.url.path == "/api/version"
            else {
                "models": [
                    {"name": "fixture:latest", "context_length": 8192},
                    {"name": "PRIVATE", "context_length": 32768},
                ]
            },
        )

    provider = Provider(
        Profile(id="local", name="Local", timeout_seconds=3), credentials, httpx.MockTransport(handler)
    )
    result = provider.observe_server("fixture")
    assert result["context_length"] == 8192 and result["loaded_models"] == 2
    assert result["server_version"] == "0.18.1" and result["scope"] == "campaign_end"
    assert "PRIVATE" not in json.dumps(result) and "fixture" not in json.dumps(result)
    assert "PRIVATE" not in json.dumps(
        public_observation({"server_version": "PRIVATE", "context_length": True, "loaded_models": -1})
    )


def test_unknown_capability_skips_only_explicit_off_trials_without_changing_saved_profile(store, credentials):
    from aigentics.campaign import run_campaign
    from test_campaign_0120 import CrewScripted

    store.save_profile(Profile(id="ollama", name="Local"))
    before = store.profiles()[0].model_dump()
    seen = []

    class Unknown(CrewScripted):
        def __init__(self, profile, *args):
            self.mode = profile.ollama_thinking
            super().__init__(profile, *args)

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, *args):
            seen.append(self.mode)
            return super().chat(*args)

    report = run_campaign(
        store,
        credentials,
        Agent(),
        threading.Event(),
        lambda e: None,
        mode="measurement",
        provider_factory=Unknown,
    )[1]
    assert report["planned_cases"] == 64 and report["summary"]["passed"] == 33
    skipped = [r for r in report["checks"] if r["status"] == "skipped"]
    assert len(skipped) == 31 and all(r["code"] == "THINKING_CONTROL_UNAVAILABLE" for r in skipped)
    assert "off" not in seen and store.profiles()[0].model_dump() == before


def test_thinking_ui_selection_saves_only_the_profile_and_never_runs_a_model(qtbot, store, credentials):
    from aigentics.ui import Window
    from test_campaign_ui_0120 import cleanup

    window = Window(store, credentials)
    qtbot.addWidget(window, before_close_func=cleanup)
    original = store.agents()[0].model_dump()
    window.thinking_selector.setCurrentIndex(window.thinking_selector.findData("off"))
    assert json.loads(window.profile_json.toPlainText())["ollama_thinking"] == "off"
    window.save_profile()
    assert store.profiles()[0].ollama_thinking == "off"
    assert store.agents()[0].model_dump() == original
    assert window.worker is None and not store.sessions()


def test_safe_thinking_and_context_metadata_survive_zip_without_private_fields(credentials):
    from aigentics.bundles import build_bundle
    from aigentics.evidence import base_report
    from aigentics.measurement import measurement_plan
    import io
    import zipfile

    report = base_report("crew_campaign", "crew-campaign-5", "PRIVATE")
    report.update(
        mode="measurement",
        thinking_comparison={
            "thinking_support": "reported",
            "thinking_values": [False, True],
            "thinking_default": True,
            "eligible": True,
            "PRIVATE": "PRIVATE",
        },
        ollama_observation={
            "context_length": 8192,
            "server_version": "0.18.1",
            "model": "PRIVATE",
            "status": "observed",
        },
    )
    report["checks"] = [
        {
            "id": measurement_plan()[9].id,
            "status": "passed",
            "code": "OK",
            "duration_ms": 5,
            "message": "PRIVATE",
            "evidence": {
                "thinking_mode": "off",
                "model_metadata": {
                    "thinking_support": "reported",
                    "thinking_values": [False, True],
                    "thinking_default": True,
                    "PRIVATE": "PRIVATE",
                },
                "request_traces": [
                    {
                        "thinking_mode": "off",
                        "usage": {"eval_count": 12, "load_duration": 100, "PRIVATE": "PRIVATE"},
                    }
                ],
            },
        }
    ]
    data, preview = build_bundle([report], credentials)
    assert "PRIVATE" not in preview
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        exported = json.loads(archive.read("reports/01.json"))
    assert exported["ollama_observation"]["context_length"] == 8192
    assert exported["thinking_comparison"]["thinking_values"] == [False, True]
    assert exported["checks"][0]["evidence"]["thinking_mode"] == "off"
    assert exported["checks"][0]["evidence"]["request_traces"][0]["usage"]["load_duration"] == 100


def test_thinking_pairs_require_verified_equal_controls_and_budgets():
    from copy import deepcopy
    from aigentics.measurement import thinking_pairs

    controls = {"thinking_support": "reported", "thinking_values": [False, True], "thinking_default": True}
    rows = [
        {
            "id": f"measure-unicode-{arm}-r1",
            "status": "passed",
            "code": "OK",
            "duration_ms": duration,
            "evidence": {
                "model_metadata": controls,
                "thinking_mode": mode,
                "max_output_tokens": 4096,
                "request_timeout_seconds": 120,
                "session_budget_seconds": 180,
            },
        }
        for arm, mode, duration in (("coordinated", "default", 100), ("thinking_off", "off", 60))
    ]
    assert thinking_pairs(rows)[0]["both_passed_duration_delta_ms"] == -40
    for field, value in (
        ("max_output_tokens", 1024),
        ("thinking_mode", "default"),
        ("model_metadata", {**controls, "thinking_default": False}),
    ):
        changed = deepcopy(rows)
        changed[1]["evidence"][field] = value
        result = thinking_pairs(changed)[0]
        assert result["eligible"] is False
        assert result["both_passed_duration_delta_ms"] is None
    rows[1]["status"] = "failed"
    assert thinking_pairs(rows)[0]["eligible"] is True
    assert thinking_pairs(rows)[0]["both_passed_duration_delta_ms"] is None


def test_cross_run_diff_refuses_changed_server_context_but_ignores_observer_cost():
    from copy import deepcopy
    from aigentics.measurement import paired_diff

    old = {
        "manifest_id": "a" * 64,
        "configuration_sha256": "b" * 64,
        "checks": [],
        "ollama_observation": {"context_length": 8192, "observer_duration_ms": 2},
    }
    new = deepcopy(old)
    new["ollama_observation"]["observer_duration_ms"] = 9
    assert paired_diff(old, new)["comparable"] is True
    new["ollama_observation"]["context_length"] = 4096
    assert paired_diff(old, new) == {"comparable": False, "reason": "observed_settings_mismatch"}
