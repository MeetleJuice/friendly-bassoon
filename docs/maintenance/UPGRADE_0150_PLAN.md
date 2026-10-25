# 0.15 — explain failures and establish repeatable measurement

## Evidence and decisions

The approved diagnostic ZIP (SHA256 ea5d5fe3359667530f34e4aa812351478bf945161bf5fa280e155e684ff794ec) had 66 campaign rows: 36 passed, 28 evaluated failures and two interrupted/unknown attempts. All 25 offline app checks passed. The retained comparison set passed 25/42 versus 31/42 previously, but instructions and acceptance changed; this is not a causal model/harness comparison. The original specialist subset declined from 14/18 to 7/18. Ten new variations passed out of 18. Of eight eventual passes after feedback, only one repaired content; seven repaired operational verification. These distinctions must remain visible.

Ten output-limit failures had thinking content but no visible content/native-call fields. Raising output allowance alone did not establish a fix: a no-op trial at 4096 reached its request deadline. The actual model/server reasoning controls remain unverified. Do not toggle unsupported controls or infer failure content from absent artifacts.

Synthetic calibration reproduced three strict-contract pitfalls: Python formatting with identical AST, JSON with extra descriptive keys, and equivalent citation spelling. This does not prove those were the user's actual outputs. Keep strict grading and explain the mismatch instead of silently relaxing it. A separate valid 1001-digit JSON integer reproduced an actual OverflowError in numeric comparison; fix it without treating booleans as numbers.

## Implemented sequence

1. Add bounded pure contract diagnosis: missing outputs, parse failures, schema pointers/types, exact formatting and citation spelling. Retain initial and final mismatches. Static hints expose no oracle answer values or actual artifact text. Clarify exact contracts in measurement prompts only; discovery retains its old prompts.
2. Capture per-call tool schema hash, allowed/required fields, safe field types, unexpected argument counts and bounded validation locations. Unexpected names are omitted except the finite registry vocabulary. Distinguish runtime schema capture from legacy current-registry fallback.
3. Add content-addressed `crew-measurement-1`: six role tasks repeated three times (18 attempts), plus Unicode/no-op across three allowance/time arms repeated twice (12 attempts). Fixed interleaved order is recorded; it is not randomization or deterministic model sampling. Same selected local model, no cloud fallback, no API checks.
4. Reference role trials use 4096 output tokens /120-second requests /180-second sessions. Baseline reference uses 1024/85/90; output-only uses 4096/85/90; coordinated uses 4096/120/180. Existing provider/session ceilings still clamp execution and actual budgets remain in each row. Output-only isolates allowance; coordinated changes allowance and time together. No reasoning toggle is claimed.
5. Default GUI/queued update campaign becomes 30 local trials plus 25 offline app checks (55 results when complete). Keep optional Deep discovery 66, Standard 36 and Quick offline-only. Each attempt has a fresh disposable workspace; permissions, bounded feedback and two-hour campaign ceiling remain.
6. Save full synthetic manifest and digest; recheck before every attempt and after the last. A changed manifest marks results diagnostic-only and prevents comparison. Manifest hashes include task fixtures/contracts, prompts, role instructions, schemas, grader/runtime policy versions and budgets. Selected connection/model configuration has a separate private fingerprint. Identical IDs alone never establish comparability.
7. Report group coverage, unknown/unrecorded trials, known-only latency/usage, observed outcome flips and paired regressions only for matching manifest/configuration. Three repeats are a pilot, not reliability certification or pass@k. No cross-version causal conclusion is implied.
8. Preserve dense evidence through SQLite reopen and reviewed ZIP export. Campaign raw JSON is bounded to 3 MB /66 cases; stored payload remains at most 1 MB using checked lossless zlib/base64 only above 1 MB. Generic reports remain 250 KB. Decode checks stream completion, checksum, length, duplicate keys, finite JSON and the decompression limit. ZIP remains at most 3 MB compressed /8 MB uncompressed. Global retention stays bounded. New compressed payloads require 0.15+; downgrade reading is not supported. Schema remains 5; backups precede updates.
9. Review/export keeps explicit local approval, immutable preview bytes, static filenames and archive hashes. The synthetic benchmark definition is shareable; private prompts, source, credentials, model names and connection configuration remain excluded. No automatic upload or support POST.

## Validation and release gates

New tests cover precise diagnostics, formatting calibration, native feedback, safe schema correlation, manifests/repeated metrics, deliberate benchmark mutation (including last attempt), stop/continue without replay, actual Qt measurement/review/save, malformed export fields and dense 66-row storage/reopen/ZIP.

The regression proof script restores immutable v0.14.1 Runtime/numeric-comparison behavior in a separate development process: current tests pass, old behavior fails, restored current behavior passes. It does not change the checkout or run in the app.

Run the full local suite, Ruff, dependencies, source startup/25 offline diagnostic smokes and wheel. Windows must pass actual installation/shortcut/startup, pinned released 0.14.1 upgrade/data preservation and silent restart before tagging exact passing source. Test phase increases from 8 to 12 minutes for the expanded suite and prior runner variation; overall 30-minute, package and installer bounds remain. No assertion, permission or checksum gate is removed. Verify the published installer through production Updater before declaring delivery.

## Research references and scope

- SWE-bench Verified: https://openai.com/index/introducing-swe-bench-verified/ — task quality and independently checked correctness matter more than raw test count.
- SWE-bench evaluation: https://www.swebench.com/SWE-bench/guides/evaluation/ — frozen task definitions and reproducible environments; this small local pilot is not SWE-bench certification.
- Anthropic evaluation guidance: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents — distinguish harness behavior, graders, trajectories and stochastic outcomes.
- MCP architecture: https://modelcontextprotocol.io/docs/learn/architecture — protocol integration is separate from permissions and evaluation; no MCP implementation is claimed in this update.

References are rationale, not proof of behavior or a fresh online source audit. User's ZIP, synthetic calibration and regression results determine this update. No model training, multi-agent orchestration, autonomous Ralph reset loop, vector database, unsupported reasoning control or expanded tools are bundled into this measurement release.

## User acceptance

Keep Ollama running. Click Update, install/restart and let the queued Measurement campaign finish once. Do not rerun merely to obtain green. After completion or a safe stop, Review / save diagnostic ZIP → inspect → approve local saving → Save. Drag the ZIP into support chat. Partial results remain useful; an unknown in-flight action is never replayed. No token or GitHub issue is needed.
