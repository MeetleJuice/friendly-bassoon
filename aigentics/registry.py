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
        "Propose full UTF-8 content. Read existing files first and use expected_sha256='last_read' "
        "or the exact returned SHA256; use 'new' for creation. Every diff requires approval. "
        "Python writes get static checks, never automatic execution.",
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
