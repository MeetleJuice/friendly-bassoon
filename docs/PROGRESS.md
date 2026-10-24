# Build progress and next actions

## 0.12 implementation complete; Windows release gate pending

Latest application/release candidate: `56d3770c28d9a9b97be3cec8317c9b4f670d53ac`. Windows validation: [40119061155](https://github.com/MeetleJuice/friendly-bassoon/actions/runs/40119061155), on pinned Windows2022. Do not tag or claim publication before this exact source passes the full installer/upgrade/restart workflow. Documentation-only commits after this candidate may skip CI; release the explicitly validated source, not an unverified HEAD.

Local final result: **714 passed, one optional live Ollama test skipped**. Source startup,24packaged offline diagnostics, dependency consistency, lint/format, wheel building and actual42attempt Qt campaign rehearsal pass. Deep produces66results:24offline+42model attempts. Six roles are individually usable; no orchestration/MCP or real-user model success is claimed. Safe continuation, exact requirement reporting, dual preview consent, silent future updates and resumed-report retention are implemented.

Initial source40115798980 failed with generic exit1 and no step details. Superseded Windows-latest runs exposed0steps and stalled far longer than prior successful0.11 run (14steps/about5minutes). Added crash breadcrumbs, phase outcome annotations, finite phase limits, and a controlled pinned runner comparison. Cause remains unproven; do not describe the runner change or Qt test cleanup as a confirmed fix. Superseded runs were cancelled to avoid continued resource use. User has no new installer yet. Pinned run40117966348 passed all tests and package building but installer verification hit its six-minute limit. PowerShell Start-Process -Wait includes child processes and was waiting for the intentionally persistent relaunched GUI. The smoke now waits only for setup Process.WaitForExit(120000) and checks the GUI independently. Twenty focused installer/updater tests pass; see ENGINEERING_LOG for Microsoft documentation and evidence boundaries.

Next: inspect run40119061155. If successful, create immutablev0.12.0 at56d3770, wait for tag installer/release workflow, verify public installer using production Updater(current_version=0.11.0), record size/SHA/runIDs in VERIFICATION and ENGINEERING_LOG, then publish the concise user steps. If failure, inspect explicit annotations/last-test context; preserve all acceptance gates. `/tmp/verify_aigentics_0120_release.py` accepts sourceSHA/sourceRun/tagRun arguments. Do not overwrite an existing tag/checksum. Original artwork has no accessible binary; faithful direction is in design/MIDNIGHT_CREW.md.

## 0.11.0 delivered: deeper evaluations and verified recovery

Published [0.11.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.11.0) from immutable `a3f362868a72abf06222c613c607688df7f771fd`. Windows source run40096724399 and tag run40097100418 passed tests/lint/build, actual installer/shortcut/startup/23packaged checks and pinned released0.10 upgrade preserving definitions/history/sharing/catalogs/project briefs/assessments/settings and uncertain task-plan state. Local537passed/1optional live Ollama skipped (89additional regressions vs0.10). Source smokes/dependencies/wheel and actual synthetic full-GUI41check rehearsal passed; its two previews were about2k/3.3kcharacters with explicit approval still required. Production Updater(current_version=0.10.0) discovered/downloaded/reverified the public installer: 42330746bytes, SHA256 `48783cd34a0d4277d22f798f797a492031837fbacad603ac48ab1c554934cc84`. No user key/live model or real issue POST used in development. Real18-case local-model performance remains for user acceptance, not inferred from fixtures.

Read maintenance/UPGRADE_0110_PLAN.md and CHECKPOINT_0110_REVIEW.md before further changes. Suite4 has18real native-agent exercises; packaged health6has23offline checks. Automatic catalog calls/checkbox and repeated legacy-history counters are removed; manual Test APIs, History and Diagnose remain. Typed schema errors feed a bounded native-call correction; only matching read-only validation can resolve operationally, with original failures retained. No denial/write/prose bypass. Checkpoints use effective latest file ownership, explicit early session binding/reconciliation and confirmation-time hash checks; no guessing or replay. Windows directory identity and equivalent scoped output-path spellings have actual regressions. Obsolete Qt worker signals cannot bind a later job.

Next acceptance: Update/install/restart, run queued Balanced suite4 once using the remembered working local agent (bounded up to45minutes), review/submit both GitHub drafts and provide URLs. Examine original10 and new8cases separately; record missing/failed operations, typed validation, recovery, usage and budget stage. Do not rerun for green or compare suite4as if conditions matched older suites. For manual plans, verify two sequential edits of the same disposable file; explicit refresh/reconcile must never re-execute an interrupted action. MCP/OS sandbox/unattended Ralph remain unimplemented.

## 0.10.0 delivered: coordinated budgets and explicit checkpoints

Published [0.10.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.10.0) from immutable `2f74f93129799564f1f47d71063519afc20abb94`. Windows source run40088844799 and tag run40089079949 passed tests/lint/build, actual installer/shortcut/startup/21packaged checks and pinned released0.9 upgrade preserving prior data and an uncertain task-plan setting. Local448passed/1optional live Ollama skipped (45additional tests). Source smokes, dependency checks, wheel and native plan dialog rendering/inspection passed. Production Updater(current_version=0.9.0) discovered/downloaded/reverified the public installer: 42314475bytes, SHA256 `81681a21b42e3623a19cff80e4e54410d26f48fb7603b6b450c8c3a4f69788ba`. No live user model/key or support POST was used in development; balanced-budget improvement and user acceptance remain to measure.

Read maintenance/UPGRADE_0100_PLAN.md before continuing. Suite3 Balanced default couples output/request/session bounds; Legacy is an explicit separate budget comparison, never a hidden retry. Local project-scoped task plans allow one fresh step at a time, explicit accepted output-hash checkpoints, predecessor revalidation and review/reset for uncertain attempts. Capacity32projects/16steps refuses eviction. No autonomous Ralph/MCP or general sandbox integration. Plans persist as local bounded configuration, separately from aged runtime history.

Next acceptance: Update from0.9, install/restart and run queued Balanced suite3 once. Review/submit both GitHub drafts; provide links. Then optionally test a two-step task plan in a disposable project: run → inspect → verify checkpoint → run next. Missing/changed files must block continuation; do not reset an uncertain attempt until its effects are reconciled. Compare Legacy deliberately only if useful to isolate the budget hypothesis.

## 0.9.0 delivered: measured harness and backpressure

Published0.9.0 from immutable `dd80858397566aeadcfeb9f4fa8561d92096213f`. Source Windows run40050971888 and tag run40051222173 passed tests/lint/build, actual installation/shortcut/startup/21packaged checks and pinned released0.8 upgrade preservation. Local403passed/1optional live Ollama skipped (150additional regressions). Full source smokes, dependency checks and wheel pass. Production Updater(current_version=0.8.0) discovered/downloaded/reverified the public installer: 42302410bytes, SHA256 `cebcca98a7fb39fb6b371e9039ff40a1b784ecfca8953283f1fe640822708ab5`. No user key/live model or actual issue POST was used. User live acceptance is pending; model failure correction is a hypothesis to measure, not a certification.

Next: click Update in0.8, install/restart and let queued suite2 run with the remembered local agent. Review and submit both GitHub drafts, then provide their issue URLs. Compare within suite2; tool visibility and edit/Python output budgets differ from suite1. Live data should resolve discovery error types and whether edit moves past OUTPUT_LIMIT. Read maintenance/UPGRADE_090_PLAN.md before further changes. MCP/skill scripts/vector indexes/unattended Ralph restarts remain unimplemented by design.

## 0.8.0 delivered: guided tests and reviewed reports

Ten isolated native agent exercises,21offline app checks, optional metadata-only API refresh, readable progress/results, completion sound, bounded saved evidence/configuration-scoped comparisons, hover hints and two jointly approved browser drafts are implemented and released. Update queues one suite after the target version restarts and preserves the chosen suite agent. See maintenance/UPGRADE_080_PLAN.md, RESEARCH_080.md and VERIFICATION.md for evidence and boundaries.

First upgrade from0.7: Update/install/restart, then click Test suite, choose the working local Ollama agent, Go. Review both previews after completion, approve once, then click Create on both GitHub browser pages and send both issue URLs. Older0.7 cannot queue the new workflow retroactively. Later0.8 Update clicks queue it. File exercises stay in fresh temporary folders, host commands/cloud fallback remain disabled, disabled tools skip and interrupted/cancelled cases cannot pass. API model listing uses at most one metadata GET per unique connection and does not certify generation.

## 0.7.0 task checks and trustworthy outcomes

Implemented maintenance/UPGRADE_070_PLAN.md using approved issues9–12 and the supplied evaluation/log evidence. Adds visible output-file restrictions, required native tools/current post-write read-back checks, fresh context by default, preserved incomplete-response work, separate runtime facts, skipped no-op writes, permission preflight and safe evidence/coverage counters. Existing schema5/agents/locations/retention remain. Local 243 tests pass / 1 optional live Ollama skipped;21 packaged offline checks and both source smokes pass. Windows source 40043557907 and tag/release 40044023333 passed actual installation, 21 packaged checks and the released 0.6 upgrade. Published 0.7.0 was downloaded/checksum-verified by the production updater; see VERIFICATION.md.

## Delivered baselines

0.6.0:215Linux tests/1 optional skip; Windows source 40039113039 and tag 40039425834 passed actual installation/19 offline checks/0.5upgrade. Public updater download verified. User issue10 independently passes21checks including the actual selected-model file task; issue11 catches syntax error; issue12 records the wrong-target task failure despite successful tools.

0.5.0:196tests/1skip, projects/retrieval/native probes,17offline checks, verified Windows installer and0.4upgrade. 0.4.0:107tests/1skip, metadata catalogs/retention,14offline checks, verified0.3upgrade. Earlier delivery and immutable hashes/run IDs remain in ENGINEERING_LOG.md and VERIFICATION.md.

## Next useful user acceptance

Run the released0.8 guided suite once using a known working local agent. A failed case is useful evidence; avoid repeat runs merely to obtain green results. Share the two reviewed reports via the generated browser drafts and send their submitted issue URLs. Full bounded traces remain local; only the exact allowlisted summaries are public. No token is needed for browser sharing.

## Validation boundaries and deferred work

Cloud fixtures and Windows CI do not certify the user's GPU, live cloud models, gameplay or universal native-tool compatibility. Qwen2.5's text-tool failure and the precise Qwen3.5 empty-final cause remain open. Explicit task operations are not a general English-goal evaluator. Python static checks do not launch code, validate dependencies or certify controls/audio. Approved host commands remain outside a true OS sandbox and can access other files; output restrictions apply to file tools.

Deferred: independent installer signing/Authenticode, atomic multi-file transactions and rollback, Windows Job Objects/OS sandboxing, full provider certification/credential UX, richer review UI, measured tokenizer/context compression, controlled live benchmarks and embedding/MCP/team features with separate permission/cost policies. No automatic uploads, cloud generation, source self-modification or trained improvement is claimed.


## 0.8 implementation history

See maintenance/UPGRADE_080_PLAN.md and maintenance/RESEARCH_080.md (relative to docs). Adds ten isolated native cases, per-case bounded evidence, two exact approved drafts, one-shot target-version update queue and shared hover help. Existing schema5/storage/healthsuite5 remain. No live model or issue POST used in development. Final test/Windows/release results will be recorded before delivery.


## 0.9 harness implementation and validation

Read maintenance/UPGRADE_090_PLAN.md for research sources, term definitions, evidence and deferred integrations. User issues13/14 show8/10native acceptance, unknown discovery error and pre-tool OUTPUT_LIMIT;21offline+5model-list checks passed. Added schema-inclusive request accounting, suite2 least-authority tool disclosure and differentiated output budgets, typed failure reporting and three-identical-failure circuit breaking. No automatic replay or permission expansion. MCP/SKILL scripts/embedding/Ralph restart integration remain deferred with rationale.

Expanded local result402passed/1optional live skip, including128permission subsets, Unicode/context accounting, actual pre-dispatch context rejection, repeated-failure breaker, public typed-error fidelity and existing full GUI bundle regression. Synthetic schema measurement: default6advertised tools2750serialized characters; list-only347, search-only356, read+write1181. These are character savings, not measured token/latency or live-model success gains. Source startup/21offline smoke and lint/format pass. Windows/install/upgrade/release verification follows. Persistent source/SQLite safeguards remain intact.


## 0.10 implementation validation

Reports15–17 reviewed: suite2 discovery now passes; retrieval stops before tools with OUTPUT_LIMIT, edit times out near45s, separate model create/readback and all21offline/API5checks pass. Implemented maintenance/UPGRADE_0100_PLAN.md: explicit suite3 balanced/legacy mode, clamped coordinated deadlines and output caps; numeric rejected-response usage; readable expected/observed failures; local user-authored step plans with manual hashes/checkpoints and no replay. Successful steps are not automatically certified, no autonomous Ralph/MCP activation. Plan limits refuse eviction and reset invalidates subsequent verification. UI project-switch and dispatch failures preserve uncertain state without attaching unrelated sessions.

Local448passed/1optional live Ollama skipped; lint/format/dependencies, source startup and21checkdiagnostic smoke pass. New tests cover32budget combinations, numeric failure privacy/compact URLs, real Store restart, checkpoint revision/ordering/protected paths/other-project rejection, failed UI dispatch and capacity preservation. Native task-plan dialog rendered/inspected. Windows/release evidence follows. No live user model/key/report POST used in development.


## 0.11 implementation evidence

User explicitly requested removal of automatic API checks and richer useful evaluations. Read primary sources and reviewed issues18/19 (19newest). Plan maintenance/UPGRADE_0110_PLAN.md and checkpoint audit record evidence/limits. Implemented18live cases/23packaged offline checks, no automatic metadata endpoints, typed schema feedback with narrowly correlated read-only recovery, session binding/reconciliation and effective latest checkpoint revisions. Detailed failures remain counted and permissions unchanged. Report tables retain all18rows under browser limits with grouped budgets and no private inputs. Automatic health excludes repeated historical counters; manual diagnostics remain available.

A separate ordered-acceptance audit rejected three false passes (wrong/no post-read no-op, missing specific stale/reread ordering, input reads after transformation). Real GUI two-step execution verifies fresh context, explicit approval, bound distinct sessions, legitimate overlapping output edits and next-step validation. Qt worker signals are scoped to their originating job so obsolete queued completions cannot bind a new plan. Snapshot confirmation races, foreign projects, absent output, interruption and forbidden acceptance all have concrete disk/SQLite/GUI regressions.

Local528passed/1optional live Ollama skipped; lint/format pass. Primary research cites OpenAI Evals/Pydantic/LangGraph checkpoint source and Temporal documented replay distinction; integrations are not claimed. More test count is not a live model reliability metric. Source smokes, actual Windows released0.10 upgrade and publication follow.
