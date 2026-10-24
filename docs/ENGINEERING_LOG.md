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

Windows source run [39987348899](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/39987348899) passed for `1122085`: tests/lint, actual installation/shortcut/startup, 14 packaged offline checks and the pinned 0.3.0-to-current preservation test including diagnostic sharing state. Annotated v0.4.0 tags that exact passing source; publication/download evidence follows.

Release tag build/publish [39987814325](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/39987814325) succeeded for `1122085a5fafd8fa67188e08653e73da010f2d91`. Published [0.4.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.4.0) installer fetched through production Updater.download and rechecked by verify_download: 42160968 bytes; SHA-256 `f5a145e65c15815b69b3e85a8397ec15a4cf64394f6af2e14f69d9518486df12`. Final validation: 107 passed, 1 optional live-Ollama skipped, lint/format/dependencies, both source smoke modes, wheel contents, Windows fresh install/14 offline diagnostics/actual 0.3.0 upgrade. No live user key, cloud generation or real report POST was used; Qwen remains an open live integration issue.


## 2026-10-23 — 0.5.0 source research and implementation

Reviewed approved reports #3/#4; recorded sanitized conclusions in maintenance/ISSUE_TRIAGE.md. Plan saved before implementation in maintenance/UPGRADE_050_PLAN.md. Public source audit covered Codex routing, OpenCode providers/tools/layout, Claude Agent SDK contracts, Aider maps and exact Ollama v0.40.8. Findings/citations are in maintenance/RESEARCH_050.md; proprietary/private internals were not claimed inspected.

Implemented a frozen tool registry, source-map/retrieval tools, remembered projects/briefs, recent chooser/project history, explicit context preview/revalidation, Builder/Reviewer templates, one-call native challenge probes with remote consent, optional four-route local comparison and confirmed route selection. Native IDs are preserved; structured NDJSON/SSE streams must complete before calls can be used. Ordinary model JSON remains non-executable. API checks remain one metadata GET/connection without generation.

Reports now retain actual HTTP status/environment, typed failure counters and active parser/renderer/template_source without raw templates/prompts. Browser token controls are hidden unless direct sharing is chosen. Review caught/fixed stale cross-project excerpts, truncated-map validation, false preflight request counts, missing HTTP200 on protocol failures and cross-model probe comparisons. Retrieval uses fresh reads and no persistent source index/embedding calls; vector/MCP/team work is deferred with acceptance criteria.

Linux validation: 196 passed, 1 optional real-Ollama skipped; lint/format pass. Both source smoke modes exited0; suite 3 includes 17 packaged offline checks. UI windows rendered with synthetic projects and no network calls. Windows installer/actual 0.4.0 upgrade and final release results follow after execution. Live Qwen/native/cloud certification is not claimed from fixtures.

Windows source run 40003263224 failed one fixture expectation: Path.write_text produced CRLF while the expected hash assumed LF. Retrieval correctly hashed the physical bytes. Updated the assertion to physical file bytes and added an explicit CRLF regression; no production hash behavior was relaxed. Local result196 passed / 1 skipped; rerun follows.

Windows source run [40003836390](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/40003836390) succeeded at `2f1a47a`: tests/lint, real wizard/shortcut/startup, 17 packaged checks and actual pinned 0.4.0 upgrade preserving settings, agents, session messages, diagnostic sharing state and model catalogs. Annotated v0.5.0 uses that exact passing source; tag publication and public download verification follow.

Release tag run [40004436196](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/40004436196) passed and published [0.5.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.5.0) from `2f1a47abd0c997b01aebc60628d515c7f37b708f`. Production updater check using current 0.4.0 discovered 0.5.0, downloaded the real installer and verify_download passed: 42249411 bytes; SHA-256 `6346fdb868b947393fd02d454986f2c37edf0152ec447beda631cab4735cc42c`. Final baseline: 196 Linux tests passed / 1 optional live-Ollama skipped; lint/format/dependencies, wheel/new modules, both source smokes, Windows tests/install/17 offline diagnostics/actual 0.4.0 upgrade all passed. No user keys, live model generation or real support POSTs were used; user-side native probe acceptance remains open.


## 2026-10-23 — 0.6 verification and recovery

Read approved issues5–8 and the supplied session as evidence only. Qwen3:8b native approved edits work; Qwen2.5-Coder14b still produces text calls across four routes. App17 offline+update checks and five catalog endpoints pass. Session exposes hash-copy/recovery friction, an obvious literal unpacking bug, unsupported working-game claims, confused planning and missing agent identity. Raw session/code/paths were not committed.

