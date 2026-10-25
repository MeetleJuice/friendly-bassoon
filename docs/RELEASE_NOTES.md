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
