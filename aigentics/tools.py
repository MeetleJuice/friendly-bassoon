"""Workspace file tools and explicitly approved, bounded host commands."""

import difflib
import hashlib
import os
import queue
import signal
import stat
import subprocess
import threading
import time
from pathlib import Path
from typing import Annotated
from pydantic import Field, field_validator
from .models import Strict
from .registry import TOOL_REGISTRY
from .retrieval import project_map, retrieve_context, MAX_CONTEXT_CHARS
from .verification import check_python


class StaleFileError(ValueError):
    """The proposed revision does not match the actual file."""


BLOCKED = {".git", ".venv", "node_modules", "__pycache__", ".aws", ".ssh", ".gnupg"}
MAX_FILE = 100_000


class PathArgs(Strict):
    path: str = Field(min_length=1, max_length=1000)


class ListArgs(Strict):
    path: str = Field(default=".", max_length=1000)


class SearchArgs(Strict):
    query: str = Field(min_length=1, max_length=200)


class MapArgs(Strict):
    pass


class RetrieveArgs(SearchArgs):
    max_chars: int = Field(default=6000, ge=1, le=MAX_CONTEXT_CHARS)


class WriteArgs(PathArgs):
    content: str = Field(max_length=MAX_FILE)
    expected_sha256: str = Field(
        description="Use 'last_read' after read_file in this run, its exact SHA256, or 'new' for creation",
        pattern=r"^(new|last_read|[a-f0-9]{64})$",
    )

    @field_validator("content")
    @classmethod
    def bounded_utf8(cls, value):
        if len(value.encode("utf-8")) > MAX_FILE or "\0" in value:
            raise ValueError("Content must be UTF-8 text of at most 100 KB without NUL bytes")
        return value


class CommandArgs(Strict):
    argv: list[Annotated[str, Field(min_length=1, max_length=4000)]] = Field(min_length=1, max_length=40)
    timeout_seconds: int = Field(default=30, ge=1, le=120)


SCHEMAS = {
    "list_files": ListArgs,
    "read_file": PathArgs,
    "search": SearchArgs,
    "write_file": WriteArgs,
    "run_command": CommandArgs,
    "project_map": MapArgs,
    "retrieve_context": RetrieveArgs,
}
DESCRIPTIONS = {name: spec.description for name, spec in TOOL_REGISTRY.items()}


def tool_definitions(agent):
    definitions = []
    for name in agent.tools:
        if name not in TOOL_REGISTRY:
            raise PermissionError("Unknown tool")
        spec = TOOL_REGISTRY[name]
        if (spec.permission == "write" and not agent.allow_writes) or (
            spec.permission == "command" and not agent.allow_commands
        ):
            continue
        definitions.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": spec.description,
                    "parameters": SCHEMAS[name].model_json_schema(),
                },
            }
        )
    return definitions


