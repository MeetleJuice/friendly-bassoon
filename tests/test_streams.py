import json
import time

import httpx
import pytest

from aigentics import streams
from aigentics.streams import StreamProtocolError, consume_chat_stream


class ByteResponse:
    def __init__(self, payload, *, fragment=7):
        self.payload = payload.encode("utf-8") if isinstance(payload, str) else payload
        self.fragment = fragment

    def iter_bytes(self):
        for offset in range(0, len(self.payload), self.fragment):
            yield self.payload[offset : offset + self.fragment]


def consume(payload, native=False, *, fragment=7):
    return consume_chat_stream(ByteResponse(payload, fragment=fragment), native, time.monotonic() + 5)


def sse(*chunks, done=True):
    result = ": synthetic keepalive\r\n\r\n"
    for chunk in chunks:
        result += "data: " + json.dumps(chunk, ensure_ascii=False) + "\r\n\r\n"
    return result + ("data: [DONE]\r\n\r\n" if done else "")


def choice(delta=None, finish=None):
    return {"choices": [{"index": 0, "delta": delta or {}, "finish_reason": finish}]}


def native_chunk(message=None, *, done=False, **kwargs):
    return json.dumps({"message": message or {}, "done": done, **kwargs}, ensure_ascii=False) + "\n"


def native_call(*, index=0, identity="native_1", name="read_file", arguments=None):
    return {
        "id": identity,
        "function": {"index": index, "name": name, "arguments": arguments or {"path": "café.txt"}},
    }


def test_sse_assembles_native_fields_across_utf8_and_function_fragments():
    payload = sse(
        choice(
            {
                "role": "assistant",
                "content": "café ",
                "tool_calls": [
                    {"index": 1, "id": "call_", "type": "function", "function": {"name": "read_"}},
                    {"index": 0, "id": "other", "function": {"name": "list_files", "arguments": "{}"}},
                ],
            }
        ),
        choice({"content": "🙂", "reasoning_content": "réfléchir"}),
        choice(
            {
                "tool_calls": [
                    {"index": 1, "id": "one", "function": {"name": "file", "arguments": '{"path":"café'}},
                ]
            }
        ),
        choice({"tool_calls": [{"index": 1, "function": {"arguments": '.txt"}'}}]}, "tool_calls"),
        {"choices": [], "usage": {"prompt_tokens": 9, "completion_tokens": 7}},
    )
    result = consume(payload, fragment=1)
    message = result["choices"][0]["message"]
    assert message["content"] == "café 🙂"
    assert message["thinking"] == "réfléchir"
    assert [call["id"] for call in message["tool_calls"]] == ["other", "call_one"]
    assert message["tool_calls"][1]["function"] == {
        "name": "read_file",
        "arguments": '{"path":"café.txt"}',
    }
    assert result["usage"] == {"prompt_tokens": 9, "completion_tokens": 7}
    assert result["choices"][0]["finish_reason"] == "tool_calls"


def test_native_aggregates_content_whole_calls_and_final_counters():
    call = native_call()
    payload = (
        native_chunk({"role": "assistant", "content": "café ", "thinking": "one "})
        + native_chunk({"content": "🙂", "thinking": "two", "tool_calls": [call]})
        + native_chunk(
            {"content": "", "tool_calls": [call]},
            done=True,
            done_reason="stop",
            prompt_eval_count=40,
            eval_count=12,
            total_duration=99,
        )
    )
    result = consume(payload, native=True, fragment=1)
    assert result["message"] == {
        "role": "assistant",
        "content": "café 🙂",
        "thinking": "one two",
        "tool_calls": [call],
    }
    assert result["prompt_eval_count"] == 40
    assert result["eval_count"] == 12
    assert result["total_duration"] == 99
    assert result["done_reason"] == "stop"


