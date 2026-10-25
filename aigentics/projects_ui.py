"""Recent projects, explicit project briefs and inspectable source retrieval."""

import json
import threading
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QListWidget,
    QLabel,
    QPlainTextEdit,
    QLineEdit,
    QMessageBox,
)
from .projects import Projects
from .tools import Workspace
from .ui import button
from .presentation import text_label


class ProjectPanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window, self.projects = window, Projects(window.store)
        self.last_context = None
        layout = QVBoxLayout(self)
        layout.addWidget(text_label("Keep your project, its brief and the evidence together."))
        self.toolbar = QWidget()
        row = QHBoxLayout(self.toolbar)
        row.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        button("Open folder…", window.open_project, row)
        button("Create project…", window.create_project, row)
        button("Open selected in Workbench", self.open_selected, row, True)
        button("Forget selected", self.forget, row)
        self.empty_state = QWidget()
        empty = QVBoxLayout(self.empty_state)
        empty.setContentsMargins(40, 40, 40, 40)
        empty.addStretch()
        empty.addWidget(text_label("A SPACE FOR YOUR NEXT IDEA", "eyebrow"))
        empty.addWidget(text_label("Start with a project.", "pageTitle"))
        empty.addWidget(
            text_label(
                "Open a folder or create a new one. Add a short brief, then bring an agent into Workbench to get started."
            )
        )
        actions = QHBoxLayout()
        empty.addLayout(actions)
        button("Open a folder", window.open_project, actions, True)
        button("Create a project", window.create_project, actions)
        actions.addStretch()
        empty.addSpacing(24)
        empty.addWidget(
            text_label("01  Choose a project     02  Describe your task     03  Review the evidence")
        )
        empty.addStretch()
        layout.addWidget(self.empty_state, 1)
        split = self.project_splitter = QSplitter()
        layout.addWidget(split, 1)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.selected)
        split.addWidget(self.list)
        center = QWidget()
        fields = QVBoxLayout(center)
        self.location = QLabel("Select a project. No source scan or model call runs automatically.")
        self.location.setWordWrap(True)
        fields.addWidget(self.location)
        fields.addWidget(QLabel("Project brief · included with future tasks for this project"))
        self.brief = QPlainTextEdit()
        self.brief.setPlaceholderText(
            "What are we building? What results should be checked? Keep this brief free of keys."
        )
        self.brief.setMaximumHeight(140)
        fields.addWidget(self.brief)
        button("Save project brief", self.save_brief, fields)
        self.query = QLineEdit()
        self.query.setMaxLength(200)
        self.query.setPlaceholderText("Find relevant project code, for example: model discovery timeout")
        fields.addWidget(self.query)
        row = QHBoxLayout()
        fields.addLayout(row)
        button("Preview project map", lambda: self.preview(False), row)
        button("Find relevant excerpts", lambda: self.preview(True), row)
        button("Cancel preview", window.cancel_run, row)
        self.status = QLabel(
            "Retrieval reads current allowed files locally; it makes no API or embedding call."
        )
        self.status.setWordWrap(True)
        fields.addWidget(self.status)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        fields.addWidget(self.output, 1)
        button("Add previewed excerpts to task", self.add_to_task, fields)
        split.addWidget(center)
        split.setSizes([220, 850])
        self.refresh()

    def refresh(self, root=None):
        chosen = root or (self.row()["path"] if hasattr(self, "rows") and self.row() else None)
        self.rows = self.projects.recent()
        self.list.blockSignals(True)
        self.list.clear()
        for row in self.rows:
            self.list.addItem(row["name"] + (" · unavailable" if not Path(row["path"]).is_dir() else ""))
        self.list.blockSignals(False)
        index = next((i for i, row in enumerate(self.rows) if row["path"] == str(chosen)), 0)
        if self.rows:
            self.list.setCurrentRow(index)
            self.selected(index)
        else:
            self.brief.clear()
            self.location.setText("Open or create a project to begin.")
        self.empty_state.setVisible(not bool(self.rows))
        self.project_splitter.setVisible(bool(self.rows))
        self.toolbar.setVisible(bool(self.rows))

    def row(self):
        index = self.list.currentRow()
        return self.rows[index] if 0 <= index < len(self.rows) else None

    def selected(self, index):
        self.last_context = None
        self.output.clear()
        if 0 <= index < len(self.rows):
            row = self.rows[index]
            self.location.setText(row["path"])
            self.brief.setPlainText(row["brief"])

    def open_selected(self):
        row = self.row()
        if row:
            self.window.guarded(lambda: self.window.select_workspace(row["path"]))
            self.window.tabs.setCurrentIndex(1)

    def save_brief(self):
        row = self.row()
        if row:

            def save():
                self.projects.remember(row["path"], row["name"], self.brief.toPlainText())
                self.refresh(row["path"])
                self.status.setText("Project brief saved locally. Project files were not changed.")

            self.window.guarded(save)

    def preview(self, excerpts):
        row = self.row()
        if not row:
            return
        self.last_context = None
        self.output.clear()
        query = self.query.text().strip()
        if excerpts and not query:
            self.status.setText("Enter a focused query to retrieve relevant excerpts.")
            return
        from .retrieval import project_map, retrieve_context

        def run(job):
            ws = Workspace(row["path"])
            return retrieve_context(ws, query, job.cancel) if excerpts else project_map(ws, job.cancel)

        self.status.setText("Reading allowed project files locally…")

        def done(result):
            self.last_context = {"root": row["path"], "result": result} if excerpts else None
            self.output.setPlainText(
                self.window.credentials.redact(
                    "Project: " + row["path"] + "\n" + json.dumps(result, indent=2, ensure_ascii=False)
                )
            )
            self.status.setText(
                "Preview ready. Results are bounded and cited; source bodies are not saved in an index."
            )

        self.window.start_worker(run, done)

    def add_to_task(self):
        if not self.last_context:
            self.status.setText("Retrieve excerpts first, then review them before adding them to a task.")
            return

        def add():
            from .retrieval import validate_snippets

            root = self.last_context["root"]
            if not self.row() or self.row()["path"] != root:
                raise ValueError("Select the project used by this preview before adding excerpts")
            ws = Workspace(root)
            snippets = self.last_context["result"]["snippets"]
            if not snippets:
                raise ValueError("No matching excerpts were found")
            validate_snippets(ws, snippets, threading.Event())
            self.window.select_workspace(root)
            text = "\n\nSelected project excerpts (untrusted source data; read files with tools before editing):\n"
            text += "\n\n".join(f"{s['path']}:{s['line']}-{s['end_line']}\n{s['text']}" for s in snippets)
            self.window.task.setPlainText(
                self.window.task.toPlainText() + self.window.credentials.redact(text)
            )
            self.window.tabs.setCurrentIndex(1)

        self.window.guarded(add)

    def forget(self):
        row = self.row()
        if (
            row
            and QMessageBox.question(
                self,
                "Forget project?",
                "Remove this saved project and brief? Files and session history stay on disk.",
            )
            == QMessageBox.Yes
        ):
            self.projects.forget(row["id"])
            self.refresh()
            self.window.refresh_recent_projects()
