# Build progress and next actions

## 0.2.0 update

Automatic local Ollama model discovery, editable model dropdowns, Desktop/OneDrive `.env` and `.env.txt` discovery, matching provider-profile setup, startup/manual GitHub update checks, bounded SHA-256-verified installer downloads, pre-install history backups, version-outcome diagnostics, a custom app icon, and a Windows PyInstaller/Inno Setup release pipeline are implemented. The pipeline tests the actual installed app and desktop shortcut before publishing a version-tag release. The Windows build/install/shortcut/packaged-startup checks passed in run 39965837080. The version-tag build/publish run 39966453059 also passed and published Aigentics-Setup-0.2.0.exe in GitHub Releases. The actual published download was fetched and checksum-verified; see VERIFICATION.md.


## Delivered: first end-to-end release

- Native PySide6 shell with connected Agents/Workbench tabs.
- Agent creation, editing, persistence, duplication, deletion, JSON import/export, read-only template, model override in the laboratory, per-agent tools/permissions/limits and ordered fallback configuration.
- Native Ollama and OpenAI-compatible adapters, discovery/connection tests, capability checks, bounded HTTP, explicit credential references, selected .env loading and OS-vault writes.
- Workspace exploration/preview, bounded search/read, reviewed and verified file writes, approved argv execution, actual exit codes, cancellation and time/output/context/step budgets.
- Shared background runtime with live evidence, session history, opt-in persistent content, conversation resume, restart recovery and one-instance data-folder locking.
- SQLite migrations v1→v2, immutable session agent snapshots, revision retention, correlated execution records, aggregate evidence, human goal assessments, export/deletion and configurable retention.
- Automated runtime/provider/filesystem/subprocess/desktop tests, optional real-Ollama workflow, Linux dependency snapshot, source installation and Windows launch instructions.

## Validation boundaries

The cloud machine is Linux/Python 3.12 with Qt offscreen rendering. Controlled provider fixtures exercise real adapters and the runtime; subprocess/file operations are real in temporary projects. No access to the user's Windows desktop, GPU, Ollama instance or API-key file was available. Do not treat fixture results as live model integration results. Final automated result: 61 passed, 1 optional real-Ollama test skipped; lint/format, dependency checks, actual entry-point smoke and wheel build passed. Refer to VERIFICATION.md for details.

## Next useful action on the user's machine

Download Aigentics-Setup-0.2.0.exe from GitHub Releases and run the wizard. Let startup discover the Desktop .env/.env.txt and Ollama models, then run the Windows acceptance procedure on a disposable project. Save a session-content capture for a non-sensitive example, label its outcome, and inspect/export the evidence. Use that evidence to choose the next improvement.

## Deferred work (not claimed complete)

- Live Windows 10/11, OS-vault and local/cloud model acceptance; model-quality/performance measurements on the RTX 3050.
- Authenticode-signed Windows installer, independent update signing and Windows 10 hardware acceptance. The release/update channel and Windows build/smoke workflow are now implemented.
- Native Gemini adapter and provider-specific live certification, richer capability settings, token streaming, throttling/backoff controls.
- Fully atomic/race-resistant file edits, multi-file transactions/rollback, Windows Job Objects and OS execution sandboxing.
- Search ignores beyond the current sensitive/cache directories, repository mapping, tokenizer-aware context compression and large-project optimization.
- Rich visual provider/configuration forms in place of advanced JSON, richer live diff panes and dedicated side-by-side laboratory comparison.
- Automated retention by disk bytes, encrypted database, broader user data-management/credential deletion UI and stronger local threat hardening.
- Agent-definition revision browser, fixture replay/evaluation UI, automatic failure clustering, controlled benchmarks and PULSE.

No autonomous self-modification, remote analytics, trained improvement, comprehensive provider support or full original Phase 1 completion is claimed. This is a functional initial vertical slice with a foundation for measured improvements.
