import threading
from urllib.parse import parse_qs, urlsplit
import pytest
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.test_suite import CASES, run_suite
from aigentics.reporting import public_report, issue_body, prepare_browser_draft


class Scripted:
    """Actual runtime/tools with deterministic native provider replies."""

    def __init__(self, *args):
        self.step = 0
        self.last_http_status = 200

    def capabilities(self, model):
        return {"tools": True, "source": "fixture"}

    def chat(self, model, messages, tools):
        prompt = next(m["content"] for m in messages if m["role"] == "user")
        self.step = 1 + sum(m["role"] == "tool" for m in messages)

        def reply(name, **kwargs):
            return Reply(calls=[ToolCall(id=str(self.step), name=name, arguments=kwargs)])

        recipes = {
            "Empty-file exercise:": [
                ("write_file", {"path": "empty.txt", "content": "", "expected_sha256": "new"}),
                ("read_file", {"path": "empty.txt"}),
            ],
            "Unicode exercise:": [
                ("write_file", {"path": "unicode.txt", "content": "café 🌊\n", "expected_sha256": "new"}),
                ("read_file", {"path": "unicode.txt"}),
            ],
            "Multiline Python exercise:": [
                (
                    "write_file",
                    {
                        "path": "square.py",
                        "content": "def square(number):\n    return number * number\n",
                        "expected_sha256": "new",
                    },
                ),
                ("read_file", {"path": "square.py"}),
            ],
            "Nested-path exercise:": [
                ("write_file", {"path": "src/report.txt", "content": "harbor\n", "expected_sha256": "new"}),
                ("read_file", {"path": "src/report.txt"}),
            ],
            "Two-file exercise:": [
                ("write_file", {"path": "first.txt", "content": "alpha\n", "expected_sha256": "new"}),
                ("write_file", {"path": "second.txt", "content": "beta\n", "expected_sha256": "new"}),
                ("read_file", {"path": "first.txt"}),
                ("read_file", {"path": "second.txt"}),
            ],
            "Two-input exercise:": [
                ("read_file", {"path": "input.txt"}),
                ("read_file", {"path": "second_input.txt"}),
                (
                    "write_file",
                    {"path": "combined.txt", "content": "lighthouse\nharbor\n", "expected_sha256": "new"},
                ),
                ("read_file", {"path": "combined.txt"}),
            ],
            "No-op exercise:": [
                ("read_file", {"path": "output.txt"}),
                (
                    "write_file",
                    {"path": "output.txt", "content": "lighthouse\n", "expected_sha256": "last_read"},
                ),
                ("read_file", {"path": "output.txt"}),
            ],
            "Stale-revision exercise": [
                ("read_file", {"path": "output.txt"}),
                (
                    "write_file",
                    {"path": "output.txt", "content": "lighthouse\n", "expected_sha256": "0" * 64},
                ),
                ("read_file", {"path": "output.txt"}),
                (
                    "write_file",
                    {"path": "output.txt", "content": "lighthouse\n", "expected_sha256": "last_read"},
                ),
                ("read_file", {"path": "output.txt"}),
            ],
        }
        for marker, recipe in recipes.items():
            if prompt.startswith(marker):
                if self.step <= len(recipe):
                    name, arguments = recipe[self.step - 1]
                    return reply(name, **arguments)
                return Reply(content="Finished.")

        if self.step == 1:
            if "replace its contents" in prompt:
                return reply("read_file", path="output.txt")
            if "Try to create" in prompt:
                return reply("write_file", path="output.txt", content="lighthouse\n", expected_sha256="new")
            if "Create output" in prompt:
                py = "output.py" in prompt
                return reply(
                    "write_file",
                    path="output.py" if py else "output.txt",
                    content="value = 7\n" if py else "lighthouse\n",
                    expected_sha256="new",
                )
            for name in ("list_files", "search", "project_map", "retrieve_context"):
                if name in prompt:
                    return reply(
                        name, **({"query": "lighthouse"} if name in ("search", "retrieve_context") else {})
                    )
            return reply("read_file", path="input.txt")
        if "replace its contents" in prompt and self.step == 2:
            return reply("write_file", path="output.txt", content="lighthouse\n", expected_sha256="last_read")
        if ("Create output" in prompt and self.step == 2) or (
            "replace its contents" in prompt and self.step == 3
        ):
            return reply("read_file", path="output.py" if "output.py" in prompt else "output.txt")
        return Reply(content="Finished.")


