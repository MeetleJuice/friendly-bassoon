"""Small native adapters. No simulated calls and no invisible cross-provider retries."""

import json
import hashlib
import re
import time
import httpx
from .models import Reply, ToolCall


class ProviderError(RuntimeError):
    def __init__(self, message, retryable=False, code="PROVIDER_ERROR", http_status=None):
        super().__init__(message)
        self.retryable = retryable
        self.code, self.http_status = code, http_status


class Provider:
    def __init__(self, profile, credentials, transport=None):
        self.profile = profile
        self.credentials = credentials
        self.transport = transport
        self.last_http_status = None
        self.chat_requests = 0

    def request(self, method, endpoint, **kwargs):
        self.last_http_status = None
        started = time.monotonic()
        headers = {}
        if self.profile.credential_ref:
            headers["Authorization"] = "Bearer " + self.credentials.get(self.profile.credential_ref)
        try:
            with httpx.Client(
                timeout=self.profile.timeout_seconds, transport=self.transport, follow_redirects=False
            ) as client:
                if method == "POST" and endpoint in (
                    "/api/chat",
                    "/chat/completions",
                    "/v1/chat/completions",
                ):
                    self.chat_requests += 1
                with client.stream(
                    method, self.profile.base_url + endpoint, headers=headers, **kwargs
                ) as response:
                    self.last_http_status = response.status_code
                    if response.status_code >= 300:
                        # Avoid retaining response bodies that may contain keys, prompts, or HTML.
                        code = response.status_code
                        raise ProviderError(
                            f"{self.profile.name}: HTTP {code}. Check endpoint, model, credentials and quota.",
                            code in (408, 429, 500, 502, 503, 504),
                            code="HTTP_ERROR",
                            http_status=code,
                        )
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        if time.monotonic() - started > self.profile.timeout_seconds:
                            raise ProviderError("Provider request deadline reached", True, code="TIMEOUT")
                        size += len(chunk)
                        if size > 2_000_000:
                            raise ProviderError("Provider response exceeds 2 MB limit")
                        chunks.append(chunk)
                    return json.loads(b"".join(chunks))
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ProviderError(
                f"{self.profile.name}: connection failed or timed out ({type(exc).__name__})",
                True,
                code="TIMEOUT" if isinstance(exc, httpx.TimeoutException) else "CONNECTION_ERROR",
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProviderError("Provider returned malformed JSON", code="MALFORMED_JSON") from exc

    def discover(self):
        data = self.request("GET", "/api/tags" if self.profile.kind == "ollama" else "/models")
        try:
            models = (
                [m["name"] for m in data["models"]]
                if self.profile.kind == "ollama"
                else [m["id"] for m in data["data"]]
            )
            if len(models) > 5000 or any(
                not isinstance(m, str) or not m.strip() or len(m) > 200 or any(ord(c) < 32 for c in m)
                for m in models
            ):
                raise ValueError("Invalid model identifier or catalog size")
            self.discovery_partial = bool(data.get("has_more") or data.get("next_page_token"))
            return sorted(set(models))
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ProviderError("Unexpected model discovery response", code="INVALID_MODEL_LIST") from exc

    def capabilities(self, model):
        if not self.profile.supports_tools:
            return {"tools": False, "source": "profile"}
        if self.profile.kind == "ollama":
            data = self.request("POST", "/api/show", json={"model": model})
            if not isinstance(data, dict):
                raise ProviderError("Unexpected model information response", code="INVALID_MODEL_INFO")
            template = data.get("template")
            metadata = {}
            if isinstance(template, str):
                metadata = {
                    "template_sha256": hashlib.sha256(template.encode()).hexdigest(),
                    "template_chars": len(template),
                    "template_mentions_tools": "tools" in template.lower(),
                }
            # /api/show's Go template is not necessarily the active GGUF/Jinja template.
            for key in ("parser", "renderer", "template_source"):
                value = data.get(key)
                if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]{0,64}", value):
                    metadata[key] = value
            capabilities = data.get("capabilities")
            if capabilities is not None:
                if not isinstance(capabilities, list) or any(not isinstance(c, str) for c in capabilities):
                    raise ProviderError("Invalid model capabilities", code="INVALID_MODEL_INFO")
                return {"tools": "tools" in capabilities, "source": "ollama.show", **metadata}
            return {"tools": True, "source": "profile; older Ollama cannot report capabilities", **metadata}
        return {"tools": True, "source": "profile declaration; verify selected cloud model"}

    def chat_stream(self, endpoint, body, native):
        from .streams import consume_chat_stream, StreamProtocolError

        headers = {}
        if self.profile.credential_ref:
            headers["Authorization"] = "Bearer " + self.credentials.get(self.profile.credential_ref)
        self.last_http_status = None
        deadline = time.monotonic() + self.profile.timeout_seconds
        try:
            with httpx.Client(
                timeout=self.profile.timeout_seconds, transport=self.transport, follow_redirects=False
            ) as client:
                self.chat_requests += 1
                with client.stream(
                    "POST", self.profile.base_url + endpoint, headers=headers, json=body
                ) as response:
                    self.last_http_status = response.status_code
                    if response.status_code >= 300:
                        raise ProviderError(
                            "Provider rejected streaming chat request",
                            response.status_code in (408, 429, 500, 502, 503, 504),
                            code="HTTP_ERROR",
                            http_status=response.status_code,
                        )
                    return consume_chat_stream(response, native, deadline)
        except StreamProtocolError as exc:
            raise ProviderError(
                "Incomplete or malformed structured chat stream; no tools were executed",
                code="STREAM_PROTOCOL_ERROR",
            ) from exc
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ProviderError(
                "Streaming provider request failed or timed out",
                True,
                code="TIMEOUT" if isinstance(exc, httpx.TimeoutException) else "CONNECTION_ERROR",
            ) from exc

    def chat(self, model, messages, tools, *, max_output_tokens=4096, route=None, stream=None):
        if not isinstance(max_output_tokens, int) or not 16 <= max_output_tokens <= 4096:
            raise ValueError("Output token limit must be between 16 and 4096")
        if route not in (None, "native", "compatible"):
            raise ValueError("Unknown chat route")
        native = self.profile.kind == "ollama" and (route or self.profile.ollama_api) == "native"
        streaming = bool(
            stream
            if stream is not None
            else self.profile.ollama_stream
            if self.profile.kind == "ollama"
            else False
        )
        if tools and not self.profile.supports_tools:
            raise ProviderError("Selected profile disables native tool calling")
        if native:
            converted = []
            for message in messages:
                m = dict(message)
                if "tool_calls" in m:
                    m["tool_calls"] = [
                        {
                            "id": c["id"],
                            "function": {
                                "name": c["function"]["name"],
                                "arguments": json.loads(c["function"]["arguments"]),
                            },
                        }
                        for c in m["tool_calls"]
                    ]
                if m["role"] == "tool" and "name" in m:
                    m["tool_name"] = m.pop("name")
                converted.append(m)
            body = {
                "model": model,
                "messages": converted,
                "stream": streaming,
                "options": {"temperature": 0.2, "num_predict": max_output_tokens},
            }
            if tools:
                body["tools"] = tools
            data = (
                self.chat_stream("/api/chat", body, True)
                if streaming
                else self.request("POST", "/api/chat", json=body)
            )
            if not isinstance(data, dict):
                raise ProviderError("Unexpected chat response", code="INVALID_CHAT_RESPONSE")
            usage = {k: data[k] for k in ("prompt_eval_count", "eval_count", "total_duration") if k in data}
            if data.get("done_reason") == "length":
                raise ProviderError(
                    "Provider stopped before a complete response; reduce context or change model",
                    code="OUTPUT_LIMIT",
                )
            message = data.get("message", {})
        else:
            converted = [
                {k: v for k, v in m.items() if not (m["role"] == "tool" and k == "name")} for m in messages
            ]
            body = {
                "model": model,
                "messages": converted,
                "stream": streaming,
                "max_tokens": max_output_tokens,
                "temperature": 0.2,
            }
            if tools:
                body["tools"] = tools
                body["tool_choice"] = "auto"
            endpoint = "/v1/chat/completions" if self.profile.kind == "ollama" else "/chat/completions"
            data = (
                self.chat_stream(endpoint, body, False)
                if streaming
                else self.request("POST", endpoint, json=body)
            )
            try:
                choice = data["choices"][0]
                if choice.get("finish_reason") in ("length", "content_filter"):
                    raise ProviderError(
                        "Provider stopped before a complete response; reduce context or change model"
                    )
                message = choice["message"]
            except (KeyError, IndexError, TypeError, AttributeError) as exc:
                raise ProviderError("Unexpected chat response", code="INVALID_CHAT_RESPONSE") from exc
            usage = data.get("usage", {})
        try:
            if not isinstance(message, dict):
                raise ValueError("Invalid message object")
            calls = []
            for i, c in enumerate(message.get("tool_calls") or []):
                if c.get("type", "function") != "function":
                    raise ValueError("Unsupported native tool-call type")
                f = c["function"]
                args = f["arguments"]
                calls.append(
                    ToolCall(
                        id=c.get("id") or f"call_{i}",
                        name=f["name"],
                        arguments=json.loads(args) if isinstance(args, str) else args,
                    )
                )
            if len({c.id for c in calls}) != len(calls):
                raise ValueError("Duplicate tool call identifiers")
            reason = data.get("done_reason") if native else choice.get("finish_reason")
            evidence = {
                "stream": streaming,
                "tool_calls_field_present": "tool_calls" in message,
                "content_field_present": "content" in message,
                "thinking_chars": len(message["thinking"]) if isinstance(message.get("thinking"), str) else 0,
                "finish_reason": reason
                if reason in ("stop", "length", "tool_calls", "load", "unload")
                else "other",
            }
            return Reply(content=message.get("content") or "", calls=calls, usage=usage, evidence=evidence)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ProviderError(
                "Malformed native tool-call response; no tools were executed", code="MALFORMED_NATIVE_CALL"
            ) from exc
