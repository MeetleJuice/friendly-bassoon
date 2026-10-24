import threading
from urllib.parse import parse_qs, urlsplit
import pytest
from aigentics.models import Agent, Profile, Reply, ToolCall
from aigentics.test_suite import CASES, run_suite
from aigentics.reporting import public_report


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


def test_ten_real_tools_cases_and_public_minimization(store, credentials):
    store.save_profile(Profile(id="ollama", name="Local"))
    report = run_suite(store, credentials, Agent(), threading.Event(), lambda e: None, Scripted)
    assert report["state"] == "passed", report
    assert len(report["checks"]) == len(CASES) == 10
    assert report["summary"]["passed"] == 10
    safe = public_report(report)
    assert all("model" not in r["evidence"] for r in safe["checks"])
    assert safe["checks"][5]["evidence"]["execution_counts"]["writes_verified"] == 1
    assert safe["checks"][9]["evidence"]["file_matches"] is True
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
    assert report["summary"]["skipped"] == 10
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
    window.update_action()
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


def test_bundle_merges_metadata_without_generation_or_extra_share_report(store, credentials, monkeypatch):
    import aigentics.test_suite as suite
    import aigentics.catalog as catalog
    from aigentics.evidence import base_report

    store.save_profile(Profile(id="ollama", name="Local"))
    store.save_profile(Profile(id="duplicate", name="Same connection"))
    calls = []

    class Metadata:
        def __init__(self, profile, credentials):
            self.last_http_status = 200
            calls.append(profile.id)

        def discover(self):
            return ["fixture-model"]

        def chat(self, *args):
            raise AssertionError("Metadata runner must never generate")

    real = catalog.CatalogRunner
    monkeypatch.setattr(catalog, "CatalogRunner", lambda s, c: real(s, c, Metadata))
    monkeypatch.setattr(
        suite, "run_suite", lambda *args: base_report("agent_suite", "agent-suite-1", "Synthetic")
    )
    reports = suite.run_bundle(store, credentials, Agent(), threading.Event(), lambda e: None)
    assert len(reports) == 2
    assert len(calls) == 1
    rows = [r for r in reports[0]["checks"] if r["id"].startswith("api_")]
    assert len(rows) == 1 and rows[0]["evidence"]["generation_requests"] == 0
    assert store.catalogs()