@pytest.mark.parametrize("native", [True, False])
def test_text_json_never_becomes_a_tool_call_and_presence_is_preserved(native):
    text = '{"name":"read_file","arguments":{"path":"synthetic.txt"}}'
    payload = native_chunk({"content": text}, done=True) if native else sse(choice({"content": text}, "stop"))
    result = consume(payload, native)
    message = result["message"] if native else result["choices"][0]["message"]
    assert message["content"] == text
    assert "tool_calls" not in message
    payload = (
        native_chunk({"tool_calls": []}, done=True) if native else sse(choice({"tool_calls": []}, "stop"))
    )
    result = consume(payload, native)
    message = result["message"] if native else result["choices"][0]["message"]
    assert message["tool_calls"] == []
    assert "content" not in message


@pytest.mark.parametrize("index", [-1, 16, True, "0", None])
def test_sse_rejects_invalid_call_indices(index):
    payload = sse(
        choice(
            {"tool_calls": [{"index": index, "function": {"name": "read_file", "arguments": "{}"}}]},
            "tool_calls",
        )
    )
    with pytest.raises(StreamProtocolError):
        consume(payload)


@pytest.mark.parametrize("index", [-1, 16, True, "0"])
def test_native_rejects_invalid_call_indices(index):
    with pytest.raises(StreamProtocolError):
        consume(native_chunk({"tool_calls": [native_call(index=index)]}, done=True), native=True)


@pytest.mark.parametrize(
    "payload,native",
    [
        ("data: {private malformed JSON\n\ndata: [DONE]\n\n", False),
        ('{"message": "private malformed shape", "done":true}\n', True),
        (b'{"message":{"content":"\xff"},"done":true}\n', True),
        (
            sse(
                choice(
                    {"tool_calls": [{"index": 0, "function": {"name": "read_file", "arguments": "[]"}}]},
                    "tool_calls",
                )
            ),
            False,
        ),
        (native_chunk({"tool_calls": [native_call(arguments="[]")]}, done=True), True),
        (
            sse(
                choice(
                    {
                        "tool_calls": [
                            {"index": 0, "function": {"name": "read_file", "arguments": '{"path":NaN}'}}
                        ]
                    },
                    "tool_calls",
                )
            ),
            False,
        ),
        (sse({"error": {"message": "private server body"}}), False),
        ('{"error":"private server body"}\n', True),
    ],
)
def test_invalid_streams_raise_generic_errors_without_provider_text(payload, native):
    with pytest.raises(StreamProtocolError) as caught:
        consume(payload, native)
    assert "private" not in str(caught.value)
    assert "path" not in str(caught.value)


@pytest.mark.parametrize("native", [True, False])
def test_unterminated_streams_are_rejected(native):
    payload = (
        native_chunk({"content": "unfinished"})
        if native
        else sse(choice({"content": "unfinished"}), done=False)
    )
    with pytest.raises(StreamProtocolError):
        consume(payload, native)


def test_sse_requires_finish_reason_and_sentinel():
    with pytest.raises(StreamProtocolError):
        consume(sse(choice({"content": "partial"})))
    with pytest.raises(StreamProtocolError):
        consume(sse(choice({"content": "complete"}, "stop"), done=False))


@pytest.mark.parametrize("native", [True, False])
def test_size_limit_bounds_single_lines_without_iter_lines(native):
    payload = b"x" * (streams.MAX_BYTES + 1)
    with pytest.raises(StreamProtocolError, match="size limit"):
        consume(payload, native, fragment=len(payload))


@pytest.mark.parametrize("native", [True, False])
def test_deadline_checked_before_and_during_stream(monkeypatch, native):
    payload = (
        native_chunk({"content": "hello"}, done=True) if native else sse(choice({"content": "hello"}, "stop"))
    )
    with pytest.raises(StreamProtocolError, match="time limit"):
        consume_chat_stream(ByteResponse(payload), native, time.monotonic() - 1)
    ticks = iter([0, 0, 0, 2])
    monkeypatch.setattr(streams.time, "monotonic", lambda: next(ticks, 2))
    with pytest.raises(StreamProtocolError, match="time limit"):
        consume_chat_stream(ByteResponse(payload, fragment=1), native, 1)


