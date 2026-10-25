"""Validated request settings and value-free model metadata; no server mutation."""

import re


def sampling_options(profile):
    return {
        key: getattr(profile, key)
        for key in ("temperature", "top_p", "top_k")
        if getattr(profile, key) is not None
    }


def public_sampling(value):
    from .models import Profile

    if not isinstance(value, dict):
        return {}
    safe = {}
    for key in ("temperature", "top_p", "top_k"):
        if key not in value:
            continue
        try:
            profile = Profile(id="validation", name="Validation", **{key: value[key]})
        except ValueError:
            continue
        safe[key] = getattr(profile, key)
    return safe


def public_model_details(value):
    if not isinstance(value, dict):
        return {}
    result = {}
    for key in ("parameter_size", "quantization_level"):
        item = value.get(key)
        pattern = (
            r"\d{1,5}(?:\.\d{1,3})?\s?[BMT]"
            if key == "parameter_size"
            else r"(?:I?Q\d{1,2}(?:_[A-Z0-9]{1,8}){0,3}|F(?:16|32|64)|BF16|FP(?:4|8|16|32))"
        )
        if isinstance(item, str) and len(item) <= 32 and re.fullmatch(pattern, item):
            result[key] = item
    return result


def public_run_details(value):
    """Revalidate additive evidence; no private filenames, reports or worker prose."""
    if not isinstance(value, dict):
        return {}
    safe = {}
    terminal = value.get("terminal_response_status")
    if terminal in ("accepted", "not_accepted", "not_recorded"):
        safe["terminal_response_status"] = terminal
    reads = []
    for row in value.get("target_reads", [])[-32:] if isinstance(value.get("target_reads"), list) else []:
        if (
            isinstance(row, dict)
            and row.get("category") in ("source", "output", "unchanged")
            and type(row.get("ordinal")) is int
            and 1 <= row["ordinal"] <= 16
            and type(row.get("after_latest_write")) is bool
        ):
            reads.append({k: row[k] for k in ("category", "ordinal", "after_latest_write")})
    if "target_reads" in value:
        safe["target_reads"] = reads
    metrics = value.get("team_metrics")
    if isinstance(metrics, dict):
        safe["team_metrics"] = {
            k: v
            for k, v in metrics.items()
            if k in ("dispatches", "total_calls", "call_limit", "output_limit", "stages_verified")
            and type(v) is int
            and 0 <= v <= 100000
        }
        if type(metrics.get("managed")) is bool:
            safe["team_metrics"]["managed"] = metrics["managed"]
    return safe
