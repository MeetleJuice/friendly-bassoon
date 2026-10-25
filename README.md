# Aigentics Desktop

## Verified completion and thinking measurements (0.17.0)

Keeps the improved interface and your selected model. Fixes unchanged-file completion ordering and clarifies strict test JSON schemas. Native Ollama thinking controls are verified before use; context stays automatic. Default tests record **27 offline app checks +34 trial slots**, including four conditional thinking-off comparisons that skip if unsupported. No API generation checks run.

After Update/install/restart, let the queued tests finish once, then **Review / save diagnostic ZIP** → inspect → approve local saving → Save → drag the ZIP into chat. Nothing uploads automatically. See the [plan](docs/maintenance/UPGRADE_0170_PLAN.md) and [research](docs/maintenance/RESEARCH_0170.md). A new benchmark identity prevents silently comparing changed conditions as a controlled improvement.

## Midnight Crew interface (0.16.0)

The new sidebar keeps **Projects**, **Workbench**, **Agents**, **Test center**, **Diagnostics**, **Local data**, **Connections** and **Settings** together. Workbench gives your conversation more room; **Files** and **History** reveal optional panels. **Task options** contains checks, session-memory capture and context; output write scope stays visible. Agent forms scroll while Save stays visible.

**Ctrl K** finds navigation/settings actions. **Ctrl1/2/3** opens Projects/Workbench/Agents; **Ctrl B** toggles files and **Ctrl Shift I** toggles history. **Ctrl Enter** runs only while typing in the Workbench task field. Test center separates passes, corrections, failures and incomplete attempts, with reviewed ZIP export up front. The0.15benchmark, model budgets, permission rules and stored evidence remain unchanged.

See the [native screenshots and source research](docs/design/UI_RESEARCH_0160.md) and [upgrade plan](docs/maintenance/UPGRADE_0160_PLAN.md). Existing setup/update functions are under **Settings**. Finish/save your current test ZIP before updating when convenient; older reports remain available.

A native Python / PySide6 desktop coding-agent application. Agents and Workbench use the same bounded runtime. Ollama runs locally; no paid API is required. This is an early functional release, not the full long-term product described in the original brief.

## Repeated measurement and precise diagnostics (0.15.0)

After Update/install/restart, the default campaign runs **25 offline app checks + 30 repeated local attempts** across George, Scout, Ada, Vera, Sentinel and Atlas on the same selected Ollama model. Optional Discovery retains 66 attempts. No API test runs automatically. Static contract/schema diagnosis, frozen benchmark identity, repeated outcomes and separate interrupted/unknown counts make results easier to interpret. Actual model improvement requires the next local run.

After completion or Stop safely, click **Review / save diagnostic ZIP**, inspect, approve local saving and save. Drag the ZIP into support chat; no token or GitHub issue is required. Dense evidence is losslessly compressed within checked limits. Nothing uploads automatically. See the [0.15 plan](docs/maintenance/UPGRADE_0150_PLAN.md).

## Windows 10/11: easy installation

