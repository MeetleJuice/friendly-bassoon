"""Explicit one-call native-tool certification; no project or host tool execution."""

import platform
import json
import secrets
import threading
import time
from uuid import uuid4
from . import __version__
from .catalog import provider_label
from .providers import Provider, ProviderError
from .runtime import cancellable_call, looks_like_text_tool_call
from .store import now, Store


def probe_text(text):
    if looks_like_text_tool_call(text):
        return True
    value = text.strip()
    if value.startswith("```json\n") and value.endswith("\n```"):
        value = value[8:-4]
    try:
        payload = json.loads(value)
        if isinstance(payload, dict):
            payload = payload.get("function", payload)
            return (
                isinstance(payload, dict)
                and payload.get("name") == "report_probe"
                and isinstance(payload.get("arguments"), dict)
            )
    except (ValueError, TypeError):
        pass
    return False


def connection_signature(profile):
    return Store.fingerprint(
        {
            "connection": Store.catalog_signature(profile),
            "route": profile.ollama_api,
            "stream": profile.ollama_stream,
        }
    )


def local_profile(profile):
    from urllib.parse import urlsplit
    import ipaddress

    if profile.kind != "ollama":
        return False
    host = urlsplit(profile.base_url).hostname
    try:
        return host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class ToolProbe:
    def __init__(self, store, credentials, provider_factory=Provider):
        self.store, self.credentials, self.provider_factory = store, credentials, provider_factory

    def run(self, agent_id, cancel=None, *, allow_cloud=False, compare_routes=False, emit=lambda event: None):
        cancel = cancel or threading.Event()
        agent = next((a for a in self.store.agents() if a.id == agent_id), None)
        if agent is None:
            raise ValueError("Select a saved agent")
        profile = next((p for p in self.store.profiles() if p.id == agent.primary.profile_id), None)
        if profile is None:
            raise ValueError("Agent provider profile is missing")
        local = local_profile(profile)
        if not local and not allow_cloud:
            raise PermissionError("Explicit approval is required for this remote model generation probe")
        current = (
            (profile.ollama_api, profile.ollama_stream) if profile.kind == "ollama" else ("compatible", False)
        )
        routes = [current]
        if compare_routes:
            if not local:
                raise ValueError("Route comparisons are restricted to local Ollama")
            routes += [
                item
                for item in (("native", False), ("native", True), ("compatible", False), ("compatible", True))
                if item != current
            ]
        report = {
            "schema_version": 1,
            "suite_version": "tool-probe-1",
            "kind": "tool_probe",
            "id": str(uuid4()),
            "created": now(),
            "app_version": __version__,
            "state": "running",
            "profile_id": profile.id,
            "model": agent.primary.model,
            "connection_signature": connection_signature(profile),
            "checks": [],
            "environment": {
                "os": platform.system(),
                "os_release": platform.release(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
            },
            "recent_runs": {},
            "privacy": "Synthetic native-tool probe only; no project files, commands or raw model text.",
        }
        self.store.save_diagnostic(report)
        began = time.monotonic()
        challenge = secrets.token_hex(4)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "report_probe",
                    "description": "Report the supplied challenge. This diagnostic function has no external effects.",
                    "parameters": {
                        "type": "object",
                        "properties": {"challenge": {"type": "string"}},
                        "required": ["challenge"],
                        "additionalProperties": False,
                    },
                },
            }
        ]
        messages = [
            {
                "role": "user",
                "content": "Call report_probe once with challenge '"
                + challenge
                + "'. Use native function calling; do not print a JSON example. No other action is needed.",
            }
        ]
        for route, stream in routes:
            if cancel.is_set():
                break
            provider = self.provider_factory(
                profile.model_copy(update={"timeout_seconds": min(profile.timeout_seconds, 40)}),
                self.credentials,
            )
            started = time.monotonic()
            evidence = {
                "provider": provider_label(profile),
                "model": agent.primary.model,
                "route": route,
                "stream": stream,
                "generation_requests": 0,
                "max_output_tokens": 96,
                "native_calls_total": 0,
                "challenge_verified": False,
            }
            status, code = "failed", "NATIVE_CALL_NOT_RETURNED"
            try:
                reply = cancellable_call(
                    lambda: provider.chat(
                        agent.primary.model, messages, tools, max_output_tokens=96, route=route, stream=stream
                    ),
                    cancel,
                    time.monotonic() + 45,
                )
                verified = (
                    len(reply.calls) == 1
                    and reply.calls[0].name == "report_probe"
                    and reply.calls[0].arguments == {"challenge": challenge}
                )
                evidence.update(
                    native_calls_total=len(reply.calls),
                    challenge_verified=verified,
                    http_status=getattr(provider, "last_http_status", None),
                    text_tool_response=probe_text(reply.content),
                    finish_reason=reply.evidence.get("finish_reason", "other"),
                    tool_calls_field_present=reply.evidence.get(
                        "tool_calls_field_present", bool(reply.calls)
                    ),
                )
                if verified:
                    status, code = "passed", "NATIVE_TOOL_PROBE_VERIFIED"
                elif reply.calls:
                    code = "NATIVE_ARGUMENT_MISMATCH"
                elif evidence["text_tool_response"]:
                    code = "TEXT_TOOL_RESPONSE"
            except InterruptedError:
                cancel.set()
                status, code = "skipped", "CANCELLED"
            except ProviderError as exc:
                code = exc.code
                evidence.update(
                    http_status=exc.http_status
                    if exc.http_status is not None
                    else getattr(provider, "last_http_status", None),
                    provider_error_code=exc.code,
                )
            except Exception as exc:
                code = "PROBE_REQUEST_FAILED"
                # Exception text can contain endpoint, prompt or credentials. Retain class only.
                evidence["error_type"] = type(exc).__name__
            evidence["generation_requests"] = getattr(provider, "chat_requests", 0)
            check = {
                "id": route + ("_stream" if stream else "") + "_tool_probe",
                "status": status,
                "code": code,
                "message": "Matching native function call verified; a full coding workflow is not certified."
                if status == "passed"
                else "Native function probe did not verify. No project or host action was executed.",
                "duration_ms": round((time.monotonic() - started) * 1000),
                "evidence": evidence,
            }
            report["checks"].append(check)
            self.store.save_diagnostic(report)
            emit({"kind": "diagnostic.result", "data": check})
        report.update(
            state="cancelled"
            if cancel.is_set()
            else "passed"
            if report["checks"] and report["checks"][0]["status"] == "passed"
            else "needs_attention",
            summary={
                key: sum(row["status"] == key for row in report["checks"])
                for key in ("passed", "failed", "warning", "skipped")
            },
            duration_ms=round((time.monotonic() - began) * 1000),
            finished=now(),
        )
        self.store.save_diagnostic(report)
        self.store.event(
            None,
            "tool_probe.completed",
            {
                "report_id": report["id"],
                "state": report["state"],
                "generation_requests": sum(c["evidence"]["generation_requests"] for c in report["checks"]),
            },
        )
        self.store.prune()
        return report
