"""Native correction, rejected-response privacy and independent mutation checks."""

import json
import threading
import pytest
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.providers import Provider, ProviderError
from aigentics.runtime import Runtime
from aigentics.task_checks import TaskChecks
from aigentics.crew_cases import CASES, evaluate_content
from aigentics.reporting import public_report
from aigentics.evidence import base_report


def call(name, **arguments):
    return Reply(calls=[ToolCall(id="native", name=name, arguments=arguments)])


@pytest.mark.parametrize("repair", [False, True])
def test_wrong_saved_content_requires_independent_acceptance(store, credentials, tmp_path, repair):
    store.save_profile(Profile(id="ollama", name="Fixture"))
    replies = [
        call("write_file", path="out.txt", content="wrong", expected_sha256="new"),
        call("read_file", path="out.txt"),
        Reply(content="Verified"),
    ]
    if repair:
        replies += [
            call("write_file", path="out.txt", content="right", expected_sha256="last_read"),
            call("read_file", path="out.txt"),
            Reply(content="Corrected"),
        ]
    seen = []

    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, model, messages, tools):
            seen.append(messages[-1]["content"])
            return replies[min(len(seen) - 1, len(replies) - 1)]

    sid, state = Runtime(store, credentials, Fixture).run(
        Agent(max_steps=8),
        tmp_path,
        "Save right to out.txt",
        lambda *args: True,
        task_checks=TaskChecks(write_targets=["out.txt"], completion_feedback=True),
        acceptance=lambda ws, text: {"EXACT_OUTPUT": ws.read("out.txt")["content"] == "right"},
    )
    summary = next(e["data"] for e in store.events(sid) if e["kind"] == "run.summary")
    assert state == ("completed" if repair else "needs_review")
    assert summary["task_checks"]["content_failures"] == (0 if repair else 1)
    assert summary["completion_feedback_count"] == 1
    assert summary["tools"]["writes_verified"] == (2 if repair else 1)
    assert summary["task_checks"]["missing_readbacks"] == 0
    assert len(seen) == (6 if repair else 4)
    assert "EXACT_OUTPUT" in seen[3]