Go to **[Releases](https://github.com/MeetleJuice/friendly-bassoon/releases/latest)** and download the latest **Aigentics-Setup-<version>.exe** from **Assets**. Double-click it and follow the wizard. Leave **Create a desktop shortcut** selected. The installer bundles Python and dependencies; no VS Code, Git or manual Python installation is needed to run the packaged app. Ollama must be installed/running separately.

The installer is currently unsigned. Do not confuse the green **Code → Download ZIP** source download with the installer in Release Assets. The Windows build publishes an installer only after its tests and installed-executable/shortcut smoke pass. Check [Actions](https://github.com/MeetleJuice/friendly-bassoon/actions) if the asset is not available yet. See [installer details](docs/INSTALLER.md).

On first launch:

1. The app looks for local Ollama and fills the installed-model list.
2. It checks your Desktop for `.env` or `.env.txt` (a Notepad file is fine). Keys load into memory and recognized providers get profiles; no cloud model is contacted during discovery.
3. The untouched default agent can select an installed coding model. Use **Settings** to review/change it, refresh discovery or disable automatic key-file loading.
4. Open **Workbench**, create a disposable project, and try: “Create hello.py that prints Hello, Aigentics. Use your file tools, then explain what changed.” Review the real diff before approving it.

The app checks GitHub Releases at launch. **Settings → Download update → Install & restart** verifies the installer, backs up history, and opens the wizard when your tasks are finished. It does not install in the middle of a task. Your projects, key file and history remain separate from application binaries.

### Source/development installation

Use 64-bit Python 3.12 (supported 3.11–3.13). Open this folder in VS Code's PowerShell terminal:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m aigentics
```

After source installation, `Start-Aigentics.cmd` is an alternative launch shortcut. Source development remains available, but the release installer is the simplest user workflow. Desktop/software updates require a published release; arbitrary changes on main are not installed automatically.

## Diagnose and share without dragging files

Open **Diagnostics** from the sidebar, choose your saved test agent and optional local-model test, then click **Run diagnostics**. The installed app runs 27 built-in checks in temporary folders, optionally tests the selected local Ollama model against a real file-create/read-back task, saves a local report, requests a completion sound, and offers a sharing review. It does not run arbitrary project test commands or call cloud models automatically.

Review the exact public report preview and approve it before sharing. **Browser draft** needs no token; finish with Create (or Submit new issue) on GitHub. **Direct submission** uses an existing `GITHUB_TOKEN` with Issues write access and records the confirmed issue URL. No report is uploaded by merely running diagnostics. Support reports go to **GitHub Issues**, not permanent source commits. Model names are optional; keys, project text, paths and conversations are excluded from the generated public report. See [diagnostic details](docs/DIAGNOSTICS.md).

The new **Update** button opens the existing check/download/install flow directly. Use Update to check for the latest published installer. File/command approval remains in force, and protocol recovery never executes JSON printed as text. Readable Workbench summaries distinguish response-only turns, execution with failures, and real protocol errors. A completed execution is not an automatic claim that the whole user goal was met.

## Test APIs and keep useful local records

Click **Test APIs** after local key discovery finishes. It makes one model-list GET per unique configured connection, with no generation prompts, and updates the model dropdowns. Supported presets are Ollama, Groq, OpenRouter, NVIDIA, Gemini-compatible and OpenAI; custom OpenAI-compatible profiles use the same contract. It does not guess endpoints for every variable in a key file. Providers may count metadata requests against rate limits. A successful list response is not proof of generation authorization or native tools.

Catalogs persist across restarts with timestamps; failed refreshes keep the previous successful list until retention removes it. Partial first-page results are labeled without making another request. **Local data** shows storage, reports, model catalogs, age/count/size limits and the data-folder location. Reports can be reviewed and explicitly approved for GitHub sharing. **Copy preview** provides a fallback for browser problems.

Qwen2.5-Coder14b still fails native tool calls in issues #5/#6/#8. The user’s Qwen3:8b session successfully edits files; this is model-specific acceptance evidence, not a universal repair. Suite 4 adds static-check/revision fixtures and recovery/assessment counters. See the [maintenance workspace](docs/maintenance/README.md) and [short user testing guide](docs/maintenance/USER_TESTING.md).

## Task checks and clear outcomes (0.7.0)

Workbench shows **Expected output files**, **Require real tools**, **Required tools**, and **Read back output files**. A simple single-file create/edit instruction can suggest a visible target; review/edit it before Run. The runtime restricts file-tool writes to configured targets and checks actual successful writes, independent read-back after the latest write, current file revision and required tools. Missing checks produce needs_review. These are operation checks, not a universal English-goal verifier. Host commands retain separate approval and are not sandboxed by the target list.

**New task · fresh context** is the default. Select Continue conversation or Resume when you want historical context. Model prose is labeled separately from the runtime's facts. A missing visible final becomes incomplete_response with preserved operation evidence and no action replay/extra generation. An identical write is skipped without changing the file or counting an actual write.

Run-review-2 reports contain safe task-check/final/no-op evidence and coverage of new fields in mixed history. User Goal met/Needs work remains separate. Source, target paths, task text and notes are excluded from public previews; existing retention and explicit sharing approval remain.

See the [0.7 plan](docs/maintenance/UPGRADE_070_PLAN.md), [research](docs/maintenance/RESEARCH_070.md) and [one-test guide](docs/maintenance/USER_TESTING.md).

## Easier verification and reports (0.6.0)

Python writes receive automatic compilation/basic static checks without running or importing the code. **Workbench → Check Python file** checks a chosen project file with no model request. A passed check does not verify installed dependencies, assets or gameplay. Saved files and their check results appear separately in execution/history.

**Plan only (read only)** removes write/command permissions for that run; **Build / edit** uses the saved agent permissions. Existing agents are preserved. Agent name/description are supplied as identity context. For edits, the model can use `expected_sha256="last_read"` after reading the file in the same run; normal stale-file checks and approval remain mandatory. Recovered stale-edit errors remain recorded without automatically making a finished corrected edit look unresolved.

Select a finished History run, label it **Goal met** or **Needs work**, then **Share run report** to review minimal counters/check codes. No transcript copying is needed. Models are optional in public reports; notes/source/paths remain excluded. Reports share through the existing preview/approval workflow and retention budget. Diagnose opens its options before starting and explains next steps; technical evidence is optional.

See the [0.6 plan](docs/maintenance/UPGRADE_060_PLAN.md) and [research](docs/maintenance/RESEARCH_060.md).

## Projects, context and model tool tests (0.5.0)

**PROJECTS** remembers opened roots and short project briefs; the app opens this page at normal startup. Open your existing folder once, save its brief, and use **Open selected in Workbench**. Workbench has a recent-project chooser and project-scoped history. Forgetting a project removes its saved definition/brief, not its files or sessions.

**Preview project map** and **Find relevant excerpts** run locally with cited current files, ignore rules and strict scan/output budgets. No embedding or model request runs for a preview, and no source-body index is saved. **Add previewed excerpts to task** rechecks current hashes/ignores and lets you inspect the task before sending it. Builder/Reviewer templates enable the read-only map/retrieval tools; existing saved agents are not silently rewritten. **Tools & permissions** shows the registered schemas and policies.

**Test model** tests one saved agent's model with a single harmless native-function challenge, requesting at most 96 output tokens. It cannot run project tools. Remote generation requires the explicit approval checkbox and may incur provider charges. The optional local Ollama comparison makes four calls (native/compatible, streaming/nonstreaming) with matching parameters; it never interprets printed JSON as executable calls or silently changes routes. A successful tested local route can be applied after confirmation, then verified by the full Diagnose workflow. The original Qwen problem remains open pending live results.

Read the [upgrade plan](docs/maintenance/UPGRADE_050_PLAN.md), [source research](docs/maintenance/RESEARCH_050.md), and [user testing guide](docs/maintenance/USER_TESTING.md).

## Your Desktop .env

Desktop `.env` and `.env.txt` are detected and loaded into memory automatically on startup. Windows' OS-reported Desktop is checked first, with normal/OneDrive Desktop candidates next; there is no whole-drive scan. Disable this in **Settings** if desired, or choose another file manually. Files must contain `NAME=value` entries and be smaller than 1 MB. Values are not executed or interpolated from the system environment.

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

Research and continuing development records: [RESEARCH.md](docs/RESEARCH.md), [ENGINEERING_LOG.md](docs/ENGINEERING_LOG.md).

### Guided tests (0.8)

After installing, choose **Test suite**, select a working local Ollama agent and click **Go**. Ten isolated tests and app diagnostics run in sequence; no project commands or cloud generation. Review both previews, approve opening the drafts and click **Create** on each GitHub page. Future Update clicks queue this workflow after installation. Existing retention settings govern saved reports. See [testing guide](docs/maintenance/USER_TESTING.md).
