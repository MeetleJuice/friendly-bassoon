"""Metadata-only API checks, saved catalogs and visible local retention controls."""

import json
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QPlainTextEdit,
    QComboBox,
    QSpinBox,
    QMessageBox,
)
from .catalog import CatalogRunner, catalog_age
from .ui import Worker, button


class RecordsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window, self.store = window, window.store
        self.runner_factory = CatalogRunner
        self.setWindowTitle("Aigentics · API checks, models & local data")
        self.resize(940, 780)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        api = QWidget()
        content = QVBoxLayout(api)
        note = QLabel(
            "One model-list request per unique configured connection, up to four at once. "
            "No prompts or generation calls. Provider request limits can still apply. "
            "Model availability does not establish coding or tool-call compatibility."
        )
        note.setWordWrap(True)
        content.addWidget(note)
        self.status = QLabel("Ready. Saved model catalogs load without network requests.")
        self.status.setWordWrap(True)
        content.addWidget(self.status)
        row = QHBoxLayout()
        content.addLayout(row)
        self.run_button = button("Test APIs / Refresh models", self.start, row, True)
        button("Cancel checks", self.cancel, row)
        self.history = QComboBox()
        self.history.currentIndexChanged.connect(self.show_report)
        content.addWidget(self.history)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        content.addWidget(self.output, 1)
        button("Review GitHub report", self.review, content)
        self.catalog = QPlainTextEdit()
        self.catalog.setReadOnly(True)
        content.addWidget(self.catalog, 1)
        tabs.addTab(api, "API checks & models")
        data = QWidget()
        retention = QVBoxLayout(data)
        explanation = QLabel(
            "Local records live in the app's data folder, separate from installation and projects. "
            "Only explicitly approved reports go to GitHub. Exported files and public issues have separate retention."
        )
        explanation.setWordWrap(True)
        retention.addWidget(explanation)
        self.inventory = QPlainTextEdit()
        self.inventory.setReadOnly(True)
        retention.addWidget(self.inventory, 1)
        form = QFormLayout()
        retention.addLayout(form)
        self.days, self.events, self.reports, self.budget = QSpinBox(), QSpinBox(), QSpinBox(), QSpinBox()
        for widget, setting, default, low, high in (
            (self.days, "retention_days", 30, 1, 3650),
            (self.events, "max_events", 20000, 100, 1000000),
            (self.reports, "max_reports", 20, 5, 200),
            (self.budget, "report_storage_mb", 10, 1, 100),
        ):
            widget.setRange(low, high)
            widget.setValue(self.store.setting(setting, default))
        form.addRow("Keep records for days", self.days)
        form.addRow("Session/configuration event budget", self.events)
        form.addRow("Maximum completed diagnostic/API reports", self.reports)
        form.addRow("Report and model-catalog budget (MB)", self.budget)
        hint = QLabel(
            "Oldest completed records are pruned first; running sessions/reports are protected. "
            "The MB limit covers reports/catalogs, not the entire database. Up to three pre-update "
            "backups are kept within the age limit; backups may contain previously saved session content."
        )
        hint.setWordWrap(True)
        retention.addWidget(hint)
        row = QHBoxLayout()
        retention.addLayout(row)
        button("Apply retention & prune", self.prune, row)
        button("Refresh inventory", self.refresh, row)
        button(
            "Open local data folder",
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.path.parent))),
            row,
        )
        button("Clear saved model catalogs", self.clear_catalogs, retention)
        tabs.addTab(data, "Data & retention")
        button("Close", self.hide, layout)
        self.refresh()

    def refresh(self, selected=None):
        self.rows = [
            row for row in self.store.diagnostic_reports() if row["payload"].get("kind") == "api_models"
        ]
        self.history.blockSignals(True)
        self.history.clear()
        for row in self.rows:
            self.history.addItem(row["created"][:19] + " · " + row["state"], row["id"])
        self.history.blockSignals(False)
        index = self.history.findData(selected) if selected else 0
        if index >= 0 and self.rows:
            self.history.setCurrentIndex(index)
            self.show_report(index)
        else:
            self.output.clear()
        catalogs = self.store.catalogs()
        lines = []
        for profile in self.store.profiles():
            cached = catalogs.get(profile.id)
            lines.append(profile.name)
            if cached:
                age = catalog_age(cached["fetched"])
                lines.append(
                    f"Fetched {cached['fetched']} · {age // 3600} hours old"
                    + (" · STALE: refresh recommended" if age >= 86400 else "")
                    + (" · first page only" if cached["partial"] else "")
                )
                lines.extend(cached["models"])
            else:
                lines.append("No retained catalog for this connection.")
            lines.append("")
        self.catalog.setPlainText("\n".join(lines))
        inventory = self.store.data_inventory()
        self.inventory.setPlainText(
            "Data folder: "
            + str(self.store.path.parent)
            + "\n\n"
            + f"Saved sessions: {inventory['sessions']}\nSaved conversation messages: {inventory['messages']}\n"
            f"Execution/configuration records: {inventory['events']}\nTest reports: {inventory['diagnostics']}\n"
            f"Saved provider catalogs: {inventory['model_catalogs']}\n"
            f"Remembered projects: {inventory['projects']}\n"
            f"Database and working files: {inventory['database_bytes'] / 1048576:.2f} MB\n"
            f"Pre-update backups: {inventory['backups_count']} ({inventory['backups_bytes'] / 1048576:.2f} MB)\n"
            f"Cached installers: {inventory['updates_count']} ({inventory['updates_bytes'] / 1048576:.2f} MB)\n\n"
            "Session content remains opt-in. No background cloud generation or report upload."
        )

    def show_report(self, index):
        if 0 <= index < len(self.rows):
            report = self.rows[index]["payload"]
            profiles = {p.id: p.name for p in self.store.profiles()}
            lines = ["Report " + report["id"], "Result: " + report["state"]]
            for check in report.get("checks", []):
                names = ", ".join(profiles.get(p, p) for p in check["evidence"].get("profile_ids", []))
                lines.extend(
                    [
                        "",
                        names + " · " + check["status"].upper() + " · " + check["code"],
                        check["message"],
                        json.dumps(check["evidence"], sort_keys=True),
                    ]
                )
            self.output.setPlainText("\n".join(lines))

    def start(self):
        window = self.window
        if any(
            job and job.isRunning()
            for job in (window.worker, window.diagnostic_worker, window.discovery_worker)
        ):
            self.status.setText(
                "Wait for the current task, diagnostics or key discovery to finish, then try again."
            )
            return
        if window.diagnostic_worker:
            window.diagnostic_worker.deleteLater()
        runner = self.runner_factory(self.store, window.credentials)
        worker = Worker(lambda job: runner.run(job.cancel, job.activity.emit), window.credentials, window)
        window.diagnostic_worker = worker
        self.run_button.setEnabled(False)
        self.status.setText("Checking configured APIs with model-list requests only…")
        worker.activity.connect(
            lambda event: self.status.setText(
                "Checked " + event["data"]["id"] + " · " + event["data"]["code"]
            )
        )
        worker.succeeded.connect(self.completed)
        worker.failed.connect(self.failed)
        worker.finished.connect(lambda: self.run_button.setEnabled(True))
        worker.start()

    def completed(self, report):
        self.status.setText(
            "API checks finished: "
            + report["state"].replace("_", " ")
            + ". Saved locally. No generation calls."
        )
        self.window.load_catalog_choices()
        self.refresh(report["id"])
        QApplication.beep()

    def failed(self, message):
        self.status.setText(message)
        self.store.recover_diagnostics()
        self.refresh()

    def cancel(self):
        if self.window.diagnostic_worker and self.window.diagnostic_worker.isRunning():
            self.window.diagnostic_worker.cancel.set()
            self.status.setText(
                "Cancelling. In-flight model-list requests may take up to their network timeout."
            )

    def review(self):
        report_id = self.history.currentData()
        if report_id:
            self.window.open_diagnostics(False)
            dialog = self.window.diagnostics_dialog
            dialog.refresh_reports(report_id)
            dialog.review()

    def prune(self):
        if (
            QMessageBox.question(
                self,
                "Apply retention?",
                "Apply these limits and permanently prune older local records? "
                "Exports and GitHub issues remain separate.",
            )
            != QMessageBox.Yes
        ):
            return
        for name, widget in (
            ("retention_days", self.days),
            ("max_events", self.events),
            ("max_reports", self.reports),
            ("report_storage_mb", self.budget),
        ):
            self.store.set_setting(name, widget.value())
        self.store.prune()
        self.window.retention_days.setValue(self.days.value())
        self.window.event_cap.setValue(self.events.value())
        self.window.load_catalog_choices()
        self.window.refresh_history()
        self.refresh()

    def clear_catalogs(self):
        if (
            QMessageBox.question(
                self,
                "Clear catalogs?",
                "Delete locally saved model lists? Provider profiles, keys and agents are kept.",
            )
            == QMessageBox.Yes
        ):
            self.store.clear_catalogs()
            self.window.model_lists.clear()
            self.window.refresh_model_choices()
            self.refresh()
