"""Diagnostic laboratory, local report history and explicit sharing preview."""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QMessageBox,
    QFileDialog,
    QTabWidget,
    QWidget,
)
from .diagnostics import DiagnosticRunner
from .reporting import (
    GitHubReporter,
    ISSUES_URL,
    issue_body,
    prepare_browser_draft,
    browser_draft,
    SubmissionUnknown,
)
from .ui import Worker


def add_button(label, slot, layout):
    button = QPushButton(label)
    button.clicked.connect(slot)
    layout.addWidget(button)
    return button


class DiagnosticsDialog(QDialog):
    def __init__(self, window, prompts=True):
        super().__init__(window)
        self.window, self.store, self.credentials = window, window.store, window.credentials
        self.prompts = prompts
        self.report = None
        self.rows = []
        self.runner_factory = DiagnosticRunner
        self.reporter_factory = GitHubReporter
        self.setWindowTitle("Aigentics · Diagnostics & support")
        self.resize(900, 760)
        layout = QVBoxLayout(self)
        heading = QLabel("DIAGNOSE · VERIFY · REVIEW")
        heading.setObjectName("title")
        layout.addWidget(heading)
        description = QLabel(
            "Built-in app checks use disposable files, not your project. An optional real local model test "
            "may take up to three minutes. Nothing is shared until you review and approve it."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        self.status = QLabel("Ready. Reports stay local by default.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        local = QWidget()
        checks = QVBoxLayout(local)
        row = QHBoxLayout()
        checks.addLayout(row)
        self.agents = QComboBox()
        for agent in self.store.agents():
            self.agents.addItem(agent.name, agent.id)
        selected = self.agents.findData(window.run_agent.currentData())
        if selected >= 0:
            self.agents.setCurrentIndex(selected)
        row.addWidget(QLabel("Test agent"))
        row.addWidget(self.agents, 1)
        self.live = QCheckBox("Include a real local Ollama file-create/read-back test")
        agent = next((a for a in self.store.agents() if a.id == self.agents.currentData()), None)
        profile = next((p for p in self.store.profiles() if agent and p.id == agent.primary.profile_id), None)
        self.live.setChecked(bool(profile and profile.kind == "ollama"))
        checks.addWidget(self.live)
        self.network = QCheckBox("Check GitHub update connectivity (no download)")
        self.network.setChecked(True)
        checks.addWidget(self.network)
        row = QHBoxLayout()
        checks.addLayout(row)
        self.run_button = add_button("Run diagnostics", self.start, row)
        self.cancel_button = add_button("Cancel tests", self.cancel, row)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        checks.addWidget(self.output, 1)
        self.history = QComboBox()
        self.history.currentIndexChanged.connect(self.load_report)
        checks.addWidget(self.history)
        row = QHBoxLayout()
        checks.addLayout(row)
        add_button("Export locally", self.export, row)
        add_button("Delete report", self.delete, row)
        add_button("Review GitHub report", self.review, row)
        self.tabs.addTab(local, "Tests & local reports")
        share = QWidget()
        sharing = QVBoxLayout(share)
        notice = QLabel(
            "Destination: public GitHub Issues for MeetleJuice/friendly-bassoon. "
            "This submits a support report, not a source-code update. Local diagnostics are not uploaded automatically."
        )
        notice.setWordWrap(True)
        sharing.addWidget(notice)
        self.method = QComboBox()
        self.method.addItem("Open a GitHub draft in my browser (no token needed)", "browser")
        self.method.addItem("Submit directly using my GitHub token", "api")
        self.method.setCurrentIndex(
            1 if self.store.setting("github_report_method", "browser") == "api" else 0
        )
        self.method.currentIndexChanged.connect(
            lambda index: self.store.set_setting("github_report_method", self.method.currentData())
        )
        self.method.currentIndexChanged.connect(self.prepare_preview)
        self.method.currentIndexChanged.connect(self.sharing_method_changed)
        sharing.addWidget(self.method)
        self.include_model = QCheckBox("Include the selected model name in the shared report")
        self.include_model.toggled.connect(self.prepare_preview)
        sharing.addWidget(self.include_model)
        row = QHBoxLayout()
        sharing.addLayout(row)
        self.token_label = QLabel("Token reference for direct sharing")
        row.addWidget(self.token_label)
        self.token_ref = QLineEdit(self.store.setting("github_token_ref", "GITHUB_TOKEN"))
        row.addWidget(self.token_ref)
        self.token_hint = QLabel(
            "Direct sharing needs a GitHub token with Issues write access to this repository. "
            "Load GITHUB_TOKEN from your key file or save that reference through Providers & credentials."
        )
        self.token_hint.setWordWrap(True)
        sharing.addWidget(self.token_hint)
        self.sharing_method_changed()
        self.title = QLineEdit()
        self.title.setMaxLength(200)
        sharing.addWidget(self.title)
        self.preview = QPlainTextEdit()
        sharing.addWidget(self.preview, 1)
        add_button(
            "Copy preview", lambda: QApplication.clipboard().setText(self.preview.toPlainText()), sharing
        )
        self.approved = QCheckBox("I approve sharing exactly this preview with the public GitHub repository.")
        self.approved.toggled.connect(self.approval_changed)
        sharing.addWidget(self.approved)
        self.preview.textChanged.connect(lambda: self.approved.setChecked(False))
        self.title.textChanged.connect(lambda: self.approved.setChecked(False))
        self.send = add_button("Share approved report", self.submit, sharing)
        self.send.setEnabled(False)
        self.share_status = QLabel()
        self.share_status.setWordWrap(True)
        sharing.addWidget(self.share_status)
        add_button("Open repository Issues", lambda: QDesktopServices.openUrl(QUrl(ISSUES_URL)), sharing)
        self.tabs.addTab(share, "Review & share")
        add_button("Close", self.hide, layout)
        self.refresh_reports()

    def sharing_method_changed(self, *_):
        direct = self.method.currentData() == "api"
        for control in (self.token_label, self.token_ref, self.token_hint):
            control.setVisible(direct)
            control.setEnabled(direct)

    def refresh_reports(self, selected=None):
        self.rows = self.store.diagnostic_reports()
        self.history.blockSignals(True)
        self.history.clear()
        for row in self.rows:
            label = {"api_models": "API checks", "tool_probe": "Tool-call probe"}.get(
                row["payload"].get("kind"), "Diagnostics"
            )
            self.history.addItem(row["created"][:19] + " · " + label + " · " + row["state"], row["id"])
        self.history.blockSignals(False)
        index = self.history.findData(selected) if selected else 0
        if index >= 0:
            self.history.setCurrentIndex(index)
            self.load_report(index)

    def load_report(self, index):
        if 0 <= index < len(self.rows):
            self.report = self.rows[index]["payload"]
            self.output.setPlainText(self.describe(self.report))
            self.output.appendPlainText(self.comparison(self.report))
            self.prepare_preview()

    def comparison(self, report):
        def scope(payload):
            if payload.get("kind") == "tool_probe":
                return (payload.get("model"), payload.get("connection_signature"))
            if payload.get("kind") == "api_models":
                return tuple(
                    tuple(check.get("evidence", {}).get("profile_ids", []))
                    for check in payload.get("checks", [])
                )
            return None

        model = next(
            (
                r.get("evidence", {}).get("model")
                for r in report.get("checks", [])
                if r["id"] == "selected_local_model"
            ),
            None,
        )
        for row in self.rows:
            previous = row["payload"]
            if previous["created"] >= report["created"] or previous.get("suite_version") != report.get(
                "suite_version"
            ):
                continue
            if previous.get("kind", "health") != report.get("kind", "health") or previous["state"] in (
                "running",
                "interrupted",
                "cancelled",
            ):
                continue
            prior_model = next(
                (
                    r.get("evidence", {}).get("model")
                    for r in previous.get("checks", [])
                    if r["id"] == "selected_local_model"
                ),
                None,
            )
            if model != prior_model:
                continue
            if scope(report) != scope(previous):
                continue
            before = {r["id"]: (r["status"], r["code"]) for r in previous.get("checks", [])}
            changes = [
                r["id"] + ": " + str(before[r["id"]]) + " → " + str((r["status"], r["code"]))
                for r in report.get("checks", [])
                if r["id"] in before and before[r["id"]] != (r["status"], r["code"])
            ]
            return (
                "\nCompared with "
                + previous["id"]
                + " (same suite/model):\n"
                + ("\n".join(changes) if changes else "No status/code changes in shared checks.")
            )
        return "\nNo earlier comparable report with the same suite and model is retained."

    @staticmethod
    def describe(report):
        lines = ["Report " + report["id"], "Result: " + report["state"].replace("_", " "), ""]
        for row in report.get("checks", []):
            lines.append(row["status"].upper() + " · " + row["id"].replace("_", " ") + " · " + row["code"])
            lines.append(row["message"])
            if row["id"] == "selected_local_model":
                lines.append(json.dumps(row.get("evidence", {}), indent=2))
        if "summary" in report:
            lines.append("\nCounts: " + json.dumps(report["summary"]))
        return "\n".join(lines)

    def busy(self):
        return self.window.diagnostic_worker is not None and self.window.diagnostic_worker.isRunning()

    def start(self):
        if self.busy() or (self.window.worker and self.window.worker.isRunning()):
            self.window.error("Finish or cancel the current task before running diagnostics.")
            return
        if self.window.diagnostic_worker:
            self.window.diagnostic_worker.deleteLater()
        agent = next((a for a in self.store.agents() if a.id == self.agents.currentData()), None)
        live, network = self.live.isChecked(), self.network.isChecked()
        runner = self.runner_factory(self.store, self.credentials, updater=self.window.updater)
        worker = Worker(
            lambda job: runner.run(job.cancel, job.activity.emit, agent, live, network),
            self.credentials,
            self.window,
        )
        self.window.diagnostic_worker = worker
        self.run_button.setEnabled(False)
        self.send.setEnabled(False)
        self.output.clear()
        self.status.setText("Running actual checks. Temporary test files will be removed.")
        worker.activity.connect(self.activity)
        worker.succeeded.connect(self.diagnostics_finished)
        worker.failed.connect(self.failure)
        worker.finished.connect(lambda: self.run_button.setEnabled(True))
        worker.start()

    def activity(self, event):
        data = event.get("data", {})
        if event["kind"] == "diagnostic.started":
            self.output.appendPlainText("Checking " + data["id"].replace("_", " ") + "…")
        elif event["kind"] == "diagnostic.result":
            self.output.appendPlainText(data["status"].upper() + " · " + data["id"].replace("_", " "))
        elif event["kind"] == "protocol.retry_requested":
            self.output.appendPlainText("Model tool protocol recovery attempt " + str(data["attempt"]))

    def diagnostics_finished(self, report):
        self.report = report
        self.status.setText(
            "Diagnostics finished: " + report["state"].replace("_", " ") + ". Report saved locally."
        )
        self.refresh_reports(report["id"])
        self.store.prune()
        QApplication.beep()
        if self.prompts:
            QTimer.singleShot(0, self.offer_review)

    def offer_review(self):
        if (
            QMessageBox.question(
                self,
                "Diagnostics finished",
                "Checks are finished and the report is saved locally. "
                "Review a redacted GitHub report? Nothing will be sent without approval.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            self.review()

    def failure(self, message):
        for row in self.store.diagnostic_reports():
            if row["state"] == "running":
                payload = row["payload"]
                payload["state"] = "interrupted"
                self.store.save_diagnostic(payload)
        self.status.setText("Diagnostic operation stopped: " + message)
        self.refresh_reports()

    def cancel(self):
        if self.busy():
            self.window.diagnostic_worker.cancel.set()

    def review(self):
        if not self.report:
            return
        self.prepare_preview()
        self.tabs.setCurrentIndex(1)

    def prepare_preview(self, *_):
        if not self.report or not hasattr(self, "preview"):
            return
        try:
            title, body = issue_body(self.report, self.credentials, self.include_model.isChecked())
            if self.method.currentData() == "browser":
                draft = prepare_browser_draft(title, body)
                body = parse_qs(urlsplit(draft).query)["body"][0]
            self.title.setText(title)
            self.preview.setPlainText(body)
            self.approved.setChecked(False)
            row = next((row for row in self.rows if row["id"] == self.report["id"]), {})
            self.share_status.setText(
                "Previous submission was not confirmed. Search GitHub Issues for this report ID before retrying."
                if row.get("submission_state") == "unknown"
                else "Already submitted: " + row["submission_url"]
                if row.get("submission_state") == "submitted"
                else "Opening a browser draft is not a confirmed submission. Review it and submit on GitHub."
            )
        except Exception as exc:
            self.share_status.setText(self.credentials.redact(str(exc)))

    def approval_changed(self, enabled):
        previous = next((row for row in self.rows if self.report and row["id"] == self.report["id"]), {})
        self.send.setEnabled(enabled and not self.busy() and previous.get("submission_state") != "submitted")

    def submit(self):
        if not self.report or not self.approved.isChecked() or self.busy():
            return
        title, body = self.title.text(), self.preview.toPlainText()
        cleaned_title, cleaned_body = self.credentials.redact(title), self.credentials.redact(body)
        if cleaned_body != body or cleaned_title != title:
            self.title.setText(cleaned_title)
            self.preview.setPlainText(cleaned_body)
            self.share_status.setText("A credential was redacted. Review and approve the cleaned preview.")
            return
        report_id = self.report["id"]
        previous = next((row for row in self.store.diagnostic_reports() if row["id"] == report_id), {})
        if previous.get("submission_state") == "submitted":
            self.share_status.setText("This report was already submitted: " + previous["submission_url"])
            return
        if self.method.currentData() == "browser":
            url = browser_draft(title, body, approved=True)
            actual = parse_qs(urlsplit(url).query)["body"][0]
            if actual != body:
                self.preview.setPlainText(actual)
                self.share_status.setText(
                    "Preview shortened to fit a browser URL. Review and approve it again."
                )
                return
            if QDesktopServices.openUrl(QUrl(url)):
                self.store.diagnostic_submission(report_id, "draft_opened")
                self.share_status.setText(
                    "GitHub draft opened. Click Submit new issue there; the app has not confirmed an upload."
                )
            else:
                self.share_status.setText(
                    "The browser could not open. Export locally or use direct submission."
                )
            self.approved.setChecked(False)
            return
        ref = self.token_ref.text().strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", ref):
            self.share_status.setText("Enter the variable name GITHUB_TOKEN here, not a key value.")
            return
        self.store.set_setting("github_token_ref", ref)
        reporter = self.reporter_factory(self.credentials)
        self.send.setEnabled(False)
        if self.window.diagnostic_worker:
            self.window.diagnostic_worker.deleteLater()

        def upload(job):
            try:
                return reporter.submit(title, body, ref, approved=True)
            except SubmissionUnknown:
                self.store.diagnostic_submission(report_id, "unknown")
                raise

        worker = Worker(upload, self.credentials, self.window)
        self.window.diagnostic_worker = worker
        worker.succeeded.connect(lambda url: self.shared(report_id, url))
        worker.failed.connect(lambda message: self.share_status.setText(message))
        worker.finished.connect(lambda: self.approved.setChecked(False))
        worker.start()

    def shared(self, report_id, url):
        self.store.diagnostic_submission(report_id, "submitted", url)
        self.share_status.setText("Submitted successfully: " + url)
        self.refresh_reports(report_id)

    def export(self):
        if not self.report:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save local diagnostic report", "aigentics-diagnostic.json", "JSON (*.json)"
        )
        if path:
            self.window.guarded(
                lambda: Path(path).write_text(self.credentials.json(self.report, indent=2), encoding="utf-8")
            )

    def delete(self):
        if not self.report or self.busy():
            return
        if (
            QMessageBox.question(
                self,
                "Delete local report?",
                "Delete this local diagnostic report? Any GitHub issue or exported copy remains separate.",
            )
            == QMessageBox.Yes
        ):
            self.store.delete_diagnostic(self.report["id"])
            self.report = None
            self.output.clear()
            self.preview.clear()
            self.refresh_reports()
