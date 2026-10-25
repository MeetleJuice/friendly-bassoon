"""Explicit, bounded task checks owned by the application, not model assertions."""

import os
import re
from typing import Annotated
from pydantic import Field, field_validator
from .models import Strict, TOOLS


class TaskChecks(Strict):
    write_targets: list[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(
        default_factory=list, max_length=16
    )
    required_tools: list[str] = Field(default_factory=list, max_length=16)
    required_reads: list[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(
        default_factory=list, max_length=16
    )
    completion_feedback: bool = False
    require_tools: bool = False
    require_readback: bool = True

    @field_validator("required_tools")
    @classmethod
    def known_tools(cls, values):
        if any(value not in TOOLS for value in values) or len(set(values)) != len(values):
            raise ValueError("Choose unique built-in tools")
        return values

    @property
    def configured(self):
        return bool(self.write_targets or self.required_tools or self.require_tools or self.required_reads)


def path_key(workspace, path):
    return os.path.normcase(str(workspace.path(path)))


def suggested_targets(task):
    """Suggest only one explicit leading operation with a single unambiguous filename.

    This is a convenience suggestion, not a general natural-language intent parser.
    The UI displays it before Run; callers never scan briefs/history/source for targets.
    """
    if re.search(
        r"\b(?:read.only|plan only|change nothing|no changes)\b|\b(?:do not|don't)\s+(?:create|write|edit|modify|change|touch|alter)\b",
        task,
        re.I,
    ):
        return []
    filename = r"[A-Za-z0-9_][A-Za-z0-9_./\\-]*\.[A-Za-z][A-Za-z0-9_]{0,12}"
    found = re.match(
        r"\s*(?:please\s+)?(?:create|write|update|edit|fix)\s+(?:(?:a|the)\s+)?(?:new\s+)?(?:file\s+(?:named\s+)?)?[`\"']?("
        + filename
        + r")[`\"']?(?=\s|[.,;:]|$)",
        task,
        re.I,
    )
    if not found:
        return []
    names = set(re.findall(filename, task))
    return [found[1]] if names == {found[1]} else []


class TaskEvidence:
    def __init__(self, workspace, checks):
        self.workspace, self.checks = workspace, checks
        self.targets = {path_key(workspace, path): path for path in checks.write_targets}
        self.writes, self.readbacks, self.tools = {}, {}, set()
        self.sources = {path_key(workspace, path): path for path in checks.required_reads}
        self.read_sources = set()

    def record(self, call, result, status):
        if status != "succeeded":
            return
        self.tools.add(call.name)
        if call.name not in ("read_file", "write_file"):
            return
        key = path_key(self.workspace, call.arguments["path"])
        if call.name == "read_file":
            self.read_sources.add(key)
        if call.name == "write_file" and result.get("verified") is True and not result.get("unchanged"):
            self.writes[key] = result["sha256"]
            self.readbacks.pop(key, None)
        elif call.name == "read_file" and key in self.writes and result.get("sha256") == self.writes[key]:
            self.readbacks[key] = result["sha256"]

    def evaluate(self):
        written, readback, stale = 0, 0, 0
        missing = []
        for key, relative in self.targets.items():
            valid = False
            if key in self.writes:
                try:
                    valid = self.workspace.read(relative)["sha256"] == self.writes[key]
                except (OSError, ValueError, UnicodeError):
                    valid = False
                if not valid:
                    stale += 1
            if valid:
                written += 1
                if self.readbacks.get(key) == self.writes[key]:
                    readback += 1
            if not valid or (self.checks.require_readback and key not in self.readbacks):
                missing.append(relative)
        missing_sources = set(self.sources) - self.read_sources
        missing_tools = set(self.checks.required_tools) - self.tools
        passed = (
            written == len(self.targets)
            and (not self.checks.require_readback or readback == len(self.targets))
            and not missing_sources
            and not missing_tools
            and (not self.checks.require_tools or bool(self.tools))
        )
        return {
            "status": "not_configured"
            if not self.checks.configured
            else "passed"
            if passed
            else "needs_attention",
            "expected_files": len(self.targets),
            "written_files": written,
            "readback_files": readback,
            "required_tools": len(self.checks.required_tools),
            "successful_required_tools": len(set(self.checks.required_tools) & self.tools),
            "missing_writes": len(self.targets) - written,
            "missing_readbacks": len(self.targets) - readback if self.checks.require_readback else 0,
            "missing_tools": len(missing_tools),
            "missing_sources": len(missing_sources),
            "revision_mismatches": stale,
            "require_tools": self.checks.require_tools,
            "any_tool_succeeded": bool(self.tools),
            "require_readback": self.checks.require_readback,
        }, {
            "unmet_targets": missing,
            "unmet_tools": sorted(missing_tools),
            "unread_sources": [self.sources[key] for key in sorted(missing_sources)],
        }


TASK_COUNT_KEYS = frozenset(
    (
        "expected_files",
        "written_files",
        "readback_files",
        "required_tools",
        "successful_required_tools",
        "missing_writes",
        "missing_readbacks",
        "missing_tools",
        "missing_sources",
        "content_failures",
        "revision_mismatches",
    )
)
TASK_BOOL_KEYS = frozenset(("require_tools", "any_tool_succeeded", "require_readback"))


def public_task_checks(value):
    value = value if isinstance(value, dict) else {}
    result = {
        key: min(number, 16)
        for key, number in value.items()
        if key in TASK_COUNT_KEYS and type(number) is int and number >= 0
    }
    result.update(
        {key: number for key, number in value.items() if key in TASK_BOOL_KEYS and type(number) is bool}
    )
    result["status"] = (
        value.get("status")
        if value.get("status") in ("not_configured", "passed", "needs_attention")
        else "not_recorded"
    )
    return result
