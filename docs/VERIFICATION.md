# Verification

## 0.3.0 diagnostics/reliability verification

Current Linux result: **83 passed, 1 skipped** (optional live Ollama); lint/format pass. New tests cover the observed text-tool response, bounded non-executing recovery, native-call permission preservation, truthful response-only/denied outcomes, 12 real built-in checks, optional model fixture acceptance, cloud-model skipping, allowlisted reports, credential/approval protections, direct API issue protocol, no automatic retry after an ambiguous POST, bounded exact browser previews, report retention/recovery, v2→v3 history preservation, legacy response counts and preview edits revoking approval. No real support issue was created during development.

The actual source entry point passed both --smoke-test and --diagnostic-smoke-test in disposable data directories. The diagnostic UI completed and rendered successfully offscreen. Windows CI now installs the actual new wizard, checks its shortcut/startup, runs the installed 12-check suite, and tests the pinned public 0.2.0 installer upgrading to this version with synthetic agents/settings/history preserved. Remote build/release results will be recorded after they complete. User-specific Ollama/API and real GitHub posting remain unverified until exercised with the user’s own authorized setup.


## 0.2.0 setup/update verification

Linux automated validation: **61 passed, 1 skipped** (optional real Ollama), with lint passing. New tests cover `.env` and `.env.txt`/UTF-8 BOM, bounded Desktop and OneDrive lookup, disabled discovery, unavailable Ollama, malformed/oversized key files, no environment interpolation, profile preservation, installed-model selection, persistent preferences, database backup retention, stable version ordering, downgrade rejection, trusted release URLs, asset validation, verified/cache downloads, checksum/digest mismatch, corrupt/oversized downloads, cancellation cleanup, credential-free updater HTTP, re-verification before launch, argv boundaries and background desktop update status/events.

Windows packaging uses `.github/workflows/windows-release.yml`. It compiles the actual installer, installs it into a temporary folder, checks the Desktop shortcut target and launches the installed executable in smoke mode. The Windows workflow at commit `5cc3aa7` passed: [run 39965837080](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/39965837080). This includes the Windows test/lint steps, PyInstaller build, Inno Setup compilation, actual installation into a temporary directory, Desktop shortcut-target check, and launch/SQLite initialization/clean shutdown of the installed executable. The installer artifact `Aigentics-Windows-0.2.0` was produced. An earlier run failed in Windows tests; explicitly closing SQLite backup handles before pruning resolved the issue, and CI now exposes individual test-failure annotations.

The matching `v0.2.0` tag repeated the Windows build/install checks and published the GitHub Release successfully: [release run 39966453059](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/39966453059), [published release](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.2.0). The released source commit is `5cc3aa7`.

The published installer was independently fetched through the production updater's bounded HTTPS download code and checked against its release checksum. It is 42,095,842 bytes; its SHA-256 is `f7f1ab999f9df45e0bf2a6d5e0c7d4839c477a1f82732ade95de59f07602874e`. The Python 0.2.0 wheel also built successfully and was checked for packaged icon/discovery/update modules. Dependency consistency (`pip check`) passed.

Windows runner success does not replace human Windows 10/Ollama/API acceptance checks on the user's machine. The executable is unsigned; no Authenticode or independent publisher signature is claimed.

Actual normal-startup smoke was also executed on Linux: Desktop/Ollama discovery and background update checks finished, local setup events were recorded, and the GUI remained usable and closed cleanly. This cloud machine had no local Ollama/Desktop key file; GitHub API access was blocked by its network proxy, which produced a handled update failure rather than preventing use. Controlled fixtures cover successful discovery/update paths without live user secrets.

The `--smoke-test` mode bypasses startup network/key-file discovery and validates native tabs/shared agent initialization and clean shutdown. This permits repeatable packaged-executable checks without touching the runner's Desktop credentials or using external models.


## Executed in this cloud machine

Linux, Python 3.12.14, PySide6 6.8.3. The development dependencies and editable source package were installed with pip using normal TLS verification. Exact Linux dependency versions are recorded in `requirements-linux.lock`. Final executed results:

| Check | Result |
| --- | --- |
| `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q` | **36 passed, 1 skipped** (optional real Ollama), 1.94 seconds |
| `ruff check aigentics tests` | Passed |
| `ruff format --check aigentics tests` | Passed |
| `pip check` | No broken requirements |
| Reapply Linux lock + editable install | Passed |
| Actual `ui.main()` entry-point smoke | Both native tabs rendered, isolated SQLite initialized, instance lock acquired, clean shutdown with exit 0 |
| `pip wheel --no-deps . -w dist` | Built `aigentics_desktop-0.1.0-py3-none-any.whl` |

