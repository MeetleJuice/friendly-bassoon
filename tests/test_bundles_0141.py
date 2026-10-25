import hashlib
import io
import json
import zipfile
import pytest
from aigentics.bundles import build_bundle, save_bundle
from aigentics.evidence import base_report


def campaign():
    r = base_report("crew_campaign", "crew-campaign-3", "PRIVATE")
    r.update(
        state="interrupted",
        planned_cases=66,
        local_configuration={"path": "PRIVATE"},
        summary={"PRIVATE": "PRIVATE"},
    )
    r["checks"] = [
        {
            "id": "baseline-edit",
            "status": "failed",
            "code": "ROLE_REQUIREMENTS_NOT_MET",
            "duration_ms": 1,
            "message": "PRIVATE",
            "evidence": {
                "local_path": "PRIVATE",
                "request_traces": [
                    {
                        "step": 2,
                        "duration_ms": 55,
                        "request_chars": 1234,
                        "content": "PRIVATE",
                        "response_shape": {"thinking_chars": 44, "thinking": "PRIVATE"},
                        "usage": {"eval_count": 123, "PRIVATE": "PRIVATE"},
                    }
                ],
                "tool_timeline": [
                    {
                        "tool": "write_file",
                        "status": "succeeded",
                        "duration_ms": 5,
                        "verified": True,
                        "path": "PRIVATE",
                        "arguments": "PRIVATE",
                    }
                ],
                "initial_acceptance_checks": {"OUTPUT_CONTENT": False},
                "acceptance_checks": {"OUTPUT_CONTENT": True},
            },
        }
    ]
    return r


def test_partial_zip_contains_rich_safe_evidence_and_verified_manifest(credentials, tmp_path):
    raw, preview = build_bundle([campaign()], credentials)
    path = tmp_path / "diagnostics.zip"
    save_bundle(path, raw)
    assert path.read_bytes() == raw
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert set(z.namelist()) == {"manifest.json", "README.txt", "reports/01.json"}
        manifest = json.loads(z.read("manifest.json"))
        for entry in manifest["files"]:
            assert hashlib.sha256(z.read(entry["name"])).hexdigest() == entry["sha256"]
            assert len(z.read(entry["name"])) == entry["bytes"]
        r = json.loads(z.read("reports/01.json"))
        assert r["state"] == "interrupted" and r["planned_cases"] == 66 and len(r["checks"]) == 1
        e = r["checks"][0]["evidence"]
        assert e["request_traces"][0]["request_chars"] == 1234
        assert e["request_traces"][0]["response_shape"]["thinking_chars"] == 44
        assert e["tool_timeline"][0]["verified"] is True
        assert e["initial_acceptance_checks"]["OUTPUT_CONTENT"] is False
        assert "PRIVATE" not in preview
        assert all(".." not in n and not n.startswith("/") for n in z.namelist())


def test_credentials_in_supported_fields_are_redacted(credentials):
    credentials._values["KEY"] = "fixture-secret-key"
    r = campaign()
    r["checks"][0]["evidence"]["model"] = "fixture-secret-key"
    raw, preview = build_bundle([r], credentials)
    assert "fixture-secret-key" not in preview


@pytest.mark.parametrize("count", [0, 3])
def test_bundle_report_count_is_bounded(credentials, count):
    with pytest.raises(ValueError):
        build_bundle([campaign()] * count, credentials)


def test_unknown_report_kind_is_not_packaged(credentials):
    with pytest.raises(ValueError):
        build_bundle([base_report("run_review", "1", "Private")], credentials)


def test_atomic_export_failure_preserves_existing_file(monkeypatch, credentials, tmp_path):
    import aigentics.bundles as module

    path = tmp_path / "existing.zip"
    path.write_bytes(b"previous")
    monkeypatch.setattr(module.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("failure")))
    with pytest.raises(OSError):
        save_bundle(path, b"new")
    assert path.read_bytes() == b"previous"
    assert list(tmp_path.iterdir()) == [path]


def test_archive_requires_review_before_save_and_saves_exact_bytes(
    qtbot, store, credentials, monkeypatch, tmp_path
):
    from aigentics.ui import Window
    from aigentics.bundles_ui import BundleDialog
    from PySide6.QtWidgets import QFileDialog

    window = Window(store, credentials)
    qtbot.addWidget(window)
    dialog = BundleDialog(window, [campaign()])
    qtbot.addWidget(dialog)
    destination = tmp_path / "approved.zip"
    requests = []
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args: (requests.append(True) or str(destination), "ZIP")
    )
    dialog.save_zip()
    assert not requests and not destination.exists() and not dialog.save.isEnabled()
    dialog.approved.setChecked(True)
    assert dialog.save.isEnabled()
    approved = bytes(dialog.data)
    dialog.save_zip()
    assert destination.read_bytes() == approved and len(requests) == 1
    assert "Nothing was uploaded" in dialog.status.text()
    window.lab_dir.cleanup()


def test_large_report_archive_keeps_all_bounded_traces(credentials):
    from test_report_capacity_0141 import large_campaign
    from aigentics.campaign import PLAN_IDS

    r = large_campaign()
    for row, identity in zip(r["checks"], PLAN_IDS):
        row["id"] = identity
        row["message"] = "Synthetic"
    raw, preview = build_bundle([r], credentials)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        saved = json.loads(z.read("reports/01.json"))
        assert len(saved["checks"]) == 66
        assert all(len(row["evidence"]["request_traces"]) == 8 for row in saved["checks"])


def test_partial_campaign_export_does_not_require_completion_approval(qtbot, store, credentials):
    from aigentics.ui import Window
    from aigentics.models import Agent, Profile
    from aigentics.campaign import campaign_scope
    from aigentics.campaign_ui import CampaignDialog

    store.save_profile(Profile(id="ollama", name="Local fixture"))
    agent = store.save_agent(Agent())
    r = campaign()
    r["local_scope"] = campaign_scope(store, agent, "deep")
    store.save_diagnostic(r)
    window = Window(store, credentials)
    qtbot.addWidget(window)
    dialog = CampaignDialog(window)
    qtbot.addWidget(dialog)
    assert not dialog.approval.isEnabled()
    dialog.export_zip()
    qtbot.addWidget(dialog.bundle_dialog)
    assert "interrupted" in dialog.bundle_dialog.preview.toPlainText()
    assert not dialog.bundle_dialog.save.isEnabled()
    window.lab_dir.cleanup()
