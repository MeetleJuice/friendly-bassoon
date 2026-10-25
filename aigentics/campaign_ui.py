"""One-screen, same-model crew evaluation with explicit dual-preview consent."""

from urllib.parse import parse_qs, urlsplit
import webbrowser
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)
from .campaign import PLAN_IDS, REQUIREMENT_LABELS, campaign_scope, latest_resumable, plan, run_campaign
from .crew import ROLES, ensure_roster
from .crew_cases import CASES as ROLE_CASES
from .diagnostics import OFFLINE_CHECK_COUNT
from .reporting import issue_body, prepare_browser_draft, ReportingError
from .presentation import Disclosure, text_label
from .measurement import UNKNOWN_CODES


class CampaignDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        from .ui import button

        self.window, self.worker, self.urls = window, None, []
        self.setWindowTitle("Aigentics • Test center")
        self.resize(1040, 800)
        self.setMinimumSize(760, 620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)
        layout.addWidget(text_label("TEST · OBSERVE · IMPROVE", "eyebrow"))
        layout.addWidget(text_label("Put the Midnight Crew to the test.", "pageTitle"))
        label = text_label(
            f"{OFFLINE_CHECK_COUNT} offline app checks + 34 local trials by default (30 completion trials + 4 conditional thinking-off trials). "
            "One model, six independent roles, disposable files. Up to 2 hours. "
            "No API checks. Saved personal agents stay unchanged."
        )
        layout.addWidget(label)
        self.agents = QComboBox()
        for agent in window.store.agents():
            self.agents.addItem(f"Use model from {agent.name}: {agent.primary.model}", agent.id)
        chosen = window.store.setting("suite_agent", window.run_agent.currentData())
        index = self.agents.findData(chosen)
        if index >= 0:
            self.agents.setCurrentIndex(index)
        self.agents.setToolTip(
            "All six controlled test configurations use this saved agent's local model connection."
        )
        layout.addWidget(self.agents)
        self.mode = QComboBox()
        self.mode.addItem("Measurement • 34 trials + app checks", "measurement")
        self.mode.addItem("Discovery • 66 model attempts + app checks", "deep")
        self.mode.addItem("Standard • 36 model attempts + app checks", "standard")
        self.mode.addItem("Quick • app checks only, no model generation", "quick")
        layout.addWidget(self.mode)
        dashboard = QHBoxLayout()
        self.metric_values = {}
        for key, title in (
            ("immediate", "PASSED FIRST TRY"),
            ("corrected", "AFTER CORRECTION"),
            ("failed", "NEEDS WORK"),
            ("unknown", "NOT COMPLETED"),
        ):
            card = QWidget()
            card.setObjectName("metricCard")
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(text_label(title, "eyebrow"))
            value = text_label("0", "metricValue")
            card_layout.addWidget(value)
            dashboard.addWidget(card, 1)
            self.metric_values[key] = value
        layout.addLayout(dashboard)
        self.current_case = text_label("Ready when you are. Failures and interruptions are useful evidence.")
        layout.addWidget(self.current_case)
        self.results = QTableWidget(len(PLAN_IDS), 4)
        self.results.setHorizontalHeaderLabels(["Agent / scenario", "Result", "Time", "Native calls"])
        self.results.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results.setMinimumHeight(150)
        self.results.setAlternatingRowColors(True)
        self.results.setShowGrid(False)
        self.results.verticalHeader().hide()
        self.results.verticalHeader().setDefaultSectionSize(36)
        self.results.setSelectionBehavior(QTableWidget.SelectRows)
        self.results.setAccessibleName("Agent test results; select a row to inspect evidence")
        layout.addWidget(self.results, 1)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumHeight(190)
        self.output.setAccessibleName("Test execution records and report previews")
        self.details = Disclosure("Execution records and report details", self.output)
        layout.addWidget(self.details)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.status = QLabel(
            "Ready. Repeated measurement is the default after updating; ZIP export remains local."
        )
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.elapsed = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.go = button("Go • start new campaign", self.start, row, True)
        self.resume = button("Continue unfinished campaign", lambda: self.start(True), row)
        self.stop_button = button("Stop safely", self.cancel, row)
        self.stop_button.setEnabled(False)
        self.zip_button = button("Review / save diagnostic ZIP", self.export_zip, layout, True)
        self.zip_button.setToolTip(
            "Review and save all retained safe evidence, even after a partial run. Nothing uploads automatically."
        )
        self.approval = QCheckBox("I reviewed BOTH previews and approve opening both public GitHub drafts.")
        self.approval.setEnabled(False)
        sharing = QWidget()
        sharing_layout = QVBoxLayout(sharing)
        sharing_layout.setContentsMargins(0, 0, 0, 0)
        sharing_layout.addWidget(self.approval)
        self.share = button("Open both approved GitHub drafts", self.open_drafts, sharing_layout)
        self.github_sharing = Disclosure("Optional · share public GitHub issue drafts", sharing)
        layout.addWidget(self.github_sharing)
        self.share.setEnabled(False)
        self.approval.toggled.connect(self.share.setEnabled)
        self.results.cellClicked.connect(self.inspect)
        self.mode.currentIndexChanged.connect(self.refresh)
        self.agents.currentIndexChanged.connect(self.refresh)
        self.rows = {}
        self.refresh()

    @staticmethod
    def unknown(row):
        return (
            row.get("code") in UNKNOWN_CODES
            or row.get("status") not in ("passed", "failed")
            or row.get("evidence", {}).get("runtime_state") == "cancelled"
        )

    def update_dashboard(self):
        counts = {"immediate": 0, "corrected": 0, "failed": 0, "unknown": 0}
        for row in self.rows.values():
            key = (
                "unknown"
                if self.unknown(row)
                else "corrected"
                if row["status"] == "passed" and row.get("evidence", {}).get("completion_feedback_count")
                else "immediate"
                if row["status"] == "passed"
                else "failed"
            )
            counts[key] += 1
        for key, value in self.metric_values.items():
            value.setText(str(counts[key]))

    def export_zip(self):
        if self.worker and self.worker.isRunning():
            self.window.error("Stop safely or wait before exporting a snapshot.")
            return
        from .bundles_ui import BundleDialog

        try:
            scope = campaign_scope(self.window.store, self.agent(), self.mode.currentData())
            rows = [r["payload"] for r in self.window.store.diagnostic_reports()]
            campaign = next(
                (r for r in rows if r.get("kind") == "crew_campaign" and r.get("local_scope") == scope), None
            )
            if campaign is None:
                self.window.error(
                    "No saved campaign for this model and mode. Use Diagnose to select an older report."
                )
                return
            health = next((r for r in rows if r.get("kind") == "health"), None)
            self.bundle_dialog = BundleDialog(self.window, [campaign] + ([health] if health else []))
            self.bundle_dialog.show()
        except (ValueError, AttributeError) as exc:
            self.window.error(str(exc))

    def start_queued(self):
        """Recover a matching saved campaign; never repeat an uncertain attempt."""
        try:
            scope = campaign_scope(self.window.store, self.agent(), self.mode.currentData())
            resume = latest_resumable(self.window.store, scope) is not None
        except (ValueError, AttributeError):
            resume = False
        self.start(resume=resume)

    def agent(self):
        return next((a for a in self.window.store.agents() if a.id == self.agents.currentData()), None)

    def refresh(self):
        self.rows = {}
        self.identities = plan(self.mode.currentData())
        self.results.setRowCount(len(self.identities))
        titles = {f"{c.role}-{c.id}": f"{ROLES[c.role].name} • {c.title}" for c in ROLE_CASES}
        from .campaign import EXPERIMENTS

        titles.update(
            {
                identity: f"George • {name}: output allowance {cap}"
                for identity, (name, cap) in EXPERIMENTS.items()
            }
        )
        from .measurement import measurement_plan

        role_cases = {c.id: c for c in ROLE_CASES}
        for trial in measurement_plan():
            role = ROLES[role_cases[trial.case_id].role].name if trial.case_kind == "role" else "George"
            scenario = (
                role_cases[trial.case_id].title
                if trial.case_kind == "role"
                else {"unicode": "Unicode file round-trip", "noop": "Unchanged file check"}[trial.case_id]
            )
            arm = {
                "reference": "reference",
                "output_only": "output allowance",
                "coordinated": "output + time",
                "thinking_off": "thinking off (conditional)",
            }[trial.arm]
            total = 3 if trial.case_kind == "role" else 2
            titles[trial.id] = f"{role} • {scenario} • {arm} • {trial.repeat}/{total}"
        for index, identity in enumerate(self.identities):
            label = titles.get(identity, "George • " + identity)
            item = QTableWidgetItem(label)
            item.setToolTip(label + "\n" + identity)
            self.results.setItem(index, 0, item)
            self.results.setItem(index, 1, QTableWidgetItem("Ready"))
            self.results.setItem(index, 2, QTableWidgetItem(""))
            self.results.setItem(index, 3, QTableWidgetItem(""))
        self.progress.setRange(0, OFFLINE_CHECK_COUNT + len(self.identities))
        self.update_dashboard()
        try:
            scope = campaign_scope(self.window.store, self.agent(), self.mode.currentData())
            self.resume.setEnabled(latest_resumable(self.window.store, scope) is not None)
            self.zip_button.setEnabled(
                any(
                    row["payload"].get("kind") == "crew_campaign"
                    and row["payload"].get("local_scope") == scope
                    for row in self.window.store.diagnostic_reports()
                )
            )
        except (ValueError, AttributeError):
            self.resume.setEnabled(False)
            self.zip_button.setEnabled(False)

    def tick(self):
        self.elapsed += 1
        self.status.setText(
            f"Running • {self.elapsed // 60}m {self.elapsed % 60}s elapsed • Stop safely preserves results."
        )

    def start(self, resume=False):
        from .ui import Worker

        w = self.window
        if any(
            job and job.isRunning()
            for job in (w.worker, w.diagnostic_worker, w.discovery_worker, w.update_worker)
        ):
            w.error("Finish the current operation first.")
            return
        agent = self.agent()
        try:
            campaign_scope(w.store, agent, self.mode.currentData())
        except (ValueError, AttributeError) as exc:
            w.error(str(exc))
            return
        if self.mode.currentData() != "quick":
            ensure_roster(w.store, agent.primary)
            w.refresh_agents()
        w.store.set_setting("suite_agent", agent.id)
        self.rows, self.urls = {}, []
        self.refresh()
        self.progress.setValue(0)
        self.output.clear()
        self.zip_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.current_case.setText("Checking the app before local agent trials…")
        self.approval.setChecked(False)
        self.approval.setEnabled(False)
        for control in (self.go, self.resume, self.agents, self.mode):
            control.setEnabled(False)
        mode = self.mode.currentData()
        worker = Worker(
            lambda job: run_campaign(
                w.store, w.credentials, agent, job.cancel, job.activity.emit, mode, resume=bool(resume)
            ),
            w.credentials,
            w,
        )
        self.worker = w.diagnostic_worker = worker
        worker.activity.connect(lambda event: self.activity(event) if self.worker is worker else None)
        worker.succeeded.connect(lambda result: self.done(result) if self.worker is worker else None)
        worker.failed.connect(lambda error: self.failed(error) if self.worker is worker else None)
        worker.finished.connect(lambda: self.finished() if self.worker is worker else None)
        self.elapsed = 0
        self.timer.start(1000)
        worker.start()

    def failed(self, error):
        self.status.setText(
            "Campaign could not finish. Use Review / save diagnostic ZIP to export saved partial evidence."
        )
        self.window.error(error)

    def finished(self):
        self.timer.stop()
        self.go.setEnabled(True)
        self.agents.setEnabled(True)
        self.mode.setEnabled(True)
        self.zip_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        try:
            scope = campaign_scope(self.window.store, self.agent(), self.mode.currentData())
            self.resume.setEnabled(latest_resumable(self.window.store, scope) is not None)
        except (ValueError, AttributeError):
            self.resume.setEnabled(False)
        if self.worker and self.worker.cancel.is_set():
            self.status.setText(
                "Stopped. Results are saved. Continue skips completed and interrupted attempts."
            )

    def activity(self, event):
        kind, data = event["kind"], event["data"]
        if kind == "diagnostic.result":
            self.progress.setValue(self.progress.value() + 1)
            self.output.appendPlainText(f"App check: {data['id']} • {data['status']}")
        elif kind == "campaign.started":
            index = self.identities.index(data["id"])
            self.results.setItem(index, 1, QTableWidgetItem("Running…"))
            self.current_case.setText(self.results.item(index, 0).text())
            self.results.scrollToItem(self.results.item(index, 0))
        elif kind == "campaign.result":
            self.rows[data["id"]] = data
            index = self.identities.index(data["id"])
            evidence = data.get("evidence", {})
            self.progress.setValue(self.progress.value() + 1)
            for col, value in enumerate(
                (
                    (
                        "Passed after correction"
                        if evidence.get("completion_feedback_count")
                        else "Passed immediately"
                    )
                    if data["status"] == "passed"
                    else "Not completed"
                    if self.unknown(data)
                    else data["status"],
                    f"{data['duration_ms'] / 1000:.1f}s",
                    str(evidence.get("native_calls_total", "?")),
                ),
                1,
            ):
                item = QTableWidgetItem(value)
                if col == 1:
                    color = (
                        "#a8b8d2"
                        if self.unknown(data)
                        else "#89d6bd"
                        if data["status"] == "passed"
                        else "#ffb7c6"
                    )
                    item.setForeground(QColor(color))
                self.results.setItem(index, col, item)
            self.update_dashboard()
            self.output.appendPlainText(f"{data['id']}: {data['status']} • {data['code']}")
            for key, passed in evidence.get("requirement_checks", {}).items():
                if not passed:
                    self.output.appendPlainText("  Unmet: " + REQUIREMENT_LABELS.get(key, key))

    def inspect(self, index, column):
        if index >= len(self.identities):
            return
        data = self.rows.get(self.identities[index])
        if not data:
            return
        self.details.set_expanded(True)
        e = data.get("evidence", {})
        text = [f"\nDETAIL: {data['id']} • {data['code']}"]
        text.extend(
            ("PASS: " if passed else "UNMET: ") + REQUIREMENT_LABELS.get(key, key)
            for key, passed in e.get("requirement_checks", {}).items()
        )
        if e.get("provider_error_code") == "OUTPUT_LIMIT":
            text.append(
                "The model reached its output allowance before a complete response. Partial tool calls were not executed."
            )
        elif e.get("task_checks", {}).get("content_failures"):
            text.append(
                "The saved content or final answer failed an explicit acceptance requirement; a readback alone cannot prove correctness."
            )
        text.append("Mismatch diagnosis: " + str(e.get("mismatches", [])))
        text.append("Thinking request: " + str(e.get("thinking_mode", "default")))
        text.append("Per-call schema evidence: " + str(e.get("tool_diagnostics", [])))
        text.append("Initial content acceptance: " + str(e.get("initial_acceptance_checks", {})))
        text.append("Content acceptance: " + str(e.get("acceptance_checks", {})))
        text.append("Rejected response shape: " + str(e.get("failure_shape", {})))
        text.append("Task counters: " + str(e.get("task_checks", {})))
        text.append("Actions (no source or arguments): " + str(e.get("tool_timeline", [])))
        text.append("Provider: " + e.get("provider_error_code", "NONE"))
        self.output.appendPlainText("\n".join(text))

    def done(self, reports):
        campaign = reports[-1]
        self.current_case.setText("Results saved locally. Review the ZIP and share it when you choose.")
        self.update_dashboard()
        rows = campaign["checks"]
        skipped_thinking = sum(
            r.get("status") == "skipped" and r.get("code", "").startswith("THINKING_") for r in rows
        )
        if skipped_thinking:
            self.current_case.setText(
                f"Results saved. {skipped_thinking} conditional thinking trials were skipped because the required control was unavailable or not applicable."
            )
        repaired = sum(
            r["status"] == "passed" and bool(r.get("evidence", {}).get("completion_feedback_count"))
            for r in rows
        )
        passed = sum(r["status"] == "passed" for r in rows)
        incomplete = sum(
            r.get("code") in ("INTERRUPTED_CASE_NOT_REPLAYED", "CANCELLED", "CAMPAIGN_BUDGET_EXHAUSTED")
            or r["status"] in ("skipped", "warning")
            for r in rows
        )
        failed = sum(r["status"] == "failed" for r in rows) - sum(
            r["status"] == "failed"
            and r.get("code") in ("INTERRUPTED_CASE_NOT_REPLAYED", "CANCELLED", "CAMPAIGN_BUDGET_EXHAUSTED")
            for r in rows
        )
        self.status.setText(
            f"Finished • Passed immediately: {passed - repaired} • After correction: {repaired} • "
            f"Failed: {failed} • Not completed: {campaign['planned_cases'] - len(rows) + incomplete} • saved locally."
        )
        if campaign.get("mode") == "measurement":
            self.output.appendPlainText("Thinking controls: " + str(campaign.get("thinking_comparison", {})))
            self.output.appendPlainText(
                "Server observation (end of run): " + str(campaign.get("ollama_observation", {}))
            )
            from .measurement import summarize_trials

            self.output.appendPlainText(
                "Repeated measurement (unknown attempts excluded from failures): "
                + str(summarize_trials(campaign["checks"]))
            )
        if campaign.get("manifest_verified") is False:
            self.status.setText(
                "Benchmark integrity check failed. Saved results are diagnostic only; scores must not be compared."
            )
        previous = next(
            (
                r["payload"]
                for r in self.window.store.diagnostic_reports()
                if r["id"] != campaign["id"]
                and r["payload"].get("kind") == "crew_campaign"
                and r["payload"].get("local_scope") == campaign.get("local_scope")
                and r["payload"].get("state") in ("passed", "needs_attention")
            ),
            None,
        )
        if previous and campaign.get("mode") == "measurement":
            from .measurement import paired_diff

            self.output.appendPlainText("Paired comparison: " + str(paired_diff(previous, campaign)))
        if previous:
            self.output.appendPlainText(
                "Previous matching configuration: " + str(previous.get("summary", {}))
            )
        try:
            self.urls = [prepare_browser_draft(*issue_body(r, self.window.credentials)) for r in reports]
        except ReportingError:
            self.urls = []
            self.output.appendPlainText(
                "Browser report limit reached; records remain local. Review/export through Diagnose."
            )
        for index, url in enumerate(self.urls):
            fields = parse_qs(urlsplit(url).query)
            self.output.appendPlainText(
                f"\nEXACT PUBLIC PREVIEW {index + 1}\n{fields['title'][0]}\n{fields['body'][0]}"
            )
        self.approval.setEnabled(len(self.urls) == 2)
        self.output.appendPlainText(
            "Review / save diagnostic ZIP packages detailed evidence locally; you can drag it into your support chat. GitHub sharing is optional."
        )
        QApplication.beep()

    def open_drafts(self):
        if not self.approval.isChecked() or len(self.urls) != 2:
            return
        urls, self.urls = self.urls, []
        self.approval.setEnabled(False)
        self.share.setEnabled(False)
        for url in urls:
            if not webbrowser.open(url):
                self.output.appendPlainText("Browser unavailable. Copy URL:\n" + url)

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
