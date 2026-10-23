"""Bounded chat-stream framing and aggregation of provider-native tool fields."""

import json
import math
import time


MAX_BYTES = 2_000_000
MAX_CALLS = 16
MAX_ARGUMENT_BYTES = 1_000_000
MAX_NAME_CHARS = 100
MAX_ID_CHARS = 200


class StreamProtocolError(RuntimeError):
    """A malformed, incomplete or oversized stream; never includes provider text."""


def _fail():
    raise StreamProtocolError("Provider returned an invalid or incomplete chat stream")


def _check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise StreamProtocolError("Provider chat stream exceeded its time limit")


def _lines(response, deadline):
    """Frame bytes directly so neither iter_lines nor decoding buffers grow unchecked."""
    pending = bytearray()
    size = 0
    _check_deadline(deadline)
    for chunk in response.iter_bytes():
        _check_deadline(deadline)
        if not isinstance(chunk, bytes):
            _fail()
        size += len(chunk)
        if size > MAX_BYTES:
            raise StreamProtocolError("Provider chat stream exceeds the response size limit")
        pending.extend(chunk)
        start = 0
        while True:
            end = pending.find(b"\n", start)
            if end < 0:
                break
            _check_deadline(deadline)
            yield bytes(pending[start:end]).removesuffix(b"\r").decode("utf-8")
            start = end + 1
        if start:
            del pending[:start]
    _check_deadline(deadline)
    if pending:
        yield bytes(pending).removesuffix(b"\r").decode("utf-8")


def _reject_constant(_value):
    _fail()


def _finite_float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        _fail()
    return parsed


def _object(value):
    parsed = json.loads(value, parse_constant=_reject_constant, parse_float=_finite_float)
    if not isinstance(parsed, dict):
        _fail()
    return parsed


def _text(value, limit=None, *, empty=True):
    if not isinstance(value, str) or (not empty and not value) or (limit is not None and len(value) > limit):
        _fail()
    return value


def _index(value):
    if type(value) is not int or not 0 <= value < MAX_CALLS:
        _fail()
    return value


def _arguments(value):
    if isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_ARGUMENT_BYTES:
            _fail()
        parsed = _object(value)
    elif isinstance(value, dict):
        parsed = value
        if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_ARGUMENT_BYTES:
            _fail()
    else:
        _fail()
    return parsed


def _finish(value):
    return _text(value, 100, empty=False)


def _native(response, deadline):
    content, thinking, calls = [], [], []
    seen_content = seen_thinking = seen_calls = done = False
    identities = {}
    result = {}
    for line in _lines(response, deadline):
        if not line.strip():
            continue
        if done:
            _fail()
        chunk = _object(line)
        if "error" in chunk:
            _fail()
        if "done" in chunk and type(chunk["done"]) is not bool:
            _fail()
        message = chunk.get("message", {})
        if not isinstance(message, dict):
            _fail()
        if "role" in message and message["role"] != "assistant":
            _fail()
        if "content" in message:
            seen_content = True
            content.append(_text(message["content"]))
        if "thinking" in message:
            seen_thinking = True
            thinking.append(_text(message["thinking"]))
        if "tool_calls" in message:
            seen_calls = True
            native_calls = message["tool_calls"]
            if native_calls is None:
                native_calls = []
            if not isinstance(native_calls, list) or len(native_calls) > MAX_CALLS:
                _fail()
            for call in native_calls:
                if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
                    _fail()
                if call.get("type", "function") != "function":
                    _fail()
                function = call["function"]
                normalized = {
                    "function": {
                        "name": _text(function.get("name"), MAX_NAME_CHARS, empty=False),
                        "arguments": _arguments(function.get("arguments")),
                    }
                }
                keys = []
                if "index" in function:
                    normalized["function"]["index"] = _index(function["index"])
                    keys.append(("index", function["index"]))
                if "id" in call:
                    normalized["id"] = _text(call["id"], MAX_ID_CHARS, empty=False)
                    keys.append(("id", call["id"]))
                previous = {identities[key] for key in keys if key in identities}
                if previous:
                    if len(previous) != 1 or calls[next(iter(previous))] != normalized:
                        _fail()
                    continue
                if len(calls) >= MAX_CALLS:
                    _fail()
                for key in keys:
                    identities[key] = len(calls)
                calls.append(normalized)
        for key in ("prompt_eval_count", "eval_count", "total_duration"):
            if key in chunk:
                if type(chunk[key]) is not int or chunk[key] < 0:
                    _fail()
                result[key] = chunk[key]
        if "done_reason" in chunk:
            result["done_reason"] = _finish(chunk["done_reason"])
        done = chunk.get("done", False)
    if not done:
        _fail()
    message = {"role": "assistant"}
    if seen_content:
        message["content"] = "".join(content)
    if seen_thinking:
        message["thinking"] = "".join(thinking)
    if seen_calls:
        message["tool_calls"] = calls
    return {**result, "message": message, "done": True}