def test_expanded_real_tools_cases_and_public_minimization(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    report = run_suite(store, credentials, Agent(), threading.Event(), lambda e: None, Scripted)
    assert report["state"] == "passed", report
    assert len(report["checks"]) == len(CASES) == 18
    assert report["summary"]["passed"] == len(CASES)
    safe = public_report(report)
    assert all("model" not in r["evidence"] for r in safe["checks"])
    assert safe["checks"][5]["evidence"]["execution_counts"]["writes_verified"] == 1
    assert safe["checks"][9]["evidence"]["file_matches"] is True
    url = prepare_browser_draft(*issue_body(report, credentials))
    assert len(url) <= 7500
    body = parse_qs(urlsplit(url).query)["body"][0]
    assert all(identity in body for identity, _, _ in CASES)
    assert "writes/errors=" in body and "tokens in/out=" in body
    assert not store.sessions()  # Synthetic sessions never contaminate user history.


def test_cloud_never_invoked_even_as_fallback(store, credentials):
    store.save_profile(Profile(id="cloud", name="Cloud", kind="openai", base_url="https://example.com"))
    agent = Agent(primary={"profile_id": "cloud", "model": "fixture"})
    with pytest.raises(ValueError, match="local Ollama"):
        run_suite(store, credentials, agent, threading.Event(), lambda e: None, Scripted)
    assert not store.diagnostic_reports()


def test_disabled_tools_skip_and_cancel_does_not_pass(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    report = run_suite(
        store, credentials, Agent(tools=[], allow_writes=False), threading.Event(), lambda e: None, Scripted
    )
    assert report["summary"]["skipped"] == len(CASES)
    assert report["state"] == "needs_attention"
    stop = threading.Event()
    stop.set()
    report = run_suite(store, credentials, Agent(), stop, lambda e: None, Scripted)
    assert report["state"] == "cancelled" and not report["checks"]


def test_two_previews_and_one_shot_browser_consent(qtbot, store, credentials, monkeypatch):
    from aigentics.ui import Window
    from aigentics.suite_ui import SuiteDialog
    from aigentics.evidence import base_report

    window = Window(store, credentials)
    qtbot.addWidget(window)
    dialog = SuiteDialog(window)
    qtbot.addWidget(dialog)
    opened = []
    monkeypatch.setattr("aigentics.suite_ui.webbrowser.open", lambda u: opened.append(u) or True)
    reports = [
        base_report("health", "5", "Metadata"),
        base_report("agent_suite", "agent-suite-1", "Metadata"),
    ]
    dialog.done(reports)
    dialog.open_drafts()
    assert not opened
    previews = dialog.output.toPlainText()
    dialog.approval.setChecked(True)
    dialog.open_drafts()
    assert len(opened) == 2
    assert all(parse_qs(urlsplit(u).query)["body"][0] in previews for u in opened)
    dialog.open_drafts()
    assert len(opened) == 2
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_wrong_search_and_text_claims_cannot_pass(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))

    class Wrong(Scripted):
        def chat(self, model, messages, tools):
            reply = super().chat(model, messages, tools)
            for call in reply.calls:
                if call.name == "search":
                    call.arguments["query"] = "missing"
            return reply

    report = run_suite(store, credentials, Agent(), threading.Event(), lambda e: None, Wrong)
    assert next(r for r in report["checks"] if r["id"] == "search")["status"] == "failed"

    class Prose(Scripted):
        def chat(self, *args):
            return Reply(content="All ten tests passed; I created all files.")

    report = run_suite(store, credentials, Agent(), threading.Event(), lambda e: None, Prose)
    assert report["summary"]["passed"] == 0


def test_update_no_new_version_dispatches_suite_without_install(qtbot, store, credentials, monkeypatch):
    from aigentics.ui import Window

    window = Window(store, credentials)
    qtbot.addWidget(window)
    actions = []
    monkeypatch.setattr(window, "open_setup", lambda: None)
    monkeypatch.setattr(window, "check_updates", lambda: actions.append("check"))
    monkeypatch.setattr(window, "resume_guided_tests", lambda: actions.append("suite"))
    preferred = Agent(name="Preferred suite agent")
    store.save_agent(preferred)
    store.set_setting("suite_agent", preferred.id)
    window.update_action()
    assert store.setting("suite_agent", None) == preferred.id
    assert actions == ["check"]
    assert store.setting("guided_tests_after_update", None) is None
    window.update_checked(None)
    assert actions == ["check", "suite"]
    assert not window.guided_update
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_post_update_queue_consumed_only_by_target_version(qtbot, store, credentials, monkeypatch):
    from aigentics.ui import Window
    from aigentics import __version__

    window = Window(store, credentials)
    qtbot.addWidget(window)
    store.set_setting("auto_ollama", False)
    store.set_setting("auto_desktop_env", False)
    store.set_setting("auto_updates", False)
    queued = []
    monkeypatch.setattr("aigentics.ui.QTimer.singleShot", lambda delay, fn: queued.append(fn))
    store.set_setting("guided_tests_after_update", {"version": "999.0.0"})
    window.startup_tasks()
    assert not queued
    store.set_setting("guided_tests_after_update", {"version": __version__})
    window.startup_tasks()
    assert len(queued) == 1
    assert store.setting("guided_tests_after_update", False) is None
    window.startup_tasks()
    assert len(queued) == 1
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_guided_flow_waits_for_worker_completion_before_downloading(qtbot, store, credentials, monkeypatch):
    from aigentics.ui import Window

    window = Window(store, credentials)
    qtbot.addWidget(window)

    class Busy:
        running = True

        def isRunning(self):
            return self.running

    busy = Busy()
    window.update_worker = busy
    window.guided_update = True
    window.available_release = object()
    deferred, calls = [], []
    monkeypatch.setattr("aigentics.ui.QTimer.singleShot", lambda delay, fn: deferred.append(fn))
    monkeypatch.setattr(window, "download_update", lambda: calls.append("download"))
    window.guided_next()
    assert deferred and not calls
    busy.running = False
    deferred.pop()()
    assert calls == ["download"]
    window.update_worker = None
    window.lab_dir.cleanup()
    window.store.close = lambda: None


def test_bundle_never_checks_provider_catalogs(store, credentials, monkeypatch):
    import aigentics.test_suite as suite
    import aigentics.catalog as catalog
    from aigentics.evidence import base_report

    store.save_profile(Profile(id="ollama", name="Local"))

    def forbidden(*args, **kwargs):
        raise AssertionError("Automatic agent suite must not check provider catalogs")

    monkeypatch.setattr(catalog, "CatalogRunner", forbidden)
    monkeypatch.setattr(
        suite, "run_suite", lambda *args, **kwargs: base_report("agent_suite", "agent-suite-4", "Synthetic")
    )
    reports = suite.run_bundle(store, credentials, Agent(), threading.Event(), lambda e: None)
    assert len(reports) == 2
    assert not any(r["id"].startswith("api_") for r in reports[0]["checks"])
    assert not store.catalogs()


def test_full_gui_worker_health_expanded_cases_and_two_drafts(qtbot, store, credentials, monkeypatch):
    import aigentics.test_suite as suite
    import aigentics.catalog as catalog
    from aigentics.ui import Window
    from aigentics.suite_ui import SuiteDialog

    real_suite = suite.run_suite
    monkeypatch.setattr(
        suite, "run_suite", lambda *args, **kwargs: real_suite(*args, provider_factory=Scripted, **kwargs)
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("No API checks in automatic suite")

    monkeypatch.setattr(catalog, "CatalogRunner", forbidden)
    window = Window(store, credentials)
    qtbot.addWidget(window)
    dialog = SuiteDialog(window)
    qtbot.addWidget(dialog)
    errors = []
    monkeypatch.setattr(window, "error", errors.append)
    dialog.start()
    try:
        # Includes real offline process/SQLite checks; Windows runners exceed 10s.
        qtbot.waitUntil(lambda: not dialog.worker.isRunning(), timeout=60000)
        qtbot.waitUntil(lambda: len(dialog.urls) == 2 or bool(errors), timeout=5000)
        assert not errors
        assert len(dialog.urls) == 2
    finally:
        # Never let failed test teardown destroy a running QThread or its SQLite owner.
        dialog.cancel()
        assert dialog.worker.wait(10000)
        qtbot.wait(1)
    from aigentics.diagnostics import OFFLINE_CHECK_COUNT

    assert dialog.progress.value() == dialog.progress.maximum() == OFFLINE_CHECK_COUNT + len(CASES)
    assert all(dialog.results.item(i, 1).text() == "Passed" for i in range(len(CASES)))
    assert not dialog.share.isEnabled()
    assert len(store.diagnostic_reports()) == 2  # Exactly health and agent evidence, no catalog.
    for url in dialog.urls:
        body = parse_qs(urlsplit(url).query)["body"][0]
        assert len(url) <= 7500
        assert "lighthouse" not in body and "qwen2.5-coder:7b" not in body
    window.lab_dir.cleanup()
    window.store.close = lambda: None
