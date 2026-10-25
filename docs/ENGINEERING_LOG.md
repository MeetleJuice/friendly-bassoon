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

Local 242 passed/1 optional-live skipped; lint/format/dependencies and both source smokes pass. Suite 5 includes 21 offline cases. Synthetic GUI task controls inspected. Initial expected regressions were the changed fixture count and an old same-content approval-race test; changed that test to propose a real edit so stale rechecking remains exercised. Added a no-op revision-change regression. Windows actual 0.6 upgrade and publication evidence follows.

Final acceptance-prompt review caught a target-suggestion guard treating “Do not run commands” as a prohibition on file edits. Narrowed it to actual read-only/write prohibitions and added the exact command-free create/read-back phrasing as a regression. Final local243 passed/1 optional live skipped; source run40043314475 is superseded by this correction and must not be tagged.

Windows source run40043314475 exposed one synthetic no-op fixture using platform-translated write_text newlines while proposing LF content; on Windows that is a real CRLF-to-LF edit and correctly requires approval. Seeded the intended unchanged bytes explicitly with write_bytes; production revision/approval logic was not relaxed. An explicit CRLF no-op regression already passes separately. Run40043492768 is superseded by this fixture correction. Final Windows rerun follows.

Final Windows source run [40043557907](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/40043557907) passed at `56dd94a79f133170a012ed157f5740eb764139df`. Annotated v0.7.0 targets that exact source. Tag/release [40044023333](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/40044023333) passed tests/build/actual wizard/shortcut/startup/21 packaged checks and pinned 0.6 upgrade preservation of all seeded definitions/history/sharing/catalogs/project briefs/assessments. [0.7.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.7.0) is published. Production Updater.check(current_version=0.6.0) found 0.7.0, downloaded and verify_download accepted the actual installer: 42278420 bytes, SHA-256 `169c3350d7bd375b30af68c20421915f57158b9355207e4af5894a64dfd4b8d4`. Final Linux 243 passed/1 optional live skipped; lint/format/dependency checks, source smokes, wheel contents and final synthetic UI inspection passed. No user key/live model request or real issue POST was used here; no universal model repair, gameplay proof or independent signing is claimed.


## 0.8 guided suite implementation history

See maintenance/UPGRADE_080_PLAN.md and maintenance/RESEARCH_080.md (relative to docs). Adds ten isolated native cases, per-case bounded evidence, two exact approved drafts, one-shot target-version update queue and shared hover help. Existing schema5/storage/healthsuite5 remain. No live model or issue POST used in development. Final test/Windows/release results will be recorded before delivery.

Local0.8 validation:250 passed/1 optional live Ollama skipped; lint/format/pipcheck/source startup and packaged21-check diagnostics passed. Deterministic suite uses actual runtime/tools, all ten cases pass; negative tests cover wrong queries/prose, cloud rejection, disabled tools/cancel, exact dual-preview consent, no-update dispatch and target-version queue consumption. Native dialog rendered/inspected; final Windows/release verification pending.

Full synthetic GUI workflow caught a browser URL overflow that unit previews with empty fixtures missed. Fixed suite-specific compact rows preserving all10 statuses/timing/native/write/error/check/final/token counters plus model metadata; full traces remain local. Added regression on the real ten-case report and graceful local-only failure if any future browser preview cannot fit. Added correct saved-suite guidance distinct from offline fixture checks. Final local suite252pass/1skip.

Promoted the full GUI rehearsal into a regression: actual worker executes21health+1deduplicatedmetadata+10native fixtures, completes all ten table rows, prepares two bounded URLs (about2.7k/3.1k) with consent still required and no synthetic source/model name in public previews. This caught a missing result-table update hookup, now fixed. Final suite253passed/1optional live skip; final source Windows validation follows.


## 0.8.0 verified release

Published [0.8.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.8.0) from immutable source `496eafd32f8d3585cdf5d9f7a164f9a671eec8c5`. Windows source [40047789947](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/40047789947) and release [40048328486](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/40048328486) passed tests/lint/build, actual installation/desktop shortcut/startup, 21 packaged offline checks and the pinned released0.7 upgrade preserving seeded agents/settings/history/messages/report sharing/catalogs/project briefs/assessments. Local253 passed/1 optional live Ollama skipped; source smokes/lint/format/dependencies/wheel and full synthetic GUI workflow passed. Production Updater(current_version=0.7.0) discovered0.8.0, downloaded and reverified the actual installer: **42301574 bytes**, SHA-256 `4587ca6dce5c7f0fda052566fd469e743527e61a543d8539e2b67edcac469a31`. No real model/key or support POST was used in development. User-specific live-model acceptance remains to run; installer signing is unchanged.

The workspace disconnected after final source validation, before publication. On resuming, verified the exact source CI success, pushed immutable annotatedv0.8.0, waited for the full tag workflow and verified the public installer with the production updater. Preferred suite agent now survives future Update clicks.


## 0.9 harness implementation and validation

Read maintenance/UPGRADE_090_PLAN.md for research sources, term definitions, evidence and deferred integrations. User issues13/14 show8/10native acceptance, unknown discovery error and pre-tool OUTPUT_LIMIT;21offline+5model-list checks passed. Added schema-inclusive request accounting, suite2 least-authority tool disclosure and differentiated output budgets, typed failure reporting and three-identical-failure circuit breaking. No automatic replay or permission expansion. MCP/SKILL scripts/embedding/Ralph restart integration remain deferred with rationale.

Expanded local result402passed/1optional live skip, including128permission subsets, Unicode/context accounting, actual pre-dispatch context rejection, repeated-failure breaker, public typed-error fidelity and existing full GUI bundle regression. Synthetic schema measurement: default6advertised tools2750serialized characters; list-only347, search-only356, read+write1181. These are character savings, not measured token/latency or live-model success gains. Source startup/21offline smoke and lint/format pass. Windows/install/upgrade/release verification follows. Persistent source/SQLite safeguards remain intact.


## 0.9.0 verified delivery

Published0.9.0 from immutable `dd80858397566aeadcfeb9f4fa8561d92096213f`. Source Windows run40050971888 and tag run40051222173 passed tests/lint/build, actual installation/shortcut/startup/21packaged checks and pinned released0.8 upgrade preservation. Local403passed/1optional live Ollama skipped (150additional regressions). Full source smokes, dependency checks and wheel pass. Production Updater(current_version=0.8.0) discovered/downloaded/reverified the public installer: 42302410bytes, SHA256 `cebcca98a7fb39fb6b371e9039ff40a1b784ecfca8953283f1fe640822708ab5`. No user key/live model or actual issue POST was used. User live acceptance is pending; model failure correction is a hypothesis to measure, not a certification.

Successful tool progress resets the repeated-failure counter, verified by actual missing-file reads → approved creation → successful read with identical earlier arguments. No blind restart/replay was introduced.


## 0.10 implementation validation

Reports15–17 reviewed: suite2 discovery now passes; retrieval stops before tools with OUTPUT_LIMIT, edit times out near45s, separate model create/readback and all21offline/API5checks pass. Implemented maintenance/UPGRADE_0100_PLAN.md: explicit suite3 balanced/legacy mode, clamped coordinated deadlines and output caps; numeric rejected-response usage; readable expected/observed failures; local user-authored step plans with manual hashes/checkpoints and no replay. Successful steps are not automatically certified, no autonomous Ralph/MCP activation. Plan limits refuse eviction and reset invalidates subsequent verification. UI project-switch and dispatch failures preserve uncertain state without attaching unrelated sessions.

