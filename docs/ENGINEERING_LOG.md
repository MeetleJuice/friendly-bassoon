# Engineering log

A durable development record, not a store for raw user traces or secrets. Append verified observations and links; keep old decisions understandable.

## 2026-10-23 — 0.1 foundation and 0.2 delivery

Built the native Agents/Workbench application, bounded runtime, Ollama/compatible providers, workspace tools, reviewed actions, SQLite history and human assessments. Then added Desktop key-file/model discovery, custom icon, per-user Inno Setup installer and checksum-verified release updates.

0.2.0 release source: `5cc3aa7`. Successful Windows build/install/shortcut/startup: [39965837080](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/39965837080). Release build/publish: [39966453059](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/39966453059). Published installer hash: `f7f1ab999f9df45e0bf2a6d5e0c7d4839c477a1f82732ade95de59f07602874e`. Explicitly closing SQLite backup handles was necessary for Windows retention/deletion.

## 2026-10-23 — observed user failure, sanitized regression

The user's first real local-model coding task produced a JSON-looking `list_files` request as ordinary assistant content. There were no native tool calls, no file operations, and no approval request. Version 0.2.0 labeled the ended model turn `completed`, which was confusing despite its unverified-result wording. Ollama reported tool capability; the export did not prove the underlying server/template cause. Do not claim a specific Ollama bug from that evidence alone.

The original export and personal paths are not committed. The minimal response shape is represented synthetically in tests/test_diagnostics.py. Acceptance: text is never executed; native-protocol recovery is bounded; persistent failure is explicit; a corrected native write still requires normal approval.

## 2026-10-23 — 0.3 research and implementation

Primary-source findings and rationale: docs/RESEARCH.md. Adopt application-owned permissions/hooks, bounded correction from real execution evidence, versioned deterministic evaluations, structured trace metadata, data minimization and separate approval for sharing. Do not import broad frameworks merely because they are references.

Implemented 12 packaged diagnostic checks, optional actual local-model create/read-back verification, completion sound, local report history, exact-preview GitHub issue sharing, ambiguous-submission handling, explicit Update/Diagnose buttons, readable activity and truthful response/execution statuses. Diagnostic schema v3 migrates existing SQLite data without replacing agents/history. Reports are limited to 20 completed records plus active records under the existing age retention setting. No cloud model is called automatically by diagnostics.

Sharing uses public GitHub Issues, not commits of user data into source history. Browser drafts need a final Submit action on GitHub; optional direct API sharing requires an existing Issues-write token. No OAuth client was fabricated. Direct submission uses controlled HTTP tests; no real issue was posted during development.

Windows validation now includes downloading the immutable 0.2.0 installer with its pinned checksum, seeding synthetic settings/history, upgrading to the new installer and checking preserved state plus v2→v3 migration. Publication and final check counts are recorded after the release checks complete.

Validation before tagging: 84 Linux tests passed, 1 opt-in live-Ollama test skipped; lint/format, native entry-point/diagnostic smoke and package/dependency checks passed. Windows run 39976752180 passed the full build/install/shortcut/packaged diagnostics and actual 0.2.0 upgrade/data-preservation checks. A final validation-feedback regression additionally verifies that Pydantic validator context/input values do not leak or break JSON serialization. No live report POST was made. Version-tag build/publish run [39977576531](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/39977576531) passed for release source `55b1ed3`. The public 0.3.0 installer was downloaded through the production updater and verified against its checksum: `d1161b40dbd74f717fdc15525c170666c6bce5095bc347d0d6fab85605205746`, 42135079 bytes. The executable is unsigned; live user Ollama/GitHub-report permissions remain local acceptance checks.


## 2026-10-23 — 0.4.0 evidence-driven maintenance

Read approved Issues #1/#2: both 7b and 14b models ended in protocol_error after two corrections; the other 13 checks passed. Model test durations were 10,328/43,500 ms. This disproves a simple larger-model workaround, not a particular server/model cause. Sanitized conclusions are in docs/maintenance/ISSUE_TRIAGE.md; no raw export was committed.

Added metadata-only, one-GET-per-unique-connection model checks, bounded concurrency/no retries, persistent catalog timestamps and failed-refresh preservation. Model listing is not generation authorization, quota or tool certification. No cloud generation or real user credential was used here. Missing keys and first-page pagination are explicit.

Added Local data inventory/retention controls and schema v4 catalogs, preserving old reports/sharing states. Reports/catalogs default to a 10 MB payload budget, oldest completed data pruned first; active reports are protected. Backups now obey age plus newest-three limits. Existing Windows data/project/key locations are not moved.

Health suite 2 adds two offline checks and bounded structural live-model evidence; no raw templates/prompts/model text. Large browser drafts preserve compact failure traces. Added docs/maintenance as the next-update index with triage, test/release matrix and user feedback instructions. Linux validation: 107 passed, 1 optional local-Ollama skipped; lint/format pass. Windows CI will test the pinned 0.3.0 installer upgrading to schema v4, including saved diagnostic submission state. Release results are appended after execution.

Source --smoke-test and --diagnostic-smoke-test both exited 0 in disposable directories; dependency check passed and the 0.4.0 wheel built with new modules/icon included.
