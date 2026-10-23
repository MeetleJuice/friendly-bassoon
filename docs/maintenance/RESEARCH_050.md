# Source-based design decisions for 0.5.0

This review inspected public source and documentation, not private implementations of Claude Code or this assistant. No upstream framework or proprietary source was copied into Aigentics.

| Reference | What was inspected | Adopted here | Not claimed |
| --- | --- | --- | --- |
| OpenCode | [local provider](https://github.com/anomalyco/opencode/blob/0471a39a0f24ba8ef89954176513b839b4b56971/packages/core/src/plugin/provider/local.ts), [streaming adapter](https://github.com/anomalyco/opencode/blob/0471a39a0f24ba8ef89954176513b839b4b56971/packages/ai/src/protocols/openai-chat.ts), tool/runtime and project/session UI source | Registry/schema/runtime alignment, project navigation beside a session, explicit compatible streaming support | That its adapter succeeds with this user's Qwen models |
| Codex | [final tool router](https://github.com/openai/codex/blob/adca78ddae79568279d0731dfdebef1df16f3cde/codex-rs/core/src/tools/router.rs), registry, bounded file search | One advertised/executable tool set, outside-model policy, bounded retrieval/cancellation | Access to the private deployment or hidden internals of this assistant |
| Claude Agent SDK | [types and permission/hook contract](https://github.com/anthropics/claude-agent-sdk-python/blob/163f50ed56fa8c3fd9346148b6e56e7696794b58/src/claude_agent_sdk/types.py), public Claude Code examples/docs | Separate tool availability from permission to act; reviews remain harness-owned | Inspection of proprietary Claude Code core |
| Aider | [repomap.py](https://github.com/Aider-AI/aider/blob/main/aider/repomap.py), retrieved October 23 (moving main), repository-map docs | Source symbols, ranked context and explicit budgets before adding embeddings | A full reference-graph implementation or Aider code transplant |
| Ollama v0.40.8 | [server/routes.go](https://github.com/ollama/ollama/blob/f580b5484a58c8370c35d669555bf887783a3f68/server/routes.go), [model configuration](https://github.com/ollama/ollama/blob/f580b5484a58c8370c35d669555bf887783a3f68/server/images.go), API types and middleware | Retain parser/renderer/template_source; preserve native call IDs; compare structured stream/nonstream routes with matched parameters | That changing route/streaming fixes the observed failure |

## The key protocol finding

Ollama v0.40.8's `/api/chat` and `/v1/chat/completions` share ChatHandler; nonstreaming aggregates the same parsed chunks. Native nonstreaming tools are supported. Merely switching routes is not a proven fix. OpenCode uses the compatible streaming route, which is a useful comparison with the user's failure, not an established cause.

`/api/show` supplies `parser`, `renderer`, and `template_source` without another HTTP request. Its returned Go `template` can differ from the active GGUF/Jinja path. Therefore the old template hash/tool-marker field alone could not identify the active parser. New metadata remains bounded and excludes actual template content.

Native tool IDs and tool-result IDs are supported by this server; preserving them improves subsequent-turn compatibility, but cannot explain a failure on the first response. Native/compatible probes explicitly use temperature 0.2 and request 96 output tokens so comparisons do not accidentally change temperature (compatible server default can be 1.0). No `tool_choice:required` repair is claimed; the inspected server request type does not establish support for that option.

## Retrieval and vector RAG

This release implements lexical retrieval: bounded current files, filename/text ranking, Python AST/source-symbol maps, cited line ranges and SHA-256 freshness checks. It respects per-directory gitignore/app-ignore rules, sensitive paths and links. There is no embedding request, vector database or persistent source-body index. `pathspec==0.12.1` supplies gitwildmatch; global Git settings/index state are not read. Complex or over-budget ignore patterns fail closed and report truncation.

A vector phase needs a small labeled query→source benchmark showing where lexical retrieval fails. Then evaluate local embeddings against the same questions, with measured recall, latency, memory, index freshness and deletion tests. Remote embeddings additionally need explicit content/cost approval. Do not add an embedding store simply to accumulate data.

## Harness and retention

A frozen tool manifest defines names/descriptions/permission categories; parameter schemas and execution bindings are checked for alignment. Read-only context tools can inform an agent, while writes and commands retain normal reviewed approval. There is no arbitrary plugin/MCP code execution.

Project definitions and short user briefs persist locally; source snippets are read on demand. Explicitly adding excerpts to a task rechecks ignore rules and full-file hashes; it can then enter the existing opt-in transcript lifecycle. Probe reports retain bounded structural outcomes, not raw model text or synthetic challenges. Listed, declared, probe-verified and full-workflow-verified remain different evidence levels.

## Next user acceptance

Open the installed Test model dialog, select the same saved Qwen agent and optionally compare the four local routes. This runs at most four small local requests and no project actions. Share its approved report. A remote/cloud model probe is a separate explicit one-request approval. Apply a tested local route only after a real probe passes, then run the full disposable Diagnose workflow. Until then the Qwen bug remains open.

Additional UI source checked at the pinned OpenCode commit: [project selector](https://github.com/anomalyco/opencode/blob/0471a39a0f24ba8ef89954176513b839b4b56971/packages/app/src/new-session/project/selector.tsx), [session region](https://github.com/anomalyco/opencode/blob/0471a39a0f24ba8ef89954176513b839b4b56971/packages/app/src/session/composer/region.tsx) and [session navigation](https://github.com/anomalyco/opencode/blob/0471a39a0f24ba8ef89954176513b839b4b56971/packages/app/src/home/sessions/view.tsx). Aigentics keeps its native PySide6 presentation while separating project definitions/context from the task and review surface.
