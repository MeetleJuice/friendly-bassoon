# Windows installation and software updates

## For users

Open [GitHub Releases](https://github.com/MeetleJuice/friendly-bassoon/releases/latest) and download `Aigentics-Setup-<version>.exe` from **Assets**. Run the wizard, leave **Create a desktop shortcut** selected, and optionally launch the app when setup finishes. Python and application libraries are included. It installs for the current Windows user, normally at `%LOCALAPPDATA%\Programs\Aigentics Desktop`, with an uninstall entry in Windows Settings. No administrator account is required for this default installation.

A source ZIP from the green Code button is still source code. The file in Release Assets is the install wizard. The executable is currently unsigned; checksums are published, but no Authenticode/publisher signature is claimed.

The app automatically checks local Ollama and known Desktop directories at startup. If your Notepad file is `.env.txt`, it is recognized. If multiple files exist, it loads the first exact `.env`/`.env.txt` from the OS-reported Desktop, then normal/OneDrive Desktop candidates. It never recursively searches your computer. For another location, click **Setup & updates → Choose key file**. Use UTF-8 or UTF-8 with BOM and normal key/value lines:

```dotenv
GROQ_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
NVIDIA_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

Quotes are supported; values are not executed or expanded from the process environment. Do not send the actual contents to chat. No cloud model is called during discovery. Existing provider profiles and configured agent models are preserved. Only the untouched default agent can receive an initial installed model suggestion automatically; capability is checked when you run an agent. The user remains responsible for selecting an appropriate installed model.

## Update behavior

- The prominent Update button opens the same flow directly. Startup checks `api.github.com` for the latest stable public release. You can disable it or check manually.
- A newer release must have the expected installer asset and `SHA256SUMS.txt` for this exact repository and tag. Downgrades, drafts and prereleases are not installed automatically.
- Downloads allow only HTTPS and known GitHub release hosts, use response/size limits and a temporary file, and compare byte size and SHA-256. When present, the GitHub API asset digest must also agree. Verification failure prevents installation. A checksum from the same release channel is not protection against a compromised repository/release account.
- **Install & restart** is available on Windows after verification. It is blocked during active runtime/setup/update jobs. The app backs up the SQLite database, re-verifies the installer immediately before launching, and closes. Finish the wizard to reopen the updated app. Nothing is installed silently at startup.
- The installer upgrades application binaries while user projects, .env files, OS-vault keys and the separate data directory remain intact. The next launch records whether the running version matches the requested version. A canceled wizard is recorded as `update.not_completed` on the next old-version launch.
- Up to two verified installer files are cached. Temporary downloads are removed on handled failures/cancellation. Three recent consistent database snapshots are kept in the application data folder's `backups` directory. Those backups may retain older session content after it is deleted from the live database. Manage backup files separately; no automatic rollback is implemented.

A network block/rate limit or inaccessible private release does not prevent using local Ollama or saved configuration. GitHub receives ordinary update requests (including IP and app-version User-Agent), not session content, provider keys or machine IDs. No analytics upload is enabled.

## Build and release for maintainers

The `.github/workflows/windows-release.yml` workflow runs on main pushes, pull requests, version tags and manual dispatch. It uses a Windows runner and Python 3.12 to:

1. Install pinned direct application/test dependencies and PyInstaller 6.16.0.
2. Run the automated test suite and lint.
3. Render the multi-size icon from the owned SVG.
4. Freeze the application into `dist/Aigentics` and compile Inno Setup's wizard.
5. Install that actual wizard into a disposable directory, inspect the Desktop shortcut's target, and run the installed executable in offscreen smoke mode. No live API key or Ollama is required.
6. Upload the installer/checksum as workflow artifacts. Only successful version-tag builds publish a GitHub Release, with the job's scoped `GITHUB_TOKEN` (not user API keys).

To publish an update, update `aigentics.__version__`, `pyproject.toml`, release notes and the installer default version together, run tests, push changes and a matching new version tag, e.g. `v0.2.1`. Tags must match the package version. Repository changes alone do not replace installed applications. Do not retag or overwrite an already released version.

Manual Windows build (requires Python development setup plus Inno Setup 6):

```powershell
python -m pip install -e ".[dev]" "pyinstaller==6.16.0"
.\scripts\build_windows.ps1
.\scripts\smoke_windows.ps1 -Version 0.2.0
```

The manual smoke script creates/removes an Aigentics Desktop shortcut and uses a temporary installation directory; use a disposable test account/machine. Keep release signing credentials outside source control. The current workflow does not have an Authenticode certificate, independent update-signing key, or Windows 10 hardware acceptance result.

For 0.3.0 the Windows smoke also runs the installed built-in diagnostic suite and a checksum-pinned 0.2.0-to-current upgrade, verifying saved agents, settings, session messages and schema migration. See DIAGNOSTICS.md for approved support reporting, which is separate from software installation and source-code releases.