Recorded plan before implementation in maintenance/UPGRADE_060_PLAN.md and public source findings in maintenance/RESEARCH_060.md. Implemented compile/static checks (no execution/import), run-scoped last_read with unchanged hash/review gates, recovery and current-check counters, plain-language diagnostics/history, explicit read-only planning/identity, selected-run minimal approved sharing and user acceptance counters. Existing schema5/locations/retention retained. Suite4 adds two fixtures (19 offline total). Windows actual 0.5 upgrade additionally checks project briefs and assessments. Initial test failures were expected old counter/count fixtures and a new synthetic provider missing its profile; corrected fixture setup/expectations, without relaxing production guards. Final Linux/Windows/publication evidence follows.

0.6 local validation:214passed/1 optional-live-Ollama-skipped; lint/format/dependency checks, source startup and19 offline diagnostic smoke passed. Synthetic Workbench and Python-check GUI renders inspected. Final code review added explicit checked-file identification in the local viewer only; public reports still exclude it. Windows source/install/0.5upgrade and release results follow.

Final retention review found manual check/run reports needed immediate pruning rather than waiting for the next runtime/startup prune. Added it to both builders and a bounded-report regression. Final local result215 passed/1skipped; lint/format pass. Source8eca6c0 Windows run 40038989780 is superseded by the retention fix; only the final source may be tagged after Windows validation.

Windows source run [40039113039](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/40039113039) passed for final source `a4cfbb6351a876b024205b1992139abec7ce795a`; superseded run 40038989780 also passed. Annotated v0.6.0 targets the final source. Tag release run [40039425834](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/40039425834) passed Windows tests/build/actual installation/shortcut/startup/19 packaged checks and actual 0.5 upgrade preservation, including project briefs and assessments. [0.6.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.6.0) is published. Production updater current 0.5.0 discovered 0.6.0 and downloaded/reverified the installer: 42269820bytes, SHA-256 `f38c7035e1d62943cae018d2fcdccabb8af609dedaf32793c71e3e9d6daf14ea`. Final local 215 passed/1 optional live skipped; lint/format/dependencies, both source smoke modes, wheel contents and synthetic UI inspection passed. No live model call, user key or real report POST was used here. Qwen3 editing is user evidence; full gameplay and Qwen2.5 compatibility remain separate acceptance tasks.


## 2026-10-23 — 0.7 task checks and preserved partial work

Reviewed issues9–12 and supplied PDFs/logs as evidence. Issue10 independently passes21checks on0.6;11 catches syntax error;12 records Needs work despite7successful calls. Pasted trace establishes wrong filename/redundant rewrite. Qwen3.5 supplied traces show11successful tools/two writes but3empty visible finals. Read-back byte hashes confirm literal newline escapes in some older generated Python; no original source/log/path was committed. History grew despite prompts saying new execution. Root causes beyond these observations remain unproven.

Recorded plan before code in maintenance/UPGRADE_070_PLAN.md and public-source research in RESEARCH_070.md. Implemented explicit per-task output/tool/read-back checks with ToolRunner write restrictions, current revision checks, fresh UI default/explicit continuation, incomplete_response with deterministic preserved-operation facts and no retry/replay, skipped no-op writes, effective permission context and fixed public counters/coverage. Schemas/retention/installer channel stay unchanged. Commands retain separate approval and are not sandboxed by file-tool targets. Native prose never becomes executable.

Local 242 passed/1optional-live skipped; lint/format/dependencies and both source smokes pass. Suite 5 includes 21 offline cases. Synthetic GUI task controls inspected. Initial expected regressions were the changed fixture count and an old same-content approval-race test; changed that test to propose a real edit so stale rechecking remains exercised. Added a no-op revision-change regression. Windows actual 0.6 upgrade and publication evidence follows.

Final acceptance-prompt review caught a target-suggestion guard treating “Do not run commands” as a prohibition on file edits. Narrowed it to actual read-only/write prohibitions and added the exact command-free create/read-back phrasing as a regression. Final local243passed/1optional live skipped; source run40043314475 is superseded by this correction and must not be tagged.

Windows source run40043314475 exposed one synthetic no-op fixture using platform-translated write_text newlines while proposing LF content; on Windows that is a real CRLF-to-LF edit and correctly requires approval. Seeded the intended unchanged bytes explicitly with write_bytes; production revision/approval logic was not relaxed. An explicit CRLF no-op regression already passes separately. Run40043492768 is superseded by this fixture correction. Final Windows rerun follows.
