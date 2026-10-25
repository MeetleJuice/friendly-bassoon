"""Promote only an immutable artifact from a successful main-branch Windows gate."""

import hashlib
import json
from pathlib import Path
import re
import sys


def source_identity(run, artifacts, repository):
    if not (
        run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and run.get("event") == "push"
        and run.get("head_branch") == "main"
        and run.get("path") == ".github/workflows/windows-release.yml"
        and run.get("head_repository", {}).get("full_name") == repository
        and re.fullmatch(r"[a-f0-9]{40}", run.get("head_sha", ""))
    ):
        raise ValueError("Source must be a successful main-branch Windows installer run")
    matches = []
    for artifact in artifacts.get("artifacts", []):
        match = re.fullmatch(r"Aigentics-Windows-(\d+\.\d+\.\d+)", artifact.get("name", ""))
        if match and artifact.get("expired") is False:
            matches.append((match[1], artifact))
    if len(matches) != 1:
        raise ValueError("Expected exactly one unexpired versioned installer artifact")
    version, artifact = matches[0]
    return {
        "source_sha": run["head_sha"],
        "source_run_id": run["id"],
        "version": version,
        "artifact_id": artifact["id"],
        "artifact_digest": artifact.get("digest"),
        "repository": repository,
    }


def verify_installer(folder, identity):
    name = f"Aigentics-Setup-{identity['version']}.exe"
    path = folder / name
    checksum = (folder / "SHA256SUMS.txt").read_text(encoding="utf-8").strip()
    match = re.fullmatch(r"([a-fA-F0-9]{64})\s+\*?" + re.escape(name), checksum)
    if not match or not path.is_file() or path.is_symlink():
        raise ValueError("Installer/checksum identity mismatch")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != match[1].lower():
        raise ValueError("Installer checksum failed")
    return identity | {"installer": name, "installer_bytes": path.stat().st_size, "installer_sha256": digest}


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "source":
        identity = source_identity(
            json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")),
            json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")),
            sys.argv[4],
        )
        Path("release-source.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
        print(f"sha={identity['source_sha']}\nversion={identity['version']}")
    elif mode == "verify":
        folder = Path(sys.argv[2])
        identity = json.loads(Path("release-source.json").read_text(encoding="utf-8"))
        result = verify_installer(folder, identity)
        (folder / "BUILD_PROVENANCE.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    else:
        raise ValueError("Unknown provenance operation")
