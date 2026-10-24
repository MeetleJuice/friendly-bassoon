"""Local, user-controlled step checkpoints. Never replays an interrupted action."""

from typing import Literal
from pydantic import Field
from .models import Strict
from .tools import Workspace


class Step(Strict):
    task: str = Field(min_length=1, max_length=4000)
    outputs: list[str] = Field(default_factory=list, max_length=16)
    state: Literal["planned", "started", "review", "verified"] = "planned"
    session: str | None = None
    hashes: dict[str, str] = Field(default_factory=dict)


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
                self.ws.path(path)
            if self.store.credentials.redact(step.task) != step.task:
                raise ValueError("Do not put credentials in task plans")
        plans = self.store.setting("task_plans", {})
        plans.pop(self.key, None)
        if steps:
            if len(plans) >= 32:
                raise ValueError("At most 32 project plans; remove an old plan before adding another")
            plans[self.key] = [s.model_dump() for s in steps]
        self.store.set_setting("task_plans", plans)

    def validate_previous(self, steps, index):
        for previous in steps[:index]:
            if previous.state != "verified":
                raise ValueError("Verify preceding steps first")
            for path, sha in previous.hashes.items():
                if self.ws.read(path)["sha256"] != sha:
                    raise ValueError("Checkpoint changed on disk; review it before continuing")

    def begin(self, index):
        steps = self.steps()
        self.validate_previous(steps, index)
        if not 0 <= index < len(steps):
            raise ValueError("Invalid step index")
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
        if not 0 <= index < len(steps):
            raise ValueError("Invalid step index")
        if steps[index].state != "started":
            raise ValueError("This step is not active")
        steps[index].state, steps[index].session = "review", sid
        self.save(steps)

    def checkpoint(self, index):
        steps = self.steps()
        self.validate_previous(steps, index)
        if not 0 <= index < len(steps):
            raise ValueError("Invalid step index")
        step = steps[index]
        if step.state != "review" or not step.session:
            raise ValueError("A finished recorded attempt is required; uncertain attempts need review/reset")
        session = next((s for s in self.store.sessions() if s["id"] == step.session), None)
        if (
            not session
            or session["workspace"] != str(self.ws.root)
            or session["state"] not in ("completed", "response_only", "needs_review")
        ):
            raise ValueError("Run is not available for checkpointing; inspect its evidence first")
        step.hashes = {p: self.ws.read(p)["sha256"] for p in step.outputs}
        step.state = "verified"
        self.save(steps)

    def reset(self, index):
        steps = self.steps()
        if not 0 <= index < len(steps):
            raise ValueError("Invalid step index")
        for step in steps[index:]:
            step.state, step.session, step.hashes = "planned", None, {}
        self.save(steps)
