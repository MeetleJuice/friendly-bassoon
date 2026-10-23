"""Public GitHub release updates with bounded HTTPS and SHA-256 integrity checks.

Checksums use the same trusted release channel, not an independent signing key.
No provider credential, session text or machine identifier is sent to GitHub.
"""

from dataclasses import dataclass
from contextlib import closing
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
import httpx
from . import __version__

REPOSITORY = "MeetleJuice/friendly-bassoon"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases/latest"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
MAX_INSTALLER = 512 * 1024 * 1024
ALLOWED_HOSTS = {
    "api.github.com",
    "github.com",
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
}


class UpdateError(RuntimeError):
    pass


def version_tuple(value):
    match = re.fullmatch(r"v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value)
    if not match:
        raise UpdateError("Only stable numeric release versions are supported")
    return tuple(int(part) for part in match.groups())


def checked_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.fragment
    ):
        raise UpdateError("Update destination is outside the trusted GitHub release hosts")
    return url


@dataclass(frozen=True)
class Release:
    version: str
    installer_name: str
    installer_url: str
    checksum_url: str
    size: int
    digest: str = ""


@dataclass(frozen=True)
class DownloadedUpdate:
    release: Release
    path: Path
    sha256: str


def verify_download(update):
    if (
        update.path.is_symlink()
        or not update.path.is_file()
        or update.path.stat().st_size != update.release.size
    ):
        raise UpdateError("Downloaded installer is missing or has changed")
    with update.path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != update.sha256:
        raise UpdateError("Installer checksum no longer matches. Download it again.")


