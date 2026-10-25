"""Packaged regressions for completion and Ollama controls; no external requests."""

from contextlib import closing
import json
from pathlib import Path
import tempfile
import threading

import httpx

from .models import Agent, Profile, Reply, ToolCall
from .providers import Provider, ProviderError
from .store import Store
from .test_suite import baseline_files, run_suite


def completion_order_check(credentials):
    content = baseline_files("noop")["output.txt"].decode()

    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, model, messages, tools):
            count = sum(m["role"] == "tool" for m in messages)
            correction = any(
                "Application verification" in m.get("content", "") for m in messages if m["role"] == "user"
            )
            if count == 0 or count == 2 and correction:
                return Reply(calls=[ToolCall(id="read", name="read_file", arguments={"path": "output.txt"})])
            if count == 1:
                return Reply(
                    calls=[
                        ToolCall(
                            id="same",
                            name="write_file",
                            arguments={
                                "path": "output.txt",
                                "content": content,
                                "expected_sha256": "last_read",
                            },
                        )
                    ]
                )
            return Reply(content="Recorded synthetic completion")

    with tempfile.TemporaryDirectory(prefix="aigentics-completion-check-") as directory:
        with closing(Store(Path(directory) / "fixture.sqlite3", credentials)) as store:
            store.save_profile(Profile(id="ollama", name="Synthetic offline fixture"))
            row = run_suite(
                store,
                credentials,
                Agent(),
                threading.Event(),
                lambda e: None,
                provider_factory=Fixture,
                case_ids=["noop"],
                persist=False,
                completion_feedback=True,
            )["checks"][0]
            evidence = row["evidence"]
            if not (
                row["status"] == "passed"
                and evidence["completion_feedback_count"] == 1
                and evidence["execution_counts"]["unchanged_writes"] == 1
                and evidence["execution_counts"]["writes_verified"] == 0
            ):
                raise AssertionError("Completion-order fixture did not enforce the final read")
    return {"completion_order_fixture_verified": True, "external_requests": 0}


def thinking_control_check(credentials):
    calls = []

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
        if request.url.path == "/api/chat":
            body = json.loads(request.content)
            if body.get("think") is not False or "num_ctx" in body["options"]:
                raise AssertionError("Thinking or context payload mismatch")
            return httpx.Response(200, json={"message": {"content": "Synthetic"}, "done_reason": "stop"})
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.18.0"})
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": [{"name": "fixture:latest", "context_length": 8192}]})
        raise AssertionError("Unexpected fixture request")

    profile = Profile(id="fixture", name="Synthetic", ollama_thinking="off")
    provider = Provider(profile, credentials, httpx.MockTransport(handler))
    provider.chat("fixture", [{"role": "user", "content": "Synthetic"}], [], max_output_tokens=16)
    observation = provider.observe_server("fixture")
    if observation.get("context_length") != 8192 or calls != [
        "/api/show",
        "/api/chat",
        "/api/version",
        "/api/ps",
    ]:
        raise AssertionError("Ollama metadata fixture mismatch")
    refused = []

    def unsupported(request):
        refused.append(request.url.path)
        return httpx.Response(200, json={"capabilities": ["tools"]})

    try:
        Provider(profile, credentials, httpx.MockTransport(unsupported)).chat("fixture", [], [])
    except ProviderError as error:
        if error.code != "THINKING_CONTROL_UNAVAILABLE" or refused != ["/api/show"]:
            raise AssertionError("Unsupported thinking control was dispatched") from None
    else:
        raise AssertionError("Unsupported thinking control was accepted")
    return {
        "thinking_controls_fixture_verified": True,
        "unsupported_control_blocked": True,
        "context_override_sent": False,
        "external_requests": 0,
    }
