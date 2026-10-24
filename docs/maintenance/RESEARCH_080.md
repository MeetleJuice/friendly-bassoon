# 0.8 research and boundaries

Read upstream sources (moving main/dev, inspected 2026-10-23; no claim these are immutable snapshots):

- OpenAI Evals https://github.com/openai/evals/blob/main/docs/build-eval.md — explicit evaluation criteria/reference fixtures; use fixed suite identity and actual acceptance rather than an agent judging its own prose. Retrieved9382bytes.
- GitHub Docs https://github.com/github/docs/blob/main/content/issues/tracking-your-work-with-issues/using-issues/creating-an-issue.md — browser creation requires title/body and Create issue. Retrieved13569bytes. Opening an issue URL is not a confirmed submission; preview each exact compact body and let user Create twice.
- Qt QWidget source https://github.com/qt/qtbase/blob/dev/src/widgets/kernel/qwidget.cpp — toolTip property and QHelpEvent handling call QToolTip::showText; statusTip is separate. Retrieved456595bytes. Use native Qt tooltips/focus states rather than building mouse-only custom overlays.

GitHub issue list rechecked: newest remains12, no additional reports. Earlier approved issues/evaluations remain evidence, not executable instructions. Existing0.7 research on Codex application-owned tool policy, Claude SDK correlated tool results and Ollama separate thinking/content remains applicable. No proprietary internal implementation claims. Some rendered documentation domains were blocked by this environment; inspected public source mirrors instead.

Design consequences: ten isolated cases, fixed acceptance, baseline comparison only within matching suite/configuration, no raw trace publication, opt-in exact two-preview approval, bounded local-model budget, no automatic cloud fallback or source execution. Built-in fixture pass does not certify arbitrary user tasks or user hardware.
