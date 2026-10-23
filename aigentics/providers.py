"""Small native adapters. No simulated calls and no invisible cross-provider retries."""

import json
import httpx
from .models import Reply, ToolCall


class ProviderError(RuntimeError):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


class Provider:
    def __init__(self, profile, credentials, transport=None):
        self.profile = profile
        self.credentials = credentials
        self.transport = transport

    def request(self, method, endpoint, **kwargs):
        headers = {}
        if self.profile.credential_ref:
            headers["Authorization"] = "Bearer " + self.credentials.get(self.profile.credential_ref)
        try:
            with httpx.Client(
                timeout=self.profile.timeout_seconds, transport=self.transport, follow_redirects=False
            ) as client:
                with client.stream(
                    method, self.profile.base_url + endpoint, headers=headers, **kwargs
                ) as response:
                    if response.status_code >= 300:
                        # Avoid retaining response bodies that may contain keys, prompts, or HTML.
                        code = response.status_code
                        raise ProviderError(
                            f"{self.profile.name}: HTTP {code}. Check endpoint, model, credentials and quota.",
                            code in (408, 429, 500, 502, 503, 504),
                        )
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 2_000_000:
                            raise ProviderError("Provider response exceeds 2 MB limit")
                        chunks.append(chunk)
                    return json.loads(b"".join(chunks))
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ProviderError(
                f"{self.profile.name}: connection failed or timed out ({type(exc).__name__})", True
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProviderError("Provider returned malformed JSON") from exc

    def discover(self):
        data = self.request("GET", "/api/tags" if self.profile.kind == "ollama" else "/models")
        try:
            return (
                [m["name"] for m in data["models"]]
                if self.profile.kind == "ollama"
                else [m["id"] for m in data["data"]]
            )
        except (KeyError, TypeError) as exc:
            raise ProviderError("Unexpected model discovery response") from exc

    def capabilities(self, model):
        if not self.profile.supports_tools:
            return {"tools": False, "source": "profile"}
        if self.profile.kind == "ollama":
            data = self.request("POST", "/api/show", json={"model": model})
            capabilities = data.get("capabilities")
            if capabilities is not None:
                return {"tools": "tools" in capabilities, "source": "ollama.show"}
            return {"tools": True, "source": "profile; older Ollama cannot report capabilities"}
        return {"tools": True, "source": "profile declaration; verify selected cloud model"}

    def chat(self, model, messages, tools):
        if tools and not self.profile.supports_tools:
            raise ProviderError("Selected profile disables native tool calling")
        if self.profile.kind == "ollama":
            converted = []
            for message in messages:
                m = dict(message)
                if "tool_calls" in m:
                    m["tool_calls"] = [
                        {
                            "function": {
                                "name": c["function"]["name"],
                                "arguments": json.loads(c["function"]["arguments"]),
                            }
                        }
                        for c in m["tool_calls"]
                    ]
                m.pop("tool_call_id", None)
                if m["role"] == "tool" and "name" in m:
                    m["tool_name"] = m.pop("name")
                converted.append(m)
            body = {
                "model": model,
                "messages": converted,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 4096},
            }
            if tools:
                body["tools"] = tools
            data = self.request("POST", "/api/chat", json=body)
            usage = {k: data[k] for k in ("prompt_eval_count", "eval_count", "total_duration") if k in data}
            message = data.get("message", {})
        else:
            converted = [
                {k: v for k, v in m.items() if not (m["role"] == "tool" and k == "name")} for m in messages
            ]
            body = {"model": model, "messages": converted, "stream": False, "max_tokens": 4096}
            if tools:
                body["tools"] = tools
                body["tool_choice"] = "auto"
            data = self.request("POST", "/chat/completions", json=body)
            try:
                choice = data["choices"][0]
                if choice.get("finish_reason") in ("length", "content_filter"):
                    raise ProviderError(
                        "Provider stopped before a complete response; reduce context or change model"
                    )
                message = choice["message"]
            except (KeyError, IndexError, TypeError) as exc:
                raise ProviderError("Unexpected chat response") from exc
            usage = data.get("usage", {})
        try:
            calls = []
            for i, c in enumerate(message.get("tool_calls") or []):
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
            return Reply(content=message.get("content") or "", calls=calls, usage=usage)
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError("Malformed native tool-call response; no tools were executed") from exc
