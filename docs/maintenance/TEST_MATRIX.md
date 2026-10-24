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
