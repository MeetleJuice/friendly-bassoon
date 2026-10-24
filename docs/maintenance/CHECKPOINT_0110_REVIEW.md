# 0.11 checkpoint audit and regression evidence

## Verified implementation gaps

- 0.10 validated every historical output hash before accepting a later step. A legitimate edit to a file produced by an earlier step could therefore never be checkpointed. Effective revisions now use the latest verified owner of each canonical file path; historical hashes remain immutable. Only declared current outputs may supersede predecessor revisions during user acceptance. Other predecessor outputs must remain unchanged.
- A session was linked only after the worker returned. A crash between actual execution and that callback could leave the plan unable to identify its run. The new `bind` operation records the explicit runtime session ID as soon as runtime activity supplies it. It does not search history heuristically. Different linked runs and foreign projects are rejected.
- Explicit reconciliation exposes a linked finished session for review without starting any provider or tool. Failed, interrupted, cancelled and timed-out sessions cannot be checkpointed as successful. Unlinked legacy attempts remain uncertain and require inspection/reset; no inferred association or replay.
- Existing dialogs guarded project switches only when launching. All modifying actions now enforce current project and idle-worker checks. Stale displayed plan records require refresh/review. The acceptance dialog captures output revisions before confirmation and rechecks them afterward, rejecting external edits during review.
- Read-only inspection shows linked runtime status, missing/changed checkpoints and accepted historical revisions superseded by a later step. Reset discards later acceptance, so the earlier accepted revision becomes effective again. No files are restored or altered implicitly.

## Primary-source research

Inspected [Temporal Workflow Execution overview](https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/workflow/workflow-execution/workflow-execution.mdx), 13,275 bytes, moving main (not a pinned immutable revision). Its Replay section describes matching generated Commands against recorded Event History and resuming from recorded events. Application here: durable identity/evidence and explicit state transitions are prerequisites for reliable recovery. Aigentics does **not** implement Temporal command-history replay or claim exactly-once effects. With native model/tool actions whose outcome may be uncertain, it reconciles a known session and current files, then requires explicit review/reset before another attempt. Candidate LangGraph documentation paths were unavailable and were not treated as inspected research.

## Validation

`tests/test_task_plans_0110.py` adds actual byte/file revision tests, real SQLite close/reopen interruption recovery, binding identity/foreign-root protection, live-run rejection, finished-run reconciliation, forbidden acceptance for failed terminal states, missing files and protected symlinks, incomplete checkpoint metadata, concurrent-dialog freshness, every plan action after a project switch, and revision changes during the acceptance prompt. Together with `tests/test_workflow_0100.py`: 69 tests passed locally. No live model, real project, secret or public report POST was used.