class Updater:
    def __init__(self, cache_dir, current_version=__version__, transport=None):
        self.cache_dir = Path(cache_dir)
        self.current_version = current_version
        self.transport = transport

    def _client(self):
        return httpx.Client(
            timeout=httpx.Timeout(30, connect=10),
            follow_redirects=False,
            transport=self.transport,
            headers={
                "User-Agent": "Aigentics-Desktop/" + self.current_version,
                "Accept": "application/vnd.github+json",
            },
        )

    def _response(self, client, url, cancel):
        for _ in range(6):
            if cancel.is_set():
                raise InterruptedError("Update cancelled")
            request = client.build_request("GET", checked_url(url))
            response = client.send(request, stream=True)
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location", "")
                next_url = str(response.url.join(location))
                response.close()
                checked_url(next_url)
                url = next_url
                continue
            return response
        raise UpdateError("Too many release redirects")

    def _small(self, client, url, cancel, limit):
        response = self._response(client, url, cancel)
        with closing(response):
            if response.status_code >= 300:
                raise UpdateError(
                    f"GitHub returned HTTP {response.status_code}. Check connection or try later."
                )
            result = bytearray()
            for chunk in response.iter_bytes():
                if cancel.is_set():
                    raise InterruptedError("Update cancelled")
                result.extend(chunk)
                if len(result) > limit:
                    raise UpdateError("Release metadata exceeds the size limit")
            return bytes(result)

    def check(self, cancel):
        import json

        try:
            with self._client() as client:
                response = self._response(client, API_URL, cancel)
                with closing(response):
                    if response.status_code == 404:
                        return None
                    if response.status_code >= 300:
                        raise UpdateError(
                            f"GitHub update check returned HTTP {response.status_code}; try later."
                        )
                    payload = bytearray()
                    for chunk in response.iter_bytes():
                        if cancel.is_set():
                            raise InterruptedError("Update cancelled")
                        payload.extend(chunk)
                        if len(payload) > 1_000_000:
                            raise UpdateError("Release metadata exceeds the size limit")
                data = json.loads(payload)
            if data.get("draft") or data.get("prerelease"):
                return None
            tag = data["tag_name"]
            version = ".".join(str(i) for i in version_tuple(tag))
            if version_tuple(version) <= version_tuple(self.current_version):
                return None
            name = f"Aigentics-Setup-{version}.exe"
            assets = {asset["name"]: asset for asset in data["assets"]}
            if name not in assets or "SHA256SUMS.txt" not in assets:
                raise UpdateError("The latest release has no complete Windows installer yet. Try later.")
            installer, sums = assets[name], assets["SHA256SUMS.txt"]
            prefix = f"https://github.com/{REPOSITORY}/releases/download/{tag}/"
            if (
                installer["browser_download_url"] != prefix + name
                or sums["browser_download_url"] != prefix + "SHA256SUMS.txt"
            ):
                raise UpdateError("Release assets do not belong to this repository and tag")
            size = installer["size"]
            if type(size) is not int or not 0 < size <= MAX_INSTALLER:
                raise UpdateError("Installer size is invalid")
            digest = installer.get("digest") or ""
            if digest and not re.fullmatch(r"sha256:[a-fA-F0-9]{64}", digest):
                raise UpdateError("Unsupported GitHub asset digest")
            return Release(
                version,
                name,
                checked_url(installer["browser_download_url"]),
                checked_url(sums["browser_download_url"]),
                size,
                digest.lower(),
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            if isinstance(exc, UpdateError):
                raise
            raise UpdateError("Could not read release metadata. Check your network and retry.") from exc

    def download(self, release, cancel, progress=lambda received, total: None):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with self._client() as client:
                manifest = self._small(client, release.checksum_url, cancel, 32000).decode("utf-8")
                expected = []
                for line in manifest.splitlines():
                    match = re.fullmatch(r"([a-fA-F0-9]{64})\s+\*?([^\s/\\]+)", line.strip())
                    if match and match[2] == release.installer_name:
                        expected.append(match[1].lower())
                if len(expected) != 1:
                    raise UpdateError("Installer is missing a unique SHA-256 checksum")
                digest = expected[0]
                if release.digest and release.digest != "sha256:" + digest:
                    raise UpdateError("GitHub asset digest and checksum manifest disagree")
                target = self.cache_dir / release.installer_name
                update = DownloadedUpdate(release, target, digest)
                if target.is_file() and not target.is_symlink():
                    try:
                        verify_download(update)
                        return update
                    except UpdateError:
                        pass
                response = self._response(client, release.installer_url, cancel)
                with closing(response):
                    if response.status_code != 200:
                        raise UpdateError(f"Installer download returned HTTP {response.status_code}")
                    sha, received = hashlib.sha256(), 0
                    with tempfile.NamedTemporaryFile(
                        dir=self.cache_dir, suffix=".part", delete=False
                    ) as stream:
                        temporary = Path(stream.name)
                        for chunk in response.iter_bytes(chunk_size=65536):
                            if cancel.is_set():
                                raise InterruptedError("Update cancelled")
                            received += len(chunk)
                            if received > release.size or received > MAX_INSTALLER:
                                raise UpdateError("Installer download exceeds its published size")
                            stream.write(chunk)
                            sha.update(chunk)
                            progress(received, release.size)
                        if cancel.is_set():
                            raise InterruptedError("Update cancelled")
                        stream.flush()
                        os.fsync(stream.fileno())
                    if received != release.size or sha.hexdigest() != digest:
                        raise UpdateError("Installer failed SHA-256 or size verification; it will not be run")
                temporary.replace(target)
                temporary = None
                self._clean_cache(target)
                return update
        except httpx.HTTPError as exc:
            raise UpdateError("Installer download failed. Check the connection and retry.") from exc
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    def _clean_cache(self, keep):
        old = sorted(
            (
                p
                for p in self.cache_dir.glob("Aigentics-Setup-*.exe")
                if re.fullmatch(r"Aigentics-Setup-\d+\.\d+\.\d+\.exe", p.name)
                and p != keep
                and not p.is_symlink()
            ),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for path in old[1:]:
            path.unlink(missing_ok=True)


def launch_installer(update):
    if sys.platform != "win32":
        raise UpdateError("This installer runs on Windows. Download it on your Windows PC.")
    verify_download(update)  # Recheck immediately before executing a file downloaded earlier.
    arguments = [str(update.path), "/UPDATE=1"]
    if getattr(sys, "frozen", False):
        arguments.append("/DIR=" + str(Path(sys.executable).parent))
    subprocess.Popen(arguments, close_fds=True)
