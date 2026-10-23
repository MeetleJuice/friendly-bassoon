"""Selected model native-call verification with explicit remote generation approval."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QPlainTextEdit,
    QApplication,
    QMessageBox,
)
from .probes import ToolProbe, connection_signature, local_profile
from .ui import Worker, button


class ProbeDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window, self.store = window, window.store
        self.runner_factory = ToolProbe
        self.report = None
        self.setWindowTitle("Aigentics · Test model tool calling")
        self.resize(900, 740)
        layout = QVBoxLayout(self)
        note = QLabel(
            "This requests one tiny native function call with a synthetic challenge, capped at 96 output tokens. "
            "It cannot run project tools or commands. A pass verifies this probe, not a full coding task."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.agents = QComboBox()
        self.agents.currentIndexChanged.connect(self.selection_changed)
        layout.addWidget(self.agents)
        self.selection = QLabel()
        self.selection.setWordWrap(True)
        layout.addWidget(self.selection)
        self.cloud = QCheckBox("I approve one remote model generation request; provider charges may apply.")
        layout.addWidget(self.cloud)
        self.compare = QCheckBox(
            "Compare four local Ollama route/stream combinations (up to four local generation calls)"
        )
        layout.addWidget(self.compare)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.run_button = button("Run selected model probe", self.start, row, True)
        button("Cancel probe", self.cancel, row)
        self.status = QLabel("Ready. No model call runs until you press Run.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)
        row = QHBoxLayout()
        layout.addLayout(row)
        button("Review GitHub report", self.review, row)
        self.apply_button = button("Use a successful tested local route", self.apply_route, row)
        self.apply_button.setEnabled(False)
        button("Close", self.hide, layout)
        self.refresh_agents()

    def refresh_agents(self):
        if not self.run_button.isEnabled():
            return
        previous = self.agents.currentData() or self.window.run_agent.currentData()
        self.agents.blockSignals(True)
        self.agents.clear()
        for agent in self.store.agents():
            self.agents.addItem(agent.name + " · " + agent.primary.model, agent.id)
        self.agents.setCurrentIndex(max(0, self.agents.findData(previous)))
        self.agents.blockSignals(False)
        self.selection_changed()

    def selection_changed(self, *_):
        self.cloud.setChecked(False)
        self.compare.setChecked(False)
        self.report = None
        self.apply_button.setEnabled(False)
        agent = next((a for a in self.store.agents() if a.id == self.agents.currentData()), None)
        self.output.clear()
        profile = next((p for p in self.store.profiles() if agent and p.id == agent.primary.profile_id), None)
        if profile:
            self.compare.setEnabled(local_profile(profile))
            self.cloud.setEnabled(not local_profile(profile))
            self.selection.setText(
                "Saved model: "
                + agent.primary.model
                + " · provider: "
                + profile.name
                + " · selected route: "
                + (
                    profile.ollama_api + (" streaming" if profile.ollama_stream else " nonstream")
                    if profile.kind == "ollama"
                    else "compatible nonstream"
                )
            )
            prior = next(
                (
                    row["payload"]
                    for row in self.store.diagnostic_reports()
                    if row["payload"].get("kind") == "tool_probe"
                    and row["payload"].get("profile_id") == profile.id
                    and row["payload"].get("model") == agent.primary.model
                    and row["payload"].get("connection_signature") == connection_signature(profile)
                ),
                None,
            )
            if prior:
                self.report = prior
                self.apply_button.setEnabled(
                    profile.kind == "ollama" and any(c["status"] == "passed" for c in prior["checks"])
                )
                self.output.setPlainText(self.window.credentials.json(prior, indent=2))
                self.status.setText(
                    "Retained probe from "
                    + prior["created"]
                    + ": "
                    + prior["state"].replace("_", " ")
                    + ". Full coding workflow remains unverified."
                )
            else:
                self.status.setText(
                    "No retained probe for this saved model and connection. Press Run to test it."
                )

    def start(self):
        if any(
            job and job.isRunning()
            for job in (self.window.worker, self.window.diagnostic_worker, self.window.discovery_worker)
        ):
            self.status.setText("Finish or cancel the active operation before probing a model.")
            return
        if self.window.diagnostic_worker:
            self.window.diagnostic_worker.deleteLater()
        runner = self.runner_factory(self.store, self.window.credentials)
        self.report = None
        self.apply_button.setEnabled(False)
        self.output.clear()
        identity, approved, compare = (
            self.agents.currentData(),
            self.cloud.isChecked(),
            self.compare.isChecked(),
        )
        worker = Worker(
            lambda job: runner.run(
                identity, job.cancel, allow_cloud=approved, compare_routes=compare, emit=job.activity.emit
            ),
            self.window.credentials,
            self.window,
        )
        self.window.diagnostic_worker = worker
        self.run_button.setEnabled(False)
        self.agents.setEnabled(False)
        self.status.setText("Testing native tool calling. No project actions will be executed.")
        worker.activity.connect(
            lambda event: self.output.appendPlainText(event["data"]["id"] + " · " + event["data"]["code"])
        )
        worker.succeeded.connect(self.completed)
        worker.failed.connect(lambda message: self.status.setText(message))
        worker.finished.connect(lambda: self.run_button.setEnabled(True))
        worker.finished.connect(lambda: self.agents.setEnabled(True))
        worker.start()

    def completed(self, report):
        from .evidence import report_guidance

        self.report = report
        profile = next((p for p in self.store.profiles() if p.id == report["profile_id"]), None)
        self.apply_button.setEnabled(
            bool(
                profile
                and profile.kind == "ollama"
                and any(c["status"] == "passed" for c in report["checks"])
            )
        )
        # Full local evidence stays in SQLite; the normal public builder still applies its allowlist.
        self.output.setPlainText(
            report_guidance(report) + "\n\n" + self.window.credentials.json(report, indent=2)
        )
        self.status.setText(
            "Probe finished: " + report["state"].replace("_", " ") + ". Report saved locally."
        )
        self.cloud.setChecked(False)
        QApplication.beep()

    def cancel(self):
        if self.window.diagnostic_worker and self.window.diagnostic_worker.isRunning():
            self.window.diagnostic_worker.cancel.set()

    def review(self):
        if self.report:
            self.window.open_diagnostics(False)
            dialog = self.window.diagnostics_dialog
            dialog.refresh_reports(self.report["id"])
            dialog.review()

    def apply_route(self):
        if not self.report or self.report.get("state") == "cancelled":
            return
        agent = next((a for a in self.store.agents() if a.id == self.agents.currentData()), None)
        if (
            not agent
            or agent.primary.profile_id != self.report["profile_id"]
            or agent.primary.model != self.report["model"]
        ):
            self.status.setText("Saved agent selection changed; run a new probe before changing its route.")
            return
        profile = next((p for p in self.store.profiles() if p.id == self.report["profile_id"]), None)
        if (
            not profile
            or profile.kind != "ollama"
            or connection_signature(profile) != self.report["connection_signature"]
        ):
            self.status.setText("Provider configuration changed; run a new probe before selecting a route.")
            return
        choices = [
            r["evidence"]
            for r in self.report["checks"]
            if r["status"] == "passed" and r["evidence"].get("challenge_verified")
        ]
        if not choices:
            self.status.setText(
                "No route returned a verified native call. The provider settings were not changed."
            )
            return
        choice = choices[0]
        if (
            QMessageBox.question(
                self,
                "Use tested route?",
                "Use "
                + choice["route"]
                + (" streaming" if choice["stream"] else " nonstream")
                + " for this Ollama profile? This affects its agents; normal permissions still apply. A full coding test is still needed.",
            )
            != QMessageBox.Yes
        ):
            return
        self.store.save_profile(
            profile.model_copy(update={"ollama_api": choice["route"], "ollama_stream": choice["stream"]})
        )
        self.window.refresh_profiles()
        self.status.setText("Selected tested route saved. Run Diagnose to verify the full local workflow.")
