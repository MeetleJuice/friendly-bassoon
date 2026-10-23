"""Native desktop presentation; workers never mutate widgets directly."""

import json
import os
import sys
import tempfile
import threading
from pathlib import Path
from uuid import uuid4
from PySide6.QtCore import QThread, Signal, QTimer, QStandardPaths, QLockFile
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QListWidget,
    QPlainTextEdit,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QTreeWidget,
    QTreeWidgetItem,
    QInputDialog,
)
from .credentials import Credentials
from .models import Agent, Profile, ModelRef, TOOLS
from .providers import Provider
from .runtime import Runtime
from .store import Store
from .tools import Workspace

STYLE = """
QWidget { background: #101721; color: #d9e3ef; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
QMainWindow { background: #101721; }
QTabWidget::pane { border: 1px solid #29374a; border-radius: 6px; }
QTabBar::tab { background: #192333; padding: 12px 24px; margin-right: 3px; }
QTabBar::tab:selected { background: #243d50; color: #69dbc6; }
QPlainTextEdit, QLineEdit, QListWidget, QComboBox, QSpinBox, QTreeWidget {
 background: #0c121b; border: 1px solid #304157; border-radius: 4px; padding: 6px; selection-background-color: #315971;
}
QLineEdit, QComboBox, QSpinBox { min-height: 24px; padding: 4px 6px; }
QPlainTextEdit { font-family: Consolas, monospace; }
QPushButton { background: #26394d; border: 1px solid #3c566e; border-radius: 5px; padding: 7px 12px; }
QPushButton:hover { background: #36546a; }
QPushButton:disabled { color: #657487; background: #192332; }
QPushButton#primary { background: #166b61; border-color: #2c9e8d; }
QLabel#title { font-size: 23px; font-weight: 600; color: #72e2cb; }
QCheckBox { padding: 3px; }
QSplitter::handle { background: #243247; width: 3px; }
"""


def button(text, callback, layout, primary=False):
    result = QPushButton(text)
    result.clicked.connect(callback)
    if primary:
        result.setObjectName("primary")
    layout.addWidget(result)
    return result


def panel():
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)
    return widget, layout


class Worker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)
    activity = Signal(object)
    approval = Signal(object)

    def __init__(self, function, credentials, parent=None):
        super().__init__(parent)
        self.function, self.credentials = function, credentials
        self.cancel = threading.Event()

    def approve(self, kind, details):
        request = {"kind": kind, "details": details, "done": threading.Event(), "allowed": False}
        self.approval.emit(request)
        while not request["done"].wait(0.05):
            if self.cancel.is_set():
                return False
        return request["allowed"] and not self.cancel.is_set()

    def run(self):
        try:
            self.succeeded.emit(self.function(self))
        except Exception as exc:
            self.failed.emit(self.credentials.redact(f"{type(exc).__name__}: {exc}"))