def sensitive(part):
    lowered = part.lower()
    stem = lowered.split(".")[0]
    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *[f"com{i}" for i in range(1, 10)],
        *[f"lpt{i}" for i in range(1, 10)],
    }
    return (
        ":" in part
        or "\0" in part
        or (part not in (".", "..") and part.endswith((".", " ")))
        or stem in reserved
        or lowered in BLOCKED
        or lowered.startswith(".env")
        or lowered in {"credentials", "credentials.json", "id_rsa", "id_ed25519"}
        or lowered.endswith((".pem", ".key"))
    )


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Workspace must be a directory")

    def path(self, relative):
        path = Path(relative)
        if path.is_absolute() or any(p == ".." or sensitive(p) for p in path.parts):
            raise PermissionError("Path is outside the workspace or is protected")
        candidate = self.root / path
        for part in [candidate, *candidate.parents]:
            if part == self.root:
                break
            reparse = False
            if os.name == "nt":
                try:
                    reparse = bool(part.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
                except FileNotFoundError:
                    pass
            if part.is_symlink() or reparse or (hasattr(part, "is_junction") and part.is_junction()):
                raise PermissionError("Symlinks and directory junctions are not accessible")
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.root):
            raise PermissionError("Path escapes the workspace")
        return resolved

    def read(self, relative, max_bytes=MAX_FILE):
        path = self.path(relative)
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or not 1 <= max_bytes <= MAX_FILE:
            raise ValueError("Invalid read limit")
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Only regular project files are accessible")
        if info.st_nlink > 1:
            raise PermissionError("Hard-linked files are not accessible")
        if info.st_size > max_bytes:
            raise ValueError("File exceeds read limit")
        # A capped read also bounds files that grow after the metadata check.
        # O_NONBLOCK avoids hanging on a replaced FIFO; fstat checks the opened
        # object. Parent-directory races are not an OS security sandbox.
        flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        with os.fdopen(os.open(path, flags), "rb", buffering=0) as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("Only regular project files are accessible")
            if info.st_nlink > 1:
                raise PermissionError("Hard-linked files are not accessible")
            if info.st_size > max_bytes:
                raise ValueError("File exceeds read limit")
            raw = stream.read(max_bytes)
            if os.fstat(stream.fileno()).st_size > max_bytes:
                raise ValueError("File exceeds read limit")
        if len(raw) > max_bytes or b"\0" in raw:
            raise ValueError("File is too large or binary")
        return {"path": relative, "content": raw.decode("utf-8"), "sha256": hashlib.sha256(raw).hexdigest()}

    def listing(self, relative="."):
        children = []
        for i, path in enumerate(self.path(relative).iterdir()):
            if i >= 2000:
                break
            try:
                self.path(str(path.relative_to(self.root)))
            except PermissionError:
                continue
            children.append({"name": path.name, "directory": path.is_dir()})
        return {"entries": sorted(children, key=lambda x: (not x["directory"], x["name"]))[:500]}

    def search(self, query, cancel):
        matches, examined = [], 0
        for root, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = [d for d in dirs if not sensitive(d) and not (Path(root) / d).is_symlink()]
            for name in files:
                if cancel.is_set():
                    raise InterruptedError("Cancelled")
                examined += 1
                if examined > 2000:
                    return {"matches": matches, "truncated": True}
                rel = str((Path(root) / name).relative_to(self.root))
                try:
                    text = self.read(rel)["content"]
                except (OSError, ValueError, UnicodeError):
                    continue
                for number, line in enumerate(text.splitlines(), 1):
                    if query in line:
                        matches.append({"path": rel, "line": number, "text": line[:500]})
                        if len(matches) >= 100:
                            return {"matches": matches, "truncated": True}
        return {"matches": matches, "truncated": False}

    def prepare_write(self, args):
        path = self.path(args.path)
        if path.exists():
            old = self.read(args.path)
            if old["sha256"] != args.expected_sha256:
                raise StaleFileError(
                    "File changed or expected hash is incorrect; read it again and use 'last_read'"
                )
            before = old["content"]
        else:
            if args.expected_sha256 != "new":
                raise ValueError("File no longer exists; use 'new' only for creation")
            before = ""
        diff = "".join(
            difflib.unified_diff(
                before.splitlines(True),
                args.content.splitlines(True),
                fromfile=args.path + " (current)",
                tofile=args.path + " (proposed)",
            )
        )
        return diff or "No content changes"

    def write(self, args):
        self.prepare_write(args)  # Recheck after review; reject stale edits.
        path = self.path(args.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if args.expected_sha256 == "new":
            with path.open("x", encoding="utf-8", newline="") as stream:
                stream.write(args.content)
        else:
            # In-place writes preserve permissions. This is not an OS security sandbox.
            with path.open("w", encoding="utf-8", newline="") as stream:
                stream.write(args.content)
        verified = self.read(args.path)
        return {
            "path": args.path,
            "sha256": verified["sha256"],
            "bytes": path.stat().st_size,
            "verified": verified["content"] == args.content,
        }


def stop_process(process):
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=5)


