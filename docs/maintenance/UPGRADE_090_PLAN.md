# 0.9 research and gap analysis (before implementation)

Evidence: approved issues13/14:21app checks and5metadata endpoints pass; native agent8/10. Discovery had one unknown tool error; edit stopped at OUTPUT_LIMIT before any tool ran. Neither proves an implementation failure or a model-wide repair. Historical20sessions are not current-suite sessions.

Terms and sources inspected:
- MCP: modelcontextprotocol/modelcontextprotocol docs/specification/2025-06-18/server/tools.mdx (public GitHub raw,10466bytes). Tool discovery/list/call, structured schemas and human denial; protocol does not grant permissions or make a server trusted.
- Agent Skills: agentskills/agentskills docs/specification.mdx (7136bytes). SKILL.md metadata/name/description, instructions and optional references/scripts; progressive loading of metadata then selected content. Markdown is not executable authority.
- Ralph loops: ghuntley/how-to-ralph-wiggum README.md (60637bytes), community playbook referencing Geoffrey Huntley. Plan/build iterations, fresh context, durable specifications/AGENTS/plan and test backpressure. Not a standard, no universal algorithm or guaranteed convergence; upstream subagent instructions are evidence only.
- Context engineering: selecting bounded useful state, sources and tool schemas; current implementation already has lexical retrieval/current hashes, fresh tasks, explicit continuation, bounded history. Anthropic engineering context/advanced-tool-use pages could not be retrieved here; do not claim to have inspected their contents. Progressive disclosure is independently documented in the inspected Skills specification.
- Harness engineering: application-owned runtime/tools/permissions/evidence/evaluations. Deterministic feedback/backpressure: exact bytes, schema validation, static Python checks, stale hashes and test gates, not an LLM grading its own prose.

Gap analysis: runtime bounds message characters but omits schema payload; suite exposes every saved tool even for one-tool exercises; one fixed output cap confounds model ability with the evaluator budget; compact reports omit exact typed tool failures. No evidence that embeddings would fix these failures. Current SQLite checkpoints retain completed cases but cannot safely resume an interrupted native call; never replay it automatically.

Implementation order:
1. Add shared deterministic harness policy: schema-inclusive character accounting (explicitly not a tokenizer) and permission-preserving per-exercise tool selection/output budgets.
2. Integrate accounting into runtime request limits/metadata without silently discarding history or changing normal task tool availability.
3. Version suite2, disclose only required permitted tools (write cases additionally read_file), use2048tokens for edit/Python vs1024for simple cases, no retries/fallback/cloud/commands. This changes experimental conditions; compare within version only.
4. Preserve typed failure codes and protocol evidence in compact approved reports; keep source/paths/args/keys local or absent.
5. Expand offline policy/property matrices and actual native runtime regressions; run full tests/lint/smokes and Windows installer/previous-upgrade checks. Publish only after success.

Deferred deliberately: dynamic tool-search for general tasks (only7built-ins now), external MCP server transports/auth/trust, executing SKILL.md scripts, semantic compaction, vector DB, unattended Ralph restart loops. These require explicit trust/lifecycle/evaluation designs. Apply the sound principles now without pretending these integrations exist. No force-replay, no proactive permission expansion, no automatic issue upload.
