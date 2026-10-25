"""Review exact diagnostic ZIP contents and save locally, independently of run completion."""

import hashlib
from pathlib import Path
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QCheckBox, QFileDialog
from .bundles import build_bundle, save_bundle


class BundleDialog(QDialog):
    def __init__(self, window, reports):
        super().__init__(window)
        from .ui import button

        self.window = window
        self.data, preview = build_bundle(reports, window.credentials)
        self.setWindowTitle("Review and save diagnostic ZIP")
        self.resize(900, 700)
        layout = QVBoxLayout(self)
        label = QLabel(
            "Partial and completed reports can be exported. Review the exact contents below. Nothing uploads automatically. Save the ZIP, then drag it into your support chat when you choose."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlainText(preview)
        layout.addWidget(self.preview)
        self.digest = hashlib.sha256(self.data).hexdigest()
        self.status = QLabel(f"ZIP: {len(self.data)} bytes • SHA256 {self.digest}")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.approved = QCheckBox("I reviewed these contents and approve saving this ZIP locally.")
        layout.addWidget(self.approved)
        self.save = button("Save approved ZIP", self.save_zip, layout)
        self.save.setEnabled(False)
        self.approved.toggled.connect(self.save.setEnabled)

    def save_zip(self):
        if not self.approved.isChecked():
            return
        directory = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save diagnostic ZIP",
            str(Path(directory) / f"aigentics-diagnostics-{self.digest[:12]}.zip"),
            "ZIP (*.zip)",
        )
        if path:

            def write():
                if hashlib.sha256(self.data).hexdigest() != self.digest:
                    raise ValueError("Archive changed; review it again before saving")
                save_bundle(path, self.data)
                self.status.setText(
                    "Saved: "
                    + path
                    + " • Drag this ZIP into your support chat when ready. Nothing was uploaded."
                )

            self.window.guarded(write)
