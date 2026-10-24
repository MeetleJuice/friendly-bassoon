"""Local, user-controlled step checkpoints. Never replays an interrupted action."""

import os
from typing import Literal
from pydantic import Field
import re
from .models import Strict
from .tools import Workspace


class Step(Strict):
    task: str = Field(min_length=1, max_length=4000)
    outputs: list[str] = Field(default_factory=list, max_length=16)
    state: Literal["planned", "started", "review", "verified"] = "planned"
    session: str | None = Field(default=None, max_length=100)
    hashes: dict[str, str] = Field(default_factory=dict, max_length=16)


class TaskPlans:
    def __init__(self, store, root):
        self.store, self.ws = store, Workspace(root)
        self.key = store.fingerprint(str(self.ws.root))

    def steps(self):
        return [Step.model_validate(s) for s in self.store.setting("task_plans", {}).get(self.key, [])]

    def save(self, steps):
        if len(steps) > 16:
            raise ValueError("At most 16 steps per project")
        for step in steps:
            Step.model_validate(step.model_dump())
            for path in step.outputs:
                self._path_key(path)
            for path, sha in step.hashes.items():
                self._path_key(path)
                if path not in step.outputs or not re.fullmatch(r"[a-f0-9]{64}", sha):
                    raise ValueError("Checkpoint revisions must be SHA256 hashes of declared outputs")
            if self.store.credentials.redact(step.task) != step.task:
                raise ValueError("Do not put credentials in task plans")
        with self.store.lock:
            plans = self.store.setting("task_plans", {})
            plans.pop(self.key, None)
            if steps:
                if len(plans) >= 32:
                    raise ValueError("At most 32 project plans; remove an old plan before adding another")
                plans[self.key] = [s.model_dump() for s in steps]
            self.store.set_setting("task_plans", plans)

    def _path_key(self, path):
        if not isinstance(path, str) or not 1 <= len(path) <= 1000:
            raise ValueError("Output paths must contain 1 to 1000 characters")
        return os.path.normcase(str(self.ws.path(path)))

    @staticmethod
    def _index(steps, index):
        if type(index) is not int or not 0 <= index < len(steps):
            raise ValueError("Invalid step index")

    def validate_previous(self, steps, index, replacing=()):
        """Check effective revisions, preserving immutable historical checkpoints.

        A later accepted writer supersedes an earlier revision of the same path.
        During acceptance only, declared current outputs may replace predecessor
        files. Other predecessor files must still match their last accepted hash.
        """
        self._index(steps, index)
        expected = {}
        for previous in steps[:index]:
            if previous.state != "verified":
                raise ValueError("Verify preceding steps first")
            if set(previous.hashes) != set(previous.outputs):
                raise ValueError("Checkpoint is incomplete; review/reset it before continuing")
            for path, sha in previous.hashes.items():
                expected[self._path_key(path)] = (path, sha)
        replacements = {self._path_key(path) for path in replacing}
        for key, (path, sha) in expected.items():
            if key not in replacements and self.ws.read(path)["sha256"] != sha:
                raise ValueError("Checkpoint changed on disk; review it before continuing")

    def _session(self, sid):
        session = next((s for s in self.store.sessions() if s["id"] == sid), None)
        if not session or os.path.normcase(session["workspace"]) != os.path.normcase(str(self.ws.root)):
            raise ValueError("The linked run is missing or belongs to another project")
        return session

    def bind(self, index, sid):
        """Attach evidence as soon as the runtime starts, without replaying it."""
        steps = self.steps()
        self._index(steps, index)
        step = steps[index]
        if step.state != "started":
            raise ValueError("This step is not active")
        self._session(sid)
        if step.session and step.session != sid:
            raise ValueError("A different run is already linked; review/reset before another attempt")
        if step.session != sid:
            step.session = sid
            self.save(steps)

    def reconcile(self, index):
        """Expose a linked terminal run for review; never guess or re-execute."""
        steps = self.steps()
        self._index(steps, index)
        step = steps[index]
        if step.state != "started" or not step.session:
            raise ValueError("No uncertain linked run to reconcile; inspect history/files before resetting")
        session = self._session(step.session)
        if session["state"] == "running":
            raise ValueError("The linked run is still active; finish or cancel it first")
        step.state = "review"
        self.save(steps)
        return session["state"]

    def inspect(self, index):
        """Local-only, fresh status for a useful review screen, without mutation."""
        steps = self.steps()
        self._index(steps, index)
        step = steps[index]
        result = {"state": step.state, "session_state": "not_linked", "checkpoint": "not_verified"}
        if step.session:
            try:
                result["session_state"] = self._session(step.session)["state"]
            except ValueError:
                result["session_state"] = "missing_or_other_project"
        if step.state == "verified":
            try:
                # Validate the full accepted chain; old immutable revisions may
                # have been deliberately superseded by a later accepted writer.
                prefix = list(steps[: index + 1])
                for later in steps[index + 1 :]:
                    if later.state != "verified":
                        break
                    prefix.append(later)
                self.validate_previous([*prefix, Step(task="inspection")], len(prefix))
                result["checkpoint"] = "current"
                later_keys = {self._path_key(path) for later in prefix[index + 1 :] for path in later.hashes}
                result["superseded_outputs"] = sum(
                    self._path_key(path) in later_keys for path in step.outputs
                )
            except FileNotFoundError:
                result["checkpoint"] = "missing_file"
            except (ValueError, PermissionError, OSError):
                result["checkpoint"] = "changed_or_inaccessible"
        return result

    def begin(self, index):
        steps = self.steps()
        self.validate_previous(steps, index)
        self._index(steps, index)
        step = steps[index]
        if step.state != "planned":
            raise ValueError(
                "Review this previous attempt before explicitly resetting it; it will not replay automatically"
            )
        step.state = "started"
        self.save(steps)
        return step

    def finish(self, index, sid):
        steps = self.steps()
        self._index(steps, index)
        if steps[index].state != "started":
            raise ValueError("This step is not active")
        if steps[index].session and steps[index].session != sid:
            raise ValueError("A different run is already linked; evidence cannot be overwritten")
        steps[index].state, steps[index].session = "review", sid
        self.save(steps)

    def review_revisions(self, index):
        """Capture file revisions shown for acceptance without mutating the plan."""
        steps = self.steps()
        step = self._review_step(steps, index)
        return {p: self.ws.read(p)["sha256"] for p in step.outputs}

    def _review_step(self, steps, index):
        self._index(steps, index)
        step = steps[index]
        self.validate_previous(steps, index, replacing=step.outputs)
        if step.state != "review" or not step.session:
            raise ValueError("A finished recorded attempt is required; uncertain attempts need review/reset")
        session = self._session(step.session)
        if session["state"] not in ("completed", "response_only", "needs_review"):
            raise ValueError("Run is not available for checkpointing; inspect its evidence first")
        return step

    def checkpoint(self, index, expected_hashes=None):
        steps = self.steps()
        step = self._review_step(steps, index)
        actual = {p: self.ws.read(p)["sha256"] for p in step.outputs}
        if expected_hashes is not None and actual != expected_hashes:
            raise ValueError(
                "Output changed during checkpoint review; inspect the new revision and try again"
            )
        step.hashes = actual
        step.state = "verified"
        self.save(steps)

    def reset(self, index):
        steps = self.steps()
        self._index(steps, index)
        for step in steps[index:]:
            step.state, step.session, step.hashes = "planned", None, {}
        self.save(steps)
