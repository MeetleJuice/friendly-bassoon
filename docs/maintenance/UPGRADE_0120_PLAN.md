# 0.12 individual-agent evaluation campaign

Status: implementation plan; final counts, measured checks and delivery evidence belong in ENGINEERING_LOG.md and VERIFICATION.md. Research reviewed 2026-10-24. This document contains sanitized conclusions, not user transcripts or raw diagnostics.

## Evidence driving the release

- [Issue 20](https://github.com/MeetleJuice/friendly-bassoon/issues/20): app0.11/suite4, 13 of18 local-model tasks passed. Edit and stale recovery produced matching bytes but failed required operations; three tasks (Unicode, transform and no-op) exhausted output before any native call. The specific omitted operations are not recoverable from the compact public report. Do not guess the exact arguments or blame a model from incomplete evidence.
- [Issue 21](https://github.com/MeetleJuice/friendly-bassoon/issues/21): all23 offline checks passed. These fixtures validate application mechanics, not live model reliability. Automatic catalog generation requests remained zero.
- Compared with prior10 cases, this run again passed9/10 with a different failed case. New8 cases passed4/8. Do not interpret13/18 as a directly comparable regression from9/10.
- Runtime task checks already record missing_writes, missing_readbacks, missing_tools and revision_mismatches. Expose those facts and ordered-operation requirements rather than weakening verification to improve scores.

## Research and interpretation

Read accessible official project sources; commercial documentation sites can be unavailable in the cloud environment. Sources are references, not installed frameworks or delegated instructions.

1. [OpenAI orchestration](https://github.com/openai/openai-agents-python/blob/main/docs/multi_agent.md): distinguishes code-controlled workflow, manager calling specialists, and handoffs. Use deterministic campaign scheduling now. Future George delegation should have bounded assignments, a retained owner and checkable outputs; do not add group-chat orchestration this release.
2. [OpenAI agent configuration](https://github.com/openai/openai-agents-python/blob/main/docs/agents.md): instructions, tool permissions, model settings and output contracts are distinct configuration surfaces. Implement versioned roles rather than personality-only prompts.
3. [Anthropic skill creation/evaluation](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md): compares a candidate against a baseline, inspects time/token tradeoffs and variance, then expands cases. Borrow the measurement method; do not execute its workflow or claim a skills engine integration. Keep shared tasks, specialist tasks, repetitions and configuration changes identifiable.
4. [Inspect](https://github.com/UKGovernmentBEIS/inspect_ai): separates multi-turn/tool-capable evaluation from scoring and review. Preserve per-requirement evidence and reject false positive graders. Model-based judging is optional advice, not the authority for exact artifacts or permissions.
5. [SWE-bench](https://github.com/SWE-bench/SWE-bench): reproducible initial repositories, concrete issues and executable grading. Borrow tiny self-contained projects and independent acceptance checks. Our local suite is not SWE-bench certification and must not impose its large Docker/storage requirements on the user.
6. [LangGraph](https://github.com/langchain-ai/langgraph): durable state and human intervention patterns inform the application-owned campaign ledger. Durable recovery does not mean blindly replaying an interrupted side effect.

## Roster and contracts

All six initial managed configurations share the explicitly selected local Ollama ModelRef. Existing agents and user edits survive installation. Test snapshots are frozen independently from editable daily-use definitions; scope hashes distinguish versions/settings.

| Role | Responsibility | Observable output |
| --- | --- | --- |
| George | Generalist and comparison baseline | Verified result and unfinished requirements |
| Scout | Read-only investigation | Relevant source references, evidence and uncertainty |
| Ada | Focused implementation | Intended changes, preserved unrelated files, readback |
| Vera | Test engineering | Tests that discriminate broken and correct behavior |
| Sentinel | Read-only review | Evidence-backed findings and justified clean reviews |
| Atlas | Project continuity | Sourced verified state, unresolved work and stale claims |

No self-delegation, multi-editor concurrency, MCP connection, autonomous Ralph restart, embedded executable skill or vector index is introduced by naming these roles. Same-model specialists can share systematic mistakes. Independent deterministic acceptance remains essential.

## Implementation sequence and acceptance

1. Preserve18-case baseline exercises and limits for identifiable comparison. Add fixed requirement booleans/counts, not arbitrary source paths, to public summaries. Correct actual false negatives if evidenced; retain denied-write and wrong-target failures.
2. Provision the managed roster without overwriting existing user definitions or silently switching models. Explain the role permissions and same-model selection in the UI.
3. Add versioned individual-role scenarios and fresh disposable workspaces. Include realistic inspection, focused edits, exact targets, meaningful test assertions, planted defects/clean examples and sourced handoffs. Required source operations and output contracts must be independently checked.
4. Include selected explicit repetitions with attempt numbers. Keep original failures. No hidden retry-until-green and no aggregate score hiding skipped/untested denominators. Time/token-cap experiments must be labeled separately from unchanged baseline cases.
5. Add a bounded campaign ledger. Persist each completed case and mark in-flight work uncertain after restart. Continue only safe fresh-workspace cases; do not replay a previous project's writes. Cancellation stops queued work and preserves completed evidence.
6. One target-version update queue starts the new campaign after the installer restarts the app and local model setup is usable. Prevent startup re-entry, concurrent campaigns and endless automatic reruns. Missing local setup should show a useful status, not invoke cloud fallback.
7. Show current case, agent, progress, limits, elapsed time and requirement explanations. Successful file bytes and completed tool workflow are separate facts. No-op existing bytes alone cannot pass; stale recovery must include its required order and final verification.
8. Produce exactly two reviewed sharing drafts: app health and bounded campaign evidence. Keep full bounded details local, never secrets/raw source. Browser draft opening remains distinct from submitted GitHub Issues. Manual API metadata testing remains available; automatic key/catalog checks remain absent.
9. Validate fixtures, actual native-runtime scripted cases, malicious/wrong evaluator inputs, persistence/restart/cancel, and complete GUI campaign-to-preview behavior. Publish only after Windows source validation, actual installer/shortcut/startup/offline diagnostics and previous-release data preservation pass.

## Meaningful data and interpretation

Record campaign/test/role/configuration versions; case and attempt IDs; precise requirement results; runtime state; native tool counts; write/readback/recovery counts; original typed errors; elapsed time; known provider usage and rejected-response usage. Unknown usage is unknown, not zero. Trace hashes and source revisions support local diagnosis without public source text.

First-attempt success, repeated-case consistency, specialist-vs-George comparisons and configuration experiments answer different questions. Report separately. Fresh disposable sessions reduce history contamination but do not create statistically independent models. A few repetitions are exploratory evidence, not a universal reliability guarantee.

Default local retention and storage bounds continue to apply. Maximum useful information does not justify unlimited raw messages or private project copies. Documentation should preserve learned causes, decisions, synthetic regression cases and next hypotheses. Raw user logs remain outside Git.

## Release verification details

For0.12, update application/package/installer metadata and release notes together. Advance scripts/smoke_windows.ps1 to the immutable0.11 installer:42330746bytes, SHA256 `48783cd34a0d4277d22f798f797a492031837fbacad603ac48ab1c554934cc84`. Preserve schema5 definitions/settings/history/messages/reports/catalogs/projects/assessments/task plans, then additionally verify roster/campaign settings. Keep package-health counts consistent with the actual runner. Never change a published tag or checksum.

## Deferred or unproven

Live local-model improvements require the user's actual run after release. Fixtures do not certify GPU behavior, cloud providers, broad program correctness, security isolation or installed dependency behavior. Host command approval is not an OS sandbox. Provider-specific reasoning controls need explicit compatibility evidence; do not silently toggle unsupported options or replace native calls with parsed prose. The original Midnight Crew artwork is a design reference, not evidence of implemented UI or available binary assets.