These observations apply to this current cloud instance. Saved configuration is a draft; publication and restoration in a fresh task have not been verified.

Checks include real temporary file creation/read/hash/review, blocked paths/links, approved subprocess execution, failure exit codes, command timeout/cancellation/output limits, sanitized subprocess environment, controlled Ollama/OpenAI HTTP responses, native tool normalization, explicit fallback, unsupported capabilities, redaction including escaped nested JSON, migration preservation, deletion/retention/export, human assessments, contextual follow-up, interruption recovery, native widgets/background execution and an actual desktop approval dialog.

A headless native-window smoke check constructed and showed the real application, rendered both tabs, confirmed the shared saved agent and shut down. This checks Qt/widget wiring, not Windows display integration or user hardware.

The opt-in real Ollama test is skipped unless `AIGENTICS_TEST_OLLAMA_MODEL` is set. No live cloud-provider request was made and no user credential was required. A wheel build verifies package assembly; it is not a signed Windows executable.

## Windows acceptance smoke procedure (not yet executed)

1. Install via README with Python 3.12. Launch the app using the module command and then the `.cmd` shortcut. Verify both tabs and responsive resizing.
2. Start your local Ollama; discover models and choose an exact installed tool-capable model. Run a laboratory prompt. Confirm real capability/latency/usage records in History, or a useful connection error if Ollama is stopped.
3. Create/save/duplicate/edit an agent. Export/import it, checking that import gets a new identity. Restart and confirm the saved definitions remain. Delete the duplicate and confirm the original remains.
4. Create a disposable project containing `input.txt` with `hello aigentics`. Request a tool-based read and creation of uppercase `output.txt`. Deny the first diff; verify no output file. Run again and approve; verify the exact bytes on disk.
5. Enable command permission and request `python --version` with the full Python path if needed. Confirm explicit approval and an actual exit code. Run a deliberately failing test in the disposable project; confirm a failed command result, regardless of the model's final wording.
6. While reviewing an edit to an existing file, change that file in VS Code before approving. Confirm the stale hash blocks the proposed overwrite.
7. Test cancellation during inference, during approval and during a long-running approved command. Confirm the session reaches a recorded stopped state, no later tool executes, and the GUI remains usable. Server-side inference may continue until timeout.
8. Test `../` and secret-file access through file tools; confirm denial. Command approval is separate and is not an OS sandbox.
9. Enable session-content capture only for this disposable project. Perform a short exchange, restart and resume it from history. Confirm conversation text returns and prior tools are not replayed. Metadata-only sessions retain evidence, without restart-resumable transcripts.
10. Stop the process during a run, reopen and verify the session is `interrupted`. Launch a second instance using the same data folder and verify it is rejected.
11. Load the selected Desktop `.env`; confirm only variable names display. Test a cloud profile if desired. Test OS-vault saving on Windows separately. Inspect exported evidence for secrets before sharing.
12. Label a run Goal met/Needs work. Inspect summary counts and assessment export. Delete it and verify events, messages and assessment disappear. Test retention with disposable sessions; do not use valuable history for this check.

## Troubleshooting

- **No module named PySide6/aigentics:** use the checkout's `.venv\Scripts\python.exe` and reinstall using README.
- **Ollama connection failure:** start Ollama locally, check its endpoint and installed model name. A cloud task cannot reach your PC's `127.0.0.1`.
- **No native tool capability:** choose a tool-capable model/profile. There is no simulated fallback that translates prose into filesystem actions.
- **HTTP 401/403/404/429:** check credential reference/access, endpoint/model name and quota respectively. Error bodies are deliberately not recorded, to avoid credential/content leaks.
- **OS keyring unavailable:** keep explicitly loaded .env credentials in memory for the current launch, or configure the OS credential service. The app will not write a plaintext credential fallback.
- **Context/step/time limit:** use a focused task, inspect the recorded evidence, and adjust agent bounds deliberately. Context is not silently truncated.
- **Linux Qt display errors:** run tests with `QT_QPA_PLATFORM=offscreen`; interactive use requires a graphical session and normal Qt system libraries.
- **Source install on Windows fails:** confirm 64-bit Python 3.11–3.13, preferably 3.12. This release has not been verified on Python 3.14 or 32-bit Windows.
