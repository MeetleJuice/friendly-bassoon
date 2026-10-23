import json
import os
import threading
from contextlib import closing
from datetime import datetime, timezone, timedelta

import httpx
import pytest

from aigentics.catalog import CatalogRunner
from aigentics.models import Agent, Profile
from aigentics.providers import Provider, ProviderError
from aigentics.reporting import public_report
from aigentics.store import Store, now


def cloud(identity, **changes):
    return Profile(
        id=identity, name=identity, kind="openai", base_url=f"https://{identity}.example/v1", **changes
    )


def factory(handler):
    return lambda profile, credentials: Provider(profile, credentials, httpx.MockTransport(handler))


def test_one_metadata_get_per_connection_updates_dropdown_catalogs_and_no_generations(store, credentials):
    credentials._values["TEST_API_KEY"] = "synthetic-secret-value"
    profiles = [
        Profile(id="ollama", name="Local"),
        cloud("first", credential_ref="TEST_API_KEY"),
        cloud("second"),
    ]
    for profile in profiles:
        store.save_profile(profile)
    calls = []

    def handle(request):
        calls.append(request)
        assert request.method == "GET" and not request.content
        assert request.url.path in ("/v1/models", "/api/tags")
        if request.url.host == "first.example":
            assert request.headers["authorization"] == "Bearer synthetic-secret-value"
        else:
            assert "authorization" not in request.headers
        return httpx.Response(
            200,
            json={"models": [{"name": "local-model"}]}
            if request.url.path == "/api/tags"
            else {"data": [{"id": "model-b"}, {"id": "model-a"}, {"id": "model-b"}]},
        )

    report = CatalogRunner(store, credentials, factory(handle)).run()
    assert report["state"] == "passed" and len(calls) == 3
    assert all(c["evidence"]["generation_requests"] == 0 for c in report["checks"])
    assert store.catalogs()["first"]["models"] == ["model-a", "model-b"]
    saved = json.dumps(store.diagnostic_reports())
    assert "synthetic-secret-value" not in saved and "first.example" not in saved
    public = json.dumps(public_report(report))
    assert "profile_ids" not in public and "model-a" not in public
    with closing(Store(store.path, credentials, recover=False)) as reopened:
        assert reopened.catalogs()["ollama"]["models"] == ["local-model"]


def test_duplicate_connections_share_one_call_but_different_credentials_do_not(store, credentials):
    credentials._values.update({"FIRST_KEY": "synthetic-one", "SECOND_KEY": "synthetic-two"})
    original = cloud("first", credential_ref="FIRST_KEY")
    store.save_profile(original)
    store.save_profile(original.model_copy(update={"id": "alias", "name": "Alias"}))
    store.save_profile(original.model_copy(update={"id": "other-key", "credential_ref": "SECOND_KEY"}))
    calls = []
    report = CatalogRunner(
        store,
        credentials,
        factory(lambda req: calls.append(req) or httpx.Response(200, json={"data": [{"id": "available"}]})),
    ).run()
    assert len(calls) == 2 and len(report["checks"]) == 2
    assert len(store.catalogs()) == 3


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "AUTHENTICATION_FAILED"),
        (403, "ACCESS_DENIED"),
        (404, "MODELS_ENDPOINT_UNAVAILABLE"),
        (429, "RATE_LIMITED"),
        (503, "HTTP_ERROR"),
    ],
)
def test_http_failures_are_coded_not_retried_and_preserve_successful_catalog(
    store, credentials, status, code
):
    profile = cloud("first")
    store.save_profile(profile)
    store.save_catalog(profile, ["last-good"])
    calls = []
    report = CatalogRunner(
        store,
        credentials,
        factory(lambda req: calls.append(req) or httpx.Response(status, text="private provider body")),
    ).run()
    assert len(calls) == 1
    assert report["checks"][0]["code"] == code
    assert report["checks"][0]["evidence"]["http_status"] == status
    assert store.catalogs()["first"]["models"] == ["last-good"]
    assert "private provider body" not in json.dumps(report)


def test_missing_key_and_precancelled_checks_make_no_requests(store, credentials, monkeypatch):
    store.save_profile(cloud("missing", credential_ref="ABSENT_KEY"))
    monkeypatch.setattr(
        credentials, "get", lambda ref: (_ for _ in ()).throw(ValueError("private key reference detail"))
    )
    calls = []
    runner = CatalogRunner(store, credentials, factory(lambda req: calls.append(req)))
    report = runner.run()
    assert report["checks"][0]["code"] == "CREDENTIAL_UNAVAILABLE" and not calls
    cancel = threading.Event()
    cancel.set()
    assert runner.run(cancel)["state"] == "cancelled" and not calls
    assert "private key reference detail" not in json.dumps(report)