def test_deadline_checks_each_small_httpx_transport_chunk(monkeypatch):
    tick = [0]

    class SlowStream(httpx.SyncByteStream):
        def __iter__(self):
            for _ in range(100):
                tick[0] += 1
                yield b":"

    monkeypatch.setattr(streams.time, "monotonic", lambda: tick[0])
    response = httpx.Response(200, stream=SlowStream())
    with pytest.raises(StreamProtocolError, match="time limit"):
        consume_chat_stream(response, False, 3)
    assert tick[0] == 3


def test_native_conflicting_call_identity_is_rejected():
    payload = native_chunk({"tool_calls": [native_call()]}) + native_chunk(
        {"tool_calls": [native_call(arguments={"path": "other.txt"})]}, done=True
    )
    with pytest.raises(StreamProtocolError):
        consume(payload, native=True)


def test_calls_and_fragments_have_independent_bounds(monkeypatch):
    with pytest.raises(StreamProtocolError):
        consume(
            native_chunk({"tool_calls": [native_call(index=i) for i in range(17)]}, done=True), native=True
        )
    for field, value in (("id", "i" * 201), ("name", "n" * 101)):
        fragment = {"index": 0, "id": "", "function": {"name": "read_file", "arguments": "{}"}}
        (fragment if field == "id" else fragment["function"])[field] = value
        with pytest.raises(StreamProtocolError):
            consume(sse(choice({"tool_calls": [fragment]}, "tool_calls")))
    monkeypatch.setattr(streams, "MAX_ARGUMENT_BYTES", 10)
    with pytest.raises(StreamProtocolError):
        consume(
            sse(
                choice(
                    {
                        "tool_calls": [
                            {
                                "index": 0,
                                "function": {"name": "read_file", "arguments": '{"path":"too long"}'},
                            }
                        ]
                    },
                    "tool_calls",
                )
            )
        )


def test_sse_rejects_duplicate_ids_and_post_finish_tool_fragments():
    calls = [
        {"index": i, "id": "duplicate", "function": {"name": "list_files", "arguments": "{}"}} for i in (0, 1)
    ]
    with pytest.raises(StreamProtocolError):
        consume(sse(choice({"tool_calls": calls}, "tool_calls")))
    with pytest.raises(StreamProtocolError):
        consume(sse(choice({}, "stop"), choice({"tool_calls": calls})))


def test_explicit_unrecognized_native_call_type_is_rejected():
    call = native_call()
    call["type"] = "other"
    with pytest.raises(StreamProtocolError):
        consume(native_chunk({"tool_calls": [call]}, done=True), native=True)


@pytest.mark.parametrize("native", [True, False])
def test_nonfinite_argument_numbers_are_rejected(native):
    arguments = '{"value":1e999}'
    payload = (
        native_chunk({"tool_calls": [native_call(arguments=arguments)]}, done=True)
        if native
        else sse(
            choice(
                {"tool_calls": [{"index": 0, "function": {"name": "read_file", "arguments": arguments}}]},
                "tool_calls",
            )
        )
    )
    with pytest.raises(StreamProtocolError):
        consume(payload, native)


def test_sse_multiline_data_and_final_frame_without_trailing_newline():
    payload = 'event: message\ndata: {"choices":\ndata: [{"delta":{"content":"ok"},"finish_reason":"stop"}]}\n\ndata: [DONE]'
    assert consume(payload)["choices"][0]["message"]["content"] == "ok"


def test_length_finish_reason_is_preserved_for_provider_policy():
    result = consume(sse(choice({"content": "cut off"}, "length")))
    assert result["choices"][0]["finish_reason"] == "length"
    result = consume(
        sse(
            choice(
                {"tool_calls": [{"index": 0, "function": {"name": "read_file", "arguments": '{"path":'}}]},
                "length",
            )
        )
    )
    assert result["choices"][0]["finish_reason"] == "length"
