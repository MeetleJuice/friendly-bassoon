## Aigentics Desktop 0.7.0 — task checks and trustworthy outcomes

- **Expected output files** is visible below the task. A narrow single-file instruction can suggest a target; review/edit it before Run. Configured targets restrict file-tool writes before approval, so an attempt to rewrite a different file is blocked. Empty means no extra target restriction. Separately approved host commands are not sandboxed by this list.
- **Require real tools**, **Required tools**, and **Read back output files** check actual successful operations. Target writes must be followed by matching read-back when required, and the current file revision must still match. Missing checks leave the run needing review. Passed operation checks do not certify program behavior or arbitrary English goals.
- **Fresh context is the default.** Choose Continue conversation or Resume explicitly when desired. Local evidence shows fresh/continued history and command permission; saved agents are preserved.
- **Missing final answers preserve work.** If the model returns no visible final answer, the app shows incomplete_response and its own recorded-operation summary. No tool is replayed, no extra generation request is made, and thinking is not substituted for an answer.
- **Runtime evidence is separate from model prose.** Actual calls/writes, unchanged writes skipped, task checks and final-answer status are shown independently. Identical writes are not re-saved, approved pointlessly or counted as real writes.
- **Better reports** carry fixed task-check/missing-final/no-op counters, successful HTTP status and mixed-history evidence coverage. Target paths, source, tasks and notes remain excluded from public previews. Existing retention limits still apply; sharing requires review/approval.
- **21 packaged offline checks** plus Linux regressions and actual Windows installation/0.6.0 upgrade preservation are required before publication.

Qwen2.5 native-tool compatibility and the exact Qwen3.5 missing-final cause remain open. Python static checks do not verify dependencies or gameplay. The installer remains unsigned.

After updating: keep a saved working local agent, open a disposable project and enter a simple create-file task. Check the visible output filename, keep fresh context/read-back enabled, and run once. Review the actual diff, runtime task checks and result. Mark Goal met/Needs work and Share run report after inspection.
