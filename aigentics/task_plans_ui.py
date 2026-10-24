"""Explicit plan authoring, single-step launch and manual revision verification."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QInputDialog,
    QMessageBox,
    QPlainTextEdit,
)
from .task_plans import TaskPlans, Step


class TaskPlanDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        from .ui import button

        self.window = window
        self.plans = TaskPlans(window.store, window.workspace)
        self.setWindowTitle("Project task plan • explicit checkpoints")
        self.resize(750, 500)
        layout = QVBoxLayout(self)
        label = QLabel(
            "Add small steps with expected outputs. Run one step, inspect results, then verify its checkpoint.\nChanged files block later steps. Interrupted attempts never replay automatically.\nPlans stay local (up to 16 steps/project, 32 projects). No automatic commits or Ralph restarts."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self.rows = QListWidget()
        layout.addWidget(self.rows)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        layout.addWidget(self.details)
        self.rows.currentRowChanged.connect(self.describe)
        for title, slot in [
            ("Add step", self.add),
            ("Run selected step", self.launch),
            ("Verify selected checkpoint", self.verify),
            ("Review and reset this step onward", self.reset),
            ("Remove selected and later steps", self.remove),
        ]:
            button(title, lambda checked=False, fn=slot: window.guarded(fn), layout)
        button("Close", self.accept, layout)
        self.refresh()

    def refresh(self):
        index = self.rows.currentRow()
        self.rows.clear()
        for i, s in enumerate(self.plans.steps()):
            self.rows.addItem(
                f"{i + 1}. {s.state.upper()} · {s.task[:120]}\nOutputs: {', '.join(s.outputs) or 'Manual acceptance; no file hashes'}"
            )
        if self.rows.count():
            self.rows.setCurrentRow(max(0, index))

    def describe(self, index):
        steps = self.plans.steps()
        if 0 <= index < len(steps):
            step = steps[index]
            self.details.setPlainText(
                step.task
                + "\n\nExpected outputs: "
                + ", ".join(step.outputs)
                + "\nState: "
                + step.state
                + "\nSession: "
                + (step.session or "none")
                + "\nCheckpoint revisions: "
                + str(step.hashes)
            )
        else:
            self.details.clear()

    def remove(self):
        self.idle()
        index = self.selected()
        if (
            QMessageBox.question(
                self,
                "Remove plan steps",
                "Remove this step and all later steps from the local plan? Project files and history remain.",
            )
            == QMessageBox.Yes
        ):
            self.plans.save(self.plans.steps()[:index])
            self.refresh()

    def selected(self):
        i = self.rows.currentRow()
        if i < 0:
            raise ValueError("Select a step")
        return i

    def idle(self):
        if any(j and j.isRunning() for j in (self.window.worker, self.window.diagnostic_worker)):
            raise ValueError("Finish or cancel the active operation before modifying a plan")

    def add(self):
        self.idle()
        task, ok = QInputDialog.getMultiLineText(self, "Step task", "Task and acceptance criteria:")
        if not ok or not task.strip():
            return
        outputs, ok = QInputDialog.getText(
            self, "Expected output files", "Relative paths, separated by commas:"
        )
        if not ok:
            return
        steps = self.plans.steps()
        steps.append(Step(task=task.strip(), outputs=[p.strip() for p in outputs.split(",") if p.strip()]))
        self.plans.save(steps)
        self.refresh()

    def launch(self):
        w = self.window
        if any(j and j.isRunning() for j in (w.worker, w.diagnostic_worker)):
            raise ValueError("Finish the active operation first")
        index = self.selected()
        from .tools import Workspace

        if Workspace(w.workspace).root != self.plans.ws.root:
            raise ValueError("The open project changed. Reopen its task plan.")
        step = self.plans.begin(index)
        w.task.setPlainText(step.task)
        w.expected_files.setText(",".join(step.outputs))
        w.conversation_mode.setCurrentIndex(w.conversation_mode.findData("fresh"))
        w.active_plan_step = (self.plans, index)
        self.accept()
        if not w.start_run():
            w.active_plan_step = None
            # Dispatch did not start: leave the step visibly uncertain for explicit review.

    def verify(self):
        self.idle()
        if (
            QMessageBox.question(
                self,
                "Verify checkpoint",
                "Have you reviewed the actual outcome and accepted this step? Current output hashes will be saved; this does not certify program behavior.",
            )
            == QMessageBox.Yes
        ):
            self.plans.checkpoint(self.selected())
            self.refresh()

    def reset(self):
        self.idle()
        if (
            QMessageBox.question(
                self,
                "Resolve previous attempt first",
                "Inspect files, history and any side effects first. Reset this step and invalidate all later checkpoints? No action is replayed until you explicitly Run again.",
            )
            == QMessageBox.Yes
        ):
            self.plans.reset(self.selected())
            self.refresh()
