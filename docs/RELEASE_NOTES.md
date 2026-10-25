# 0.17.0 — verify completion and measure thinking controls

- Fixes a harness false pass for unchanged files: the requested read → one identical write request → final read must be proven. Missing evidence can use the existing single bounded correction; strict graders and approvals remain.
- Clarifies test artifact/final JSON structure before execution, including Vera's required object wrapper. Provides schema without expected answer values. Existing results are not regraded.
- Connections adds model-default/off/on thinking for native Ollama. Explicit settings require advertised support; default preserves behavior. Your saved models/agents, automatic context and server configuration remain.
- Default Measurement records 27 token-free app checks plus 34 trial slots: all six local roles, repeated output/time arms, and four conditional matched thinking-off trials. Unsupported, unknown or already-off models skip the new controls without a generation probe. No API-key generation checks.
- Reviewed diagnostic ZIP includes requested control, safe advertised metadata, native load/prompt/evaluation counters, unchanged-file proof counts and one end-of-campaign context/server observation. Matched outcomes/latency and comparison guards distinguish evidence from assumptions. Existing bounded retention/privacy and local-only saving remain.
- Fixes a floating-point deadline edge: resuming an already-exhausted campaign cannot dispatch extra attempts.
- Shutdown cancels active work, refuses a new task and suppresses late error popups/result updates while closing. Windows GUI integration retains worker output and joins tasks safely on test failure.
- Keeps the 0.16 interface. This is a new benchmark version; differences from older scores do not establish a controlled performance improvement. No model training, model switch, MCP or orchestration is claimed.

Keep Ollama running. Update → install/restart → let Measurement finish once → Review / save diagnostic ZIP → inspect and approve local saving → Save → drag the ZIP into support chat. Expect 61 outcomes, with up to four legitimate control skips. No token, GitHub issue or automatic upload is needed. Actual model improvement awaits your local run.

Windows install/shortcut, packaged offline diagnostics, released0.16 upgrade/data-preservation/restart and production public-updater verification gate delivery. Old reports remain exportable; incompatible partial benchmark campaigns start a new matching version rather than silently mixing conditions.

# 0.16.0 — a calmer Midnight Crew desktop

- New sidebar navigation, clearer page headings, consistent dark theme, original role emblems, improved spacing and keyboard/hover focus states.
- Workbench puts the conversation first. Files/history panels can be hidden and their visibility remembered; opening a file reveals its actual preview. Expected output scope stays visible; advanced checks, context and session capture are under Task options.
- Ctrl K navigation command search; Ctrl1/2/3 pages, Ctrl B files, Ctrl Shift I history. Ctrl Enter runs only from the focused task composer. New task protects an active run's context/evidence.
- Agent forms scroll while Save remains accessible. Saved instructions, selected models and permissions are preserved. Projects has an actionable empty state.
- Test center separates first-try passes, corrections, failures and incomplete attempts. Readable case labels, active-case progress and expandable records make the run easier to follow. Reviewed local ZIP export is prominent; public GitHub drafts remain optional and approval-gated.
- Model/harness/benchmark/storage behavior remains unchanged from0.15. Existing test results stay usable and matching partial campaigns can continue. No new background model/API calls.

Keep Ollama running. Save the current test ZIP before updating when convenient, then Update/install/restart. Use Test center for queued test progress and Review / save diagnostic ZIP when finished. Nothing is shared automatically.

Research and actual native screenshots are documented in docs/design/UI_RESEARCH_0160.md. Developer tests, actual Windows installation/0.15upgrade/data-preservation/restart and public updater checks gate delivery. This release improves presentation; it does not claim improved model performance.

# 0.15.0 — precise failure evidence and repeated local measurement

- Default tests now run 30 repeated local trials across all six agents and output/time comparisons, plus 25 offline app checks. Optional Discovery keeps the broader 66-case suite. API checks remain excluded.
- Failed contracts identify safe JSON schema paths/types, missing outputs, exact formatting and citation-spelling mismatches. Initial and final outcomes stay separate; strict grading remains.
- Per-call schema fingerprints and safe argument-type evidence make native tool failures diagnosable without exporting values or raw argument names.
- A versioned synthetic benchmark manifest records tasks, prompts, role instructions, tool schemas, runtime/grader policy and budgets. Changed definitions invalidate comparison; interruptions remain unknown. Repeated coverage/outcome flips and matching-configuration regressions are explicit.
- Dense campaign reports use bounded lossless compression when needed. Reopen and reviewed ZIP export preserve evidence; private content remains excluded. No automatic upload or new permissions.
- Fixes numeric grading of large valid JSON integers without conflating booleans and numbers.

Keep Ollama running, Update/install/restart and let Measurement finish once (55 results when complete). Review / save diagnostic ZIP → inspect → approve local saving → Save → drag ZIP into support chat. Partial results are useful. No GitHub token is needed.

Real model improvement awaits this next local run. This update adds no model training, orchestration, MCP or unsupported reasoning toggle. Reading newly compressed reports requires 0.15+; downgrades are unsupported. Windows installation/0.14.1 upgrade/restart and public updater validation gate publication.

# 0.14.1 — preserve long campaign reports

- Fixes “Diagnostic report exceeds the storage limit” for long66attempt campaigns using compact lossless JSON and a separate bounded1MBcampaign allowance. Other reports retain250KBcaps; global retention limits remain.
- Preserves all recorded trace/correctness evidence rather than dropping older results.
- After updating, automatically continues a matching interrupted campaign. Previously committed attempts remain; an unknown in-flight attempt is marked interrupted and never silently replayed.
- Adds Review / save diagnostic ZIP in Campaign and Diagnose. Partial results can be reviewed and saved without completing tests or approving GitHub sharing. Drag the saved ZIP into support chat; nothing uploads automatically. Static filenames, hashes and bounded sanitized numeric traces retain useful evidence without private content.
- No changes to campaign cases, model budgets, agent permissions or public sharing approval. Existing0.14campaign scope remains compatible.

Windows install/upgrade from0.14/data-preservation/silent-restart and public updater verification gate delivery. The last unsaved attempt from a failed process cannot be reconstructed.