class Window(QMainWindow):
    def __init__(self, store, credentials):
        super().__init__()
        self.store, self.credentials = store, credentials
        self.runtime = Runtime(store, credentials)
        self.worker = None
        self.agent_id = None
        self.workspace = None
        self.parent_session = None
        self.lab_dir = tempfile.TemporaryDirectory(prefix="aigentics-lab-")
        self.setWindowTitle("Aigentics Desktop · Agent Engineering Studio")
        self.resize(1280, 860)
        self.setMinimumSize(900, 650)
        if not store.profiles():
            store.save_profile(Profile(id="ollama", name="Local Ollama"))
        if not store.agents():
            store.save_agent(Agent())
        root, layout = panel()
        title = QLabel("AIGENTICS  /  DESKTOP")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(QLabel("Local execution. Inspectable evidence. Agents you control."))
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.make_agents()
        self.make_workbench()
        self.setCentralWidget(root)
        self.statusBar().showMessage("Ready · Local diagnostics · No external telemetry")
        self.refresh_agents()
        self.refresh_profiles()
        self.refresh_history()

    def error(self, message):
        QMessageBox.warning(self, "Aigentics", self.credentials.redact(str(message)))

    def guarded(self, fn):
        try:
            return fn()
        except Exception as exc:
            self.error(exc)

    def make_agents(self):
        page, layout = panel()
        sections = QTabWidget()
        layout.addWidget(sections)
        self.tabs.addTab(page, "AGENTS")
        studio, sl = panel()
        split = QSplitter()
        sl.addWidget(split)
        library, ll = panel()
        ll.addWidget(QLabel("AGENT LIBRARY"))
        self.agent_list = QListWidget()
        self.agent_list.currentRowChanged.connect(self.load_agent)
        ll.addWidget(self.agent_list, 1)
        row = QHBoxLayout()
        ll.addLayout(row)
        button("New", self.new_agent, row)
        button("Read-only template", self.readonly_template, ll)
        button("Duplicate", self.duplicate_agent, row)
        button("Delete", self.delete_agent, row)
        row = QHBoxLayout()
        ll.addLayout(row)
        button("Import", self.import_agent, row)
        button("Export", self.export_agent, row)
        editor, el = panel()
        form = QFormLayout()
        el.addLayout(form)
        self.agent_name = QLineEdit()
        self.agent_description = QLineEdit()
        self.agent_profile = QComboBox()
        self.agent_model = QLineEdit()
        form.addRow("Name", self.agent_name)
        form.addRow("Description", self.agent_description)
        form.addRow("Provider profile", self.agent_profile)
        form.addRow("Model (exact installed name)", self.agent_model)
        el.addWidget(QLabel("Instructions"))
        self.instructions = QPlainTextEdit()
        el.addWidget(self.instructions, 2)
        tools_row = QHBoxLayout()
        el.addLayout(tools_row)
        self.tool_checks = {}
        for tool in TOOLS:
            check = QCheckBox(tool)
            self.tool_checks[tool] = check
            tools_row.addWidget(check)
        self.allow_writes = QCheckBox("Allow writes (every diff requires approval)")
        self.allow_commands = QCheckBox("Allow host commands (every command requires approval)")
        el.addWidget(self.allow_writes)
        el.addWidget(self.allow_commands)
        limits = QFormLayout()
        self.steps, self.seconds = QSpinBox(), QSpinBox()
        self.steps.setRange(1, 100)
        self.seconds.setRange(5, 3600)
        limits.addRow("Maximum model steps", self.steps)
        limits.addRow("Session time budget (seconds)", self.seconds)
        el.addLayout(limits)
        el.addWidget(QLabel('Ordered fallbacks: JSON list of {"profile_id": "…", "model": "…"}'))
        self.fallbacks = QPlainTextEdit("[]")
        self.fallbacks.setMaximumHeight(70)
        el.addWidget(self.fallbacks)
        self.agent_revision = QLabel()
        el.addWidget(self.agent_revision)
        button("Save agent", lambda: self.guarded(self.save_agent), el, True)
        split.addWidget(library)
        split.addWidget(editor)
        split.setStretchFactor(1, 3)
        sections.addTab(studio, "Studio")
        providers, pl = panel()
        pl.addWidget(QLabel("PROVIDER PROFILES · Keys stay in the OS vault or this process's memory"))
        self.profile_select = QComboBox()
        self.profile_select.currentIndexChanged.connect(self.load_profile)
        pl.addWidget(self.profile_select)
        self.profile_json = QPlainTextEdit()
        pl.addWidget(self.profile_json, 1)
        row = QHBoxLayout()
        pl.addLayout(row)
        button("Save profile", lambda: self.guarded(self.save_profile), row, True)
        button("New cloud profile", self.new_profile, row)
        button("Discover models / test connection", self.discover, row)
        creds = QFormLayout()
        self.credential_ref, self.credential_value = QLineEdit(), QLineEdit()
        self.credential_value.setEchoMode(QLineEdit.Password)
        creds.addRow("Credential reference (e.g. GROQ_API_KEY)", self.credential_ref)
        creds.addRow("Key (only when saving to OS vault)", self.credential_value)
        pl.addLayout(creds)
        row = QHBoxLayout()
        pl.addLayout(row)
        button("Save key to OS vault", self.save_credential, row)
        button("Load selected .env into memory", self.load_env, row)
        self.provider_output = QPlainTextEdit()
        self.provider_output.setReadOnly(True)
        self.provider_output.setMaximumHeight(150)
        pl.addWidget(self.provider_output)
        sections.addTab(providers, "Providers & credentials")
        lab, labl = panel()
        labl.addWidget(
            QLabel("AGENT LABORATORY · Same runtime, disposable scratch project, real model requests")
        )
        self.lab_agent = QComboBox()
        labl.addWidget(self.lab_agent)
        labl.addWidget(QLabel("Model override for this test only (blank uses the saved agent model)"))
        self.lab_model = QLineEdit()
        labl.addWidget(self.lab_model)
        self.lab_prompt = QPlainTextEdit(
            "List this project's files using your tools, then explain what you found."
        )
        self.lab_prompt.setMaximumHeight(100)
        labl.addWidget(self.lab_prompt)
        row = QHBoxLayout()
        labl.addLayout(row)
        self.lab_run = button("Run laboratory test", lambda: self.start_run(True), row, True)
        button("Cancel active run", self.cancel_run, row)
        self.lab_output = QPlainTextEdit()
        self.lab_output.setReadOnly(True)
        labl.addWidget(self.lab_output, 1)
        labl.addWidget(
            QLabel("Lab runs share the retention settings. Compare recorded runs in Workbench → History.")
        )
        sections.addTab(lab, "Laboratory")

    def make_workbench(self):
        page, layout = panel()
        self.tabs.addTab(page, "WORKBENCH")
        row = QHBoxLayout()
        layout.addLayout(row)
        button("Open project", self.open_project, row)
        button("Create project", self.create_project, row)
        self.project_label = QLabel("Choose a project folder")
        row.addWidget(self.project_label, 1)
        self.run_agent = QComboBox()
        row.addWidget(self.run_agent)
        split = QSplitter()
        layout.addWidget(split, 1)
        explorer, el = panel()
        el.addWidget(QLabel("PROJECT FILES"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemExpanded.connect(self.expand_directory)
        self.tree.itemDoubleClicked.connect(self.preview_file)
        el.addWidget(self.tree, 1)
        button("Refresh files", self.refresh_tree, el)
        center, cl = panel()
        cl.addWidget(QLabel("TASK & EXECUTION · Model completion is not proof that tests passed"))
        self.work_output = QPlainTextEdit()
        self.work_output.setReadOnly(True)
        cl.addWidget(self.work_output, 1)
        self.task = QPlainTextEdit()
        self.task.setPlaceholderText("Describe a focused coding task…")
        self.task.setMaximumHeight(110)
        cl.addWidget(self.task)
        self.capture = QCheckBox("Save redacted session content for resume (may include project code)")
        cl.addWidget(self.capture)
        row = QHBoxLayout()
        cl.addLayout(row)
        self.work_run = button("Run task", lambda: self.start_run(False), row, True)
        self.cancel_button = button("Cancel", self.cancel_run, row)
        button("New conversation", self.new_conversation, row)
        split.addWidget(explorer)
        split.addWidget(center)
        split.setStretchFactor(1, 3)
        history, hl = panel()
        hl.addWidget(QLabel("LOCAL EVIDENCE & HISTORY"))
        self.history = QListWidget()
        self.history.currentRowChanged.connect(self.show_history)
        hl.addWidget(self.history)
        row = QHBoxLayout()
        hl.addLayout(row)
        button("Refresh", self.refresh_history, row)
        button("Resume", self.resume_session, row)
        button("Export", self.export_session, row)
        button("Delete", self.delete_session, row)
        feedback_row = QHBoxLayout()
        hl.addLayout(feedback_row)
        button("Goal met", lambda: self.assess_session("goal_met"), feedback_row)
        button("Needs work", lambda: self.assess_session("needs_work"), feedback_row)
        self.history_details = QPlainTextEdit()
        self.history_details.setReadOnly(True)
        hl.addWidget(self.history_details, 1)
        retention = QFormLayout()
        self.retention_days, self.event_cap = QSpinBox(), QSpinBox()
        self.retention_days.setRange(1, 3650)
        self.event_cap.setRange(100, 1000000)
        self.retention_days.setValue(self.store.setting("retention_days", 30))
        self.event_cap.setValue(self.store.setting("max_events", 20000))
        retention.addRow("Retention days", self.retention_days)
        retention.addRow("Event budget", self.event_cap)
        hl.addLayout(retention)
        button("Apply retention & prune", self.apply_retention, hl)
        button("View evidence summary", self.show_metrics, hl)
        button("View configuration events", self.show_configuration_events, hl)
        evidence_tabs = QTabWidget()
        evidence_tabs.addTab(history, "History & diagnostics")
        self.file_preview = QPlainTextEdit()
        self.file_preview.setReadOnly(True)
        evidence_tabs.addTab(self.file_preview, "File preview")
        split.addWidget(evidence_tabs)
        split.setSizes([210, 620, 400])

    def refresh_agents(self):
        agents = self.store.agents()
        self.agent_list.blockSignals(True)
        self.agent_list.clear()
        for agent in agents:
            self.agent_list.addItem(agent.name)
        self.agent_list.blockSignals(False)
        for combo in (self.run_agent, self.lab_agent):
            previous = combo.currentData()
            combo.clear()
            for agent in agents:
                combo.addItem(agent.name, agent.id)
            index = combo.findData(previous)
            if index >= 0:
                combo.setCurrentIndex(index)
        index = next((i for i, a in enumerate(agents) if a.id == self.agent_id), 0)
        if agents:
            self.agent_list.setCurrentRow(index)
            self.load_agent(index)
        else:
            self.new_agent()

    def display_agent(self, agent):
        self.agent_id = agent.id
        self.editing_agent = agent
        self.agent_name.setText(agent.name)
        self.agent_description.setText(agent.description)
        index = self.agent_profile.findData(agent.primary.profile_id)
        if index < 0:
            self.agent_profile.addItem(agent.primary.profile_id, agent.primary.profile_id)
            index = self.agent_profile.count() - 1
        self.agent_profile.setCurrentIndex(index)
        self.agent_model.setText(agent.primary.model)
        self.instructions.setPlainText(agent.instructions)
        self.allow_writes.setChecked(agent.allow_writes)
        self.allow_commands.setChecked(agent.allow_commands)
        self.steps.setValue(agent.max_steps)
        self.seconds.setValue(agent.max_seconds)
        self.fallbacks.setPlainText(json.dumps([m.model_dump() for m in agent.fallbacks], indent=2))
        for name, check in self.tool_checks.items():
            check.setChecked(name in agent.tools)
        self.agent_revision.setText(f"Schema {agent.schema_version} · Revision {agent.revision} · {agent.id}")

    def load_agent(self, index):
        agents = self.store.agents()
        if 0 <= index < len(agents):
            self.display_agent(agents[index])

    def new_agent(self):
        self.display_agent(Agent(name="New agent"))

    def readonly_template(self):
        self.display_agent(
            Agent(
                name="Project reviewer",
                description="Inspect and explain a project without editing it",
                instructions="Review project files. Explain findings with file references. Do not propose writes or commands.",
                tools=["list_files", "read_file", "search"],
                allow_writes=False,
                allow_commands=False,
            )
        )

    def form_agent(self):
        return Agent.model_validate(
            self.editing_agent.model_dump()
            | {
                "name": self.agent_name.text().strip(),
                "description": self.agent_description.text(),
                "instructions": self.instructions.toPlainText(),
                "primary": {
                    "profile_id": self.agent_profile.currentData(),
                    "model": self.agent_model.text().strip(),
                },
                "tools": [name for name, check in self.tool_checks.items() if check.isChecked()],
                "allow_writes": self.allow_writes.isChecked(),
                "allow_commands": self.allow_commands.isChecked(),
                "max_steps": self.steps.value(),
                "max_seconds": self.seconds.value(),
                "fallbacks": json.loads(self.fallbacks.toPlainText()),
            }
        )

    def save_agent(self):
        agent = self.store.save_agent(self.form_agent())
        self.agent_id = agent.id
        self.refresh_agents()
        self.statusBar().showMessage(f"Saved {agent.name} revision {agent.revision}")

    def duplicate_agent(self):
        def perform():
            agent = self.form_agent().model_copy(
                update={"id": str(uuid4()), "name": self.agent_name.text() + " copy"}
            )
            self.agent_id = self.store.save_agent(agent).id
            self.refresh_agents()

        self.guarded(perform)

    def delete_agent(self):
        if (
            QMessageBox.question(
                self,
                "Delete agent?",
                "Delete this agent and its definition revisions? Session evidence is retained.",
            )
            == QMessageBox.Yes
        ):
            self.store.delete_agent(self.agent_id)
            self.agent_id = None
            self.refresh_agents()

    def import_agent(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import agent", "", "Agent JSON (*.json)")
        if path:

            def perform():
                source = Path(path)
                if source.stat().st_size > 100000:
                    raise ValueError("Agent file is too large")
                agent = Agent.model_validate_json(source.read_text(encoding="utf-8"))
                # Imports always get a new identity; they cannot overwrite an existing agent.
                agent = agent.model_copy(update={"id": str(uuid4())})
                self.agent_id = self.store.save_agent(agent).id
                self.refresh_agents()

            self.guarded(perform)

    def export_agent(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export agent (no credentials)", "agent.json", "JSON (*.json)"
        )
        if path:
            self.guarded(
                lambda: Path(path).write_text(
                    self.credentials.json(self.form_agent().model_dump(), indent=2), encoding="utf-8"
                )
            )

    def refresh_profiles(self):
        profiles = self.store.profiles()
        previous = self.agent_profile.currentData()
        self.profile_select.blockSignals(True)
        self.profile_select.clear()
        self.agent_profile.clear()
        for profile in profiles:
            self.profile_select.addItem(profile.name, profile.id)
            self.agent_profile.addItem(profile.name, profile.id)
        self.profile_select.blockSignals(False)
        index = self.agent_profile.findData(previous)
        if index >= 0:
            self.agent_profile.setCurrentIndex(index)
        self.load_profile()

    def load_profile(self, *_):
        profile = next((p for p in self.store.profiles() if p.id == self.profile_select.currentData()), None)
        if profile:
            self.profile_json.setPlainText(profile.model_dump_json(indent=2))
            self.credential_ref.setText(profile.credential_ref)

    def save_profile(self):
        profile = Profile.model_validate_json(self.profile_json.toPlainText())
        self.store.save_profile(profile)
        self.refresh_profiles()
        self.profile_select.setCurrentIndex(self.profile_select.findData(profile.id))

    def new_profile(self):
        self.profile_json.setPlainText(
            Profile(
                id="groq",
                name="Groq",
                kind="openai",
                base_url="https://api.groq.com/openai/v1",
                credential_ref="GROQ_API_KEY",
            ).model_dump_json(indent=2)
        )
        self.credential_ref.setText("GROQ_API_KEY")

    def start_worker(self, function, completed):
        if self.worker and self.worker.isRunning():
            self.error("An operation is already running. Cancel it or wait for completion.")
            return False
        if self.worker:
            self.worker.deleteLater()
        worker = Worker(function, self.credentials, self)
        self.worker = worker
        worker.succeeded.connect(completed)
        worker.failed.connect(self.error)
        worker.activity.connect(self.on_activity)
        worker.approval.connect(self.on_approval)
        worker.finished.connect(self.worker_finished)
        self.work_run.setEnabled(False)
        self.lab_run.setEnabled(False)
        worker.start()
        return True

    def worker_finished(self):
        self.work_run.setEnabled(True)
        self.lab_run.setEnabled(True)
        self.refresh_history()
        self.refresh_tree()
        self.statusBar().showMessage("Operation finished · inspect recorded results")

    def discover(self):
        def perform():
            profile = Profile.model_validate_json(self.profile_json.toPlainText())
            from .runtime import cancellable_call
            import time

            self.start_worker(
                lambda worker: cancellable_call(
                    lambda: Provider(profile, self.credentials).discover(),
                    worker.cancel,
                    time.monotonic() + profile.timeout_seconds,
                ),
                lambda models: self.provider_output.setPlainText(
                    "Connection succeeded. Models:\n" + "\n".join(models)
                ),
            )

        self.guarded(perform)

    def load_env(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select your .env (values stay in memory)", "", "All files (*)"
        )
        if path:
            self.guarded(
                lambda: self.provider_output.setPlainText(
                    "Loaded variable names:\n" + "\n".join(self.credentials.load_env(Path(path)))
                )
            )

    def save_credential(self):
        def perform():
            self.credentials.save(self.credential_ref.text().strip(), self.credential_value.text())
            self.credential_value.clear()
            self.provider_output.setPlainText("Credential saved to the OS credential service.")

        self.guarded(perform)

    def select_workspace(self, path):
        ws = Workspace(path)
        self.workspace = ws.root
        self.parent_session = None
        self.project_label.setText(f"{ws.root.name} · {ws.root}")
        self.refresh_tree()

    def open_project(self):
        path = QFileDialog.getExistingDirectory(self, "Choose project")
        if path:
            self.guarded(lambda: self.select_workspace(path))

    def create_project(self):
        parent = QFileDialog.getExistingDirectory(self, "Choose parent folder for new project")
        if not parent:
            return
        name, ok = QInputDialog.getText(self, "New project", "Folder name")
        if ok:

            def perform():
                if not name.strip() or name in (".", "..") or any(c in name for c in "/\\:"):
                    raise ValueError("Use a simple folder name")
                path = Path(parent) / name.strip()
                path.mkdir(exist_ok=False)
                self.select_workspace(path)

            self.guarded(perform)

    def refresh_tree(self):
        self.tree.clear()
        if self.workspace:
            self.guarded(lambda: self.populate_tree(None, "."))

    def populate_tree(self, parent, relative):
        entries = Workspace(self.workspace).listing(relative)["entries"]
        for entry in entries:
            path = str(Path(relative) / entry["name"])
            item = QTreeWidgetItem([entry["name"] + (" /" if entry["directory"] else "")])
            item.setData(0, 256, (path, entry["directory"]))
            if parent:
                parent.addChild(item)
            else:
                self.tree.addTopLevelItem(item)
            if entry["directory"]:
                item.addChild(QTreeWidgetItem(["…"]))

    def expand_directory(self, item):
        data = item.data(0, 256)
        if data and data[1]:
            item.takeChildren()
            self.guarded(lambda: self.populate_tree(item, data[0]))

    def preview_file(self, item, _column):
        data = item.data(0, 256)
        if data and not data[1]:
            self.guarded(
                lambda: self.file_preview.setPlainText(
                    self.credentials.redact(Workspace(self.workspace).read(data[0])["content"])
                )
            )

    def start_run(self, lab=False):
        def perform():
            agent_id = (self.lab_agent if lab else self.run_agent).currentData()
            agent = next((a for a in self.store.agents() if a.id == agent_id), None)
            if not agent:
                raise ValueError("Save and select an agent first")
            if lab and self.lab_model.text().strip():
                agent = agent.model_copy(
                    update={
                        "primary": ModelRef(
                            profile_id=agent.primary.profile_id, model=self.lab_model.text().strip()
                        )
                    }
                )
            workspace = Path(self.lab_dir.name) if lab else self.workspace
            task = (self.lab_prompt if lab else self.task).toPlainText().strip()
            if not workspace or not task:
                raise ValueError("Choose a project and enter a task")
            output = self.lab_output if lab else self.work_output
            capture, parent = self.capture.isChecked(), None if lab else self.parent_session
            self.active_output = output
            started = self.start_worker(
                lambda worker: self.runtime.run(
                    agent,
                    workspace,
                    task,
                    worker.approve,
                    worker.cancel,
                    worker.activity.emit,
                    capture,
                    parent,
                ),
                lambda result: self.run_completed(result, lab),
            )
            if started:
                output.appendPlainText("\nUSER\n" + self.credentials.redact(task) + "\n")
                self.statusBar().showMessage("Running · File edits and commands pause for your approval")

        self.guarded(perform)

    def run_completed(self, result, lab):
        sid, state = result
        if not lab:
            self.parent_session = sid
        self.statusBar().showMessage(f"Session {state} · {sid}")

    def on_activity(self, event):
        output = getattr(self, "active_output", self.work_output)
        if event["kind"] == "assistant.text":
            text = "AGENT\n" + event["data"]["text"]
        else:
            text = event["kind"] + "  " + json.dumps(event["data"], ensure_ascii=False)
        output.appendPlainText(text)
        # Bound live widgets as well as the persistent store.
        output.document().setMaximumBlockCount(3000)

    def on_approval(self, request):
        if not self.worker or self.worker.cancel.is_set():
            request["done"].set()
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Review proposed " + request["kind"])
        dialog.resize(850, 600)
        layout = QVBoxLayout(dialog)
        label = (
            "Apply only this file change?"
            if request["kind"] == "write_file"
            else (
                "Run this command on your computer? It can access files and networks outside the project. "
                "The project folder is not an OS sandbox. Only approve commands you understand."
            )
        )
        warning = QLabel(label)
        warning.setWordWrap(True)
        layout.addWidget(warning)
        detail = QPlainTextEdit()
        detail.setReadOnly(True)
        detail.setPlainText(
            self.credentials.redact(json.dumps(request["details"], indent=2))
            if request["kind"] != "write_file"
            else self.credentials.redact(request["details"]["path"] + "\n\n" + request["details"]["diff"])
        )
        layout.addWidget(detail)
        actions = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        actions.button(QDialogButtonBox.Yes).setText("Approve once")
        actions.button(QDialogButtonBox.No).setText("Deny")
        actions.button(QDialogButtonBox.No).setDefault(True)
        actions.accepted.connect(dialog.accept)
        actions.rejected.connect(dialog.reject)
        layout.addWidget(actions)
        timer = QTimer(dialog)
        timer.timeout.connect(lambda: dialog.reject() if self.worker.cancel.is_set() else None)
        timer.start(100)
        request["allowed"] = dialog.exec() == QDialog.Accepted
        request["done"].set()

    def cancel_run(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel.set()
            self.statusBar().showMessage("Cancellation requested")

    def new_conversation(self):
        self.parent_session = None
        self.work_output.clear()

    def refresh_history(self):
        self.history_rows = self.store.sessions()
        self.history.clear()
        for row in self.history_rows:
            agent = Agent.model_validate_json(row["agent"])
            self.history.addItem(f"{row['created'][:19]} · {agent.name} · {row['state']}")

    def selected_session(self):
        i = self.history.currentRow()
        return self.history_rows[i] if 0 <= i < len(self.history_rows) else None

    def show_history(self, *_):
        session = self.selected_session()
        if session:
            self.history_details.setPlainText(
                json.dumps(
                    {
                        "session": session,
                        "events": self.store.events(session["id"]),
                        "user_assessment": self.store.assessment(session["id"]),
                    },
                    indent=2,
                )
            )

    def resume_session(self):
        session = self.selected_session()
        if not session:
            return
        if session["state"] == "running":
            self.error("Wait for this session to finish")
            return
        if not self.store.messages(session["id"]):
            self.error(
                "This run used metadata-only storage. Its timeline is available, but there is no transcript to resume."
            )
            return

        def perform():
            self.select_workspace(session["workspace"])
            agent = Agent.model_validate_json(session["agent"])
            index = self.run_agent.findData(agent.id)
            if index < 0:
                raise ValueError("This agent was deleted; import or create it before resuming")
            self.run_agent.setCurrentIndex(index)
            self.parent_session = session["id"]
            self.work_output.clear()
            self.work_output.appendPlainText(
                "RESUMING CONVERSATION · using the currently saved agent revision; previous tools will not rerun"
            )
            for message in self.store.messages(session["id"]):
                if message["role"] in ("user", "assistant") and message.get("content"):
                    self.work_output.appendPlainText(message["role"].upper() + "\n" + message["content"])
            self.capture.setChecked(True)

        self.guarded(perform)

    def export_session(self):
        session = self.selected_session()
        if session:
            path, _ = QFileDialog.getSaveFileName(
                self, "Export local evidence (review before sharing)", "session.json", "JSON (*.json)"
            )
            if path:
                self.guarded(lambda: self.store.export(session["id"], Path(path)))

    def delete_session(self):
        session = self.selected_session()
        if (
            session
            and session["state"] != "running"
            and QMessageBox.question(
                self, "Delete local history?", "Delete this session, its transcript and diagnostic events?"
            )
            == QMessageBox.Yes
        ):
            self.store.delete_session(session["id"])
            self.runtime._conversations.pop(session["id"], None)
            if self.parent_session == session["id"]:
                self.parent_session = None
            self.history_details.clear()
            self.refresh_history()

    def assess_session(self, label):
        session = self.selected_session()
        if not session:
            return
        note, ok = QInputDialog.getMultiLineText(
            self, "Save your assessment locally", "Optional note (saved with this session; no credentials):"
        )
        if ok:
            self.guarded(lambda: self.store.assess(session["id"], label, note))
            self.show_history()

    def show_metrics(self):
        self.history_details.setPlainText(json.dumps(self.store.metrics(), indent=2))

    def show_configuration_events(self):
        self.history_details.setPlainText(json.dumps(self.store.events(None), indent=2))

    def apply_retention(self):
        self.store.set_setting("retention_days", self.retention_days.value())
        self.store.set_setting("max_events", self.event_cap.value())
        self.store.event(
            None,
            "configuration.retention_changed",
            {"days": self.retention_days.value(), "event_cap": self.event_cap.value()},
        )
        self.store.prune()
        self.refresh_history()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.cancel_run()
            self.statusBar().showMessage("Stopping the current operation. Close again once it finishes.")
            event.ignore()
            return
        self.lab_dir.cleanup()
        self.store.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Aigentics Desktop")
    app.setOrganizationName("Aigentics")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    data = Path(
        os.environ.get("AIGENTICS_DATA_DIR")
        or QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    )
    data.mkdir(parents=True, exist_ok=True)
    instance_lock = QLockFile(str(data / "aigentics.lock"))
    if not instance_lock.tryLock(0):
        QMessageBox.warning(
            None, "Aigentics already running", "Another Aigentics instance is using this data folder."
        )
        return
    credentials = Credentials()
    window = Window(Store(data / "aigentics.sqlite3", credentials), credentials)
    window.show()
    sys.exit(app.exec())
