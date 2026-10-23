# Help test 0.6 without copying transcripts

1. Update to0.6.0 and restart. Keep your saved working Qwen3:8b agent; no new agent/model download is needed.
2. Open a disposable project in Workbench. Choose **Build / edit**, then ask: “Read game.py, fix any Python check errors, and explain what remains untested. Use tools; do not run commands.” Review any diff before approval.
3. Inspect the automatic Python check after each write. **Check Python file** also checks the chosen current .py file without calling a model. Passing means compilation/basic static checks, not a working game.
4. Launch/test the game separately using your usual Python/VSCode workflow. If it fails, copy the actual error (no keys) and mark **Needs work**; if the requested behavior works, mark **Goal met**.
5. Select that finished run in History, click **Share run report**, include the model name if comfortable, inspect/approve the preview, then finish **Create** in Chrome. Send the posted /issues/N link and one sentence about expected/actual behavior. No dragging logs/database files is required.
6. To test planning, choose **Plan only (read only)** for a separate task. The runtime blocks writes/commands even if requested by the model. Switch back to Build/edit when you want approved changes.
7. For app health, Diagnose → choose agent/options → Run diagnostics. It runs19 offline checks; the optional local-model test uses temporary files. Share one report per changed hypothesis, not repeated identical Qwen14b tests.

Test APIs remains one metadata GET per configured unique connection, no generation. Test model remains one synthetic probe (or four local variants if explicitly selected); cloud generation requires separate approval. Neither certifies a complete coding task.

Reports are local until approved. Model names are optional; public previews exclude project source/paths/transcripts/assessment notes. Retention uses the existing Local data settings. Original Desktop keys, project folders and app data stay where they are.
