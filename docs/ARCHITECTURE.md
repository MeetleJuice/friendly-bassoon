# Architecture and decisions

## Implemented layout

- `models.py`: Pydantic schema-versioned agent, model reference, provider, tool-call and response definitions.
- `credentials.py`: explicit .env loading, OS vault references, recursive redaction; values never become agent fields.
- `providers.py`: native Ollama and OpenAI-compatible HTTP adapters, model discovery, capability checks, bounded responses and normalized native tool calls.
- `tools.py`: tool schemas, workspace file access, hash-checked edits, reviewed writes, host subprocess execution, time/output limits and cancellation.
- `runtime.py`: one bounded loop shared by Laboratory and Workbench; context budgets, routing/fallback, permissions, evidence and terminal states.
- `store.py`: SQLite migrations, definition revisions, event timeline, opt-in transcripts, user assessments, retention and exports.
- `ui.py`: PySide6 widgets and background workers. The UI approves individual operations; it does not execute model-generated prose.

The Qt main thread owns widgets. A worker runs the runtime; model HTTP work uses a daemon thread so cancellation/deadlines can stop the agent promptly. That thread has no tool-execution authority. An already-sent inference request can continue at the server, incur cost, and run locally until its configured HTTP timeout after cancellation. Only one foreground operation is allowed. Automatic token streaming is deferred; output appears when complete responses and tools finish.

## Engineering references examined

Reviewed these upstream references during implementation; no upstream code was copied:

- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md): native `tool_calls`, `tool_name` results, usage counters and model discovery. Tool-capable models are required. `/api/show` capability reporting is used when available; older responses explicitly identify the profile-declaration fallback.
- [Aider overview](https://github.com/Aider-AI/aider): project-aware context and real lint/test workflows. This release uses bounded listing/search and hash-checked full-file edits rather than a repository map or custom edit language.
- [Codex sandbox documentation entry](https://github.com/openai/codex/blob/main/docs/sandbox.md): permissions and execution isolation are separate responsibilities. This app enforces file-tool boundaries and per-command approval, and explicitly does not claim OS sandboxing.
- [LiteLLM](https://github.com/BerriAI/litellm): provider normalization and routing are valuable, but its broad gateway/dependency scope is unnecessary for two protocols in this release. Small adapters expose a replaceable interface. Introduce a wider abstraction only when supported providers justify it.

This was focused research, not an exhaustive audit of the complete reference-product list in the original prompt. References are mutable upstream documentation, not vendored or release-pinned dependencies.

## Main tradeoffs

1. **Python + PySide6:** genuine native desktop components and an independently testable Python runtime, fitting the user's existing tools. Larger distribution than a minimal CLI. Windows runtime verification and installer signing remain separate work.
2. **SQLite + versioned JSON:** low operational burden with queryable events and portable agent definitions. Database schema v2 added human assessments; v3 adds retained diagnostic reports and submission states while preserving existing sessions/agents. Unsupported future database/agent schemas are rejected.
3. **Metadata by default:** fingerprints and structured results support recurrence analysis without storing every file. Reproducing a failure from full input/output requires opt-in session content and potentially the original project revision.
4. **Explicit control:** every write and command requires approval; no broad “approve everything” switch. Read/search tools are automatically allowed only when present in the saved agent definition.
5. **No implicit truncation:** oversized context stops clearly. Prompt token counts vary by model; character budgets are conservative guards, not tokenizer-accurate limits.
6. **Observable fallback:** transient failures may advance the user-configured chain. Capability/auth/protocol errors stop. No retry loop can repeatedly execute a tool. Model responses alone never execute shell text.
7. **Small extensible registry:** tool schemas, descriptions, permission enforcement and handlers are explicit. New tools need an implementation and validation tests, not just a prompt entry.

## Boundary limitations

File tools reject absolute/traversal paths, secret-like filenames, `.git`, sensitive directories, symlinks/junctions and hard-linked files. Binary/oversized reads are refused. Writes recheck the original SHA after approval and verify the resulting file. This protects ordinary single-user workflows; it is not race-proof against another malicious local process changing paths between checks. Existing-file writes are in place and are not crash-atomic. Use version control/backups. Full transactional edits and stronger OS file-handle restrictions are follow-up work.

Approved processes run with the user's OS privileges, a reduced environment, the selected working directory, stdin closed, a 1–120 second per-command timeout and 32 KB output limit. POSIX process groups or Windows `taskkill /T` are used for termination. Process-tree containment is best effort, especially for detached processes; a Windows Job Object/OS sandbox would be needed for stronger guarantees. The 32 KB cap terminates a noisy process, rather than merely hiding its output.

No provider failover, project file or model message can expand the agent's saved permissions. A cloud fallback can transmit existing context, so users must configure it deliberately. Model capability declarations are not guarantees of model quality. Unsupported or malformed native calls fail visibly; there is no prose-to-tool-call simulation.


## 0.3 runtime and diagnostic extensions

`diagnostics.py` implements a versioned packaged health/evaluation suite independent of pytest. `diagnostics_ui.py` runs it in a worker and owns local history/preview approval. `reporting.py` builds an allowlisted public payload and separates local URL preparation, browser drafts and explicit API issue creation. No GitHub source-write token is needed for reports.

Known text-tool response shapes are detected, never executed. Two maximum protocol-correction attempts share the existing step/time/context budgets. Real native calls still pass schemas, saved capabilities and per-action approvals. Native protocol recovery and tool/goal success are separate recorded outcomes. Schema validation feedback omits argument input values.

The runtime adds `response_only`, `needs_review` and `protocol_error` states; `completed` means actual tool execution ended, with human goal assessment still separate. Default activity is readable; the detailed-record toggle retains inspection of recorded evidence. Diagnostics aggregates the latest 20 sessions without uploading their contents.


## 0.4.0 metadata and maintenance

`catalog.py` owns explicit, deduplicated metadata GET batches with bounded concurrency and no generation/retry behavior. `records_ui.py` presents API reports, timestamps, cached choices and retention controls; it reuses the diagnostic worker lifecycle and sharing preview rather than inventing a second uploader. Schema v4 persists catalog snapshots separately from versioned diagnostic/API reports. Provider adapters emit low-cardinality HTTP/protocol codes and structural response evidence. Health suite 2 collects a bounded trace from its disposable local run and adds offline catalog/retention checks.

The durable engineering workspace is `docs/maintenance/`; actual user data stays in the existing OS data folder. Cloud artifacts and temporary acceptance data live outside the checkout. Catalog discovery, live tool certification, public support sharing, source changes and release installation retain separate acceptance criteria.


## 0.5.0 project and harness organization

registry.py defines frozen built-in metadata; tools.py binds the same names to schemas and executors and checks conformance. retrieval.py performs bounded ignore-aware traversal and fresh lexical/cited retrieval using pathspec. projects.py manages local project definitions; projects_ui.py keeps navigation/brief/context separate from Workbench's session/files/history layout. Context is explicitly added or retrieved by an allowed read-only tool, not silently accumulated in a vector store.

probes.py owns harmless synthetic native-call certification with explicit remote consent; probe_ui.py exposes bounded comparisons and confirmation before route selection. streams.py aggregates native NDJSON/SSE function fields with completion/time/size checks before the normal provider normalizer can return calls. providers.py preserves IDs and captures active parser metadata; runtime still owns approvals and execution. Native/compatible route/stream changes do not expand an agent's tool permissions.

Schema 5 preserves old definitions, sessions, diagnostics and catalogs. The maintenance plan/research records describe implemented scope and deferred embeddings/MCP/teams/OAuth. Public report builders still rebuild allowlisted evidence rather than uploading a database or source tree.
