# 0.20 — final proof, grounded review and useful measurements

Status: implemented; release validation in progress. Publication requires the exact-source Windows gate and immutable artifact promotion.

## Evidence and scope

The newly attached ZIP has the exact SHA256 of the already reviewed 0.19 bundle, `6a5b7a5aab4e52f1f5f536eb7cc4d99f326616956ee2284e2bd7267b20ec2fe3`. It is not an independent second campaign. [The findings](RESULTS_0190_REVIEW.md): 29/29 app checks, 20/24 trials; two Vera final-read omissions, missing Scout source reads and a wrong Sentinel citation. Orion delegated to Ada but did not dispatch Sentinel; direct reservations were placeholders.

Apply the evidence without unrestricted retries, model-setting changes or weaker graders. Existing research and source-access limits remain in RESEARCH_0190.md. Native search already returns one-based lines; no new citation tool or external dependency is needed.

## Implemented

1. **Verification-only feedback:** admit the existing single feedback round only when every unresolved failure is a tracked eligible no-effect proposal error, all saved writes still match disk, all semantic/source/tool/unchanged checks pass and only readback is missing. Advertise only read_file; independently restrict execution to pending declared output paths. No writes, commands or unrelated reads. Real current-revision readback resolves errors; offering feedback does not. Preserve original failure counters, acceptance, step/deadline/cancel limits and refusal for other errors.
2. **Grounded cases:** retain the focused core; add Scout's comment trap, Sentinel's clean negative and a shifted-line defect requiring native search, source reads and exact values. A guessed correct answer cannot substitute for required operations.
3. **Reviewer canary:** two explicitly required-review trials exercise Orion → Ada → Sentinel within the existing aggregate 12 requests / 49,152 output reservation / deadline. Code requires a verified read-only Sentinel stage. Review prose does not replace strict artifact acceptance. Ordinary pilot review stays optional.
4. **Budget/evidence:** retain the direct RootBudget and export measured counters beside managed counters, review-required/completed flags and actor totals. Measurement5 uses known all-actor response usage plus rejected-response counters; archives keep their original calculation. Private-safe verification_feedback_count distinguishes the restricted proof phase.
5. **Focused32 + health30:** campaign8, measurement5, runtime5, pilot3, health12. Recommended62 outcomes; full64/94 remains optional, Discovery66 unchanged. Twenty focused slots depend on advertised thinking-off support; 12 matched thinking pairs. Installed offline fixture tests successful readback and blocked mutation. Skips/partial data remain useful; two hours is a ceiling, not a duration promise.
6. **README:** current installation/update/testing/contribution guidance, original Midnight Crew emblem banner, labelled historical result graph and existing labelled native screenshot. Reproducible documentation artwork adds no desktop dependencies and is not falsely described as archived user originals.
7. **Report serialization performance:** after the first Windows gate timed out, profiling identified repeated redaction of growing snapshots as a measured CPU hotspot. Reuse repeated string results only inside one scrub traversal, bounded to1,024entries/262,144combined characters and4,096characters per eligible input/output. The existing reentrant lock provides a coherent credential state; no memo survives the call or a later credential update. Every uncached/over-limit string still passes the original redactor, and every diagnostic snapshot is still saved. No production SQLite durability change.

## Boundaries

Keep the selected 8B engine, personal profiles, automatic context and sampling defaults. No weights training, 9B promotion, cloud generation, API-key tests, MCP, email connection or external telemetry. Email needs a separate provider authorization, durable message identity, authenticated command and ambiguous-send design; no mailbox/password setup is required now.

## Validation and delivery

Synthetic replay against immutable 0.19 reproduces needs_review / failed1 / recovered0 / feedback0. New runtime completes with failed1 / recovered1 / feedback1, preserving error history. Native regressions cover wrong-phase actions, unsupported done, denial followed by valid read, wrong values, changed revisions, missing source/tool/unchanged proof, exhausted steps and cancellation. Scripted review dispatch, skipped/failed review, search evidence, aggregate budgets and private-safe export are covered.

Freeze manifest5; retain manifests1–4 and exact 0.19 report/summary/check roundtrip. One full local suite after implementation, lint/format/dependencies, startup/30 packaged offline checks and wheel/source fidelity. Final Windows gate tests actual install/shortcut/packaged health, pinned published0.19 upgrade/data preservation and silent restart. Promote that exact successful artifact without rebuilding; verify public productionUpdater from0.19 and commit a receipt with [skip ci].

Synthetic green is harness evidence, not a claim that the user's model improved. Next user acceptance: one queued focused run and one reviewed ZIP; no repeated full suites merely for green.

## Windows timeout investigation

Candidate d861e4d/source40246310010 was not published: tests timed out at12minutes after500+completed checks and no recorded assertion failure. The last-started diagnostics UI test is not a proven cause. Slow completed full-campaign tests took53–65seconds. A diagnostic-only workflow40247528337 compared offline health on one Windows runner:0.19health6,750ms,0.20health6,297ms(newverification500ms); a temporary in-memory proof experiment5,547ms/63ms. This does not identify the new fixture as the main slowdown, so production/disk policy stays unchanged. This profiling workflow cannot substitute for the release gate.

Same local64campaign under cProfile:16.14→13.49seconds after memoization; redact calls385,502→58,255, save_diagnostic cumulative8.632→5.234seconds, all177snapshots retained. Observational developer CPU measurement, not a local-model speedup or Windows success claim. Privacy-equivalence/bounds/rotation/concurrency checks pass before a new complete exact-source Windows gate. This justified follow-up addresses a measured bottleneck; do not repeatedly rerun an unchanged failing gate.
