# 0.18 draft — Orion coordination and measured model profiles

**Status: implemented and published as0.18.0; actual Windows and public-updater verification passed. See RELEASE_0180_VERIFIED.json.** User accepted Orion's name and manager role and requested a plan based on the new ZIP. Public installer0.18.0is available; the user upgrades through Update. See RESULTS_0170_REVIEW.md; user confirmed the ZIP uses the same8Bmodel as before; exact tag/quantization remain omitted. Keep the praised UI and existing Update/restart/reviewedZIP flow.

## Outcome

Make inference settings explicit and measurable; preserve a generalist baseline; introduce a bounded, observable coordinator pilot. One selected local engine serves the six roles sequentially. No automatic9B switch, server/environment changes, separateModelfiles, weights training, API-key generation suite, MCP expansion or unrestricted orchestration.

## 1. Versioned roles and Orion migration

- Canonical active crew: Orion(coordinator), Scout(investigator), Ada(builder), Vera(test engineer), Sentinel(reviewer), Atlas(continuity).
- Coordinator identity is a typed role/kind, never inferred from an editable display name. Orion gets allowlisted dispatch/status/evidence capabilities, no direct file writes or commands. Workers cannot delegate recursively.
- Preserve existing custom definitions and historical session/benchmark IDs. Keep the legacy generalist template as an internal independent evaluation baseline; historical George3/3 is not a manager score. Explicitly handle stock-versus-user-edited migration rather than silently replacing personal instructions.
- Archive trusted manifest2 identity/bytes alongside manifest1 before changing role/schema/runtime policy. Benchmark3 must disclose the actual new definitions. Archived ZIP export must remain complete and retain original versions/outcomes.

## 2. Recorded inference profiles and fair calibration

- Replace hard-coded native temperature with validated per-profile options, preserving0.2for existing profiles. Thinking default/on/off stays capability-verified. Limit supported options to documented finite numeric ranges; distinguish omitted/inherited from explicitly requested values. User-facing presets are few, readable and experimental until validated.
- Record the requested temperature/sampling/output/thinking values and safe server-reported controls. Request settings override ModelFile values; do not claim a terminal profile is the app profile.
- Establish current8Bdefault versus8Bthinking-off across all roles first, since the4/4fast matched passes came from8B. Compare9Bunder the same baseline conditions and fair tuning; change one factor at a time. If naming a model winner, use fair settings/budgets for both models, not only one tuned contender. Record quantization/parameter-size and allocation observations where API metadata supports them, without secret values or model names unless approved.
- Extend on/off trials across each role, especially Vera and Scout, plus hard/boundary/negative tasks. Do not infer complex reasoning quality from two easy scenarios. Keep deterministic expected outputs and source-grounding checks.
- Serial model blocks avoid constant reloading; record cold-load time/order and observed contexts. Do not silently pin8192or alter keep_alive/MAX_LOADED_MODELS. Mismatched observed settings are labelled, not treated as controlled matches.
- Stage a short calibration before a full candidate run to bound elapsed work. Predeclare trial order, repetition counts, selection criteria and total time/call/output budgets. Report selection and missing coverage honestly; do not stop/retry just to obtain green.

## 3. Targeted Vera/completion improvements

- Retain strict schemas, byte checks, current-revision proof and final readback. Do not pass a timed-out session merely because an output happens to be correct.
- Diagnose JSON_PARSE with safe reason enums and line/column positions, never file excerpts/keys/answer values. Record initial versus corrected output and final readback separately.
- Make correction guidance explicitly sequence repair→read final artifact→finish. Reproduce the final-write-without-final-read scenario before choosing a behavior change. Existing finite feedback/step/time limits remain; any new verification phase must be explicit, bounded and separately measured/versioned.
- Consider a schema-validated JSON writer only if improved modes still show recurring syntax failures. It must retain the same approved diff/path/revision/write-scope guards and strict value grading. It is not a prerequisite for the first coordinator pilot.

## 4. Bounded coordinator pilot

- Start with a closed build/review workflow: Orion assigns Ada, then optionally Sentinel for read-only review. Treat a two-dispatch limit as this pilot's chosen bound, not a universal research ceiling. Other specialists stay individually usable/tested; expand routed workflows when evidence supports them.
- Keep simple direct-agent mode for the baseline. The coordinator should not automatically invoke all five workers.
- Use one local model and serial execution, one writer at a time. Reuse existing linked sessions/checkpoint foundations before adding new persistence layers. Root-run time/call/output limits include the coordinator and every child; cancellation propagates and survives restart as interrupted/unknown, without silent replay.
- Handoffs carry bounded task/acceptance data, evidence references, output ownership and current revision hashes. Exclude unrelated history. Reject stale/conflicting handoffs and illegal routing. The app owns authoritative state and permissions; an LLM reviewer is advisory, not a replacement for actual checks or user approvals.
- In the UI show who owns the task, current stage, evidence, approvals and remaining budget. Preserve exact local writes/command approval. An empty or rejected worker result cannot become success through Orion's summary.

