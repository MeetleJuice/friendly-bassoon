"""A reviewable update/test workflow with two exact browser draft previews."""

import webbrowser
from urllib.parse import parse_qs, urlsplit
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QVBoxLayout,
)
from .test_suite import CASES, CASE_TITLES, run_bundle
from .diagnostics import OFFLINE_CHECK_COUNT
from .reporting import issue_body, prepare_browser_draft, ReportingError


class SuiteDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        from .ui import button

        self.window = window
        self.setWindowTitle(f"Update & test • {len(CASES)} guided checks")
        self.resize(850, 720)
        layout = QVBoxLayout(self)
        label = QLabel(
            f"{len(CASES)} tests, fresh disposable folders, no host commands, API checks or cloud calls.\nGo authorizes only listed synthetic output edits. Denial test rejects its write automatically.\nBalanced budgets may take up to 45 minutes. Local records follow your retention settings. Sharing stays optional."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self.agents = QComboBox()
        for agent in window.store.agents():
            self.agents.addItem(agent.name, agent.id)
        selected = window.store.setting("suite_agent", window.run_agent.currentData())
        index = self.agents.findData(selected)
        if index >= 0:
            self.agents.setCurrentIndex(index)
        self.agents.setToolTip(
            "Use a saved local Ollama agent. Disabled tools are skipped; cloud fallback is disabled."
        )
        layout.addWidget(self.agents)
        self.results = QTableWidget(len(CASES), 4)
        self.results.setHorizontalHeaderLabels(["Test", "Result", "Time", "Native calls"])
        self.results.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results.setMaximumHeight(210)
        titles = CASE_TITLES
        for index, title in enumerate(titles):
            self.results.setItem(index, 0, QTableWidgetItem(title))
            self.results.setItem(index, 1, QTableWidgetItem("Ready"))
        layout.addWidget(self.results)
        self.budget_mode = QComboBox()
        self.budget_mode.addItem("Balanced • coordinated time/token budgets", "balanced")
        self.budget_mode.addItem("Legacy • previous suite2 budgets (explicit comparison)", "legacy")
        self.budget_mode.setToolTip(
            "Each Go is one run. Compare modes deliberately; no automatic reruns. Saved agent limits still apply."
        )
        layout.addWidget(self.budget_mode)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlainText(
            "\n".join(f"{i + 1}. {identity}: {prompt}" for i, (identity, prompt, _) in enumerate(CASES))
        )
        layout.addWidget(self.output)
        self.progress = QProgressBar()
        self.progress.setRange(0, OFFLINE_CHECK_COUNT + len(CASES))
        layout.addWidget(self.progress)
        self.go = button("Go • run all tests", self.start, layout, True)
        button("Cancel tests", self.cancel, layout)
        self.approval = QCheckBox("I reviewed BOTH previews and approve opening both public GitHub drafts.")
        self.approval.setEnabled(False)
        layout.addWidget(self.approval)
        self.share = button("Open both approved GitHub drafts", self.open_drafts, layout)
        self.share.setEnabled(False)
        self.approval.toggled.connect(self.share.setEnabled)
        self.urls = []
        self.worker = None

    def start(self):
        from .ui import Worker

        w = self.window
        if any(
            j and j.isRunning() for j in (w.worker, w.diagnostic_worker, w.discovery_worker, w.update_worker)
        ):
            w.error("Finish the current operation first. Then click Go.")
            return
        agent = next((a for a in w.store.agents() if a.id == self.agents.currentData()), None)
        if not agent:
            w.error("Save a local Ollama agent first.")
            return
        budget_mode = self.budget_mode.currentData()
        w.store.set_setting("suite_agent", agent.id)
        self.go.setEnabled(False)
        self.agents.setEnabled(False)
        self.budget_mode.setEnabled(False)
        self.approval.setChecked(False)
        self.approval.setEnabled(False)
        self.urls = []
        self.output.clear()
        self.progress.setRange(0, OFFLINE_CHECK_COUNT + len(CASES))
        self.progress.setValue(0)
        for index in range(len(CASES)):
            for column in range(1, 4):
                self.results.setItem(index, column, QTableWidgetItem("Ready" if column == 1 else ""))
        worker = Worker(
            lambda job: run_bundle(w.store, w.credentials, agent, job.cancel, job.activity.emit, budget_mode),
            w.credentials,
            w,
        )
        self.worker = w.diagnostic_worker = worker
        worker.activity.connect(self.activity)
        worker.succeeded.connect(self.done)
        worker.failed.connect(w.error)
        worker.finished.connect(lambda: self.go.setEnabled(True))
        worker.finished.connect(lambda: self.agents.setEnabled(True))
        worker.finished.connect(lambda: self.budget_mode.setEnabled(True))
        worker.start()

    def activity(self, event):
        if event["kind"] in ("suite.result", "diagnostic.result"):
            row = event["data"]
            self.progress.setValue(self.progress.value() + 1)
            if event["kind"] == "suite.result":
                index = next(i for i, case in enumerate(CASES) if case[0] == row["id"])
                values = [
                    (
                        row["status"].replace("_", " ").title()
                        if row["status"] == "passed"
                        else {"OUTPUT_LIMIT": "Output length limit", "TIMEOUT": "Request timed out"}.get(
                            row.get("evidence", {}).get("provider_error_code"),
                            "Session time exhausted"
                            if row.get("evidence", {}).get("runtime_state") == "timed_out"
                            else "Skipped: disabled tool"
                            if row["status"] == "skipped"
                            else "Acceptance needs review",
                        )
                    ),
                    f"{row['duration_ms'] / 1000:.2f} s",
                    str(row.get("evidence", {}).get("native_calls_total", 0)),
                ]
                for column, text in enumerate(values, 1):
                    self.results.setItem(index, column, QTableWidgetItem(text))
            self.output.appendPlainText(row["id"] + ": " + row["status"] + " (" + row["code"] + ")")
            if event["kind"] == "suite.result":
                evidence = row.get("evidence", {})
                self.output.appendPlainText(
                    "Expected: "
                    + next(c[1] for c in CASES if c[0] == row["id"])
                    + "\nObserved: runtime="
                    + str(evidence.get("runtime_state", "not run"))
                    + "; output match="
                    + str(evidence.get("file_matches", "unknown"))
                    + "; provider="
                    + str(evidence.get("provider_error_code", "NONE"))
                    + "; tokens/request seconds/session seconds="
                    + str(evidence.get("max_output_tokens", "unknown"))
                    + "/"
                    + str(evidence.get("request_timeout_seconds", "unknown"))
                    + "/"
                    + str(evidence.get("session_budget_seconds", "unknown"))
                )
        elif event["kind"] == "suite.started":
            self.results.setItem(event["data"]["index"] - 1, 1, QTableWidgetItem("Running…"))
            self.output.appendPlainText("Running " + event["data"]["id"] + "…")

    def done(self, reports):
        self.output.appendPlainText(
            "\nFinished. Reports saved locally. Browser drafts still require Create on GitHub."
        )
        suite = next((r for r in reports if r.get("kind") == "agent_suite"), None)
        if suite:
            previous = next(
                (
                    row["payload"]
                    for row in self.window.store.diagnostic_reports()
                    if row["id"] != suite["id"]
                    and row["payload"].get("kind") == "agent_suite"
                    and row["payload"].get("suite_version") == suite["suite_version"]
                    and row["payload"].get("local_scope") == suite.get("local_scope")
                ),
                None,
            )
            if previous:
                self.output.appendPlainText(
                    "Previous matching suite: "
                    + str(previous.get("summary", {}))
                    + "\nCurrent suite: "
                    + str(suite.get("summary", {}))
                )
        try:
            self.urls = [prepare_browser_draft(*issue_body(r, self.window.credentials)) for r in reports]
        except ReportingError:
            self.urls = []
            self.output.appendPlainText(
                "Reports saved locally, but the browser preview exceeded its limit. Open Diagnose to review/export them; nothing was shared."
            )
            QApplication.beep()
            return
        for index, url in enumerate(self.urls):
            fields = parse_qs(urlsplit(url).query)
            self.output.appendPlainText(
                f"\nEXACT PUBLIC PREVIEW {index + 1}\n" + fields["title"][0] + "\n" + fields["body"][0]
            )
        self.approval.setEnabled(len(self.urls) == 2)
        QApplication.beep()

    def open_drafts(self):
        if not self.approval.isChecked() or len(self.urls) != 2:
            return
        self.share.setEnabled(False)
        self.approval.setEnabled(False)
        urls, self.urls = self.urls, []
        for url in urls:
            if not webbrowser.open(url):
                self.output.appendPlainText("Browser could not open this draft. Copy the URL:\n" + url)

    def cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel.set()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.cancel()
            event.ignore()
            QTimer.singleShot(100, self.close)
        else:
            event.accept()