Local448passed/1optional live Ollama skipped; lint/format/dependencies, source startup and21checkdiagnostic smoke pass. New tests cover32budget combinations, numeric failure privacy/compact URLs, real Store restart, checkpoint revision/ordering/protected paths/other-project rejection, failed UI dispatch and capacity preservation. Native task-plan dialog rendered/inspected. Windows/release evidence follows. No live user model/key/report POST used in development.


## 0.10.0 verified delivery

Published [0.10.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.10.0) from immutable `2f74f93129799564f1f47d71063519afc20abb94`. Windows source run40088844799 and tag run40089079949 passed tests/lint/build, actual installer/shortcut/startup/21packaged checks and pinned released0.9 upgrade preserving prior data and an uncertain task-plan setting. Local448passed/1optional live Ollama skipped (45additional tests). Source smokes, dependency checks, wheel and native plan dialog rendering/inspection passed. Production Updater(current_version=0.9.0) discovered/downloaded/reverified the public installer: 42314475bytes, SHA256 `81681a21b42e3623a19cff80e4e54410d26f48fb7603b6b450c8c3a4f69788ba`. No live user model/key or support POST was used in development; balanced-budget improvement and user acceptance remain to measure.


## 0.11 implementation evidence

User explicitly requested removal of automatic API checks and richer useful evaluations. Read primary sources and reviewed issues18/19 (19newest). Plan maintenance/UPGRADE_0110_PLAN.md and checkpoint audit record evidence/limits. Implemented18live cases/23packaged offline checks, no automatic metadata endpoints, typed schema feedback with narrowly correlated read-only recovery, session binding/reconciliation and effective latest checkpoint revisions. Detailed failures remain counted and permissions unchanged. Report tables retain all18rows under browser limits with grouped budgets and no private inputs. Automatic health excludes repeated historical counters; manual diagnostics remain available.

A separate ordered-acceptance audit rejected three false passes (wrong/no post-read no-op, missing specific stale/reread ordering, input reads after transformation). Real GUI two-step execution verifies fresh context, explicit approval, bound distinct sessions, legitimate overlapping output edits and next-step validation. Qt worker signals are scoped to their originating job so obsolete queued completions cannot bind a new plan. Snapshot confirmation races, foreign projects, absent output, interruption and forbidden acceptance all have concrete disk/SQLite/GUI regressions.

Local528passed/1optional live Ollama skipped; lint/format pass. Primary research cites OpenAI Evals/Pydantic/LangGraph checkpoint source and Temporal documented replay distinction; integrations are not claimed. More test count is not a live model reliability metric. Source smokes, actual Windows released0.10 upgrade and publication follow.

Windows source40095996121 caught real checkpoint project-identity handling: tempfile paths can be represented with short/long Windows names, so string normalization rejected a session for the same physical directory. Replaced raw path spelling comparison with os.path.samefile (errors fail closed), preserving foreign-root rejection. Added equivalent spelling/identity and missing-root regressions; fixture-only canonicalization would hide the application issue, so production identity logic was corrected. Failed run must not be tagged.

Acceptance audit found an evaluator false-negative: valid ./file paths could be rejected by string equality in scoped suite approval and operation matching. Uses Workspace.path canonical identity with existing protected-path/escape checks now; wrong-file/order failures remain rejected. Eight actual native runtime regressions cover alias spelling for read/create/denial/noop/stale/transform/multiple outputs/nested output. Windows source40096313854 passed the filesystem-identity correction; this further scoring correction requires a new final source check before tagging.


## 0.11.0 verified delivery

Published [0.11.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.11.0) from immutable `a3f362868a72abf06222c613c607688df7f771fd`. Windows source run40096724399 and tag run40097100418 passed tests/lint/build, actual installer/shortcut/startup/23packaged checks and pinned released0.10 upgrade preserving definitions/history/sharing/catalogs/project briefs/assessments/settings and uncertain task-plan state. Local537passed/1optional live Ollama skipped (89additional regressions vs0.10). Source smokes/dependencies/wheel and actual synthetic full-GUI41check rehearsal passed; its two previews were about2k/3.3kcharacters with explicit approval still required. Production Updater(current_version=0.10.0) discovered/downloaded/reverified the public installer: 42330746bytes, SHA256 `48783cd34a0d4277d22f798f797a492031837fbacad603ac48ab1c554934cc84`. No user key/live model or real issue POST used in development. Real18-case local-model performance remains for user acceptance, not inferred from fixtures.


## 0.12 Midnight Crew implementation and evidence

Read maintenance/UPGRADE_0120_PLAN.md and design/MIDNIGHT_CREW.md. User approved six same-model individual roles plus automated evaluation before orchestration. Reviewed approved issues20/21:23offline checks pass,13/18live cases pass. Three failures hit output limits before native calls; edit/stale had correct bytes but unverified required operations. Public summaries cannot establish the exact omitted steps. Do not weaken verification or infer model improvement from fixture scores.

Implemented six versioned definitions with non-destructive managed roster setup; daily definitions stay editable while campaign snapshots remain controlled. New crew-campaign-1 Deep=24offline+42attempts:18baseline+18rolecases(3each)+6explicitrepeats. Standard36, Quick0model calls; sequential local Ollama only. No API checks/cloudfallback/hostcommands/orchestration/generated-code execution. Specialist acceptance checks native source reads, source-before-write ordering, exact/semantic artifacts, strict sourced JSON, unchanged inputs and unexpected files. Vera's vectors distinguish seeded mutants in deterministic evaluator tests; this does not certify arbitrary test-code execution. Baseline suite5 now explicitly requires initial edit-read and reports fixed requirement flags and task-check counters. Original failing outcomes remain retained.

Campaign ledger preserves each case, marks unknown in-flight effects without replay, refuses superseded continuation, scopes comparisons to configured model/profile/manifest, and bounds runtime to7200budgetseconds. Unknown crash timing remains unknown; up to180seconds is conservatively charged separately from measured duration. Budget charge is persisted before resume diagnostics and at completed-case save. Per-case timeout tokens are isolated. Temporary child suites use persist=False so retention cannot evict the final campaign behind24newerchildreports. Local configuration snapshots and bounded argument-free tool timelines aid diagnosis. Full raw source/prompts/answers are not retained by these synthetic campaigns; aggregate/model traces remain. Same model tag may change underlying weights; matching configuration is not proof of identical weights.

Actual Qt worker integration exercises42native fixture attempts,24appchecks,66progresssteps, addedroster/personalpreservation, stopped/resumedcampaign, twoexactreviewedpreviews/explicitconsent/oneopening andobsoleteworker rejection. Public summaries retain all42case rows with exact failedrequirementmask+legend and known-only usage under7500URLcharacters; interrupted timing uses?, not0. Actual source startup/24packagedsmoke/dependency consistency pass. Local full run: 708 passed, one optional live Ollama test skipped. Two additional guided installer-order tests passed. Silent updater flags retain checksums/path; Inno launchesautomaticallyonlyforUPDATE=1. GuidedUpdate avoids duplicate appconfirmation and persists queuedtarget/pendingversion beforeinstallerlaunch, clearsbothiflaunchfails. Real Windows previous0.11installation/upgrade and silentrelaunch gatepublication.

The workspace disconnected during finalintegration, before anycommit/push/release. Recovered workingfiles, completed audits and resumedvalidation. Original userimage has no downloadablefile/localpath; documented direction and provenance without falsely committing a replica. Futureartwork remainsdeferred. No usermodel/key or realGitHubissuePOST used in development. Actual0.12localmodel outcomes remainpendinguseracceptance.


### Final retention audit

