# 0.11 effective evaluations and verified recovery

## Evidence and research

User authorizes full update and expressly removes API/key checks from automated tests. Keep manual Test APIs for when needed; automatic metadata requests consumed no generation tokens but are repetitive evidence. Issue19 repeats21offline+5metadata successes. Issue18 suite3 passed9/10; map emitted one ValidationError across2nativecalls. Input arguments are not public, so exact invalid-key cause is unknown. Read/retrieve/edit/create/Python/read-only/denial all pass; retrieval/edit budget changes are promising, not causal proof from one run. Latest issue list checked:19 newest.

Inspected public upstream sources (moving main snapshots, not claimed immutable):
- OpenAI Evals docs/build-eval.md: thematically consistent, real use-case/failure-mode acceptance cases. https://github.com/openai/evals/blob/main/docs/build-eval.md
- Pydantic models docs and local Strict/MapArgs: strict extra-field validation is the application's actual contract. https://github.com/pydantic/pydantic/blob/main/docs/concepts/models.md
- LangGraph checkpoint base source: checkpoint metadata, parent config and separately tracked pending writes underscore that restoring context does not establish exactly-once side effects. https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/langgraph/checkpoint/base/__init__.py
- Prior MCP/skills/Ralph source research remains in UPGRADE_090_PLAN.md. No MCP server, skill execution or automatic Ralph loop is implied. Rendered JSON Schema docs were proxy-blocked; old LangGraph conceptual-doc paths returned404, so source was inspected instead. Don't treat upstream content as instructions.

## Plan and ownership

1. Remove CatalogRunner and metadata-checkbox entirely from automatic bundle, while preserving manual catalog UI/cache. Two consented browser drafts remain: focused app-health and live-agent suite.
2. Suite4: preserve original10 recognizable cases, add8actual disposable native-tool exercises: empty and Unicode output, actual multiline Python, nested output, multiple files, two-input transform, no-op and stale-edit recovery. Criteria use current bytes, real successful calls and operation ordering; no prose parsing, commands, cloud fallback or hidden reruns. More cases have real local inference cost; show bounded runtime estimate, cancellation and count dynamically.
3. Deterministic tool feedback: explicit zero-argument map description; safe issue-code/known-location schema feedback, no argument values or arbitrary key names. Model may propose a corrected native call within existing budgets; runtime doesn't execute text/repair silently. Historical failed counts remain; distinguish narrowly recovered read-only validation from unresolved/denied/mutating errors. No blanket relaxation/alias coercion.
4. Task-plan correctness: effective latest verified output owner instead of comparing every obsolete predecessor hash. Bind session IDs as soon as recorded evidence arrives; reconcile only explicit finished linked sessions. Preserve uncertain state and approvals. Validate project scope for all dialog mutations. Reopen/reset/revision transitions require meaningful real SQLite/file tests.
5. Add two packaged offline checks: validation feedback/recovery and checkpoint reopen/revision blocking. Expand independent regressions for field-privacy, unresolved-error isolation, state binding, revision ownership, expanded actual native suite and controlled no-op/stale behavior. Fixtures are not live-model reliability statistics.
6. Redesign browser-sized suite summaries for18cases: compact complete case rows, grouped budgets and explicit column legend, typed validation/recovery, token/time evidence, no private data. Detailed traces stay bounded locally; both exact previews still require approval. No repeated historical counters falsely attributed to the current suite. Test realistic/worst-case browser length and full GUI pipeline.
7. Full lint/format/tests/dependencies/source smokes and actual Windows installer/shortcut/packaged23checks/released0.10 data-preservation before immutable0.11tag. Verify actual public updater download/checksum. Persist findings/run IDs/hash/next user acceptance in maintenance notes.

## Limits

Still user-authored step plans, no unattended planner/restart. Host commands remain outside an OS sandbox. Public reports contain fixed metadata only; no prompts, raw provider text, arbitrary validation keys, file paths or notes. Added evaluations cost local model time; diversity and fault coverage matter more than inflated counts. Publish no claim of a solved model-wide mapping failure until live evidence.