## 5. Tests, measurements and local ZIP

- Frozen same-task individual baselines; separate comparison track for model/profile treatments; separate direct-versus-managed workflow trials with matched TOTAL budgets, counting routing/review/narration overhead. Do not combine them into one undifferentiated success score.
- Positive/negative reviewer fixtures, invalid/recursive dispatch, missing/empty result, stale revision, denied write, cancelled child, crash/reopen, duplicate completion, aggregate budget exhaustion and late UI signal tests. Actual native tool paths and actual Qt workers matter more than tests that mirror implementation.
- Retain candidate definitions/configuration IDs, per-role/per-stage results, first-try versus repaired outcomes, known-only tokens/timing, tool/route failures and incomplete coverage. Final-response evidence must distinguish an earlier provisional reply from the terminal outcome.
- Improve private-safe target-role/ordinal evidence so a read of the wrong file is distinguishable without exporting private paths. ZIP membership/hash/size validation and existing bounded retention remain. No automatic public upload or private content collection.
- One Update→restart→queued recommended run→review/saveZIP workflow. The final workload/count is set before implementation, with bounded stages and a clear duration estimate; avoid an unbounded Cartesian product of every model/setting/role.

## 6. Acceptance and delivery gates

Full relevant native/schema/GUI/storage regressions, lint/format, source startup/offline smoke, wheel fidelity, actual Windows installer/shortcut, released0.17upgrade/data preservation/restart and productionUpdater verification. Preserve the newly fixed explicitUTF8 readers, integer spent-budget guard and always-joined GUI test workers. Keep critical CI failure annotations available; progress stays ordinary logs.

Use a tested coordinator feature flag/pilot surface until matched local runs demonstrate benefit. Name change alone is not an architectural upgrade. Ship inference-profile/evidence foundations first; activate the managed pilot only after its safety/state/budget tests pass. No release or app modification is authorized by this planning document alone.


## Implemented scope and predeclared workload

Campaign6 / measurement3 / crew3 / strict-contract4 / verified-completion3. Retain34 trial slots, add18 role thinking-off trials and4 total-budget direct/managed comparisons:56model slots plus28offline checks =84recorded outcomes. Scout/Vera repeat1 pairs lead the fixed order; there is no outcome-dependent early selection or hidden retry. Total campaign ceiling remains7200s; completion is not promised by that time. All26off-dependent slots skip when explicit active-default controls are unavailable. Personal settings remain unchanged; measurement temperature0.2 and inherited top-p/top-k are explicit and recorded. Test a9Bcandidate by selecting its saved model separately, not automatic reloads.

Orion is a typed coordinator; only an exact stock George definition migrates in place. User edits/custom George remain, with a separate Orion record. A saved generalist session keeps its original snapshot. The internal George benchmark remains a generalist baseline, not a manager score. Closed pilot uses canonical bounded worker definitions on Orion's selected native local engine, independent of personal worker editor changes. Workbench selection plus explicit outputs starts the experimental pilot; direct agent mode remains the default elsewhere. Workers cannot dispatch. Root12requests/49152outputreservation (further clamped by root steps), maximum2worker dispatches, one serial writer and original root time include all planning/worker/narration calls. Child links are lineage only, never conversation replay. Read-only review is advisory, not semantic proof; arbitrary daily tasks only prove configured operational checks unless an application-owned acceptance contract is supplied.

Sampling presets edit the preview; saving is explicit. Existing temperature0.2/model-defaultthinking retained. Omitted top-p/top-k are server-inherited, not known numeric settings. No universal vendor optimum or hidden-compute guarantee claimed. Current scope adds parameter/quantization metadata and allocation/context end observations when reported; no per-request full GPU telemetry, seed isolation, automatic model tournament or schema-validated JSON writer.

Release optimization: main-branch Windows source run remains the full gate. An explicit promotion dispatch verifies successful source/run/artifact provenance, downloads that immutable installer, verifies version/checksum and publishes without another full run/build. Published tags/checksums cannot be overwritten. Public BUILD_PROVENANCE.json records the binding. This replaces duplicate source/tag validation, not the actual installer/upgrade checks.
