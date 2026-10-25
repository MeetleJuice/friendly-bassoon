# 0.16 — Midnight Crew desktop interface

User explicitly authorized research, planning, implementation and a UI release while their0.15local tests run. There is no remote access to that running desktop session. Publishing an installer cannot replace an active run; existing install guards and explicit Update workflow remain.

Read ../design/UI_RESEARCH_0160.md for inspected primary sources, visual evidence, unavailable websites and the distinction between DeepSeek models and third-party desktop clients. Apply useful interaction patterns without copying competitors' branding or claiming their implementation.

## Delivery

- Introduce presentation.py: consistent Midnight Crew theme, original geometric role/navigation emblems, plain-text labels, path elision retaining full accessible text, progressive disclosure and a navigation-only command palette.
- Replace the seven-action header with a sidebar, page title, command search and Update. Keep underlying three-page routes stable for projects/workflows/history.
- Give Workbench a larger conversation surface and grouped composer. Keep expected output scope visible; advanced task checks, capture and context retain their existing values inside Task options. Remember file/history visibility with validated local preferences. Small windows collapse unchosen file panels and scroll expanded content. Previewing a file opens the matching inspector tab.
- Keep agent form Save visible outside the scroll area, simplify library actions, add colored role emblems and retain personal definitions. Connection/laboratory/registry functions remain available; no keys are exposed or added to search.
- Add actionable project empty state and keep existing brief/retrieval/history behavior.
- Test center has first-try/corrected/failed/incomplete counters, readable repeated case labels, active-case progress and expandable records. Reviewed ZIP is primary; optional public draft sharing remains approval-gated. Stop/ZIP controls reflect current availability.
- Ctrl1Projects, Ctrl2Workbench, Ctrl3Agents, CtrlKcommands, CtrlBfiles, CtrlShiftIhistory. CtrlEnter runs only from the focused task composer with Run enabled. New task cannot clear an active run's context/evidence.

## Preserve comparison and data

No changes to runtime, crew instructions, strict contracts, tool schemas, provider behavior, model budgets, measurement order or storage encoding. Campaign4/crew2/schema5 remain. Frozen measurement digest remains0dcfdb6158c959aa7ac6c6591b862031f7edb75813bccf9aafb3184431b9261d. Existing0.15partial campaigns remain eligible for matching continuation with no replay. Local UI preferences are separate from model/benchmark identity. Existing automatic post-update suite behavior remains; no additional hidden model calls are introduced. Save the current test ZIP before updating when convenient; older reports remain in Diagnose.

## Validation

New actual Qt regressions cover page/nav synchronization including reselecting the current page, keyboard palette search/Enter/Esc without generation, option-value preservation, persistent panel state, actual file-preview routing, small/large geometry, new-task guards during active work, saved-agent preservation, safe shortcut scope, actionable empty state and unknown-aware result counters. Existing actual native-tool runs, approval/denial dialogs, thirty/sixty-six-case Qt workers, report approval and ZIP save tests must pass. Benchmark golden manifest must remain unchanged.

Full pytest, lint/format, source startup/25offline diagnostic smoke, dependency consistency and wheel; inspect real rendered PNGs. Windows must pass actual installer/shortcut/packaged diagnostics and pinned public0.15upgrade/data preservation/silent restart. Tag only exact passing source, repeat release gates and verify the public installer through production Updater. Keep source, release, installer size/hash and real limitations in repository memory.
