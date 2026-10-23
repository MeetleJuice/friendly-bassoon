"""Synthetic retrieval quality, freshness, boundary and registry regressions."""

import hashlib
import json
import os
import threading

import pytest
from pydantic import ValidationError

from aigentics import retrieval, tools
from aigentics.models import Agent, ToolCall, TOOLS
from aigentics.registry import TOOL_REGISTRY, TOOL_SPECS
from aigentics.tools import SCHEMAS, EXECUTORS, ToolRunner, Workspace, tool_definitions


def write(root, path, content):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def test_map_symbols_and_lexical_ranking_with_source_citations(tmp_path):
    source = "class Invoice:\n    def total_due(self):\n        return 42\n"
    write(tmp_path, "src/invoice.py", source)
    write(tmp_path, "notes.txt", "An invoice was mentioned in passing.\n")
    write(tmp_path, "web/client.ts", "export function loadInvoice() { return 1; }\n")
    ws, cancel = Workspace(tmp_path), threading.Event()
    mapped = retrieval.project_map(ws, cancel)
    files = {item["path"]: item for item in mapped["files"]}
    assert files["src/invoice.py"]["symbols"] == [
        {"name": "Invoice", "kind": "class", "line": 1},
        {"name": "total_due", "kind": "function", "line": 2},
    ]
    assert files["web/client.ts"]["symbols"][0]["name"] == "loadInvoice"
    result = retrieval.retrieve_context(ws, "invoice", cancel)
    snippet = result["snippets"][0]
    assert snippet["path"] == "src/invoice.py"
    assert snippet["line"] == 1 and snippet["end_line"] == 3
    assert snippet["sha256"] == hashlib.sha256(source.encode()).hexdigest()
    assert "class Invoice" in snippet["text"]
    assert result["scanned"]["files"] == 3
    assert result["scanned"]["bytes"] == sum(
        path.stat().st_size for path in tmp_path.rglob("*") if path.is_file()
    )


def test_retrieval_is_fresh_after_edit_rename_and_delete(tmp_path):
    path = write(tmp_path, "source.py", "def old_symbol():\n    return 1\n")
    ws, cancel = Workspace(tmp_path), threading.Event()
    before = retrieval.retrieve_context(ws, "old_symbol", cancel)["snippets"][0]
    path.write_text("def new_symbol():\n    return 2\n", encoding="utf-8")
    assert not retrieval.retrieve_context(ws, "old_symbol", cancel)["snippets"]
    after = retrieval.retrieve_context(ws, "new_symbol", cancel)["snippets"][0]
    assert before["sha256"] != after["sha256"]
    path.rename(tmp_path / "renamed.py")
    assert retrieval.retrieve_context(ws, "new_symbol", cancel)["snippets"][0]["path"] == "renamed.py"
    (tmp_path / "renamed.py").unlink()
    assert not retrieval.project_map(ws, cancel)["files"]


def test_context_validation_is_independent_of_map_display_prefix(tmp_path):
    for index in range(275):
        write(tmp_path, f"source_{index:03}.py", f"VALUE = {index}\n")
    write(tmp_path, "source_274.py", "def final_unique_symbol():\n    return 274\n")
    ws, cancel = Workspace(tmp_path), threading.Event()
    mapped = retrieval.project_map(ws, cancel)
    snippets = retrieval.retrieve_context(ws, "final_unique_symbol", cancel)["snippets"]
    assert len(mapped["files"]) == retrieval.MAX_MAP_FILES
    assert snippets[0]["path"] == "source_274.py"
    assert snippets[0]["path"] not in {item["path"] for item in mapped["files"]}
    assert retrieval.validate_snippets(ws, snippets, cancel) is None
    write(tmp_path, ".gitignore", "source_274.py\n")
    with pytest.raises(ValueError, match="ignored or unavailable"):
        retrieval.validate_snippets(ws, snippets, cancel)