def _sse_events(response, deadline):
    data = []
    for line in _lines(response, deadline):
        if not line:
            if data:
                yield "\n".join(data)
                data = []
            continue
        if line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if separator and field == "data":
            data.append(value.removeprefix(" "))
    if data:
        yield "\n".join(data)


def _compatible(response, deadline):
    content, thinking, calls = [], [], {}
    seen_content = seen_thinking = seen_calls = done = False
    finish_reason = None
    usage = None
    for event in _sse_events(response, deadline):
        _check_deadline(deadline)
        if done:
            _fail()
        if event.strip() == "[DONE]":
            done = True
            continue
        chunk = _object(event)
        if "error" in chunk:
            _fail()
        if "usage" in chunk and chunk["usage"] is not None:
            if not isinstance(chunk["usage"], dict):
                _fail()
            usage = chunk["usage"]
        choices = chunk.get("choices")
        if not isinstance(choices, list) or len(choices) > 1:
            _fail()
        if not choices:
            continue
        choice = choices[0]
        if not isinstance(choice, dict):
            _fail()
        if "index" in choice and (type(choice["index"]) is not int or choice["index"] != 0):
            _fail()
        delta = choice.get("delta", {})
        if not isinstance(delta, dict):
            _fail()
        if finish_reason is not None and delta:
            _fail()
        if "role" in delta and delta["role"] != "assistant":
            _fail()
        if "content" in delta:
            seen_content = True
            if delta["content"] is not None:
                content.append(_text(delta["content"]))
        for key in ("reasoning_content", "reasoning"):
            if key in delta and delta[key] is not None:
                seen_thinking = True
                thinking.append(_text(delta[key]))
        if "tool_calls" in delta:
            seen_calls = True
            fragments = delta["tool_calls"]
            if fragments is None:
                fragments = []
            if not isinstance(fragments, list) or len(fragments) > MAX_CALLS:
                _fail()
            for fragment in fragments:
                if not isinstance(fragment, dict):
                    _fail()
                index = _index(fragment.get("index"))
                call = calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
                if fragment.get("type", "function") != "function":
                    _fail()
                function = fragment.get("function", {})
                if not isinstance(function, dict):
                    _fail()
                for source, target, limit in (
                    (fragment, "id", MAX_ID_CHARS),
                    (function, "name", MAX_NAME_CHARS),
                    (function, "arguments", MAX_ARGUMENT_BYTES),
                ):
                    if target not in source:
                        continue
                    part = _text(source[target], limit)
                    if len(call[target]) + len(part) > limit:
                        _fail()
                    call[target] += part
        if choice.get("finish_reason") is not None:
            if finish_reason is not None:
                _fail()
            finish_reason = _finish(choice["finish_reason"])
    if not done or finish_reason is None:
        _fail()
    message = {"role": "assistant"}
    if seen_content:
        message["content"] = "".join(content)
    if seen_thinking:
        message["thinking"] = "".join(thinking)
    if seen_calls:
        normalized = []
        ids = set()
        for index in sorted(calls):
            call = calls[index]
            # Provider.chat rejects these terminal reasons before normalizing
            # calls. Preserve them even when truncation left partial arguments.
            if finish_reason not in ("length", "content_filter"):
                _text(call["name"], MAX_NAME_CHARS, empty=False)
                _arguments(call["arguments"])
            if call["id"]:
                if call["id"] in ids:
                    _fail()
                ids.add(call["id"])
            normalized_call = {
                "type": "function",
                "function": {"name": call["name"], "arguments": call["arguments"]},
            }
            if call["id"]:
                normalized_call["id"] = call["id"]
            normalized.append(normalized_call)
        message["tool_calls"] = normalized
    result = {"choices": [{"message": message, "finish_reason": finish_reason}]}
    if usage is not None:
        result["usage"] = usage
    return result


def consume_chat_stream(response, native: bool, deadline: float):
    """Aggregate structured tool fields only; text never becomes an executable call.

    ``deadline`` is an absolute ``time.monotonic()`` deadline. HTTP read timeouts
    still belong to the caller; this deadline is checked whenever bytes arrive.
    """
    try:
        return _native(response, deadline) if native else _compatible(response, deadline)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise StreamProtocolError("Provider returned an invalid or incomplete chat stream") from None
