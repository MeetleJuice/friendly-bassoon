# 0.11.0 • deeper evaluations and verified recovery

- Suite4 expands10to18live native-agent cases: empty/Unicode/multiline/nested outputs, multiple files, ordered two-input transformation, proven no-op and stale-hash recovery. Criteria correlate actual ordered operations and exact current bytes; invented prose cannot pass. Dynamic progress23offline+18live, cancellation and bounded Balanced/Legacy modes remain. More live cases use local-model time (up to45minutes at allowed bounds).
- Removed real API model-list checks from automatic suite and its checkbox. Test APIs remains a separate manual action. Automatic health reports focus on current checks rather than copying legacy session-history counters; manual Diagnose/History remain.
- Validation feedback supplies fixed issue codes and known schema fields, without arbitrary invalid keys/values. project_map explicitly takes {}. A matching corrected read-only call may operationally recover a schema failure; original failed counters remain. Denials, changed targets and mutating operations are not silently forgiven. No prose-to-tool execution or hidden retry.
- Plan checkpoints now use latest verified file ownership, allowing a later declared step to edit an earlier output while preserving earlier hashes. Early explicit session binding and manual reconciliation expose interrupted evidence without replay. All dialog actions guard changed projects/stale records; acceptance rechecks the confirmed revision.
- Health suite6adds actual offline validation-recovery and SQLite-reopen/checkpoint regressions (23total). Expanded tests cover fault handling, correlated ordered acceptance, full GUI plan execution, stale Qt worker signals and browser-sized18case evidence.
- Compact reports keep every case, timing, available usage, budgets, typed validation and recovered/remaining failures, while full bounded traces stay local. Both previews still require approval and GitHub Create clicks; no public upload or model-training claim.

# 0.10.0 • coordinated test budgets and explicit task checkpoints

- Suite3 offers Balanced vs Legacy budget modes. Each Go is one deliberate run. Balanced allows larger retrieval/edit outputs and coordinated request/session deadlines, respecting stricter saved-agent limits. No hidden retry or cloud generation. Compare within matching mode; changes are experiments, not proof of model repair.
- Failure rows show output-limit/request-timeout/session-time distinctions, expected versus observed facts and actual budget settings. Ollama length-limit failures retain only bounded numeric usage, never rejected content/thinking.
- Workbench → Task plan: author up to16small steps, launch one with fresh context and normal approvals, inspect results and explicitly verify output-hash checkpoints. Later steps revalidate preceding checkpoints. Interrupted/failed-dispatch attempts stay uncertain and require explicit review/reset before another run. No automatic Ralph restart or tool replay.
- Plans stay in local project-scoped settings (up to32projects); a full store refuses additional plans rather than evicting uncertain state. Reset invalidates later checkpoints; removing plan steps does not remove project files. Existing schema5/backup mechanism remains.
- Expanded budget, privacy, durable-state and native GUI regressions; actual Windows upgrade additionally checks preserved uncertain-plan settings.

# 0.9.0 • measured harness budgets and deterministic backpressure

- Context limits now include serialized tool schemas; no silent history truncation. Character estimates remain distinct from token counts.
- Agent suite2 advertises only permitted tools relevant to each exercise. Edit/Python output limits are2048tokens; simpler cases remain1024. No automatic replay, commands or cloud fallback.
- Three identical failed tool requests stop execution with NO_PROGRESS and a reviewable outcome. Changed arguments can still recover.
- Shared compact suite reports preserve allowlisted tool error types and the output budget, with full bounded protocol evidence retained locally.
- Expanded offline policy matrices and real-runtime regressions cover permissions, Unicode/envelope limits, context rejection, circuit breaking and public-report fidelity.
- MCP/skills/external script execution and unattended restart loops remain future integrations, not enabled by this release.

# 0.8.0 • guided update and test suite

- Test suite runs ten preloaded native-agent exercises in fresh disposable folders, with app diagnostics, progress, cancellation, retained reports and completion sound.
- Update queues one post-install test run; existing installer verification, backup and installation approval remain. First upgrade from0.7: open Test suite once after installing0.8.
- Two exact allowlisted previews share one approval control, then open two GitHub drafts. Click Create on both pages; no token is required.
- Local-only configuration-scoped comparison, timings/available usage/protocol/task evidence. Existing retention controls apply. No commands or cloud generation in automatic suites.
- Optional remembered API model-list refresh joins the health report: one metadata request per connection, no generation tokens.
- Rounded controls, visible keyboard focus and native hover help. Disabled agent capabilities are skipped instead of being granted.

## Aigentics Desktop 0.7.0 — task checks and trustworthy outcomes

- **Expected output files** is visible below the task. A narrow single-file instruction can suggest a target; review/edit it before Run. Configured targets restrict file-tool writes before approval, so an attempt to rewrite a different file is blocked. Empty means no extra target restriction. Separately approved host commands are not sandboxed by this list.
- **Require real tools**, **Required tools**, and **Read back output files** check actual successful operations. Target writes must be followed by matching read-back when required, and the current file revision must still match. Missing checks leave the run needing review. Passed operation checks do not certify program behavior or arbitrary English goals.
- **Fresh context is the default.** Choose Continue conversation or Resume explicitly when desired. Local evidence shows fresh/continued history and command permission; saved agents are preserved.
- **Missing final answers preserve work.** If the model returns no visible final answer, the app shows incomplete_response and its own recorded-operation summary. No tool is replayed, no extra generation request is made, and thinking is not substituted for an answer.
- **Runtime evidence is separate from model prose.** Actual calls/writes, unchanged writes skipped, task checks and final-answer status are shown independently. Identical writes are not re-saved, approved pointlessly or counted as real writes.
- **Better reports** carry fixed task-check/missing-final/no-op counters, successful HTTP status and mixed-history evidence coverage. Target paths, source, tasks and notes remain excluded from public previews. Existing retention limits still apply; sharing requires review/approval.
- **21 packaged offline checks** plus Linux regressions and actual Windows installation/0.6.0 upgrade preservation are required before publication.

Qwen2.5 native-tool compatibility and the exact Qwen3.5 missing-final cause remain open. Python static checks do not verify dependencies or gameplay. The installer remains unsigned.

After updating: keep a saved working local agent, open a disposable project and enter a simple create-file task. Check the visible output filename, keep fresh context/read-back enabled, and run once. Review the actual diff, runtime task checks and result. Mark Goal met/Needs work and Share run report after inspection.
