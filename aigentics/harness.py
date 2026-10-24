"""Deterministic request accounting and least-authority evaluation policy."""

import json


def request_size(messages, tools):
    """Serialized character estimate, including schemas; deliberately not token count."""
    return len(json.dumps({"messages": messages, "tools": tools}, ensure_ascii=True))


def exercise_tools(allowed, required, writing):
    needed = {required}
    if writing:
        needed.add("read_file")
    return [name for name in allowed if name in needed and name != "run_command"]


def output_budget(identity):
    return 2048 if identity in ("edit", "python") else 1024


def suite_budget(identity, mode, agent_seconds, profile_seconds):
    if mode not in ("balanced", "legacy"):
        raise ValueError("Unknown budget mode")
    legacy = mode == "legacy"
    tokens = (
        output_budget(identity)
        if legacy
        else (4096 if identity == "edit" else 2048 if identity in ("retrieve", "python") else 1024)
    )
    total = min(
        agent_seconds, 60 if legacy else 180 if identity == "edit" else 120 if identity == "retrieve" else 90
    )
    request = min(profile_seconds, total, 45 if legacy else max(1, total - 5))
    return {"max_output_tokens": tokens, "request_timeout_seconds": request, "session_budget_seconds": total}