def run_command(root, args, cancel):
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper()
        in {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "PATHEXT",
            "TEMP",
            "TMP",
            "HOME",
            "USERPROFILE",
            "LANG",
        }
    }
    options = (
        {"start_new_session": True}
        if os.name != "nt"
        else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
    )
    process = subprocess.Popen(
        args.argv,
        cwd=root,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        **options,
    )
    output_queue = queue.Queue(maxsize=16)
    reader_stop = threading.Event()

    def read_output():
        try:
            while not reader_stop.is_set():
                chunk = process.stdout.read1(2048)
                if not chunk:
                    break
                while not reader_stop.is_set():
                    try:
                        output_queue.put(chunk, timeout=0.1)
                        break
                    except queue.Full:
                        pass
        finally:
            process.stdout.close()

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    started, output, reason = time.monotonic(), bytearray(), "exited"
    try:
        while process.poll() is None or reader.is_alive() or not output_queue.empty():
            if cancel.is_set():
                reason = "cancelled"
                break
            if time.monotonic() - started > args.timeout_seconds:
                reason = "timeout"
                break
            try:
                output.extend(output_queue.get(timeout=0.05))
            except queue.Empty:
                continue
            if len(output) > 32000:
                reason = "output_limit"
                break
    finally:
        reader_stop.set()
        if process.poll() is None or reason != "exited":
            stop_process(process)
        reader.join(timeout=1)
    return {
        "argv": args.argv,
        "exit_code": process.returncode,
        "reason": reason,
        "output": bytes(output[:32000]).decode("utf-8", errors="replace"),
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


class ToolRunner:
    def __init__(self, workspace, agent, approve, cancel):
        self.workspace, self.agent, self.approve, self.cancel = workspace, agent, approve, cancel
        self._read_revisions = {}

    def execute(self, call):
        if call.name not in self.agent.tools or call.name not in EXECUTORS:
            raise PermissionError("Agent does not have this tool")
        args = SCHEMAS[call.name].model_validate(call.arguments)
        if self.cancel.is_set():
            raise InterruptedError("Cancelled")
        result = EXECUTORS[call.name](self, args)
        if call.name == "read_file":
            self._read_revisions[str(self.workspace.path(args.path))] = result["sha256"]
        return result

    def _write_file(self, args):
        if not self.agent.allow_writes:
            raise PermissionError("Writes disabled for this agent")
        if args.expected_sha256 == "last_read":
            revision = self._read_revisions.get(str(self.workspace.path(args.path)))
            if not revision:
                raise StaleFileError("Read this file in the current run before using 'last_read'")
            args = args.model_copy(update={"expected_sha256": revision})
        diff = self.workspace.prepare_write(args)
        if not self.approve("write_file", {"path": args.path, "diff": diff}):
            raise PermissionError("User denied file change")
        if self.cancel.is_set():
            raise InterruptedError("Cancelled")
        result = self.workspace.write(args)
        if args.path.lower().endswith(".py"):
            result["python_check"] = check_python(self.workspace, args.path)
            if result["python_check"]["sha256"] != result["sha256"]:
                result["python_check"].update(status="failed", code="CHECK_REVISION_CHANGED")
        return result

    def _run_command(self, args):
        if not self.agent.allow_commands:
            raise PermissionError("Commands disabled for this agent")
        if not self.approve("run_command", args.model_dump() | {"cwd": str(self.workspace.root)}):
            raise PermissionError("User denied command")
        if self.cancel.is_set():
            raise InterruptedError("Cancelled")
        return run_command(self.workspace.root, args, self.cancel)


EXECUTORS = {
    "list_files": lambda runner, args: runner.workspace.listing(args.path),
    "read_file": lambda runner, args: runner.workspace.read(args.path),
    "search": lambda runner, args: runner.workspace.search(args.query, runner.cancel),
    "write_file": ToolRunner._write_file,
    "run_command": ToolRunner._run_command,
    "project_map": lambda runner, args: project_map(runner.workspace, runner.cancel),
    "retrieve_context": lambda runner, args: retrieve_context(
        runner.workspace, args.query, runner.cancel, args.max_chars
    ),
}
if set(TOOL_REGISTRY) != set(SCHEMAS) or set(SCHEMAS) != set(EXECUTORS):
    raise RuntimeError("Registered tool metadata, schemas and execution routes must match")