def test_context_validation_rejects_changed_protected_linked_and_cancelled_sources(tmp_path):
    path = write(tmp_path, "src/code.py", "def marker():\n    return 1\n")
    ws, cancel = Workspace(tmp_path), threading.Event()
    snippets = retrieval.retrieve_context(ws, "marker", cancel)["snippets"]
    path.write_text("def marker():\n    return 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed or is unavailable"):
        retrieval.validate_snippets(ws, snippets, cancel)
    path.unlink()
    outside = write(tmp_path, "outside.py", "def marker():\n    return 1\n")
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("Filesystem does not support links")
    with pytest.raises(ValueError, match="ignored or unavailable"):
        retrieval.validate_snippets(ws, snippets, cancel)
    with pytest.raises(ValueError, match="ignored or unavailable"):
        retrieval.validate_snippets(ws, [snippets[0] | {"path": ".env"}], cancel)
    cancel.set()
    with pytest.raises(InterruptedError):
        retrieval.validate_snippets(ws, snippets, cancel)


def test_gitwildmatch_and_nested_application_ignore_boundaries(tmp_path):
    write(tmp_path, ".gitignore", "*.log\n/root-only.txt\ncache/\n!keep.log\nsecret[0-9].txt\n")
    write(tmp_path, ".aigenticsignore", "private/**\n")
    write(tmp_path, "src/.gitignore", "*.txt\n!public.txt\n")
    for path in [
        "debug.log",
        "root-only.txt",
        "cache/hidden.py",
        "secret3.txt",
        "private/key.py",
        "src/hidden.txt",
    ]:
        write(tmp_path, path, "hidden_marker\n")
    for path in ["keep.log", "src/public.txt", "src/root-only.txt", "src/app.py"]:
        write(tmp_path, path, "visible_marker\n")
    # An ancestor git exclusion cannot be bypassed by a different ignore family.
    write(tmp_path, "src/.aigenticsignore", "!hidden.txt\n")
    ws, cancel = Workspace(tmp_path), threading.Event()
    paths = {item["path"] for item in retrieval.project_map(ws, cancel)["files"]}
    assert paths == {"keep.log", "src/public.txt", "src/app.py"}
    assert not retrieval.retrieve_context(ws, "hidden_marker", cancel)["snippets"]
    assert len(retrieval.retrieve_context(ws, "visible_marker", cancel)["snippets"]) == 3


def test_ignore_comments_escaped_names_double_star_and_negation(tmp_path):
    write(tmp_path, ".gitignore", "# comment\n\\#private.txt\n**/generated/*.py\n*.txt\n!important.txt\n")
    for path in ["#private.txt", "notes.txt", "pkg/generated/x.py"]:
        write(tmp_path, path, "hidden\n")
    for path in ["important.txt", "pkg/source.py"]:
        write(tmp_path, path, "visible\n")
    result = retrieval.project_map(Workspace(tmp_path), threading.Event())
    assert {item["path"] for item in result["files"]} == {"important.txt", "pkg/source.py"}


