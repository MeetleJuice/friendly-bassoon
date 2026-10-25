# Test matrix

| Layer | Location | Acceptance | Limits |
| --- | --- | --- | --- |
| Unit/regressions | Linux and Windows CI | Temporary filesystem/process operations, controlled provider HTTP, permissions, protocol, catalogs/retention and UI workers | Fixtures are not live models |
| Packaged diagnostics, suite 2 | Source and installed app | 14 disposable checks including GET-only catalog/deduplication and active-report retention | No user project testing or automatic cloud generation |
| API models, api-models-1 | Explicit Test APIs action | At most one GET per unique adapter/endpoint/credential reference; parsed, cached, dated models | First page only; no generation/tool/billing certification |
| Optional real local model | User's PC | Exact disposable file bytes plus read-back and completed runtime | Up to 180 seconds of local generation; no cloud fallback |
| Fresh installation | Windows CI | Real installer, shortcut, executable startup, installed diagnostics | Not the user's GPU/Windows 10 |
| Upgrade from 0.3.0 | Windows CI | Pinned old installer SHA; agent, setting, session, message and diagnostic sharing state survive schema 3→4 | No backward downgrade support |
| Published download | Cloud | Production updater checks actual release size/SHA | Same GitHub trust channel; unsigned exe |
| Report sharing | Fixtures/user browser | Exact preview, model opt-in, redaction, approval; draft distinguished from upload | No live issue creation in automated tests |

Run AGENTS.md's checks and record actual counts/run IDs in ENGINEERING_LOG.md and VERIFICATION.md. Keys stay on the user's PC. Prefer one focused acceptance run per meaningful change over repeated tests of every model.

Validated 0.4.0 baseline: 107 passed, 1 live-Ollama skipped; Windows source run 39987348899 and tag/release run 39987814325 passed. The actual released installer download/checksum passed; see VERIFICATION.md.


0.5 acceptance adds native NDJSON/SSE completion/fragment/limit tests, scoped challenge probes/consent/request counts, fresh ignore-aware context and >250 display-prefix validation, project definitions/briefs/history and schema 4→5 upgrade with model-catalog preservation. Health suite 3 has 17 offline checks. See UPGRADE_050_PLAN.md and RESEARCH_050.md; final validation belongs in VERIFICATION.md.

Validated 0.5.0: 196 passed / 1 optional live test skipped; source Windows run 40003836390 and release run 40004436196 passed. Production updater check/download/SHA verification passed. See VERIFICATION.md for immutable source/hash and the remaining live boundary.


0.6 adds Python compile/no-execution/literal assignment cases, current-versus-historical checks, run-scoped read revisions (including CRLF, review races, denied approval and wrong explicit hashes), recovered/unresolved edit counters, read-only planning, selected-file UI and minimal run-report privacy/assessment rules. Suite4 has19 offline checks. The previous installer is pinned0.5.0; upgrade preservation also covers remembered project briefs and user assessments. Final counts/run IDs are recorded in VERIFICATION.md.

Validated 0.6.0:215 passed/1 optional-live skipped; Windows source 40039113039 and tag/release 40039425834 passed. Production 0.5 updater discovered/downloaded/checksum-verified 0.6.0. See VERIFICATION.md for immutable source/hash and acceptance limits.


0.7 adds wrong-target blocking before approval, exact write/read-back/current revision checks, required-native-tool enforcement, safe missing finals without replay or thinking substitution, no-op/CRLF/revision safety, fresh/continued UI dispatch, disabled-tool preflight and private-target report filtering. Health suite 5 has 21 offline checks. Windows upgrade pins released 0.6.0's verified hash; preserve all prior fixture data. Final counts/run IDs belong in VERIFICATION.md.

Validated 0.7.0:243 passed/1 optional-live skip; Windows source 40043557907 and release 40044023333 passed. Production updater current 0.6 discovered/downloaded/checksum-verified 0.7.0. Immutable source/hash and limitations are in VERIFICATION.md.


## 0.8 guided suite

See maintenance/UPGRADE_080_PLAN.md and maintenance/RESEARCH_080.md (relative to docs). Adds ten isolated native cases, per-case bounded evidence, two exact approved drafts, one-shot target-version update queue and shared hover help. Existing schema5/storage/healthsuite5 remain. No live model or issue POST used in development. Final test/Windows/release results will be recorded before delivery.

Final0.8:253 local regressions pass/1 optional live skip; Windows source40047789947 and tag40048328486 pass real installation/shortcut/packaged21checks/released0.7 preservation. Production public updater download/checksum accepted. See ../VERIFICATION.md.


## 0.9 final evidence