@pytest.mark.parametrize(
    "contract",
    [
        lambda ws, text: {},
        lambda ws, text: {"EXACT_OUTPUT": "passed"},
        lambda ws, text: {"EXACT_OUTPUT": True, "bad key": True},
    ],
)
def test_invalid_application_checker_fails_closed(store, credentials, tmp_path, contract):
    store.save_profile(Profile(id="ollama", name="Fixture"))

    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, *args):
            return Reply(content="Done")

    sid, state = Runtime(store, credentials, Fixture).run(
        Agent(max_steps=2), tmp_path, "Task", lambda *args: True, acceptance=contract
    )
    assert state == "needs_review"
    summary = next(e["data"] for e in store.events(sid) if e["kind"] == "run.summary")
    assert summary["acceptance_checks"] == {"CHECKER_ERROR": False}


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("route", ["native", "compatible"])
def test_truncated_native_fields_never_execute_and_shape_is_numeric(credentials, route, stream):
    profile = Profile(id="ollama", name="Fixture", ollama_api=route)
    raw = {
        "content": "PRIVATE-CONTENT",
        "thinking": "PRIVATE-THOUGHT",
        "tool_calls": [
            {"function": {"name": "write_file", "arguments": {"path": "secret.txt", "content": "secret"}}}
        ],
    }
    native = {"message": raw, "done_reason": "length", "eval_count": 1024, "done": True}
    compatible = {"choices": [{"message": raw, "finish_reason": "length"}]}
    # Stream assembly is tested separately; both adapter settings reject the same assembled response.
    provider = Provider(profile, credentials)
    provider.request = lambda *args, **kwargs: native if route == "native" else compatible
    provider.chat_stream = lambda *args: native if route == "native" else compatible
    with pytest.raises(ProviderError) as caught:
        provider.chat("fixture", [], [], stream=stream)
    error = caught.value
    assert error.code == "OUTPUT_LIMIT"
    assert error.evidence["thinking_chars"] == len("PRIVATE-THOUGHT")
    assert error.evidence["native_call_count"] == 1
    assert "PRIVATE" not in str(error.evidence) and "secret" not in str(error.evidence)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_independent_oracle_rejects_wrong_artifacts_or_answers(case, tmp_path):
    for name, data in case.files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for name, data in case.outputs.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for name, data in case.output_json.items():
        (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")
    final = json.dumps(case.answer) if case.answer is not None else "Done"
    assert all(evaluate_content(case, tmp_path, final).values())
    if case.outputs or case.output_json:
        name = next(iter(case.outputs or case.output_json))
        (tmp_path / name).write_bytes(b'{"cases": []}')
        assert not evaluate_content(case, tmp_path, final)["OUTPUT_CONTENT"]
    else:
        assert not evaluate_content(case, tmp_path, '{"invented":true}')["FINAL_ANSWER"]


def test_public_new_evidence_drops_private_text_and_bad_types():
    r = base_report("crew_campaign", "crew-campaign-3", "Synthetic")
    r["checks"] = [
        {
            "id": "baseline-unicode",
            "status": "failed",
            "code": "MODEL_OR_RUNTIME_FAILED",
            "message": "Synthetic",
            "duration_ms": 1,
            "evidence": {
                "failure_shape": {
                    "thinking_chars": 42,
                    "content_chars": "PRIVATE",
                    "native_call_count": True,
                    "thinking": "PRIVATE",
                    "finish_reason": "length",
                },
                "acceptance_checks": {"EXACT_OUTPUT": False, "PRIVATE": True},
                "initial_acceptance_checks": {"EXACT_OUTPUT": "PRIVATE"},
            },
        }
    ]
    safe = public_report(r)
    assert "PRIVATE" not in str(safe)
    evidence = safe["checks"][0]["evidence"]
    assert evidence["failure_shape"] == {"thinking_chars": 42, "finish_reason": "length"}
    assert evidence["acceptance_checks"] == {"EXACT_OUTPUT": False}


def test_complete_66_case_failure_report_fits_one_browser_draft(credentials):
    from copy import deepcopy
    from urllib.parse import parse_qs, urlsplit
    from aigentics.campaign import PLAN_IDS
    from aigentics.reporting import issue_body, prepare_browser_draft
    from test_campaign_reports_0120 import campaign_report

    r = campaign_report()
    r["suite_version"] = "crew-campaign-3"
    r["planned_cases"] = 66
    original = r["checks"][0]
    r["checks"] = []
    for identity in PLAN_IDS:
        row = deepcopy(original)
        row["id"] = identity
        row["evidence"].update(
            completion_feedback_count=1,
            initial_task_checks={
                "missing_writes": 1,
                "missing_readbacks": 2,
                "missing_sources": 2,
                "content_failures": 2,
            },
            failure_shape={"thinking_chars": 12345, "content_chars": 100, "native_call_count": 1},
            group="experiment" if identity.startswith("experiment-") else "comparison",
        )
        r["checks"].append(row)
    url = prepare_browser_draft(*issue_body(r, credentials))
    assert len(url) <= 7500
    body = parse_qs(urlsplit(url).query)["body"][0]
    assert body.count(" F ") == 66
    assert "PRIVATE" not in body
    assert "12345.100.1" in body
    assert "1.2.2.2" in body
    assert "Recorded/planned: 66/66" in body


@pytest.mark.parametrize("allowed", [False, True])
def test_content_failure_cannot_bypass_denial_or_step_limit(store, credentials, tmp_path, allowed):
    store.save_profile(Profile(id="ollama", name="Fixture"))
    requests = []

    class Fixture:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {"tools": True}

        def chat(self, *args):
            requests.append(1)
            return (
                call("write_file", path="out.txt", content="wrong", expected_sha256="new")
                if len(requests) == 1
                else Reply(content="Done")
            )

    sid, state = Runtime(store, credentials, Fixture).run(
        Agent(max_steps=2),
        tmp_path,
        "Task",
        lambda *args: allowed,
        task_checks=TaskChecks(write_targets=["out.txt"], completion_feedback=True),
        acceptance=lambda ws, text: {"EXACT_OUTPUT": False},
    )
    summary = next(e["data"] for e in store.events(sid) if e["kind"] == "run.summary")
    assert state == "needs_review"
    assert summary["completion_feedback_count"] == 0
    assert len(requests) == 2
    assert (tmp_path / "out.txt").exists() == allowed


@pytest.mark.parametrize("cap", [1024, 2048, 4096])
def test_budget_experiment_changes_real_request_output_allowance_only(store, credentials, monkeypatch, cap):
    import httpx
    import aigentics.providers as providers
    from aigentics.test_suite import run_suite

    store.save_profile(Profile(id="ollama", name="Fixture"))
    bodies = []

    def handle(request):
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["tools"]})
        body = json.loads(request.content)
        bodies.append(body)
        count = sum(m["role"] == "tool" for m in body["messages"])
        if count == 0:
            message = {
                "tool_calls": [
                    {
                        "function": {
                            "name": "write_file",
                            "arguments": {
                                "path": "unicode.txt",
                                "content": "café 🌊\n",
                                "expected_sha256": "new",
                            },
                        }
                    }
                ]
            }
        elif count == 1:
            message = {
                "tool_calls": [{"function": {"name": "read_file", "arguments": {"path": "unicode.txt"}}}]
            }
        else:
            message = {"content": "Verified"}
        return httpx.Response(200, json={"message": message, "done_reason": "stop"})

    original = providers.Provider
    monkeypatch.setattr(
        providers, "Provider", lambda profile, keys: original(profile, keys, httpx.MockTransport(handle))
    )
    report = run_suite(
        store,
        credentials,
        Agent(),
        threading.Event(),
        lambda e: None,
        case_ids=["unicode"],
        completion_feedback=True,
        output_cap=cap,
        persist=False,
    )
    assert report["checks"][0]["status"] == "passed", report
    assert len(bodies) == 3
    assert all(b["options"] == {"temperature": 0.2, "num_predict": cap} for b in bodies)
    assert report["checks"][0]["evidence"]["session_budget_seconds"] == 90
