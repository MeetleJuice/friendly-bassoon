"""Inspectable tool metadata, independent of models, UI and execution code."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str
    description: str
    permission: Literal["read", "write", "command"]
    read_only: bool


TOOL_SPECS = (
    ToolSpec(
        "list_files",
        "List files",
        "List immediate children of a project directory; sensitive files and symlinks are hidden.",
        "read",
        True,
    ),
    ToolSpec(
        "read_file",
        "Read file",
        "Read a UTF-8 project file, returning its SHA256 for safe edit review.",
        "read",
        True,
    ),
    ToolSpec(
        "search",
        "Search text",
        "Search literal text in project UTF-8 files (bounded traversal and results).",
        "read",
        True,
    ),
    ToolSpec(
        "write_file",
        "Write file",
        "Propose full UTF-8 file content. Requires prior SHA256 and explicit user approval of its diff.",
        "write",
        False,
    ),
    ToolSpec(
        "run_command",
        "Run command",
        "Propose argv for a host process. Always requires user approval. No implicit shell.",
        "command",
        False,
    ),
    ToolSpec(
        "project_map",
        "Map project",
        "Inspect a bounded, ignore-aware project file and source-symbol map without saving file contents.",
        "read",
        True,
    ),
    ToolSpec(
        "retrieve_context",
        "Retrieve context",
        "Find bounded lexical source snippets with project paths, line numbers and current SHA256 citations. "
        "Respects protected paths, links and project ignore files; no embedding or provider request.",
        "read",
        True,
    ),
)
TOOL_REGISTRY = MappingProxyType({spec.name: spec for spec in TOOL_SPECS})
TOOLS = tuple(TOOL_REGISTRY)
