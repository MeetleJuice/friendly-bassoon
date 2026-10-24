"""Actual-disk, SQLite-restart and native-dialog checkpoint regressions."""

import pytest
from aigentics.task_plans import TaskPlans, Step
from aigentics.models import Agent
from aigentics.store import Store


def session(store, root, state="completed"):
    sid = store.start(Agent(), root, False, None)
    if state != "running":
        store.finish(sid, state, "Synthetic task-plan evidence")
    return sid


def accepted(plans, store, root, index):
    plans.begin(index)
    sid = session(store, root)
    plans.bind(index, sid)
    plans.finish(index, sid)
    plans.checkpoint(index)


def test_later_step_can_edit_same_file_and_preserve_prior_revision(store, tmp_path):
    plans = TaskPlans(store, tmp_path)
    plans.save(
        [
            Step(task="Create", outputs=["item.txt"]),
            Step(task="Edit", outputs=["./item.txt"]),
            Step(task="Use latest"),
        ]
    )
    path = tmp_path / "item.txt"
    path.write_bytes(b"original")
    accepted(plans, store, tmp_path, 0)
    first_hashes = plans.steps()[0].hashes.copy()
    plans.begin(1)
    path.write_bytes(b"updated")
    plans.finish(1, session(store, tmp_path))
    plans.checkpoint(1)
    assert plans.steps()[0].hashes == first_hashes
    assert plans.steps()[1].hashes["./item.txt"] != first_hashes["item.txt"]
    assert plans.inspect(0)["checkpoint"] == "current"
    assert plans.inspect(0)["superseded_outputs"] == 1
    assert plans.begin(2).state == "started"


def test_replacement_does_not_allow_changes_to_other_prior_outputs(store, tmp_path):
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Create", outputs=["a.txt", "b.txt"]), Step(task="Edit only a", outputs=["a.txt"])])
    for name in ("a.txt", "b.txt"):
        (tmp_path / name).write_bytes(b"initial")
    accepted(plans, store, tmp_path, 0)
    plans.begin(1)
    for name in ("a.txt", "b.txt"):
        (tmp_path / name).write_bytes(b"changed")
    plans.finish(1, session(store, tmp_path))
    with pytest.raises(ValueError, match="changed"):
        plans.checkpoint(1)
    assert plans.steps()[1].state == "review"


def test_reset_discards_superseding_acceptance_and_requires_earlier_hash(store, tmp_path):
    plans = TaskPlans(store, tmp_path)
    plans.save(
        [Step(task="Create", outputs=["a.txt"]), Step(task="Edit", outputs=["a.txt"]), Step(task="Later")]
    )
    path = tmp_path / "a.txt"
    path.write_bytes(b"one")
    accepted(plans, store, tmp_path, 0)
    plans.begin(1)
    path.write_bytes(b"two")
    plans.finish(1, session(store, tmp_path))
    plans.checkpoint(1)
    plans.reset(1)
    with pytest.raises(ValueError, match="changed"):
        plans.begin(1)
    assert plans.steps()[0].state == "verified"
    path.write_bytes(b"one")
    plans.begin(1)


def test_checkpoint_rejects_revision_changed_during_user_confirmation(store, tmp_path):
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Create", outputs=["a.txt"])])
    plans.begin(0)
    path = tmp_path / "a.txt"
    path.write_bytes(b"reviewed")
    plans.finish(0, session(store, tmp_path))
    displayed = plans.review_revisions(0)
    path.write_bytes(b"external edit")
    with pytest.raises(ValueError, match="during checkpoint review"):
        plans.checkpoint(0, expected_hashes=displayed)
    assert plans.steps()[0].state == "review"
    assert not plans.steps()[0].hashes


def test_session_binding_survives_crash_without_replay(tmp_path, credentials):
    project = tmp_path / "project"
    project.mkdir()
    database = tmp_path / "data.sqlite3"
    store = Store(database, credentials)
    plan = TaskPlans(store, project)
    plan.save([Step(task="Uncertain create", outputs=["a.txt"])])
    plan.begin(0)
    sid = session(store, project, "running")
    plan.bind(0, sid)
    (project / "a.txt").write_bytes(b"possible side effect")
    store.close()
    reopened = Store(database, credentials)
    try:
        plan = TaskPlans(reopened, project)
        assert plan.steps()[0].session == sid
        assert plan.inspect(0)["session_state"] == "interrupted"
        assert plan.reconcile(0) == "interrupted"
        with pytest.raises(ValueError):
            plan.begin(0)
        with pytest.raises(ValueError):
            plan.checkpoint(0)
        assert (project / "a.txt").read_bytes() == b"possible side effect"
        assert len(reopened.sessions()) == 1
    finally:
        reopened.close()


