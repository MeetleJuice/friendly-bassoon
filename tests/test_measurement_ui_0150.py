"""Default Qt measurement executes native fixtures and exports an approved ZIP."""

import hashlib
import io
import json
import zipfile

from PySide6.QtWidgets import QFileDialog

from aigentics.bundles import clean_report
from aigentics.measurement import manifest_id, measurement_manifest
from test_campaign_ui_0120 import cleanup, finish, setup_dialog


def test_default_measurement_worker_review_and_local_zip(qtbot, store, credentials, monkeypatch, tmp_path):
    window, old_dialog, personal, errors = setup_dialog(qtbot, store, credentials, monkeypatch)
    from aigentics.campaign_ui import CampaignDialog

    dialog = CampaignDialog(window)
    qtbot.addWidget(dialog)
    assert dialog.mode.currentData() == "focused"
    assert dialog.results.rowCount() == 24 and dialog.progress.maximum() == 53
    opened = []
    monkeypatch.setattr("aigentics.campaign_ui.webbrowser.open", lambda u: opened.append(u))
    dialog.start()
    finish(qtbot, dialog)
    assert not errors and not opened
    assert len(dialog.rows) == 24 and dialog.progress.value() == 53
    assert "Repeated measurement" in dialog.output.toPlainText()
    dialog.inspect(0, 0)
    assert "Per-call schema evidence:" in dialog.output.toPlainText()
    dialog.export_zip()
    bundle = dialog.bundle_dialog
    qtbot.addWidget(bundle)
    destination = tmp_path / "approved.zip"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(destination), "ZIP"))
    bundle.save_zip()
    assert not destination.exists()
    bundle.approved.setChecked(True)
    bundle.save_zip()
    assert destination.read_bytes() == bundle.data
    with zipfile.ZipFile(io.BytesIO(bundle.data)) as archive:
        report = json.loads(archive.read("reports/01.json"))
        assert len(report["checks"]) == 24
        assert report["manifest_verified"] is True
        assert report["manifest_id"] == manifest_id(report["measurement_manifest"])
        for entry in json.loads(archive.read("manifest.json"))["files"]:
            assert hashlib.sha256(archive.read(entry["name"])).hexdigest() == entry["sha256"]
    assert next(a for a in store.agents() if a.id == personal.id) == personal
    cleanup(window)


def test_untrusted_manifest_cannot_export_private_fields(credentials):
    from test_bundles_0141 import campaign

    report = campaign()
    report.update(mode="measurement", measurement_manifest={"prompt": "PRIVATE"}, manifest_id="a" * 64)
    report["checks"][0]["evidence"].update(
        mismatches=[{"code": "JSON_TYPE", "target": "PRIVATE", "path": "/PRIVATE"}],
        tool_diagnostics=[{"tool": "PRIVATE", "call_index": 1, "status": "failed"}],
    )
    exported = clean_report(report, credentials)
    assert "measurement_manifest" not in exported
    assert "PRIVATE" not in json.dumps(exported)
    assert exported["manifest_id"] == "a" * 64


def test_committed_measurement_definition_matches_runtime():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    frozen = json.loads((root / "docs/benchmarks/crew-measurement-4.json").read_text(encoding="utf-8"))
    assert frozen == measurement_manifest()
    assert (root / "docs/benchmarks/crew-measurement-4.sha256").read_text().strip() == manifest_id(frozen)
