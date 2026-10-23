"""Bounded first-launch discovery. Never scan projects or send keys to cloud services."""

from dataclasses import dataclass, field
from pathlib import Path
import os
import time
from .models import Profile
from .providers import Provider

PROVIDER_PRESETS = (
    ("groq", "Groq", "https://api.groq.com/openai/v1", ("GROQ_API_KEY", "GROQ_KEY")),
    (
        "openrouter",
        "OpenRouter",
        "https://openrouter.ai/api/v1",
        ("OPENROUTER_API_KEY", "OPEN_ROUTER_API_KEY"),
    ),
    ("nvidia", "NVIDIA", "https://integrate.api.nvidia.com/v1", ("NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY")),
    (
        "gemini",
        "Gemini (compatible API)",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    ),
    ("openai", "OpenAI", "https://api.openai.com/v1", ("OPENAI_API_KEY",)),
)


def desktop_locations(known_desktop=None, environ=None, home=None):
    env = os.environ if environ is None else environ
    result = []
    candidates = [Path(known_desktop)] if known_desktop else []
    candidates.append(Path(home or Path.home()) / "Desktop")
    for key in ("USERPROFILE", "OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        if env.get(key):
            candidates.append(Path(env[key]) / "Desktop")
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate not in result:
            result.append(candidate)
    return result


def find_desktop_env(desktops):
    """Known Desktop directories only, .env first, then common hidden-extension variant."""
    result = []
    for folder in desktops:
        for filename in (".env", ".env.txt"):
            path = folder / filename
            if path.is_file() and not path.is_symlink() and path not in result:
                result.append(path)
    return result


@dataclass
class DiscoveryResult:
    models: list[str] = field(default_factory=list)
    profiles: list[Profile] = field(default_factory=list)
    env_found: int = 0
    variables_loaded: int = 0
    ollama_status: str = "Not checked"
    ollama_success: bool = False
    env_status: str = "Not checked"
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0

    def evidence(self):
        return {
            "models_found": len(self.models),
            "profiles_available": [p.id for p in self.profiles],
            "env_files_found": self.env_found,
            "variables_loaded": self.variables_loaded,
            "error_types": self.errors,
            "duration_ms": self.duration_ms,
        }


def discover(
    credentials,
    desktops,
    cancel,
    *,
    load_desktop_env=True,
    find_ollama=True,
    provider_factory=Provider,
    ollama_profile=None,
):
    started = time.monotonic()
    result = DiscoveryResult()
    if load_desktop_env and not cancel.is_set():
        try:
            candidates = find_desktop_env(desktops)
            result.env_found = len(candidates)
            if candidates:
                names = credentials.load_env(candidates[0])
                result.variables_loaded = len(names)
                result.env_status = (
                    f"Loaded {len(names)} variables from Desktop {candidates[0].name} into memory."
                )
                if not names:
                    result.env_status = (
                        "Desktop key file found, but no KEY=value entries were loaded. Check the file format."
                    )
                if len(candidates) > 1:
                    result.env_status += " Multiple files found; used the first known Desktop location."
            else:
                result.env_status = "No Desktop .env found. You can select a file manually."
        except (OSError, ValueError, UnicodeError) as exc:
            result.errors.append(type(exc).__name__)
            result.env_status = "Could not read Desktop .env. Select it manually or check its encoding/size."
    else:
        result.env_status = "Automatic Desktop .env loading is off."
    names = credentials.names()
    for identity, name, endpoint, aliases in PROVIDER_PRESETS:
        ref = next((key for key in aliases if key in names), None)
        if ref:
            result.profiles.append(
                Profile(id=identity, name=name, kind="openai", base_url=endpoint, credential_ref=ref)
            )
    if find_ollama and not cancel.is_set():
        try:
            profile = (ollama_profile or Profile(id="ollama", name="Local Ollama")).model_copy(
                update={"timeout_seconds": 3}
            )
            result.models = provider_factory(profile, credentials).discover()
            result.ollama_success = True
            result.ollama_status = (
                f"Ollama connected. Found {len(result.models)} installed models."
                if result.models
                else "Ollama connected, but no models are installed yet."
            )
        except Exception as exc:
            result.errors.append(type(exc).__name__)
            result.ollama_status = "Ollama is unavailable. Start Ollama, then click Refresh discovery."
    else:
        result.ollama_status = "Automatic Ollama discovery is off."
    result.duration_ms = round((time.monotonic() - started) * 1000)
    return result


def suggested_model(models):
    if "qwen2.5-coder:7b" in models:
        return "qwen2.5-coder:7b"
    return next((name for name in models if "coder" in name.lower()), models[0] if models else None)
