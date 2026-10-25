"""Versioned, portable definitions. Credentials are references, never values."""

from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .registry import TOOLS


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ModelRef(Strict):
    profile_id: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)


class Agent(Strict):
    schema_version: Literal[1] = 1
    id: str = Field(default_factory=lambda: str(uuid4()))
    revision: int = Field(default=1, ge=1)
    name: str = Field(default="Coding partner", min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    kind: Literal["worker", "coordinator"] = "worker"
    instructions: str = Field(
        default="Inspect files before editing. Make focused changes and verify them.", max_length=16000
    )
    primary: ModelRef = Field(default_factory=lambda: ModelRef(profile_id="ollama", model="qwen2.5-coder:7b"))
    fallbacks: list[ModelRef] = Field(default_factory=list, max_length=5)
    tools: list[str] = Field(default_factory=lambda: list(TOOLS))
    allow_writes: bool = True
    allow_commands: bool = False
    max_steps: int = Field(default=12, ge=1, le=100)
    max_seconds: int = Field(default=300, ge=5, le=3600)
    context_chars: int = Field(default=48000, ge=4000, le=200000)

    @model_validator(mode="after")
    def coordinator_permissions(self):
        if self.kind == "coordinator" and (
            self.tools or self.allow_writes or self.allow_commands or self.fallbacks
        ):
            raise ValueError(
                "Coordinators use the bounded team pilot, without file tools, commands or fallbacks"
            )
        return self

    @field_validator("tools")
    @classmethod
    def known_tools(cls, value):
        if len(set(value)) != len(value) or any(t not in TOOLS for t in value):
            raise ValueError("Unknown or duplicate tool")
        return value


class Profile(Strict):
    schema_version: Literal[1] = 1
    id: str = Field(min_length=1, max_length=100, pattern=r"^[\w.-]+$")
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["ollama", "openai"] = "ollama"
    base_url: str = "http://127.0.0.1:11434"
    credential_ref: str = Field(default="", max_length=100, pattern=r"^[\w.-]*$")
    supports_tools: bool = True
    ollama_api: Literal["native", "compatible"] = "native"
    ollama_stream: bool = False
    ollama_thinking: Literal["default", "off", "on"] = "default"
    temperature: float | None = Field(default=0.2, ge=0, le=2, allow_inf_nan=False, strict=True)
    top_p: float | None = Field(default=None, gt=0, le=1, allow_inf_nan=False, strict=True)
    top_k: int | None = Field(default=None, ge=1, le=1000, strict=True)
    timeout_seconds: int = Field(default=120, ge=1, le=300)

    @model_validator(mode="after")
    def native_top_k(self):
        if self.top_k is not None and (self.kind != "ollama" or self.ollama_api != "native"):
            raise ValueError("top_k requires native Ollama")
        return self

    @model_validator(mode="after")
    def native_thinking_only(self):
        if self.ollama_thinking != "default" and (self.kind != "ollama" or self.ollama_api != "native"):
            raise ValueError("Explicit thinking controls require native Ollama")
        return self

    @field_validator("base_url")
    @classmethod
    def safe_url(cls, value):
        from urllib.parse import urlsplit
        import ipaddress

        url = urlsplit(value)
        if not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("Use a base URL without credentials, query, or fragment")
        local = url.hostname == "localhost"
        try:
            local = local or ipaddress.ip_address(url.hostname).is_loopback
        except ValueError:
            pass
        if url.scheme != "https" and not (url.scheme == "http" and local):
            raise ValueError("HTTPS required except for local loopback servers")
        return value.rstrip("/")


class ToolCall(Strict):
    id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=100)
    arguments: dict


class Reply(Strict):
    content: str = ""
    calls: list[ToolCall] = Field(default_factory=list, max_length=16)
    usage: dict = Field(default_factory=dict)
    evidence: dict = Field(default_factory=dict)
