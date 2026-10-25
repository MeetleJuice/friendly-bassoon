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
            if k
            in (
                "dispatches",
                "total_calls",
                "call_limit",
                "output_limit",
                "output_reserved",
                "format_feedback_count",
                "stages_verified",
            )
            and type(v) is int
            and 0 <= v <= 100000
        }
        for key in ("managed", "review_required", "review_completed"):
            if type(metrics.get(key)) is bool:
                safe["team_metrics"][key] = metrics[key]
    safe.update(public_team_evidence(value))
    return safe


ACTORS = frozenset(("worker", "orion", "george", "scout", "ada", "vera", "sentinel", "atlas"))
TEAM_CODES = frozenset(
    (
        "NONE",
        "ARGUMENT_VALIDATION",
        "ROUTE_REJECTED",
        "WORKER_UNVERIFIED",
        "EMPTY_FINAL",
        "NO_WORKER_EVIDENCE",
        "REVIEW_REQUIRED",
        "ACCEPTANCE_FAILED",
        "STALE_HANDOFF",
        "STALE_FINAL_REVISION",
        "UNKNOWN_TOOL",
        "MULTIPLE_CALLS",
        "TEAM_REJECTED",
        "TEAM_BUDGET",
        "TIMEOUT",
        "OUTPUT_LIMIT",
        "TOOLS_UNSUPPORTED",
        "THINKING_CONTROL_UNAVAILABLE",
        "HTTP_ERROR",
        "CONNECTION_ERROR",
    )
)


def actor_statistics(events):
    """All recorded responses, independent of the bounded trace preview."""
    requests = {
        event["data"]["request_id"]: event["data"] for event in events if event["kind"] == "model.requested"
    }
    result = {}

    def actor_row(actor):
        actor = actor if isinstance(actor, str) and actor in ACTORS else "worker"
        return result.setdefault(
            actor,
            {
                "actor": actor,
                "requests": 0,
                "responses": 0,
                "native_calls": 0,
                "eval_count": None,
                "eval_samples": 0,
                "prompt_eval_count": None,
                "prompt_samples": 0,
            },
        )

    for request in requests.values():
        actor_row(request.get("actor"))["requests"] += 1
    for event in events:
        if event["kind"] != "model.responded":
            continue
        data = event["data"]
        request = requests.get(data.get("request_id"), {})
        row = actor_row(request.get("actor"))
        row["responses"] += 1
        row["native_calls"] += data.get("tool_calls", 0)
        for key, samples in (("eval_count", "eval_samples"), ("prompt_eval_count", "prompt_samples")):
            value = data.get("usage", {}).get(key)
            if type(value) is int and value >= 0:
                row[key] = (row[key] or 0) + value
                row[samples] += 1
    return list(result.values())


def public_team_evidence(value):
    if not isinstance(value, dict):
        return {}
    safe = {}
    code = value.get("team_error_code")
    if isinstance(code, str):
        safe["team_error_code"] = code if code in TEAM_CODES else "TEAM_REJECTED"
    diagnostics = []
    for row in (
        value.get("team_diagnostics", [])[:16] if isinstance(value.get("team_diagnostics"), list) else []
    ):
        if not isinstance(row, dict):
            continue
        if (
            row.get("tool") not in ("dispatch_worker", "team_status", "inspect_evidence", "unknown")
            or row.get("stage") not in ("build", "review", "summarize")
            or row.get("status") not in ("requested", "succeeded", "failed")
        ):
            continue
        item = {k: row[k] for k in ("tool", "stage", "status")}
        if "code" in row:
            item["code"] = (
                row["code"] if isinstance(row["code"], str) and row["code"] in TEAM_CODES else "TEAM_REJECTED"
            )
        if type(row.get("unexpected_arguments")) is int and 0 <= row["unexpected_arguments"] <= 1000:
            item["unexpected_arguments"] = row["unexpected_arguments"]
        types = row.get("argument_types")
        if isinstance(types, dict):
            item["argument_types"] = {
                k: v
                for k, v in types.items()
                if k in ("role", "handoff")
                and v in ("str", "int", "float", "bool", "dict", "list", "NoneType", "other")
            }
        diagnostics.append(item)
    if "team_diagnostics" in value:
        safe["team_diagnostics"] = diagnostics
    actors = []
    for row in (
        value.get("actor_statistics", [])[:8] if isinstance(value.get("actor_statistics"), list) else []
    ):
        if not isinstance(row, dict) or not isinstance(row.get("actor"), str) or row["actor"] not in ACTORS:
            continue
        item = {"actor": row["actor"]}
        for key in (
            "requests",
            "responses",
            "native_calls",
            "eval_count",
            "eval_samples",
            "prompt_eval_count",
            "prompt_samples",
        ):
            number = row.get(key)
            if type(number) is int and 0 <= number <= 10**15:
                item[key] = number
            elif key in ("eval_count", "prompt_eval_count") and number is None:
                item[key] = None
        actors.append(item)
    if "actor_statistics" in value:
        safe["actor_statistics"] = actors
    coverage = value.get("trace_coverage")
    if isinstance(coverage, dict):
        safe["trace_coverage"] = {
            k: v
            for k, v in coverage.items()
            if k in ("responses_recorded", "traces_retained") and type(v) is int and 0 <= v <= 1000
        }
    return safe
