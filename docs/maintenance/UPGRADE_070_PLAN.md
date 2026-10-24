# 0.7 plan: task checks and trustworthy outcomes

Authorized: plan, implement, validate and publish the next update. Inputs: approved issues9–12, earlier issues1–8, user evaluations and execution logs. Preserve raw logs/source/private paths outside Git. Issue10 passes all21 checks; issue11 detects a line1 syntax error; issue12 shows all7 tools succeeding while the user goal failed because the wrong file was rewritten.

## Deliver and verify

1. Workbench shows expected output files and optional required native tools/read-back checks. Suggest a target only for a narrow unambiguous create/write/edit instruction in the current task; suggestions remain visible/editable and never come from project files/briefs/history. Runtime checks independently validate workspace paths. Configured output files restrict file writes before approval; reads remain within the usual project rules. A wrong-file write fails without touching that file.
2. Evaluate recorded writes and matching independent read-back after the latest write, current file revision, required tool successes and any required native execution. Missing checks produce needs_review. A passed check is not a verified game or arbitrary natural-language goal.
3. Handle empty model finals after successful tools as incomplete_response, preserving the saved work and emitting a deterministic application-owned evidence summary. No retry, tool replay, thinking-as-answer substitution or hidden generation.
4. Show authoritative execution/task-check facts separately from model prose. No-op writes do not rewrite files, request pointless approval or count as actual writes. Keep hash/permission/cancellation gates.
5. Make New task (fresh context) the visible default. Continue conversation and Resume are explicit. Expose effective tools/blocked command permission and context source in local evidence.
6. Retain/share typed counters for contract failures, missing finals, unchanged writes and actual validations. Public previews exclude target paths, source, prompts, agent names and notes; retention remains bounded. Mixed old history must not imply zero missing evidence.
7. Add synthetic regressions and packaged fixtures. Run Linux checks, actual Windows installation/shortcut/diagnostics and released0.6.0 upgrade/data preservation. Tag only passing source; verify the public installer through the production updater.

## Limits

No broad English goal parser or universal claim detector. Task checks certify configured operations, not program behavior. No silent newline repair, command enablement, model switching, extra cloud generation, vector index or autonomous report upload. Qwen2.5 native-tool failure is still open. Thinking/final channel root cause requires live model evidence; missing-final handling is a safe partial-work outcome, not a claimed model repair.
