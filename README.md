# Aigentics Desktop

A native Python / PySide6 desktop coding-agent application. Agents and Workbench use the same bounded runtime. Ollama runs locally; no paid API is required. This is an early functional release, not the full long-term product described in the original brief.

## Windows 10/11: easy installation

Go to **[Releases](https://github.com/MeetleJuice/friendly-bassoon/releases/latest)** and download **Aigentics-Setup-0.2.0.exe** from **Assets**. Double-click it and follow the wizard. Leave **Create a desktop shortcut** selected. The installer bundles Python and dependencies; no VS Code, Git or manual Python installation is needed to run the packaged app. Ollama must be installed/running separately.

The installer is currently unsigned. Do not confuse the green **Code → Download ZIP** source download with the installer in Release Assets. The Windows build publishes an installer only after its tests and installed-executable/shortcut smoke pass. Check [Actions](https://github.com/MeetleJuice/friendly-bassoon/actions) if the asset is not available yet. See [installer details](docs/INSTALLER.md).

On first launch:

1. The app looks for local Ollama and fills the installed-model list.
2. It checks your Desktop for `.env` or `.env.txt` (a Notepad file is fine). Keys load into memory and recognized providers get profiles; no cloud model is contacted during discovery.
3. The untouched default agent can select an installed coding model. Use **Setup & updates** to review/change it, refresh discovery or disable automatic key-file loading.
4. Open **Workbench**, create a disposable project, and try: “Create hello.py that prints Hello, Aigentics. Use your file tools, then explain what changed.” Review the real diff before approving it.

The app checks GitHub Releases at launch. **Setup & updates → Download update → Install & restart** verifies the installer, backs up history, and opens the wizard when your tasks are finished. It does not install in the middle of a task. Your projects, key file and history remain separate from application binaries.

### Source/development installation

Use 64-bit Python 3.12 (supported 3.11–3.13). Open this folder in VS Code's PowerShell terminal:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m aigentics
```

After source installation, `Start-Aigentics.cmd` is an alternative launch shortcut. Source development remains available, but the release installer is the simplest user workflow. Desktop/software updates require a published release; arbitrary changes on main are not installed automatically.

## Your Desktop .env

Desktop `.env` and `.env.txt` are detected and loaded into memory automatically on startup. Windows' OS-reported Desktop is checked first, with normal/OneDrive Desktop candidates next; there is no whole-drive scan. Disable this in **Setup & updates** if desired, or choose another file manually. Files must contain `NAME=value` entries and be smaller than 1 MB. Values are not executed or interpolated from the system environment.

Only variable names may appear in the provider interface, never their values. Automatic setup creates matching Groq, OpenRouter, NVIDIA, Gemini-compatible or OpenAI profiles for recognized key names, preserves existing profiles, and makes no cloud requests. Each startup reloads Desktop keys into memory. The original file is not copied into the app, committed, uploaded or written into history. **Save key to OS vault** remains available with no plaintext fallback.

Create/save a cloud provider profile and set `credential_ref` to its variable name, e.g. `GROQ_API_KEY`. Agents reference profile IDs, never keys. Do not paste credentials into tasks or instructions. Loaded credentials are redacted before sending tool results and user tasks to a model, but unknown secret formats cannot be detected reliably. Review exports before sharing them.

The `openai` adapter supports native-tool-capable OpenAI-compatible APIs. Example profile:

```json
{
  "schema_version": 1,
  "id": "groq",
  "name": "Groq",
  "kind": "openai",
  "base_url": "https://api.groq.com/openai/v1",
  "credential_ref": "GROQ_API_KEY",
  "supports_tools": true,
  "timeout_seconds": 120
}
```

Other endpoint examples: OpenRouter `https://openrouter.ai/api/v1`, NVIDIA `https://integrate.api.nvidia.com/v1`. Their individual model capabilities and live credentials have **not** been verified in this environment. Model discovery may be unavailable on some compatible services; manual model entry works. Gemini's OpenAI-compatible endpoint can be auto-configured; its native protocol remains deferred. Cloud profiles require HTTPS. Redirects are not followed, preventing credential forwarding to another destination.

Fallbacks are an ordered JSON list in Studio. They activate on transient network errors, timeouts, HTTP 429 and selected server errors. Authentication, malformed protocol and capability errors fail visibly. A fallback may send the current context to another configured service: configure only destinations you intend to use. No automatic cloud fallback is installed by default.

## Data collection is foundational

All storage is local; there is no external telemetry or automatic upload. A cloud model request necessarily sends its context to the provider you configured.

The SQLite database records versioned agents, provider references, sessions, configuration events, model usage/timing, tool requests/results, approvals, failures, fallback events, cancellations and final runtime state. Events have stable IDs, timestamps, application versions and session IDs. Model requests and tool executions have correlation IDs. See [the data contract](docs/DATA.md).

**Metadata mode is the default.** Live conversation remains in RAM for up to eight recent runs. Diagnostics retain argument/result fingerprints and execution metadata, not complete project text or command output. Check **Save redacted session content** to persist messages and tool content and resume across restarts. This may retain project code. Resume uses the current saved agent revision and previous conversation text; it does not replay prior tool actions or restore a paused program counter.

In History, inspect/export/delete a run and mark **Goal met** or **Needs work** with an optional note. These are user assessments, separate from model completion and command success. **View evidence summary** aggregates runtime states, tool outcomes, per-model durations/usage and user labels. This is the foundation for future evaluations; no autonomous self-modification or learned improvement is claimed.

Defaults: 30-day retention, 20,000-event budget, 100 recent definition revisions per agent. Pruning removes whole oldest completed sessions to preserve coherent timelines, and caps configuration events. Running sessions are preserved until completion; the event budget is not a strict disk-byte quota. The database is compacted after pruning/deletion. Exports, OS backups and the original `.env` remain your responsibility.

The default database is in Qt's per-user application data folder (normally under `%LOCALAPPDATA%\Aigentics\Aigentics Desktop` on Windows). Set `AIGENTICS_DATA_DIR` to explicitly choose another folder. Credentials remain in the selected `.env`/OS vault, not the database. A per-data-folder instance lock prevents two GUI processes from recovering each other's running sessions.

## Tests and cloud development

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check aigentics tests
```

The normal tests require no GPU, model, network service or API key. They exercise native desktop widgets, worker integration, diff approval, real temporary filesystem changes, real subprocesses, HTTP provider fixtures, persistence, migration, retention, redaction and execution bounds. Desktop tests use Qt's offscreen platform through `tests/conftest.py`.

Optional **real Ollama** end-to-end test (requires an installed tool-capable model):

```powershell
$env:AIGENTICS_TEST_OLLAMA_MODEL = "qwen2.5-coder:14b"
.\.venv\Scripts\python.exe -m pytest tests/test_ollama.py -q
```

Cloud/Linux setup, with the validated Linux/Python 3.12 dependency snapshot:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-linux.lock
.venv/bin/python -m pip install --no-deps -e .
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

`requirements-linux.lock` pins all installed development dependencies for this Linux environment. It is **not** a Windows lockfile; Windows installs from the pinned direct dependencies in `pyproject.toml` and resolves platform-specific transitive packages. Regenerate/test the Linux snapshot deliberately when upgrading dependencies. A universal `uv` lock could not be resolved by the available runtime tool; the tested pip workflow above is the supported setup.

For an interactive Linux desktop, launch `.venv/bin/python -m aigentics` from a graphical session with the system Qt/X11 libraries installed. A cloud shell does not display a window on your Windows computer.

## Verification and remaining work

See [verification and Windows smoke testing](docs/VERIFICATION.md), [architecture](docs/ARCHITECTURE.md), and [progress](docs/PROGRESS.md). File tools apply workspace restrictions, but approved host commands are **not sandboxed**. Avoid untrusted projects and use version control/backups for real work.

Software-release build and update integrity details: [docs/INSTALLER.md](docs/INSTALLER.md).