def test_protected_files_links_and_binary_never_enter_context(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    outside = write(tmp_path, "outside.txt", "private_marker\n")
    for path in [".env", ".env.production", ".aws/config", ".git/config", "id_ed25519", "key.pem", "key.key"]:
        write(root, path, "private_marker\n")
    write(root, "public.py", "def public_marker():\n    pass\n")
    (root / "binary.txt").write_bytes(b"private_marker\x00")
    try:
        (root / "link.txt").symlink_to(outside)
        (root / "hard.txt").hardlink_to(outside)
        (root / "linked_dir").symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("Filesystem does not support links")
    ws, cancel = Workspace(root), threading.Event()
    assert not retrieval.retrieve_context(ws, "private_marker", cancel)["snippets"]
    paths = {item["path"] for item in retrieval.project_map(ws, cancel)["files"]}
    assert paths == {"public.py", "binary.txt"}


@pytest.mark.parametrize("ignore_content", ["x" * (retrieval.MAX_IGNORE_BYTES + 1), "\xff"])
def test_unreadable_or_oversized_ignore_fails_closed(tmp_path, ignore_content):
    write(tmp_path, "safe.py", "public_marker\n")
    ignore = write(tmp_path, "private/.gitignore", ignore_content)
    if ignore_content == "\xff":
        ignore.write_bytes(b"\xff")
    write(tmp_path, "private/secret.txt", "private_marker\n")
    result = retrieval.retrieve_context(Workspace(tmp_path), "marker", threading.Event())
    assert {item["path"] for item in result["snippets"]} == {"safe.py"}
    assert result["truncated"]


def test_linked_ignore_fails_closed_for_subtree(tmp_path):
    outside = write(tmp_path, "outside.ignore", "secret.txt\n")
    root = tmp_path / "project"
    write(root, "private/secret.txt", "private_marker\n")
    try:
        (root / "private/.gitignore").symlink_to(outside)
    except OSError:
        pytest.skip("Filesystem does not support links")
    result = retrieval.retrieve_context(Workspace(root), "private_marker", threading.Event())
    assert not result["snippets"] and result["truncated"]


def test_character_result_file_and_byte_budgets(tmp_path, monkeypatch):
    for index in range(8):
        write(tmp_path, f"source{index}.py", f"def marker_{index}():\n    return '{'a' * 100}'\n")
    ws, cancel = Workspace(tmp_path), threading.Event()
    limited = retrieval.retrieve_context(ws, "marker", cancel, max_chars=31)
    assert sum(len(snippet["text"]) for snippet in limited["snippets"]) <= 31
    assert limited["truncated"]
    monkeypatch.setattr(retrieval, "MAX_FILES", 3)
    result = retrieval.retrieve_context(ws, "marker", cancel)
    assert result["scanned"]["files"] == 3 and result["truncated"]
    monkeypatch.setattr(retrieval, "MAX_FILES", 100)
    monkeypatch.setattr(retrieval, "MAX_BYTES", 150)
    result = retrieval.retrieve_context(ws, "marker", cancel)
    assert result["scanned"]["bytes"] <= 150 and result["truncated"]


def test_entry_directory_map_and_ignore_rule_budgets(tmp_path, monkeypatch):
    for index in range(6):
        write(tmp_path, f"dir{index}/code.py", "def marker():\n    pass\n")
    ws, cancel = Workspace(tmp_path), threading.Event()
    monkeypatch.setattr(retrieval, "MAX_DIRECTORIES", 2)
    result = retrieval.project_map(ws, cancel)
    assert result["scanned"]["directories"] == 2 and result["truncated"]
    monkeypatch.setattr(retrieval, "MAX_DIRECTORIES", 100)
    monkeypatch.setattr(retrieval, "MAX_ENTRIES", 3)
    result = retrieval.project_map(ws, cancel)
    assert result["scanned"]["entries"] <= 3 and result["truncated"]
    monkeypatch.setattr(retrieval, "MAX_ENTRIES", 100)
    monkeypatch.setattr(retrieval, "MAX_MAP_FILES", 2)
    result = retrieval.project_map(ws, cancel)
    assert len(result["files"]) == 2 and result["truncated"]
    write(tmp_path, ".gitignore", "secret.txt\n" * 3)
    monkeypatch.setattr(retrieval, "MAX_IGNORE_RULES", 2)
    result = retrieval.project_map(ws, cancel)
    assert not result["files"] and result["truncated"]


def test_failed_content_reads_and_ignore_matching_consume_budgets(tmp_path, monkeypatch):
    for index in range(4):
        (tmp_path / f"binary{index}.txt").write_bytes(b"\x00" * 50)
    monkeypatch.setattr(retrieval, "MAX_BYTES", 100)
    result = retrieval.retrieve_context(Workspace(tmp_path), "marker", threading.Event())
    assert result["scanned"]["bytes"] == 100 and result["truncated"]
    assert result["scanned"]["files"] < 4
    monkeypatch.setattr(retrieval, "MAX_BYTES", 200_000)
    write(tmp_path, ".gitignore", "secret.txt\n")
    write(tmp_path, "safe.py", "marker\n")
    monkeypatch.setattr(retrieval, "MAX_IGNORE_MATCHES", 1)
    result = retrieval.retrieve_context(Workspace(tmp_path), "marker", threading.Event())
    assert result["truncated"]


def test_complex_wildcards_fail_closed_without_regex_backtracking(tmp_path):
    write(tmp_path, ".gitignore", "*a" * 20 + "b\n")
    write(tmp_path, "a" * 40, "private_marker\n")
    result = retrieval.retrieve_context(Workspace(tmp_path), "private_marker", threading.Event())
    assert not result["snippets"] and result["truncated"]


def test_common_double_star_segments_and_matching_work_budget(tmp_path, monkeypatch):
    write(tmp_path, ".gitignore", "*.sqlite*\n*test*.py\n")
    write(tmp_path, "cache.sqlite-wal", "private_marker\n")
    write(tmp_path, "my_test_helper.py", "private_marker\n")
    write(tmp_path, "app.py", "public_marker\n")
    ws, cancel = Workspace(tmp_path), threading.Event()
    result = retrieval.project_map(ws, cancel)
    assert {item["path"] for item in result["files"]} == {"app.py"}
    monkeypatch.setattr(retrieval, "MAX_IGNORE_WORK", 1)
    result = retrieval.project_map(ws, cancel)
    assert not result["files"] and result["truncated"]


def test_cancellation_before_and_during_traversal(tmp_path):
    write(tmp_path, "source.py", "marker\n" * 100)
    cancel = threading.Event()
    cancel.set()
    for operation in [
        lambda: retrieval.project_map(Workspace(tmp_path), cancel),
        lambda: retrieval.retrieve_context(Workspace(tmp_path), "marker", cancel),
    ]:
        with pytest.raises(InterruptedError):
            operation()

    class CancelAfterRead(Workspace):
        def read(self, relative, **kwargs):
            value = super().read(relative, **kwargs)
            cancel.set()
            return value

    cancel.clear()
    with pytest.raises(InterruptedError):
        retrieval.retrieve_context(CancelAfterRead(tmp_path), "marker", cancel)


def test_nonregular_file_does_not_block_retrieval(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO fixture requires POSIX")
    os.mkfifo(tmp_path / "pipe")
    write(tmp_path, "code.py", "marker\n")
    ws, cancel = Workspace(tmp_path), threading.Event()
    assert retrieval.retrieve_context(ws, "marker", cancel)["snippets"][0]["path"] == "code.py"
    with pytest.raises(ValueError, match="regular"):
        ws.read("pipe")


def test_registry_schema_and_all_execution_routes_agree(tmp_path, monkeypatch):
    assert tuple(spec.name for spec in TOOL_SPECS) == TOOLS
    assert set(TOOLS) == set(TOOL_REGISTRY) == set(SCHEMAS) == set(EXECUTORS)
    assert all(spec.read_only == (spec.permission == "read") for spec in TOOL_SPECS)
    old = ["list_files", "read_file", "search", "write_file", "run_command"]
    assert Agent.model_validate({"tools": old}).tools == old
    write(tmp_path, "code.py", "def marker():\n    pass\n")
    monkeypatch.setattr(tools, "run_command", lambda *args: {"execution": "command"})
    approvals = []
    runner = ToolRunner(
        Workspace(tmp_path),
        Agent(allow_commands=True),
        lambda name, args: approvals.append(name) or True,
        threading.Event(),
    )
    arguments = {
        "list_files": {},
        "read_file": {"path": "code.py"},
        "search": {"query": "marker"},
        "write_file": {"path": "new.txt", "content": "test", "expected_sha256": "new"},
        "run_command": {"argv": ["never-executed"]},
        "project_map": {},
        "retrieve_context": {"query": "marker"},
    }
    for name in TOOLS:
        assert isinstance(runner.execute(ToolCall(id=name, name=name, arguments=arguments[name])), dict)
    assert approvals == ["write_file", "run_command"]
    with pytest.raises(PermissionError):
        runner.execute(ToolCall(id="bad", name="imaginary", arguments={}))
    with pytest.raises(ValidationError):
        runner.execute(ToolCall(id="bad", name="project_map", arguments={"execute": "anything"}))
    with pytest.raises(ValidationError):
        runner.execute(
            ToolCall(id="bad", name="retrieve_context", arguments={"query": "marker", "max_chars": 999999})
        )
    # Advertised descriptions and permissions use the same registry as the UI.
    definitions = tool_definitions(Agent(allow_writes=False, allow_commands=False))
    assert {definition["function"]["name"] for definition in definitions} == {
        spec.name for spec in TOOL_SPECS if spec.read_only
    }
    assert all(
        item["function"]["description"] == TOOL_REGISTRY[item["function"]["name"]].description
        for item in definitions
    )
    assert "project_map" in json.dumps(definitions)


@pytest.mark.parametrize("query,max_chars", [("", 6000), ("x" * 201, 6000), ("x", 0), ("x", True)])
def test_retrieval_validates_bounds(tmp_path, query, max_chars):
    with pytest.raises(ValueError):
        retrieval.retrieve_context(Workspace(tmp_path), query, threading.Event(), max_chars)
