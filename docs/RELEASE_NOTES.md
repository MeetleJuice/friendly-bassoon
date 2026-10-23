## Aigentics Desktop 0.6.0 — clearer checks and useful agent evidence

- **Diagnose** now opens test options before running. Choose the saved agent, select the real local-model test if wanted, then Run diagnostics. Progress, plain-language findings and next steps distinguish app checks from model failures; technical evidence is optional.
- **Python checking** automatically compile-checks Python writes and flags obvious literal assignment count mistakes. Workbench's **Check Python file** checks a chosen project file without a model call. Neither action executes/imports the program or verifies dependencies/gameplay.
- **Safer editing** supports run-scoped `last_read` revisions, preserving exact-hash support, protected paths, diff approval and stale checks before/after review. Recovered stale-edit failures remain in history and counters; unresolved failures or current failed Python checks still require review.
- **Plan only** enforces read-only tools for a run without changing saved agents. Agent name and description are included in identity context. Build/edit retains the saved permissions.
- **Share run report** turns a finished selected run into preview-approved counters and check codes. File writes, static checks, approved commands, recovered errors, unresolved errors and user Goal met/Needs work labels remain separate. No transcript/source/path/assessment notes are included in public reports; model names remain optional.
- **Useful local retention** stores these reports under existing limits, adds bounded aggregate recovery/check/assessment counters and readable history. No background cloud generation, report upload or raw-content collection was added.
- **19 packaged offline checks**, synthetic regressions and actual released-0.5.0 installer upgrade preservation are required before publication. Existing app data/project/key locations and schema5 remain unchanged.

Live evidence: Qwen3:8b successfully performed approved file edits in the user's session. Qwen2.5-Coder14b's text-tool failure remains unresolved; no universal Ollama fix is claimed. The Windows executable remains unsigned.

After updating: keep your saved Qwen3:8b agent, open a disposable project in Workbench, request one small Python edit, and inspect the automatic check. Use Check Python file for the current game, then test its actual behavior separately. Label the run and use Share run report to send minimal approved evidence through GitHub Issues.