A real cancel/continue test with a five-report cap exposed an important lifecycle bug: a resumed campaign could finish successfully and then be pruned because its original record timestamp was older than intervening reports. The final campaign save now explicitly refreshes its retention clock while preserving the report ID, original payload creation timestamp, and every prior result. Other report saves retain their existing age semantics. A database-close/reopen regression verifies the completed campaign remains available. Source candidate 5afbc43 was superseded before tagging; no published artifact was changed.


Windows source run40115798980 failed with only a generic exit-code annotation; available job metadata omitted steps and signed log download was blocked by the execution network. Candidate c976e3b includes the independently verified retention correction. Added explicit PowerShell package/installer exception annotations so a future failure provides an actionable cause through the accessible checks API, without relying on log downloads. No failed source is eligible for tagging.


CI test observability now preserves the last-started test and exact interpreter exit code when a process stops before JUnit output exists. The full campaign GUI fixture has a finite90second completion allowance for Windows I/O and always cancels/joins child workers before Qt parent teardown, including assertion-failure paths. Five focused GUI tests pass. This addresses a plausible lifecycle failure, not a confirmed cause of the earlier generic Windows failure.


Source run40116380991 remained active substantially longer than the previous five-minute successful0.11 build, without intermediate step metadata. Added finite dependency/test/package/installer phase limits and always-run phase-outcome/last-test annotations, preserving every test and installer requirement. This makes stalls diagnosable before the30minute job ceiling. The superseded run is cancelled; only the latest exact source can be tagged after success.


### Controlled Windows runner comparison

The previous successful source run40096724399 exposes14executedsteps. Recent stalled Windows-latest runs expose0steps, including the generic initial failure. This is insufficient to attribute a cause to application code. Pinning validation to the supported Windows2022 runner image tests runner variability and makes the Windows10-compatible build environment reproducible. All tests, phase limits, actual installation, previous-release upgrade and silent restart requirements remain. A pass is still required before tagging; the runner change is not presented as a proven fix until measured.


### Recoverable release handoff

Final local run:714passed/1optional liveOllamaskipped. Exact release candidate849b42b5c61316b7fccedf4f7e2629f7c4ccef7e is being validated by Windows2022 run40117966348. Product code is frozen while the external gate runs. Source startup/24offline diagnostics/dependencies/wheel/lint/format and full42attempt GUI rehearsal pass. No release tag or new public installer exists yet. Read PROGRESS.md for exact remaining steps and prior cancelled/generic-failure evidence.


### Windows installer-check timeout diagnosis

