# 0.13 — bounded completion and evidence-backed inspection

Issues22/23:24offline checks pass;22/42live attempts pass over31minutes. Correct writes frequently lack readbacks; Sentinel twice uses0nativecalls; five attempts hit OUTPUT_LIMIT beforetools. Atlas3/3 is exploratory, not reliability certification.

Implement an explicit TaskChecks completion-feedback option: one correction turn on unmet checks, only within existing step/time/context budgets, no unresolved denied/failed calls, no permission changes, no prose execution and no hidden provider retries. Add application-owned required source reads to specialist cases. Preserve first incomplete-check counters and final outcomes separately. Campaign version2 retains42attempts/24offline checks and original output budgets for a controlled harness comparison. Existing ordinary TaskChecks default to feedback disabled; the controlled campaign explicitly enables it. No model reasoning switch or blanket cap increase is introduced without compatibility evidence.

Reference: OpenAI Agents SDK orchestration guide recommends bounded feedback/evaluation; Pydantic validation remains strict. Microsoft PowerShell process-tree waiting lesson and exact Windows release gates remain in engineering notes. New tests must exercise actual native writes/readbacks, denied actions, no-op model replies, wrong sources, equivalent Unicode paths, budget exhaustion and privacy. Release0.13 requires full Linux checks, actual Windows installation/upgrade from pinned0.12, silent restart, and public updater verification.

The seven new inline artwork references are documented in design/MIDNIGHT_CREW.md; original binaries are unavailable and remain an explicit incomplete asset task.
