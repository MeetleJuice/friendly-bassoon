# 0.7 focused research and acceptance evidence

Follow-up to RESEARCH_050.md and RESEARCH_060.md. Public sources were re-read during this update; proprietary product internals were not available. No upstream code was copied or broad framework imported.

| Primary source | Finding | Applied decision |
| --- | --- | --- |
| [Ollama v0.40.8 API Message](https://github.com/ollama/ollama/blob/f580b5484a58c8370c35d669555bf887783a3f68/api/types.go), [thinking documentation](https://github.com/ollama/ollama/blob/f580b5484a58c8370c35d669555bf887783a3f68/docs/capabilities/thinking.mdx) | Thinking, visible content and native tool calls are distinct fields. Thinking controls are model-specific; a reasoning trace is not a final answer. | Keep thinking content out of persistent/public evidence; record bounded structure/counts. A missing visible final becomes incomplete_response with an application-owned summary; no fabricated final or unapproved retry. |
| [Codex apply-patch handler](https://github.com/openai/codex/blob/4610b573e59b211bf9430cf6ffb97cfb84623090/codex-rs/core/src/tools/handlers/apply_patch.rs) | Verified edit actions pass through application-owned policy, permission and execution routes. | Check configured file-tool write targets in ToolRunner before review/execution, independently from model text and existing workspace protections. This is not an OS sandbox; separately approved commands retain broader access. |
| [OpenAI Evals build guide](https://github.com/openai/evals/blob/5e8663a3f2a1fba84e94c81df3d08c97a78a5b2a/docs/build-eval.md) | An evaluation needs explicit examples/reference criteria and a chosen evaluation procedure. | Add deterministic, explicit per-task operation checks and synthetic regressions instead of treating a model's VERIFIED label as a score. We do not import an evaluator model or claim arbitrary English goals are solved. |
| [Claude Agent SDK tool hooks](https://github.com/anthropics/claude-agent-sdk-python/blob/aada02405ede575d7cbf8e6851a8179762560816/src/claude_agent_sdk/types.py) | Pre/post-tool/failure contracts carry tool-use IDs, responses and permission context. | Preserve correlated execution facts, selected-versus-effective permission context and distinct missing-final/task-check outcomes. No inference about private Claude Code implementation. |
| Aider compile checks and OpenCode mutation/permission services, pinned sources in RESEARCH_060.md | Compilation, write success, code behavior and permissions are separate concerns. | Preserve 0.6 static checking/hash/approval gates. Skip genuine no-op writes without mutating files or counting them as actual writes. Never silently turn literal backslash-n into newlines. |

## Sanitized live findings

- Issue9 repeats the old0.5 Qwen2.5-Coder14b text-tool failure; no universal repair is established.
- Issue10:0.6 passes19 offline checks, update connectivity and the selected live local file task. Native calls2; exact bytes/read-back true; no retries. Public model name omitted.
- Issue11:0.6 static checker reports a Python syntax error at line1. Public filename intentionally omitted.
- Issue12:0.6 selected run completes7/7 tools, one verified/static-checked write, while the user's assessment says Needs work. The separately supplied log establishes the requested new filename was not created and an existing file was redundantly rewritten.
- Supplied evaluations/logs: Qwen3:8b can omit required calls and make unsupported inspection claims. Qwen3.5:9b executes11/11 tools and saves2 files, but three final replies have empty visible content and nonzero thinking counts; no exact server/parser cause is established. A denial test approved its write and therefore did not test denial. Some read-back Python source contains literal backslash-n characters, confirmed by matching hashes and non-executing compilation, not merely JSON display escaping.
- Increasing conversation history is visible despite prompt wording saying new execution. Causation for tool omission is unproven. Fresh versus continued context must be a real application setting.

## Scope of the new checks

Visible output paths and optional successful-tool/read-back requirements are configured before Run. Only a narrow single-filename leading operation gets a convenience suggestion, derived from current task text only; users can override it. No LLM or general goal parser is used. Exact target writes, read-back after the latest write, and current revision equality are assessed. Missing requirements cannot pass based on prose. These checks do not establish correct dependency installation, safe arbitrary commands, gameplay or universal task completion. Original logs/PDFs/source/private paths are not copied into Git.

Run reports use run-review-2; health suite5 adds target/revision and missing-final fixtures. Existing schema5, retention, support approval, native protocol, installer channel and source/update separation remain. Mixed-history coverage counters describe which sessions actually recorded the new evidence. Raw task text/target paths/assessment notes stay out of public previews.
