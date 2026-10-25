"""Strict, value-free Ollama controls and observation metadata.

No model-name heuristics, server environment changes or context overrides.
"""

import re

OLLAMA_USAGE_FIELDS = (
    "prompt_eval_count",
    "eval_count",
    "total_duration",
    "load_duration",
    "prompt_eval_duration",
    "eval_duration",
)
THINKING_LEVELS = frozenset(("none", "minimal", "low", "medium", "high"))
THINKING_MODES = frozenset(("default", "off", "on"))


def thinking_metadata(value):
    """Only explicit /api/show controls authorize automated boolean requests."""
    if value is None:
        return {"thinking_support": "unavailable"}
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("values"), list)
        or not 1 <= len(value["values"]) <= 16
    ):
        return {"thinking_support": "invalid"}
    values = value["values"]
    if any(type(v) is not bool and (not isinstance(v, str) or v not in THINKING_LEVELS) for v in values):
        return {"thinking_support": "invalid"}
    if len({(type(v).__name__, v) for v in values}) != len(values):
        return {"thinking_support": "invalid"}
    result = {"thinking_support": "reported", "thinking_values": list(values)}
    default = value.get("default")
    if any(type(default) is type(v) and default == v for v in values):
        result["thinking_default"] = default
    return result


def public_thinking(value):
    if not isinstance(value, dict):
        return {}
    status = value.get("thinking_support")
    if status != "reported":
        return {"thinking_support": status} if status in ("unavailable", "invalid") else {}
    return thinking_metadata(
        {"values": value.get("thinking_values"), "default": value.get("thinking_default")}
    )


def permits_thinking(value, mode):
    if mode == "default":
        return True
    return (
        mode in ("on", "off")
        and value.get("thinking_support") == "reported"
        and any(type(v) is bool and v is (mode == "on") for v in value.get("thinking_values", []))
    )


def thinking_experiment_available(value):
    """No redundant experiment for a model advertising only [false]."""
    default = value.get("thinking_default")
    return permits_thinking(value, "off") and (
        default is True or isinstance(default, str) and default in THINKING_LEVELS - {"none"}
    )


def public_observation(value):
    if not isinstance(value, dict):
        return {}
    safe = {"source": "ollama.api", "scope": "campaign_end"}
    if value.get("status") in ("observed", "unavailable", "not_loaded"):
        safe["status"] = value["status"]
    for key, maximum in (
        ("context_length", 2_000_000),
        ("loaded_models", 1024),
        ("observer_duration_ms", 10000),
    ):
        number = value.get(key)
        if type(number) is int and 0 <= number <= maximum:
            safe[key] = number
    version = value.get("server_version")
    if isinstance(version, str) and re.fullmatch(
        r"\d{1,3}\.\d{1,3}\.\d{1,3}(?:[-+][A-Za-z0-9.-]{1,24})?", version
    ):
        safe["server_version"] = version
    return safe
