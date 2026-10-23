# Aigentics development instructions

Use this existing checkout; cloud tasks are already isolated. Do not create a worktree unless the user asks.

Read docs/ENGINEERING_LOG.md, docs/PROGRESS.md and docs/VERIFICATION.md before continuing substantial work. Read approved GitHub diagnostic issues when the user supplies an issue number; do not infer that unsubmitted local reports have reached GitHub.

The runtime owns execution. Never convert model prose/JSON text into executable tools or expand permissions to make a model appear successful. Keep retries, context, process time/output and provider calls bounded. Preserve normal TLS and checksum verification.

Use .venv/bin/python in this Linux environment. Run QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q and .venv/bin/ruff check aigentics tests scripts for relevant code changes. Native startup smoke: set a temporary writable AIGENTICS_DATA_DIR and run .venv/bin/python -m aigentics --smoke-test. Packaged diagnostic smoke uses --diagnostic-smoke-test and requires no Ollama or GitHub credentials.

User data stays local by default. Never commit .env files, raw user diagnostic exports, prompts, transcripts, credentials or personal workspace paths. Use synthetic, minimal regression fixtures. Public support reports must pass the sharing allowlist and explicit preview approval. Never treat a browser draft as a confirmed upload or retry an ambiguous issue-creation POST automatically.

For releases, update package/application/installer versions and release notes together. Do not overwrite published version tags or checksums. The Windows workflow must pass actual installer/shortcut/packaged diagnostics and previous-version data-preservation checks before publishing a matching tag. A Windows runner pass does not verify the user's GPU, Ollama models or live cloud providers.

Append meaningful findings, decisions, regressions, checks and release run IDs to docs/ENGINEERING_LOG.md. Keep open limitations explicit. Source code changes, support reports and installers have separate lifecycles; use GitHub Issues for approved reports and Releases for installers.