Pinned run40117966348 completed all tests/lint and built the executable/installer successfully. Actual installer verification timed out after its6minute phase limit. The new automatic-relaunch check used PowerShell Start-Process -Wait, which waits for the entire descendant process tree, including the intentionally persistent relaunched GUI. MicrosoftDocs PowerShell7.5 Start-Process documents this explicitly (https://github.com/MicrosoftDocs/PowerShell-Docs/blob/main/reference/7.5/Microsoft.PowerShell.Management/Start-Process.md). The check now starts setup without -Wait, bounds only its own Process.WaitForExit to120seconds, and independently polls/asserts the GUI remains alive. This corrects the test harness; it does not remove the relaunch requirement or change application behavior. The earlier generic first-source failure remains unproven and is not retroactively attributed to this cause. FinalWindows/release validation follows.


## 0.12.0 verified delivery

Published [0.12.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.12.0) from immutable `56d3770c28d9a9b97be3cec8317c9b4f670d53ac`. Windows source run 40119061155 and release run 40136502403 passed tests, lint, packaging, actual installation/desktop shortcut/startup, 24 packaged diagnostics, pinned released 0.11 upgrade preservation, and silent update automatic GUI restart. Local final suite: 714 passed, one optional live Ollama test skipped. Full scripted Qt campaign exercises 42 native-runtime attempts and 24 app checks with two consent-gated report previews. Production Updater(current_version=0.11.0) discovered, downloaded and reverified the public installer: **42397914 bytes**, SHA256 `372f293756a21de084894642c7b2965339379af697cd41a0f161425c0bb29dd0`. No user model/key or real issue POST was used in development.

The installer test timeout was resolved by waiting for the setup process alone rather than PowerShell Start-Process -Wait's descendant tree, which includes the intentionally persistent reopened GUI. The successful Windows gate confirms the corrected check and automatic restart. Earlier generic first-source failure remains unattributed; published tags/checksums were never overwritten. Resumed campaign retention and crash-budget reservations have real database lifecycle regressions.

Next user acceptance: click Update in0.11, finish its existing confirmation/wizard if shown, keep Ollama running and allow the queued Midnight Crew Deep campaign to run once. Expected66results:24offline plus42local model attempts, bounded to2hours. Review both previews, approve opening, click Create on both GitHub pages and provide links. Inspect baseline18, specialist18 and explicitrepeat6 separately. Saved personal agents are preserved; controlled campaign definitions share the selected model and remain separate from daily edits. Failure data is valuable; do not rerun merely for green. Original artwork direction is documented, but its raster was unavailable. No orchestration/MCP/model retraining is claimed.


## 0.13 completion feedback implementation

User approved the next update after issues22/23 and supplied seven inline artworks. Original image binaries have no local path/downloadable ID; expanded design references are documented honestly, not represented as saved originals. Plan maintenance/UPGRADE_0130_PLAN.md records scope. Added opt-in one-turn completion feedback, required native source reads, separate initial/final verification evidence, correction counts and compact report columns. Campaign version2 explicitly enables this with the same42cases and unchanged output budgets; ordinary TaskChecks retain their existing default. No correction after unresolved failure/denial, no provider-output retry, no permission expansion, no prose execution. Native regression cases verify missing readback repair without repeat writes, source grounding, wrong files, equivalent/Unicode paths, step exhaustion and public counter privacy. Existing714tests plus new focused cases pass; final checks and Windows delivery follow. No live user model or actual support POST used.


## 0.13.0 verified delivery

Published [0.13.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.13.0) from immutable `f532ebfea494271e98382df063e9a6fba3c46a3f`. Source Windows run 40141003967 and release run 40141645149 passed all tests, packaging, actual installation/shortcut/startup,24offline diagnostics, pinned0.12upgrade and silent restart. Local727tests passed/1optional live model skipped plus the new report privacy regression; Windows validates the full728test set. Production Updater(current_version=0.12.0) discovered/downloaded/reverified the public installer: **42396457bytes**, SHA256 `7d823956862338bd5ce07bc585e76bc52c533c118f7852fdd18c2767c51fbb00`. No live user model/key/supportPOST used.

Campaign2 keeps42model attempts/24offline checks and unchanged generation budgets. One feedback cycle may use remaining model steps, never additional step/time/context limits. Initial missing checks and feedback request counts remain separate from final outcomes. Source reads are explicit for specialists. Ordinary TaskChecks preserve the prior default unless opted in; personal agents/settings remain. Real improvements require user Ollama acceptance. Output-limit failures are not claimed fixed. No orchestration/MCP/model retraining added.

Seven new inline artworks are inventoried in design/MIDNIGHT_CREW.md and reference/README.md. Their original files remain inaccessible; no raster originals or generated substitutes were committed. Exact-file archival requires original attachments, preferably one ZIP.

Next: Update/restart, keep Ollama running and let queued Deep campaign2 finish once (66results, up to2hours). Review/approve both previews and Create both GitHub issues; compare feedback-needed/final outcomes and source grounding with issues22/23. Do not rerun merely for green.


## 0.14 architecture and validation

Read maintenance/UPGRADE_0140_PLAN.md for evidence, experiments, reference and explicit boundaries. Independent application-owned boolean contracts now participate in one bounded completion correction; denied/unresolved operations and checker failures cannot trigger it. Native/compatible truncated responses retain only numeric/enum shape and never dispatch partial calls. Crew2fresh campaign snapshots preserve saved user definitions. Deep66local attempts and health8/25offline checks have group-separated evidence, retained original cases and labelled output-cap comparisons; same case names do not imply unchanged cross-version conditions. New oracle mutation/native correction/privacy/GUI regressions run without live model, user keys or real issue POST. Final checks and Windows gates follow.


Local0.14verification: full865passed/1optional live model skipped, followed by5newreal-HTTP-budget/denial/step-bound regressions (52focused tests pass), plus57GUI/correctness tests after the final UI labels. All25offline packaged-style diagnostics and source startup, Ruff lint/format, dependency consistency and wheel pass. Real66attempt Qt workflow and failure-rich66row browser summary pass. No live user model/key or issue POST used. Windows will validate the complete870test set, actual0.13upgrade and silent restart before release.


### 0.14 release retry handoff

Immutable source b9dde2768961ae72a1da47693d4a8c839589af9d passed Windows source run40146622078, including all tests, actual installation, pinned0.13upgrade/data preservation and silent restart. Its test phase took4m47s. Tag v0.14.0 points to that source. Release run40147100352 attempt1 hit its8minute test timeout; last recorded node was tests/test_suite_0110.py::test_approximate_output_is_not_exact_output[unicode-cafe\n]. Packaging/publish did not run. Cause remains unproven; an unchanged failed-job retry is running as attempt2 on a fresh runner. Do not retag or weaken checks. No public0.14installer yet. After successful publication, run the production Updater check/download/SHA verification from current0.13, then record the final receipt/run attempt and update this handoff.


## 0.14.0 verified delivery

Published [0.14.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.14.0) from immutable `b9dde2768961ae72a1da47693d4a8c839589af9d`. Source Windows run 40146622078 and release run 40147100352 attempt2 passed the complete test set, lint, packaging, actual installer/shortcut/startup,25offline diagnostics, pinned0.13upgrade/data preservation and silent automatic GUI restart. The first tagged run timed out at its8minute test bound; last started test was test_suite_0110 Unicode acceptance. The same immutable source had already passed Windows; an unchanged fresh-runner retry preserved all gates. Timeout cause is unproven. Local full865passed/1optional live model skipped plus5additional native HTTP-budget/denial/step-bound regressions pass; final57GUI/correctness focused tests and source smokes/dependencies/wheel/lint/format pass. Windows runs validate the entire871collected-test set, with optional platform/live skips as applicable. Production Updater(current_version=0.13.0) discovered/downloaded/reverified the public installer: **42412800bytes**, SHA256 `c14a900e252ab23c0e71add22d9c5ac7fcb7b5f30233d41762583348824db1c8`. No live user model/key or support POST was used in development.

Campaign3Deep has66local attempts (42retained tasks/repeats,18specialist variations,6explicit1024/2048/4096output-cap comparisons) plus25offline checks. Application-owned exact/semantic acceptance participates in one bounded completion correction, without oracle answer values, permission/budget expansion, partial-call execution or provider retries. Initial/final content and operational evidence remain separate. Readback alone never certifies correctness. Existing saved user definitions remain; fresh campaign snapshots use crew2instructions. Cross-version conditions changed, and one sample per scenario/cap does not certify reliability. Numeric rejected-response shape and documented compact66row reports support the next diagnosis. Actual real-model improvement awaits the user's next campaign. No MCP/orchestration/sandbox/retraining is claimed. Original artwork binaries remain pending.


Release timeout diagnosis: unchanged attempt2 completed its test phase in4m28s (00:43:25–00:47:53UTC), compared with4m47s for the successful source run and the first attempt's8minute timeout. Both successful runs passed actual installation/upgrade/restart; the production updater accepted the public installer. The immediate publication blocker was the test-phase timeout, not an observed installer or updater failure. The exact cause of the first run's slowdown remains unproven: detailed attempt1logs were unavailable because the signed GitHub log endpoint returned HTTP403; accessible check annotations identify the timeout and last-started node only. Do not label that node a failing assertion or infer a deterministic Unicode defect. No test/time/permission/checksum gate or published tag was weakened or overwritten.


## 0.14.1 report-capacity hotfix in progress

User storage-limit exception traced to250KBgeneric cap applied to66case real-model evidence. Read maintenance/HOTFIX_0141.md. Compact lossless JSON, bounded1MB/66casecampaign capacity, unchanged250KBother/global retention, and queued matching-campaign continuation implemented. New growing-report/restart/recovery/oversize-replacement/queued-resume regressions preserve all payload evidence. Earlier committed rows remain; last unsaved/in-flight result cannot be reconstructed and must not replay. No user data accessed remotely. Local/Windows/public-updater validation follows; no release claim yet.

Local0.14.1:876passed/1optional live model skipped; Ruff lint/format, dependency consistency, source startup and25offline smoke pass. Real long-report prefix/restart/recovery and queued-resume behavior covered. Windows/release gate pending.


### 0.14.1 expanded ZIP delivery scope

Storage-only candidate a16a561 passed Windows run40152705666, but was not tagged/published: user then explicitly requested reviewed localZIPexport and drag-and-drop analysis. Added bounded immutable archive/manifest with hashes, strict sharing allowlist plus rich numeric traces/action timelines, explicit approval and atomic local save. Campaign partial export is independent of GitHub approval; Diagnose history also exports campaign/health. No upload occurs. Raw supplied progress stays outsideGit; it is incomplete and cannot establish provider failure causes. Final combined source requires new Windows/release validation.

Combined0.14.1local validation:885passed/1optional live model skipped, Ruff lint/format/dependencies and source startup/25offline smoke pass. ZIP-specific tests cover partial GUI export without GitHub completion approval, exact approved bytes, manifest hashes, trace privacy,66case/8trace retention, count bounds and failed atomic replacement. Final Windows validation follows.


### 0.14.1 release handoff

Combined immutable source20af8cde4232eee532d29b00c617343a4ddb6913 passed Windows run40153849074 (full tests/lint, packaging, actual install/shortcut/25checks, pinned0.14upgrade/data preservation and silent restart). Taggedv0.14.1at that source; release run40154380304is in progress. No public0.14.1installer claim until publish succeeds and productionUpdater(current0.14.0) downloads/verifies it. Do not retag. Source archive/wheel and rendered ZIPreview screenshot are outsideGit in /workspace/artifacts. Read HOTFIX_0141.md, DIAGNOSTIC_BUNDLES_PLAN.md and USER_TESTING.md for local ZIP/recovery flow. Userhasnotapproved/submittedcurrentGitHubreports; only copied partialprogress is supplied. No automatic upload.


## 0.14.1 verified delivery

Published [0.14.1](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.14.1) from immutable `20af8cde4232eee532d29b00c617343a4ddb6913`. Source Windows run40153849074 and release run40154380304 attempt1 passed full tests/lint, packaging, actual installation/shortcut/startup,25offline diagnostics, pinned released0.14upgrade/data-preservation and silent restart. Local885tests passed/1optional live model skipped; ZIP-focused9cases, source smokes, dependencies, lint/format and wheel pass. Production Updater(current_version=0.14.0) discovered/downloaded/reverified public installer **42420035bytes**, SHA256 `aeedf86f83c97a8067b09dc89ac2541f5a49b4b785774c5e474ee98057f5429d`. No live user model/key, real support POST or automated upload used.

Lossless compact JSON plus bounded1MB/66casecampaign allowance fixes the250KBcapacity rejection; other reports retain250KBcaps and global retention remains. Queued updates continue matching interrupted campaigns using existing scope/budget/no-replay guards. Last unsaved results cannot be reconstructed. Reviewed localZIPexport works for partial/completed campaign/health reports independently of GitHub completion approval. Immutable bytes,3MBlimit/static names/hashmanifest, numeric traces/action timelines and strict sharing allowlist preserve useful bounded evidence without private content/model names. User saves locally and drags ZIP into support chat; GitHub issues are optional; direct upload remains future work. Campaign3/crew2tasks/model budgets unchanged, so0.14partialcontinuation remains compatible. The original campaign report can retain0.14.0as its creation version; ZIPmanifest records0.14.1as exporter. User supplied only copied progress, not an approved/submitted full report. Raw text is outsideGit; no actual user's SQLite was remotely inspected.


## 0.15 implementation and evidence

Read maintenance/UPGRADE_0150_PLAN.md. Approved ZIP:66 rows,36passed/28evaluated failures/2unknown; health25/25. Retained42 cases25pass vs31previous, changed conditions prevent causal attribution. Eight feedback-assisted passes included only one content repair. Ten output-limit failures lacked visible content/native fields. Synthetic formatting/key/citation calibration is not proof of actual artifacts. Fixed a reproducible large-JSON-integer grader OverflowError.

Added bounded strict-contract mismatch feedback, per-call safe field/type/schema evidence, immutable measurement manifest, 30 interleaved repeated trials across six roles/two budget-sensitive tasks, known-only repeated metrics/comparability checks and diagnostic-only invalid-manifest handling. UI default55results; Deep66discovery remains. No API generation, reasoning toggle, tool expansion, orchestration or training. New campaign4 separates incompatible old campaign3 continuation; old reports remain exportable.

Dense evidence stress exceeded old1MBcap. Added checked lossless campaign compression:3MBraw/1MBstored/66cases,250KBother,8MBuncompressed/3MBcompressed ZIP. Global retention unchanged; downgrade readers unsupported. Synthetic manifest allowed; private content/keys remain excluded. Test-phase ceiling explicitly8→12minutes for expanded suite/prior runner variation; overall30minutes and all installer/upgrade/checksum gates remain. Pinned upgrade now public0.14.1 SHA aeedf86f83c97a8067b09dc89ac2541f5a49b4b785774c5e474ee98057f5429d. Final validation follows.


Local 0.15 validation: 1043 passed /1 optional live-model skipped in75.18s. Ruff lint/format, dependency consistency, source startup,25offline diagnostic smoke and wheel passed. Actual Qt30attempt/55result reviewed-ZIP save, dense66case storage/reopen/export and manifest mutation through lastattempt passed. Developer green/red/green proof catches three failures under immutable0.14.1 behavior and passes when restored. Frozen manifest SHA256 0dcfdb6158c959aa7ac6c6591b862031f7edb75813bccf9aafb3184431b9261d. Network proxy blocked sandboxed build/GitHub access; approved network execution succeeded without changing application behavior. No live user model/key or support POST used. Windows/public updater validation still pending.


Final read-only review reproduced an in-flight cancellation classification defect: actual role and baseline runtimes returned cancelled but their rows were counted as ordinary failure. Two real native-runtime regressions failed before the correction. Campaign rows now carry CANCELLED or CAMPAIGN_BUDGET_EXHAUSTED, and measurement also treats legacy runtime_state=cancelled as unknown. Completed-before-stop passes remain passes. Manifest policy and frozen digest updated before first publication. Superseded source f48458f /Windows40173348851 intentionally cancelled; no release tag was created. Corrected source will repeat full local/Windows gates.


Final corrected local suite:1045passed/1optional live model skipped; new in-flight stop regressions pass for both measurement and discovery. Ruff lint/format, rebuilt wheel, source startup/25offline diagnostic smoke and dependencies pass. Benchmark digest0dcfdb6158c959aa7ac6c6591b862031f7edb75813bccf9aafb3184431b9261d. Source Windows gate will rerun for this correction.


## 0.15.0 verified delivery

Published [0.15.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.15.0) from immutable `84866b7a184bfcb81e2065d49302745d82b713e5`. Source Windows run40173676957 and tag/release run40174199391 attempt1 passed tests/lint, packaging, actual installation/shortcut/startup,25offline diagnostics, pinned released0.14.1 upgrade/data preservation and silent restart. Local1045tests passed/1optional live model skipped; Ruff/dependencies/source smokes/wheel and green-red-green pre-fix proof passed. Production Updater(current_version=0.14.1) discovered/downloaded/reverified the public installer: **42455740bytes**, SHA256 `ae4f463aab3724e81537cae624aaf2298580381cd4b5d0d35bbfd0c379e860c9`. No live user model/key or support POST used; model improvement remains for user acceptance.

Default Measurement now has30local attempts plus25offline checks (55results): each of six roles repeats one task three times, and Unicode/no-op each have two repetitions of reference/output-only/coordinated budget arms. Optional Deep discovery66 remains. Frozen synthetic manifest/digest, safe initial/final contract diagnostics and per-call typed schema evidence improve diagnosis; strict grading stays. In-flight cancellations are unknown, not scored model failures. Dense evidence survives bounded lossless campaign compression, database reopen and reviewed localZIP. Private content remains excluded and nothing uploads automatically. No model training/MCP/orchestration/reasoning toggle/tool expansion added. New compressed records require0.15+; downgrade unsupported. Manifest SHA256 `0dcfdb6158c959aa7ac6c6591b862031f7edb75813bccf9aafb3184431b9261d`. Source f48458f/run40173348851 was intentionally superseded before release by the cancellation correction; no published tag was overwritten.

Next: keep Ollama running, Update/install/restart and let the queued Measurement run finish once. After completion or Stop safely, Review / save diagnostic ZIP → inspect → approve local saving → Save → drag ZIP into support chat. No token or issue submission needed. Partial results are useful; do not rerun merely for green. Compare only matching manifest/configuration and inspect repeated coverage/unknowns, content repairs, tool-schema errors and allowance/time outcomes separately.


## 0.16 research and UI implementation

User authorized a UI overhaul while their0.15local tests continue. Inspected official OpenCode app shell/desktop/provider docs and UI assets, Codex README/app-server docs, Claude README/changelog desktop references and DeepSeek's integration directory/Cline/Chatbox/Cherry sources. Several official websites were proxy-blocked; no claim of live proprietary desktop inspection. See design/UI_RESEARCH_0160.md for direct links and evidence boundaries. Do not conflate DeepSeek model/API with one desktop harness.

Added presentation.py design system/original vectors/plain-text labels, persistent sidebar and navigation-only command search. Workbench focuses on conversation with optional remembered panels, explicit write scope, value-preserving task-options disclosure and focused-only run shortcut. Agent Save is sticky around a scroll form, library actions simplified and saved role emblems added; actionable Projects empty state. Test center has separate actual outcome counters/current-case feedback/readable names/folded evidence and optional public sharing, with reviewed ZIP prominent. New task guards active context. Literal ampersands/accessibility hints fixed. No benchmark/runtime/model/tool/permission/storage changes; digest unchanged. Existing user agent definitions are not rewritten.

Visual/native geometry review reproduced/fixed current-nav deselection and small-window composer clipping. Full local1062passed/1optional live model skipped in73.91s; final focused/native package checks follow. Windows upgrade pins actual public0.15installer SHA ae4f463aab3724e81537cae624aaf2298580381cd4b5d0d35bbfd0c379e860c9. No remote interaction with user's active run, live user model/key, competitor installation or support POST. Release must pass all existing Windows and public-updater gates.


Final0.16local validation:1062passed/1optional live model skipped, followed by27focused UI/campaign/ZIP tests after final presentation-only labels/control states. Ruff lint/format, dependency check, wheel/source fidelity, source startup and25offline diagnostics passed. Actual synthetic renders at900×650,1000×740,1440×900 were inspected and included in design notes. Frozen benchmark unchanged. Windows source/release and production-updater delivery gates follow.


### 0.16 immutable release retry

Source e1d742fad7f274a21083b309eae3ac57891079a0 passed Windows40177480849, including actual installation/0.15upgrade/restart. Tagv0.16.0points to that source. Tagged run40178128741attempt1hit the unchanged12minute test-phase ceiling (08:49:54–09:01:55UTC); last-started breadcrumb tests/test_suite_080.py::test_disabled_tools_skip_and_cancel_does_not_pass. This is not a proven assertion failure/cause. Packaging/publish did not run. Signed detailed-log endpoint returnedHTTP403. Unchanged failed-job retryattempt2started on a fresh runner; no checks/time limits/permissions/tag/checksums altered. Publication and production updater verification remain pending.

The last-started timeout breadcrumb node passed an isolated Linux check in0.03seconds (1passed/0.12seconds total). This does not reproduce or explain the Windows timeout. Public research source-byte hashes recorded separately in design/UI_SOURCE_MANIFEST_0160.json; no third-party screenshots or source bodies vendored.


## 0.16.0 verified delivery

Published [0.16.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.16.0) from immutable `e1d742fad7f274a21083b309eae3ac57891079a0`. Source Windows run40177480849 and tag/release run40178128741 attempt2 passed tests/lint, packaging, actual installer/shortcut/startup,25offline diagnostics, pinned released0.15upgrade/data preservation and silent restart. Local1062passed/1optional live model skipped; final27focused UI/campaign/ZIP checks, Ruff, source smokes, dependencies and wheel/source fidelity passed. Production Updater(current_version=0.15.0) discovered/downloaded/reverified the public installer: **42489920bytes**, SHA256 `d33101ae45e7b1ed4129c1836e32495f182bce4b165a19e6e0c164d3ae59e952`. No live user model/key or support POST used.

Research and actual native screenshots are in design/UI_RESEARCH_0160.md; source access limits and DeepSeek/third-party client distinctions are explicit. New Midnight Crew sidebar/theme/original emblems, navigation-only CtrlK search, conversation-first Workbench with optional remembered panels and value-preserving Task options, scrollable agent editor with sticky Save, actionable project empty state and readable Test center outcomes/progress/ZIP flow are implemented. Existing model/harness/crew/benchmark/storage/permission rules remain; frozen digest0dcfdb6158c959aa7ac6c6591b862031f7edb75813bccf9aafb3184431b9261d is unchanged. Partial0.15campaigns remain scope-compatible; no hidden retries or additional model calls. New UI preferences are local booleans. Original character binaries remain unavailable; no claim of packaging them or competitors' assets. A UI release does not demonstrate model improvement or verify the user's exact Windows10 GPU/font/scaling behavior.

Next: let the user's existing0.15run finish and save/review its diagnostic ZIP before updating when convenient. Update/install/restart, use sidebar Test center for the queued matching continuation or new campaign, then Review / save diagnostic ZIP. Projects/Workbench/Agents are sidebar routes; Files/History expose extra panes, Task options holds checks/capture/context, Settings retains setup/update. Ask for ZIP plus any clipped/unreadable/confusing control and display resolution/scaling if known; never keys. No automatic sharing.

Unchanged attempt2 completed successfully: [{"completed_at": "2026-10-25T09:12:43Z", "conclusion": "success", "name": "Validate tests and code", "started_at": "2026-10-25T09:03:40Z"}]. Actual installation/upgrade/restart and production public-updater verification passed. First timeout cause remains unproven; no tag/time/test/checksum gate was weakened or overwritten.


## 0.17 research and implementation

User authorized research/plan/update based on reviewed ZIP and separate terminal9B opinion. See maintenance/RESEARCH_0170.md and source hashes. Thinking-off is a valid capability-dependent request, not an increase in context. Automatic8192 is not universal; server env1loaded/10mkeepalive are tradeoffs and unchanged. Kept current model/temp0.2, contextauto and0.16UI.

Reproduced two initial failing synthetic regressions: runtime no-op missing final read and ambiguous Vera wrapper. Added explicit unchanged-target proof/checklist and structural-only contract schemas, existing one bounded feedback intact. Native boolean thinking controls require advertised metadata, cached per route; manualdefault unchanged. Campaign5/measurement2/grader3/runtime2:30retained IDs plus4conditional default/off matched trials, old1manifest bytes preserved. New17code paths cover refusal/streaming/body placement/profile preservation/schema/privacy/known-only comparisons. Safe end-observation and native duration counters,27offlinefixtures and reviewedZIP retain evidence within existing limits. CI-only progress/slow-phase notices aid runner diagnosis without changing ceilings. Final validation/delivery pending; no real user generation/key/supportPOST.


Local0.17validation:1104passed/1optional live-model skipped in93.68s;45final focused tests, Ruff lint/format, source startup/27offline diagnostic smoke, pipcheck and wheel/source fidelity passed. Native Test center/Connections previews inspected. Frozen measurement2digest e5efea395071aff13862f9d943e5a9909b1e0a537e0727a2bc51e08bc51a847e; archived1bytes unchanged. Windows/public delivery gates pending.


### 0.17 source Windows attempt1

Source b146258d6d71eb5c834a96fd2386cb7b88435f80 /run40203797626 attempt1 failed during tests (14:47:16–14:58:17UTC,11m1s), exit1; this was not the12minute phase timeout. Last-started breadcrumb tests/test_task_checks_070.py::test_wrong_existing_target_blocked_before_approval_even_if_unchanged. Annotations expose several28–45s test calls but no assertion or traceback. Detailed signed log downloadHTTP403; no downloadable JUnit artifact available. Cause remains unclassified, not attributed to that last test. Same isolated node passes locally. Unchanged failed-job retryattempt2 requested on fresh runner; no source, permissions, time ceilings, tests or tag changed. No release published.


### Windows failure observability correction

The new frequent progress annotations could consume GitHub's per-step annotation quota before critical errors. Switched progress/slow-phase events to ordinary log lines; retained stdout, explicit native process exit and hidden breadcrumb in the synthetic CI artifact; separate always-run phase emits bounded output tail/exit annotations. This changes CI observability only, not tests, assertions, platform gates or12minute ceiling. Run-level detailed log route also returned403. Initial isolated breadcrumb passes1/0.14s locally. Supersede still-running unchangedretry with this diagnostic correction; no published tag exists. Failure cause remains unclassified pending real traceback.


### Windows trace leads to shutdown and integration-lifecycle correction

Corrected-reporting source c1435e18e515ab7f255a64979520b091ef13ddaf /run40205205939 exposed actual native exit-1073740940 /0xc0000374 (Windows heap failure) while ui.py error() opened QMessageBox during pytestqt setup. Preceding call955 is test_full_gui_worker_health_expanded_cases_and_two_drafts, failed after10.2s with a10s GUI wait. Last task-check breadcrumb is a subsequent setup and is not the failed assertion. Signed artifact/log storage remains403; bounded annotations now preserve exit/trace despite this. The exact native heap root is not independently proven, but the expanded real-check fixture's deadline/unsafe unfinished teardown is concrete and corrected.

Native regression first failed: after closing/cancelling an active window, a queued failure still opens a modal. Window now marks closing, refuses new task starts, skips late task result/activity/finish updates and suppresses late modal errors; error is an explicit Qt Slot. Actual job persistence/cancellation and approvals remain. Integration test uses a bounded60s wait for real Windows process/SQLite checks, asserts collected worker errors and all existing report outcomes, and always cancels/joins its worker before fixture teardown. No model/request/session limit, test assertions or12minute workflow ceiling relaxed. Final full validation and new source Windows run follow.


Post-shutdown full local validation:1105passed/1optional live-model skipped in101.83s;14shutdown/realGUI checks, source startup/27offline diagnostic smoke, Ruff lint/format, pipcheck and rebuilt wheel/source fidelity passed. Benchmark2digest unchanged. Source Windows run will repeat every gate; no immutable release tag yet.


### Windows completion and explicit Unicode benchmark reader

Shutdown-corrected source6c9a924c333669cffb7bdbe6432c1164606c9999 /Windows40206669640 completed the test process normally (15:23:46–15:30:53UTC,7m7s) with a concrete frozen-manifest mismatch: test_committed_measurement_definition_matches_runtime read new UTF8 JSON using platform-default encoding. No native crash in this run. Corrected both new/archived benchmark fixture reads to explicitUTF8; canonical manifest/hash and all runtime behavior stay unchanged. This is a test-file reader correction, not relaxation of the equality/hash assertion. New source will repeat the Windows gates. User's PC reset is unrelated to cloud build; partial local reports should be retained if any.


### Exhausted-campaign floating-point boundary regression

UTF8-corrected source ffc291e5c9ab8aaad5326e97f27190e08217b096 /Windows40207457612 completed normally:1103passed/2platform-live skips/1failure in458.75s. Golden Unicode check now passes. Failure: resumed exhausted budget dispatched two forbidden fixture attempts. Deterministic Linux reproduction with fixed monotonic10000.1 fails before correction: (7200 +10000.1)-10000.1 becomes7199.999999999998, below the exact7200second boundary. Added fixed-clock parameter alongside real-clock regression. Campaign now rejects integer spent milliseconds already at ceiling before doing clock arithmetic, and adds elapsed delta in parentheses. No time allowance increased; exact exhausted budget cannot dispatch. Intended bounded policy/benchmark definition unchanged, unpublished0.17manifest2hash stays. Full validation repeats for this actual harness correction.


Post-deadline full local validation:1106passed/1optional live-model skipped in95.88s;16focused campaign/shutdown checks, Ruff/source startup/27offline diagnostics and rebuilt wheel pass. Exhausted-budget fixture also uses a forbidden provider factory so it makes no actual endpoint observation. Final2fixed/real-clock cases repeat after that test-only isolation. No benchmark policy/hash, request/session allowance or permission change. Windows acceptance reruns from corrected source.


### 0.17 exact passing source and tagged delivery

Source ec4c06fede1e998bc22fb1afeea9e03e4af297b7 passed Windows40208559425attempt1: tests/lint (15:47:44–15:54:54UTC), packaging, actual installer/shortcut/27offline diagnostics, pinned0.16upgrade/data-preservation and silent restart (15:55:49–15:56:20UTC). Published immutabletagv0.17.0points exactly to this source. Tagged run40209357532 repeats acceptance before publishing installers. No source/tag/test/time/permission weakening. Local1106passed/1optional live-model skipped; two final deterministic deadline cases and wheel fidelity pass. Production updater verification still pending.


## 0.17.0 verified delivery

Published [0.17.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.17.0) from immutable `ec4c06fede1e998bc22fb1afeea9e03e4af297b7`. Source Windows40208559425 and tagged release40209357532 attempt1 passed tests/lint, packaging, actual installer/desktop shortcut/27offline diagnostics, pinned released0.16 upgrade/data preservation and silent restart. Local1106passed/1optional live-model skipped,16campaign/shutdown focused checks and2final deterministic deadline cases, Ruff/source smokes/dependencies/wheel fidelity passed. Production Updater(current_version=0.16.0) discovered/downloaded/reverified the actual public installer: **42512798bytes**, SHA256 `1b8740aaf190efb21bcac84a7c8eb1bf539a4bccd689ce5e63f42519a5df61a7`. Receipt: maintenance/RELEASE_0170_VERIFIED.json. No live user model/key or support upload used.

Completion now proves unchanged-file read→one identical write request→read; initial output/final JSON schemas clarify contracts without solution values or relaxed graders. Verified native default/off/on controls preserve personal settings; automatic context, temperature0.2 and server environment stay. Measurement2/campaign5/grader3/runtime verified-completion-2 records34trialslots plus27offline checks (61outcomes); four conditional thinking-off comparisons legitimately skip if controls/default are unavailable or not applicable. Matched eligible pairs and both-passed-only latency deltas, known-only native duration counters and one end-of-campaign context/server observation improve evidence. This is a new benchmark, not proof of model improvement. Frozen2digest e5efea395071aff13862f9d943e5a9909b1e0a537e0727a2bc51e08bc51a847e; trusted archived1bytes unchanged. Old reports stay exportable; incompatible partial benchmarks do not silently mix.

Windows validation exposed and corrected a GUI fixture's10s deadline/unfinished-worker teardown plus late close-time error popup path, platform-default Unicode fixture reading, and an exact exhausted-budget floating-point defect. Red/green shutdown and fixed-clock regressions remain. Closing refuses new tasks and skips late task UI updates; runtime records remain. Integration wait60s is bounded and all outcome assertions/runtime/workflow ceilings remain. CI now preserves synthetic stdout/exit/breadcrumbs with ordinary progress logs; details and superseded run IDs are in ENGINEERING_LOG.md. The original native heap root was not independently isolated; corrected source and tag completed full Windows gates without that crash.

Research/plan: maintenance/RESEARCH_0170.md and UPGRADE_0170_PLAN.md, with exact source hashes. Thinking-off does not enlarge context;8192 is not a universal automatic value. No model switch, weights training, new cloud generation, MCP, orchestration or automatic upload. Preserves the praised0.16UI and six independent same-model roles.

Next user acceptance: keep Ollama running with the current selected model; Update→install/restart→let queued Measurement finish once (or Test center→Go if not queued)→Review / save diagnostic ZIP→inspect/approve local saving→Save→attach ZIP in chat. Four control skips are useful evidence; do not rerun merely for green. Analyze initial versus corrected content/operational outcomes, known controls and both-passed timings before tuning. Actual model improvement remains unverified until that local run. No token or GitHub issue required.

Tagged tests/lint completed16:06:11UTC (8m5s); installer/upgrade/restart16:07:10–16:07:41UTC; publication16:08:02UTC. Delivery verified through production updater. Future release engineering may reuse an exact already-gated artifact with commit/version/checksum provenance to reduce duplicated build time, but must preserve actual installation/upgrade gates; not implemented in0.17.


## New 0.17 ZIP review and 0.18 draft

User accepted Orion as future coordinator name and uploaded the completed0.17ZIP. Validated archive CRC/size/hash and recomputed manifest2/summary. Sanitized conclusions in maintenance/RESULTS_0170_REVIEW.md; draft UPGRADE_0180_PLAN.md is planning only. Health27/27; trials26/34 (19firsttry,7feedback-assisted), no skips/interruption,34m24.344s. Four same-budget coordinated/off pairs passed4/4both;300.375s→18.203s,11014→437generated tokens,14requests/10nativecalls in both. Strong narrow evidence for calibration, not a universal16.5x or9B claim. Model name intentionally omitted; user subsequently confirms same8Bas before (exact tag not exported). The large narrow speed difference is8Bdefault versus8Boff, not evidence for9B. 91recorded tool calls all succeeded; remaining failures focus on thinking/output/time, strict JSON/readback rather than a broken tool transport. Preserve old generalist scores as historical; manager behavior untested. No app, runtime, server configuration or installed state changed. Raw ZIP/reports remain outsideGit; aggregate local analysis artifacts are in /workspace/artifacts/analysis-d2c20beb8497.


## 0.18 implementation and local validation

User authorized execution of the Orion/calibration draft, asking to avoid repeated full validation. Implemented typed dispatch-only Orion, exact-stock migration preserving custom definitions/history, serial build/read-only-review pilot using linked sessions, revision guards, explicit output ownership, normal diff approvals, aggregate12call/49152output reservation and shared root deadline/cancellation. No conversation replay for child lineage or interrupted team runs. Model prose/reviewer agreement never certifies task success. Operational checks remain distinct from an independent semantic acceptance contract.

Validated sampling profiles/presets preserve0.2/default; measurement requests fix0.2 with inherited top-p/top-k and capability-gated thinking. Safe request sampling, model quantization/size, end allocation/context observation, parser reason/position, ordinal read evidence and terminal acceptance survive reviewed ZIP. No model switch, context/environment change, training, keys or real user generation/upload used.

Campaign6/crew3/measurement3/grader4/runtime3:56trialslots (retained34 +18roleoff +4direct/managed),28offlinechecks=84outcomes;26conditionaloffslots. Fixed Scout/Vera calibration first, then retained comparisons and bounded pilot; no outcome-driven selection. Each role still has one repeated core scenario; optional Discovery holds broader variations. Old manifests1/2bytes unchanged and trusted for complete old ZIP export; no old score regrading. New manifest SHA256: 2e90f43b81731250ffe9d77c4a17256ebdcb45bafa6d2109c9f33f1ba8749142.

New synthetic tests cover actual native build/review paths and SQLite/Qt: permissions, invalid/recursive/duplicate/stale dispatch, missing worker reply, deny/cancel/reopen, aggregate request/output limits, stock/custom migration, wire-level sampling/inheritance and finite range rejection, safe parse diagnostics, old archive identity/export, preset preview/save, and release provenance. First full local run:1158passed/1optional live skipped/1failure in132.72s. The failure was the old cancellation fixture not advertising thinking controls: the reordered first off case skipped before its intended model cancellation. Fixed fixture advertises explicit controls; unchanged cancellation/unknown assertions pass. Follow-up120focused cases all pass, including all final changed areas. Ruff lint/format, pipcheck, source startup and28offline diagnostic smoke pass. Windows will run the full exact source once; do not repeat full local tests merely for green.

Release delivery now promotes the exact immutable installer from a successful main-branch Windows workflow. Source tests/lint/actual installer/shortcut/28packagedchecks/pinned0.17upgrade/data preservation/restart remain mandatory. Explicit promotion validates run event/repository/branch/path/commit, single unexpired artifact, package version and installer checksum, refuses an existing tag and publishes BUILD_PROVENANCE.json. This avoids the duplicate tag build/test cycle without weakening a gate. Initial no-isolation wheel command found setuptools absent; normal isolated build uses the declared backend instead. Windows/public updater delivery pending.

Final UI review caught Continue conversation silently resetting Orion to a fresh root. Explicit coordinator API already rejected a parent, but Workbench had cleared it. UI now rejects Continue for team pilots before any worker/session starts; user must choose New task. New actual Qt regression proves zero dispatch/files/session on this path; all21coordinator checks pass. Initial source a563948 /Windows40223633397 superseded before release; no tag created. Final source repeats required Windows gates for this real UI correction. Isolated wheel/source fidelity passed for the initial source; rebuild follows final UI change. No second full local run merely for green.

Approval-timeout audit found a concrete nested cancellation gap: Worker.approve waits on the outer Worker.cancel Event, while a child timer previously set only RootBudget.local. A pending UI approval could outlive the shared deadline. RootBudget.set now propagates to the outer event, and an explicit root timer covers the entire manager/worker/approval run and is cancelled on exit. Deadline-triggered local cancellation is classified as timed_out. A5second pending-approval regression proves the outer wait wakes, creates no file and leaves no running session; all22coordinator tests pass. Source9e248b2 /Windows40223773137 superseded before release for this safety correction; no published tag exists. This extra Windows pass is required by an actual source change, not a repeated green run.


## 0.18.0 verified delivery

Published [0.18.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.18.0) from immutable `ac20964f31c1ff18a8fde2617c462f67b4739716`. Windows source40225012646 passed full tests/lint (19:14:31–19:26:10UTC), packaging, actual install/desktop shortcut,28packaged offline checks, pinned released0.17upgrade/data preservation and silent restart (19:26:56–19:27:28UTC). Explicit promotion40226156569 reused that exact immutable installer; build was skipped in promotion and no tag rebuild occurred. Public BUILD_PROVENANCE.json binds source/run/artifact/checksum. Production Updater(current_version=0.17.0) discovered/downloaded/reverified **42541991bytes**, SHA256 `68264b4064d758530ed0e18dcded9a574bedb8d97251bf71c9f828f3886951ce`. Receipt: maintenance/RELEASE_0180_VERIFIED.json.

Typed Orion coordinator, exact-stock migration preserving custom George/history, opt-in bounded Ada/Sentinel pilot, shared request/output/time/approval budgets, linked fresh child sessions and no automatic replay. Reviewer prose is advisory; ordinary tasks prove operational checks, not arbitrary semantic correctness. Same selected native local engine; workers serial. Direct agents remain available. Inference presets edit preview before Save; validated sampling preserves existing0.2/default thinking and automatic context. Measurement fixes0.2/inherited sampling and verifies explicit thinking controls. No model switch, server environment/context change, weights training, MCP expansion, live user/key generation or automatic upload.

Recommended campaign6/measurement3/crew3/grader4/runtime3:56modelslots +28offlinechecks =84outcomes, including26conditionaloff-dependent slots. Scout/Vera first calibration, retained34comparisons,18roleofftrials and4matched TOTAL-budget direct/managed attempts. Each role still has one repeated core scenario; broader Discovery remains optional. Historical George generalist scores are not Orion manager scores. New manifest SHA256 `2e90f43b81731250ffe9d77c4a17256ebdcb45bafa6d2109c9f33f1ba8749142`; archived1/2bytes/identities preserved and exportable. Safe sampling/quantization/allocation observations, parser reason/location, ordinal readback and terminal acceptance improve the reviewed local ZIP. Known-only retained usage is not a complete billing total.

Local full1158passed/1optional live skip/1legacy cancellation-fixture failure in132.72s; explicit-control fixture correction preserves its original assertions. Follow-up120focused passes and final22coordinator passes include real Qt, deny/invalid/stale/recursive/duplicate/empty routes, crash/reopen/no replay, total budgets and pending UI approval deadline. Temporarily restoring old local-only cancellation reproduces the deadline regression; actual source is green. Final lint/format, pipcheck, startup,28offline source smoke and rebuilt wheel/source fidelity pass. The final exact-source Windows full run is green. Earlier candidates a563948/40223633397 and9e248b2/40223773137 were superseded unpublished for genuine Continue/fresh-context and pending-approval timeout corrections; no published tag/checksum was overwritten.

Next user acceptance: keep the same8Bmodel/Ollama running; Update→install/restart→allow queued Recommended campaign once (or Test center→Go)→Review/save diagnostic ZIP→inspect/approve local save→Save→attach ZIP. No manual agent editing, token or GitHub issue is required. Conditional skips and partial data are useful; do not rerun merely for green. Compare real per-role off/default outcomes and direct/managed overhead before changing defaults. Test9Bseparately only after reviewing8Bdata. Actual model improvement/pilot benefit remains unverified until the user's local run.