def test_pagination_is_explicit_without_a_second_call(store, credentials):
    store.save_profile(cloud("paged"))
    calls = []
    report = CatalogRunner(
        store,
        credentials,
        factory(
            lambda req: calls.append(req)
            or httpx.Response(200, json={"data": [{"id": "first-page"}], "has_more": True})
        ),
    ).run()
    assert len(calls) == 1 and report["checks"][0]["code"] == "MODEL_LIST_PARTIAL"
    assert store.catalogs()["paged"]["partial"]


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"data": None},
        {"data": [{"id": 1}]},
        {"data": [{"id": "bad\nmodel"}]},
        {"data": [{"id": "x" * 201}]},
    ],
)
def test_invalid_catalog_payloads_do_not_poison_cache(store, credentials, payload):
    p = cloud("first")
    store.save_profile(p)
    store.save_catalog(p, ["good"])
    report = CatalogRunner(
        store,
        credentials,
        factory(
            lambda req: httpx.Response(
                200, content=json.dumps(payload), headers={"content-type": "application/json"}
            )
        ),
    ).run()
    assert report["checks"][0]["code"] == "INVALID_MODEL_LIST"
    assert store.catalogs()["first"]["models"] == ["good"]


def test_timeout_is_not_retried(store, credentials):
    store.save_profile(cloud("timeout"))
    calls = []

    def handle(req):
        calls.append(req)
        raise httpx.ReadTimeout("private network detail", request=req)

    report = CatalogRunner(store, credentials, factory(handle)).run()
    assert len(calls) == 1 and report["checks"][0]["code"] == "TIMEOUT"
    assert "private network detail" not in json.dumps(report)


def test_cache_invalidates_when_connection_changes_but_not_display_name(store):
    profile = cloud("first")
    store.save_profile(profile)
    store.save_catalog(profile, ["model"])
    store.save_profile(profile.model_copy(update={"name": "Renamed"}))
    assert "first" in store.catalogs()
    store.save_profile(profile.model_copy(update={"base_url": "https://new.example/v1"}))
    assert "first" not in store.catalogs()


def test_report_byte_budget_age_and_backup_retention_protect_active_reports(store):
    stamp = now()
    for number in range(8):
        store.save_diagnostic(
            {"id": str(number), "created": stamp + str(number), "state": "passed", "padding": "x" * 180000}
        )
    store.save_diagnostic({"id": "active", "created": stamp, "state": "running"})
    store.set_setting("report_storage_mb", 1)
    store.prune()
    assert len(store.diagnostic_reports()) < 9
    assert any(row["id"] == "active" for row in store.diagnostic_reports())
    assert store.db.execute("SELECT SUM(length(payload)) FROM diagnostics").fetchone()[0] <= 1024 * 1024
    profile = cloud("old")
    store.save_profile(profile)
    store.save_catalog(profile, ["old-model"])
    old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    with store.db:
        store.db.execute("UPDATE model_catalogs SET fetched=?", (old,))
    backup = store.backup()
    old_time = datetime.now(timezone.utc).timestamp() - 31 * 86400
    os.utime(backup, (old_time, old_time))
    store.prune()
    assert not backup.exists() and not store.catalogs()


def test_v3_migration_preserves_approved_reports_and_sessions(store, credentials, tmp_path):
    agent = store.save_agent(Agent())
    sid = store.start(agent, tmp_path, capture=True)
    store.messages(sid, [{"role": "user", "content": "synthetic history"}])
    store.finish(sid, "completed", "done")
    store.save_diagnostic({"id": "prior-report", "created": now(), "state": "passed"})
    store.diagnostic_submission("prior-report", "draft_opened")
    with store.db:
        store.db.execute("DROP TABLE model_catalogs")
        store.db.execute("PRAGMA user_version=3")
    with closing(Store(store.path, credentials, recover=False)) as migrated:
        assert migrated.db.execute("PRAGMA user_version").fetchone()[0] == 4
        assert migrated.messages(sid)[0]["content"] == "synthetic history"
        assert migrated.diagnostic_reports()[0]["submission_state"] == "draft_opened"
        assert migrated.catalogs() == {}


