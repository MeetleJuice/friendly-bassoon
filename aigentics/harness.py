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