Published0.9.0 from immutable `dd80858397566aeadcfeb9f4fa8561d92096213f`. Source Windows run40050971888 and tag run40051222173 passed tests/lint/build, actual installation/shortcut/startup/21packaged checks and pinned released0.8 upgrade preservation. Local403passed/1optional live Ollama skipped (150additional regressions). Full source smokes, dependency checks and wheel pass. Production Updater(current_version=0.8.0) discovered/downloaded/reverified the public installer: 42302410bytes, SHA256 `cebcca98a7fb39fb6b371e9039ff40a1b784ecfca8953283f1fe640822708ab5`. No user key/live model or actual issue POST was used. User live acceptance is pending; model failure correction is a hypothesis to measure, not a certification.
128subsets cover all built-in permission combinations; Unicode/schema-envelope tests, real pre-dispatch context rejection, repeated failures and successful recovery, typed-error allowlist/compact browser fidelity and full native GUI bundle remain offline synthetic acceptance, not universal model compatibility.


## 0.10 delivery

Published [0.10.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.10.0) from immutable `2f74f93129799564f1f47d71063519afc20abb94`. Windows source run40088844799 and tag run40089079949 passed tests/lint/build, actual installer/shortcut/startup/21packaged checks and pinned released0.9 upgrade preserving prior data and an uncertain task-plan setting. Local448passed/1optional live Ollama skipped (45additional tests). Source smokes, dependency checks, wheel and native plan dialog rendering/inspection passed. Production Updater(current_version=0.9.0) discovered/downloaded/reverified the public installer: 42314475bytes, SHA256 `81681a21b42e3623a19cff80e4e54410d26f48fb7603b6b450c8c3a4f69788ba`. No live user model/key or support POST was used in development; balanced-budget improvement and user acceptance remain to measure.
Regression depth includes32budget combinations, rejected-response numeric usage/privacy, browser URL bounds, durable Store reopen without replay, checkpoint ordering/revision/protected paths/cross-project rejection, failed UI dispatch correlation and32-project capacity without uncertain-state eviction.


## 0.11 final evidence

Published [0.11.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.11.0) from immutable `a3f362868a72abf06222c613c607688df7f771fd`. Windows source run40096724399 and tag run40097100418 passed tests/lint/build, actual installer/shortcut/startup/23packaged checks and pinned released0.10 upgrade preserving definitions/history/sharing/catalogs/project briefs/assessments/settings and uncertain task-plan state. Local537passed/1optional live Ollama skipped (89additional regressions vs0.10). Source smokes/dependencies/wheel and actual synthetic full-GUI41check rehearsal passed; its two previews were about2k/3.3kcharacters with explicit approval still required. Production Updater(current_version=0.10.0) discovered/downloaded/reverified the public installer: 42330746bytes, SHA256 `48783cd34a0d4277d22f798f797a492031837fbacad603ac48ab1c554934cc84`. No user key/live model or real issue POST used in development. Real18-case local-model performance remains for user acceptance, not inferred from fixtures.
Coverage adds18case exact byte/ordering contracts, negative no-tool prose, wrong-target/no-readback/no-initial-read falsepasses, Unicode/empty/multiline/nested/multi-input outputs, stale/no-op behavior, strict schema feedback privacy/recovery, real SQLite interruption, superseded checkpoints, stale dialogs/confirmation races/foreign roots, full native two-step plan GUI and obsolete queued workers, browser summaries up to24cases, and safe path aliases. Increased count measures regression coverage, not live-model reliability.


## 0.12 campaign acceptance

- Controlled role definitions/model clones/personal agent preservation: real Store/restart tests.
-18specialist semantic/byte fixtures and adversarial evaluators: source/JSON/Unicode/duplicates/links/unexpectedchanges; no model-generated execution.
- Realnative-runtime42attempt campaign and Qtworker66-step flow; no cloud/APIs/source retention.
- Exactrequirement evidence, read/write order, latestrevision, denial/cancellation, stale recovery, safe boundedtimelines.
- Resume supersession/inflightnonreplay/SQLite restart/timeoutisolation/chargepersistence/faultinjection.
- Public42row worstcase/privacy/knownusage/unknowninterruptedtiming/twoconsentpreview limits.
- ActualWindows wizard/shortcut/24packagedchecks/pinned0.11upgrade/silentrelaunch; releasegate.
- LiveOllama capability remainsuseracceptance, distinctfrom fixture correctness.


## 0.14 expanded acceptance

Campaign3Deep66attempts (42existing +18variants +6output-cap comparisons), Standard36, Quick0model calls; health8has25offline checks. Native wrong-content correction, oracle mutations across36specialistcases, typed/truncated response privacy and real66attempt GUI/consent/resume/retention checks added. Final local and Windows counts/run IDs remain in VERIFICATION.md. Windows upgrade pins actual0.13checksum. The global2hourlimit can leave incomplete coverage; fixtures do not establish live model reliability.


Published [0.14.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.14.0) from immutable `b9dde2768961ae72a1da47693d4a8c839589af9d`. Source Windows run 40146622078 and release run 40147100352 attempt2 passed the complete test set, lint, packaging, actual installer/shortcut/startup,25offline diagnostics, pinned0.13upgrade/data preservation and silent automatic GUI restart. The first tagged run timed out at its8minute test bound; last started test was test_suite_0110 Unicode acceptance. The same immutable source had already passed Windows; an unchanged fresh-runner retry preserved all gates. Timeout cause is unproven. Local full865passed/1optional live model skipped plus5additional native HTTP-budget/denial/step-bound regressions pass; final57GUI/correctness focused tests and source smokes/dependencies/wheel/lint/format pass. Windows runs validate the entire871collected-test set, with optional platform/live skips as applicable. Production Updater(current_version=0.13.0) discovered/downloaded/reverified the public installer: **42412800bytes**, SHA256 `c14a900e252ab23c0e71add22d9c5ac7fcb7b5f30233d41762583348824db1c8`. No live user model/key or support POST was used in development.