def test_structural_ollama_evidence_records_template_and_counts_without_contents(store, credentials):
    from aigentics.diagnostics import DiagnosticRunner

    profile = Profile(id="ollama", name="Local")
    store.save_profile(profile)
    agent = store.save_agent(Agent())

    def handle(req):
        if req.url.path == "/api/version":
            return httpx.Response(200, json={"version": "fixture-1"})
        if req.url.path == "/api/show":
            return httpx.Response(
                200,
                json={"capabilities": ["completion", "tools"], "template": "private template {{ .Tools }}"},
            )
        assert req.url.path == "/api/chat"
        body = json.loads(req.content)
        assert len(body["tools"]) == 3
        return httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": '{"name":"list_files","arguments":{"path":""}}'},
                "eval_count": 12,
                "done_reason": "stop",
            },
        )

    report = DiagnosticRunner(store, credentials, factory(handle)).run(
        threading.Event(), agent=agent, include_model=True, include_network=False
    )
    evidence = report["checks"][-1]["evidence"]
    assert evidence["runtime_state"] == "protocol_error"
    assert evidence["model_metadata"]["template_mentions_tools"]
    assert len(evidence["model_metadata"]["template_sha256"]) == 64
    assert evidence["native_calls_total"] == 0 and len(evidence["request_traces"]) == 3
    assert all(
        t["text_tool_response"] and t["advertised_tool_count"] == 3 for t in evidence["request_traces"]
    )
    assert evidence["request_traces"][0]["usage"]["eval_count"] == 12
    assert "private template" not in json.dumps(report)
    shared = public_report(report)
    assert "request_traces" in shared["checks"][-1]["evidence"]
    assert "qwen2.5" not in json.dumps(shared)
    from urllib.parse import parse_qs, urlsplit
    from aigentics.reporting import issue_body, prepare_browser_draft

    title, body = issue_body(report, credentials, include_model=True)
    url = prepare_browser_draft(title, body)
    preview = parse_qs(urlsplit(url).query)["body"][0]
    assert len(url) <= 7500
    assert "last_three_requests" in preview or "native_call_count" in preview
    assert "private template" not in preview


def test_api_dialog_worker_populates_models_and_reuses_report_review(qtbot, store, credentials):
    from aigentics.ui import Window
    from aigentics.records_ui import RecordsDialog

    window = Window(store, credentials)
    qtbot.addWidget(window)
    dialog = RecordsDialog(window)
    qtbot.addWidget(dialog)
    dialog.runner_factory = lambda s, c: CatalogRunner(
        s, c, factory(lambda req: httpx.Response(200, json={"models": [{"name": "fixture-local"}]}))
    )
    dialog.start()
    qtbot.waitUntil(lambda: dialog.run_button.isEnabled(), timeout=5000)
    assert "fixture-local" in dialog.catalog.toPlainText()
    assert window.model_lists["ollama"] == ["fixture-local"]
    assert "No generation calls" in dialog.status.text()
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_catalog_concurrency_is_bounded_and_cancel_skips_queued_connections(store, credentials):
    for index in range(12):
        store.save_profile(cloud("p" + str(index)))
    cancel, four_started, release = threading.Event(), threading.Event(), threading.Event()
    lock = threading.Lock()
    counts = {"active": 0, "max": 0, "requests": 0}

    def handle(req):
        with lock:
            counts["active"] += 1
            counts["requests"] += 1
            counts["max"] = max(counts["active"], counts["max"])
            if counts["active"] == 4:
                four_started.set()
        assert release.wait(5)
        with lock:
            counts["active"] -= 1
        return httpx.Response(200, json={"data": [{"id": "available"}]})

    result = []
    thread = threading.Thread(
        target=lambda: result.append(CatalogRunner(store, credentials, factory(handle)).run(cancel))
    )
    thread.start()
    try:
        assert four_started.wait(5)
        cancel.set()
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()
    assert counts["max"] == 4 and counts["requests"] == 4
    assert result[0]["state"] == "cancelled"
    assert not store.catalogs()


def test_malformed_native_response_is_reported_separately_from_text_tool_content(credentials):
    provider = Provider(
        Profile(id="ollama", name="Local"),
        credentials,
        httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                json={
                    "message": {
                        "tool_calls": [{"function": {"name": "read_file", "arguments": "not JSON: private"}}]
                    }
                },
            )
        ),
    )
    with pytest.raises(ProviderError) as failure:
        provider.chat("fixture", [], [])
    assert failure.value.code == "MALFORMED_NATIVE_CALL"
    assert "private" not in str(failure.value)
