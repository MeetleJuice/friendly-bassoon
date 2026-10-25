"""Explicit, bounded task checks owned by the application, not model assertions."""

import os
import re
from typing import Annotated, Literal
from pydantic import Field, field_validator
from .models import Strict, TOOLS


class TaskChecks(Strict):
    json_outputs: dict[
        Annotated[str, Field(min_length=1, max_length=1000)],
        Literal["object", "array", "string", "number", "boolean", "null"],
    ] = Field(default_factory=dict, max_length=16)
    write_targets: list[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(
        default_factory=list, max_length=16
    )
    required_tools: list[str] = Field(default_factory=list, max_length=16)
    required_reads: list[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(
        default_factory=list, max_length=16
    )
    unchanged_targets: list[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(
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
        return bool(
            self.write_targets
            or self.required_tools
            or self.require_tools
            or self.required_reads
            or self.unchanged_targets
        )

    def instructions(self):
        parts = ["Before the final response, complete every configured check using native tools."]
        if self.required_reads:
            parts.append("Inspect the required source files: " + ", ".join(self.required_reads) + ".")
        if self.write_targets:
            parts.append("Produce the declared outputs and compare them with the requested contract.")
            if self.require_readback:
                parts.append(
                    "After the LAST saved change, call read_file on EACH output. A write_file verification result is not that read_file call."
                )
        if self.json_outputs:
            parts.append(
                "Declared JSON root contracts (validated before saving): "
                + "; ".join(path + "=" + kind for path, kind in self.json_outputs.items())
                + ". A rejected proposal changed no file; correct its shape, use 'new' for creation and read the final saved output."
            )
        if self.unchanged_targets:
            parts.append(
                "For EACH unchanged-file target: read_file, request exactly ONE identical write_file with its current revision, then read_file AGAIN after that request. Do not make any actual content change."
            )
        return " ".join(parts)


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
        if any(path_key(workspace, path) not in self.targets for path in checks.json_outputs):
            raise ValueError("JSON contracts must refer to declared output files")
        self.writes, self.readbacks, self.tools = {}, {}, set()
        self.sources = {path_key(workspace, path): path for path in checks.required_reads}
        self.read_sources = set()
        self.unchanged = {path_key(workspace, path): path for path in checks.unchanged_targets}
        self.unchanged_reads, self.unchanged_results, self.unchanged_readbacks = {}, {}, {}
        self.unchanged_counts, self.changed_unchanged = {}, set()

    def record(self, call, result, status):
        if status != "succeeded":
            return
        self.tools.add(call.name)
        if call.name not in ("read_file", "write_file"):
            return
        key = path_key(self.workspace, call.arguments["path"])
        if key in self.unchanged:
            digest = result.get("sha256")
            if call.name == "read_file":
                self.unchanged_reads[key] = digest
                previous = self.unchanged_results.get(key)
                if previous and previous[0] == digest and previous[1]:
                    self.unchanged_readbacks[key] = digest
            elif result.get("verified") is True:
                self.unchanged_readbacks.pop(key, None)
                if result.get("unchanged") is True:
                    self.unchanged_counts[key] = self.unchanged_counts.get(key, 0) + 1
                    self.unchanged_results[key] = (digest, self.unchanged_reads.get(key) == digest)
                else:
                    self.changed_unchanged.add(key)
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
        missing_unchanged = []
        for key, relative in self.unchanged.items():
            result = self.unchanged_results.get(key)
            valid = False
            if (
                result
                and result[1]
                and self.unchanged_counts.get(key) == 1
                and key not in self.changed_unchanged
            ):
                try:
                    valid = (
                        self.unchanged_readbacks.get(key)
                        == result[0]
                        == self.workspace.read(relative)["sha256"]
                    )
                except (OSError, ValueError, UnicodeError):
                    pass
            if not valid:
                missing_unchanged.append(relative)
        passed = (
            written == len(self.targets)
            and (not self.checks.require_readback or readback == len(self.targets))
            and not missing_sources
            and not missing_tools
            and not missing_unchanged
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
            "expected_unchanged_files": len(self.unchanged),
            "verified_unchanged_files": len(self.unchanged) - len(missing_unchanged),
            "missing_unchanged_files": len(missing_unchanged),
        }, {
            "unmet_targets": missing,
            "unmet_tools": sorted(missing_tools),
            "unread_sources": [self.sources[key] for key in sorted(missing_sources)],
            "unmet_unchanged_targets": missing_unchanged,
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
        "expected_unchanged_files",
        "verified_unchanged_files",
        "missing_unchanged_files",
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
