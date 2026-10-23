# 0.5.0 plan: projects, retrieval and proven tool calls

## Evidence and design

The user's 0.4.0 reports [#3](https://github.com/MeetleJuice/friendly-bassoon/issues/3) and [#4](https://github.com/MeetleJuice/friendly-bassoon/issues/4) establish two separate facts: five metadata endpoints list models successfully, while the selected Qwen model produces text-form requests without native tool calls. More model lists cannot establish executable-tool compatibility. Do not label fixture success as a repaired live model.

Primary-source research informs implementation, without transplanting upstream frameworks/code:

- [Codex tool router](https://github.com/openai/codex/blob/adca78ddae79568279d0731dfdebef1df16f3cde/codex-rs/core/src/tools/router.rs): finalized advertised tools and matching execution routing; cancellation and policy live in the harness.
- [OpenCode](https://github.com/anomalyco/opencode/tree/71f3ca1860939591184ef223a968616268d8c7f5/packages): registered validated tools, application-owned permissions, project navigation separate from the conversation and review surfaces.
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python/tree/163f50ed56fa8c3fd9346148b6e56e7696794b58): distinguish available tools from approval rules; hooks/permissions surround tool execution. Claude Code's public repository provides documentation/examples, not its proprietary core implementation.
- [Aider repository maps](https://aider.chat/docs/repomap.html) and [Codex file search](https://github.com/openai/codex/tree/main/codex-rs/file-search): bounded source maps, symbols and ignore-aware search are useful before adding a vector store. Embeddings require a separate measured benefit, source freshness/deletion rules and explicit provider/cost decisions.

## Implement this release

1. **One inspectable tool registry.** Tool descriptions, schemas, permission category and execution availability stay aligned. Add read-only project-map/context retrieval tools, with unknown names rejected and every write/command still reviewed. Provide Builder/Reviewer templates and visible tool descriptions.
2. **Remembered projects and bounded local retrieval.** Keep recent project roots and a user-written brief locally; restore selection without opening or scanning arbitrary folders automatically. Add a project chooser and context preview beside files/history. Search respects sensitive paths, links, ignore patterns, cancellation, file/byte/result limits and returns cited paths/lines. Read content on demand; do not persist a full source-content index. This is lexical retrieval, not vector similarity or trained memory.
3. **Explicit tool-call certification.** A selected-model probe requests one tiny harmless native function call with a fixed challenge and validates its structured arguments. It cannot read/write project files or run host commands. Cloud generation requires explicit local approval and a small output cap; metadata refresh remains generation-free. Store dated scoped results, distinguish listed/declared/probe-verified/workflow-verified, and expose safe protocol comparisons where supported. Never execute JSON printed in prose or silently change transports/models.
4. **Close reporting gaps.** Record actual HTTP status, API-check environment, typed counters and bounded failure classifications from recent sessions without raw errors/prompts. Keep public reports allowlisted and model names optional. Hide direct-token controls in browser mode and preserve meaningful failure evidence in short browser drafts.
5. **Measured delivery.** Synthetic regressions, retrieval quality/secret-boundary cases, registry conformance and no-action probe tests; installed offline diagnostic checks and an actual 0.4.0 upgrade preserving old records/catalogs. Update this maintenance workspace and release a verified 0.5.0 installer only after checks pass.

## Deferred deliberately

Vector embeddings, arbitrary MCP/plugin execution, autonomous agent teams, unattended source changes, broad OS sandbox claims, full checkpoint/rollback and GitHub OAuth are separate projects. A registry is not a permission bypass; a model list is not a capability benchmark; a one-call probe is not full coding acceptance. Do not copy proprietary Claude Code internals or claim access to this assistant's private implementation.

## Acceptance and next user run

- Existing 0.4.0 agents/profiles/sessions/diagnostic sharing states/catalogs survive upgrade.
- Metadata Test APIs still uses at most one GET per unique connection, with no generation.
- Probe accepts only a matching native function call; text/malformed/denied cases produce distinct retained failures with no project actions.
- Project retrieval has source citations, excludes secret/ignored/linked paths, stays bounded and refreshes from current files. Context preview itself makes no model call.
- Same model's live acceptance remains user-side; never claim the Qwen issue fixed without a matching successful native-call/workflow report.
- After installation, the user selects a project, previews context, and runs one selected-model probe. A cloud probe is optional and explicitly consented. Share the resulting reviewed report and issue URL.
