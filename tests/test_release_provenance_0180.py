"""Release promotion must reuse the exact successful source's immutable artifact."""

import importlib.util
from pathlib import Path
import hashlib
import pytest

spec = importlib.util.spec_from_file_location(
    "provenance", Path(__file__).resolve().parents[1] / "scripts/release_provenance.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def source():
    return {
        "id": 123,
        "status": "completed",
        "conclusion": "success",
        "event": "push",
        "head_branch": "main",
        "path": ".github/workflows/windows-release.yml",
        "head_repository": {"full_name": "test/project"},
        "head_sha": "a" * 40,
    }


def artifact():
    return {
        "artifacts": [
            {"id": 456, "name": "Aigentics-Windows-0.18.0", "expired": False, "digest": "sha256:" + "b" * 64}
        ]
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "in_progress"),
        ("conclusion", "failure"),
        ("event", "pull_request"),
        ("event", "workflow_dispatch"),
        ("head_branch", "other"),
        ("path", "untrusted.yml"),
        ("head_repository", {"full_name": "foreign/repo"}),
        ("head_sha", "bad"),
    ],
)
def test_non_gated_sources_rejected(field, value):
    run = source() | {field: value}
    with pytest.raises(ValueError):
        module.source_identity(run, artifact(), "test/project")


def test_expired_or_ambiguous_artifacts_rejected():
    for artifacts in (
        {"artifacts": []},
        {"artifacts": [artifact()["artifacts"][0] | {"expired": True}]},
        {"artifacts": artifact()["artifacts"] * 2},
    ):
        with pytest.raises(ValueError):
            module.source_identity(source(), artifacts, "test/project")


def test_verified_source_and_corrupted_installer(tmp_path):
    identity = module.source_identity(source(), artifact(), "test/project")
    assert identity["source_sha"] == "a" * 40 and identity["artifact_id"] == 456
    exe = tmp_path / "Aigentics-Setup-0.18.0.exe"
    exe.write_bytes(b"synthetic installer")
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    (tmp_path / "SHA256SUMS.txt").write_text(digest + "  " + exe.name + "\n", encoding="utf-8")
    assert module.verify_installer(tmp_path, identity)["installer_sha256"] == digest
    exe.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        module.verify_installer(tmp_path, identity)