@pytest.mark.parametrize("state", ["completed", "response_only", "needs_review"])
def test_finished_linked_session_can_be_reconciled_explicitly(store, tmp_path, state):
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Review result")])
    plans.begin(0)
    sid = session(store, tmp_path, state)
    plans.bind(0, sid)
    plans.bind(0, sid)  # Idempotent correlation, no new session or action.
    assert plans.reconcile(0) == state
    plans.checkpoint(0)
    assert plans.steps()[0].state == "verified"
    assert len(store.sessions()) == 1


@pytest.mark.parametrize("state", ["running", "failed", "timed_out", "cancelled", "interrupted"])
def test_unfinished_or_failed_runs_cannot_be_accepted(store, tmp_path, state):
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Unfinished")])
    plans.begin(0)
    sid = session(store, tmp_path, state)
    plans.bind(0, sid)
    if state == "running":
        with pytest.raises(ValueError, match="still active"):
            plans.reconcile(0)
    else:
        plans.reconcile(0)
    with pytest.raises(ValueError):
        plans.checkpoint(0)


def test_binding_rejects_foreign_project_and_different_session(store, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Bound")])
    plans.begin(0)
    with pytest.raises(ValueError, match="another project"):
        plans.bind(0, session(store, other))
    sid = session(store, tmp_path)
    plans.bind(0, sid)
    second = session(store, tmp_path)
    with pytest.raises(ValueError, match="different run"):
        plans.bind(0, second)
    with pytest.raises(ValueError, match="different run"):
        plans.finish(0, second)
    assert plans.steps()[0].session == sid


def test_no_guess_when_uncertain_run_has_no_binding(store, tmp_path):
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Legacy interrupted")])
    plans.begin(0)
    session(store, tmp_path)  # Even one plausible historical run is not enough.
    with pytest.raises(ValueError, match="No uncertain linked run"):
        plans.reconcile(0)
    assert plans.steps()[0].session is None


def test_missing_output_and_protected_link_fail_closed(store, tmp_path):
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Create", outputs=["a.txt"]), Step(task="Next")])
    path = tmp_path / "a.txt"
    path.write_bytes(b"safe")
    accepted(plans, store, tmp_path, 0)
    path.unlink()
    assert plans.inspect(0)["checkpoint"] == "missing_file"
    with pytest.raises(FileNotFoundError):
        plans.begin(1)
    outside = tmp_path.parent / (tmp_path.name + "-outside.txt")
    outside.write_bytes(b"external")
    try:
        path.symlink_to(outside)
    except (OSError, NotImplementedError):
        return  # Windows runner without symlink permission still checks deletion above.
    with pytest.raises(PermissionError):
        plans.begin(1)


def test_incomplete_checkpoint_metadata_cannot_authorize_later_step(store, tmp_path):
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Claimed", outputs=["a.txt"], state="verified"), Step(task="Next")])
    (tmp_path / "a.txt").write_bytes(b"present")
    with pytest.raises(ValueError, match="incomplete"):
        plans.begin(1)


def dialog_for(qtbot, store, credentials, project):
    from aigentics.ui import Window
    from aigentics.task_plans_ui import TaskPlanDialog

    window = Window(store, credentials)
    qtbot.addWidget(window)
    window.select_workspace(project)
    dialog = TaskPlanDialog(window)
    qtbot.addWidget(dialog)
    window.store.close = lambda: None
    return window, dialog


def test_stale_dialog_selection_requires_refreshed_review(qtbot, store, credentials, tmp_path):
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Original")])
    window, dialog = dialog_for(qtbot, store, credentials, tmp_path)
    plans.save([Step(task="New task")])
    with pytest.raises(ValueError, match="Plan changed"):
        dialog.selected()
    assert "New task" in dialog.rows.item(0).text()
    window.lab_dir.cleanup()


@pytest.mark.parametrize("operation", ["add", "verify", "reset", "remove", "launch", "reconcile"])
def test_project_switch_blocks_every_plan_action(qtbot, store, credentials, tmp_path, operation):
    plans = TaskPlans(store, tmp_path)
    plans.save([Step(task="Keep this project")])
    window, dialog = dialog_for(qtbot, store, credentials, tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    window.select_workspace(other)
    with pytest.raises(ValueError, match="project changed"):
        getattr(dialog, operation)()
    assert plans.steps()[0].state == "planned"
    window.lab_dir.cleanup()