## 0.14.1 verified delivery

Published [0.14.1](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.14.1) from immutable `20af8cde4232eee532d29b00c617343a4ddb6913`. Source Windows run40153849074 and release run40154380304 attempt1 passed full tests/lint, packaging, actual installation/shortcut/startup,25offline diagnostics, pinned released0.14upgrade/data-preservation and silent restart. Local885tests passed/1optional live model skipped; ZIP-focused9cases, source smokes, dependencies, lint/format and wheel pass. Production Updater(current_version=0.14.0) discovered/downloaded/reverified public installer **42420035bytes**, SHA256 `aeedf86f83c97a8067b09dc89ac2541f5a49b4b785774c5e474ee98057f5429d`. No live user model/key, real support POST or automated upload used.

Lossless compact JSON plus bounded1MB/66casecampaign allowance fixes the250KBcapacity rejection; other reports retain250KBcaps and global retention remains. Queued updates continue matching interrupted campaigns using existing scope/budget/no-replay guards. Last unsaved results cannot be reconstructed. Reviewed localZIPexport works for partial/completed campaign/health reports independently of GitHub completion approval. Immutable bytes,3MBlimit/static names/hashmanifest, numeric traces/action timelines and strict sharing allowlist preserve useful bounded evidence without private content/model names. User saves locally and drags ZIP into support chat; GitHub issues are optional; direct upload remains future work. Campaign3/crew2tasks/model budgets unchanged, so0.14partialcontinuation remains compatible. The original campaign report can retain0.14.0as its creation version; ZIPmanifest records0.14.1as exporter. User supplied only copied progress, not an approved/submitted full report. Raw text is outsideGit; no actual user's SQLite was remotely inspected.


## 0.15 additions

Contract diagnostics test strict byte/AST distinctions, typed JSON paths, bounded structure and redaction. Native runtime feedback and correlated failed/corrected calls have regression proof against immutable0.14.1 behavior. Measurement exercises all30attempts through actual Runtime and Qt worker, manifests/order/budgetarms, repeated unknown-aware metrics, mutation on first/lastattempt and cancellation/continuation. Dense66row telemetry survives realSQLitecompression/reopen/ZIP. Export tests reject untrusted manifest/private fields and require exact approval before saving. CI covers actual released0.14.1 upgrade/data preservation and restart. Synthetic outcomes do not certify the user's model.


## 0.15.0 verified delivery

Published [0.15.0](https://github.com/MeetleJuice/friendly-bassoon/releases/tag/v0.15.0) from immutable `84866b7a184bfcb81e2065d49302745d82b713e5`. Source Windows run40173676957 and tag/release run40174199391 attempt1 passed tests/lint, packaging, actual installation/shortcut/startup,25offline diagnostics, pinned released0.14.1 upgrade/data preservation and silent restart. Local1045tests passed/1optional live model skipped; Ruff/dependencies/source smokes/wheel and green-red-green pre-fix proof passed. Production Updater(current_version=0.14.1) discovered/downloaded/reverified the public installer: **42455740bytes**, SHA256 `ae4f463aab3724e81537cae624aaf2298580381cd4b5d0d35bbfd0c379e860c9`. No live user model/key or support POST used; model improvement remains for user acceptance.

Default Measurement now has30local attempts plus25offline checks (55results): each of six roles repeats one task three times, and Unicode/no-op each have two repetitions of reference/output-only/coordinated budget arms. Optional Deep discovery66 remains. Frozen synthetic manifest/digest, safe initial/final contract diagnostics and per-call typed schema evidence improve diagnosis; strict grading stays. In-flight cancellations are unknown, not scored model failures. Dense evidence survives bounded lossless campaign compression, database reopen and reviewed localZIP. Private content remains excluded and nothing uploads automatically. No model training/MCP/orchestration/reasoning toggle/tool expansion added. New compressed records require0.15+; downgrade unsupported. Manifest SHA256 `0dcfdb6158c959aa7ac6c6591b862031f7edb75813bccf9aafb3184431b9261d`. Source f48458f/run40173348851 was intentionally superseded before release by the cancellation correction; no published tag was overwritten.

Next: keep Ollama running, Update/install/restart and let the queued Measurement run finish once. After completion or Stop safely, Review / save diagnostic ZIP → inspect → approve local saving → Save → drag ZIP into support chat. No token or issue submission needed. Partial results are useful; do not rerun merely for green. Compare only matching manifest/configuration and inspect repeated coverage/unknowns, content repairs, tool-schema errors and allowance/time outcomes separately.
