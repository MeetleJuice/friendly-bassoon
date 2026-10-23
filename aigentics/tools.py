"""Workspace file tools and explicitly approved, bounded host commands."""

import difflib
import hashlib
import os
import queue
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Annotated
from pydantic import Field, field_validator
from .models import Strict

BLOCKED = {".git", ".venv", "node_modules", "__pycache__", ".aws", ".ssh", ".gnupg"}
MAX_FILE = 100_000


class PathArgs(Strict):
    path: str = Field(min_length=1, max_length=1000)


class ListArgs(Strict):
    path: str = Field(default=".", max_length=1000)


class SearchArgs(Strict):
    query: str = Field(min_length=1, max_length=200)


class WriteArgs(PathArgs):
    content: str = Field(max_length=MAX_FILE)
    expected_sha256: str = Field(
        description="SHA256 returned by read_file, or 'new' when creating a file",
        pattern=r"^(new|[a-f0-9]{64})$",
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
}
DESCRIPTIONS = {
    "list_files": "List immediate children of a project directory; sensitive files and symlinks are hidden.",
    "read_file": "Read a UTF-8 project file, returning its SHA256 for safe edit review.",
    "search": "Search literal text in project UTF-8 files (bounded traversal and results).",
    "write_file": "Propose full UTF-8 file content. Requires prior SHA256 and explicit user approval of its diff.",
    "run_command": "Propose argv for a host process. Always requires user approval. No implicit shell.",
}


def tool_definitions(agent):
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": DESCRIPTIONS[name],
                "parameters": SCHEMAS[name].model_json_schema(),
            },
        }
        for name in agent.tools
        if (name != "write_file" or agent.allow_writes) and (name != "run_command" or agent.allow_commands)
    ]


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
            if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
                raise PermissionError("Symlinks and directory junctions are not accessible")
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.root):
            raise PermissionError("Path escapes the workspace")
        return resolved

    def read(self, relative):
        path = self.path(relative)
        if path.stat().st_size > MAX_FILE:
            raise ValueError("File exceeds 100 KB limit")
        if path.stat().st_nlink > 1:
            raise PermissionError("Hard-linked files are not accessible")
        raw = path.read_bytes()
        if len(raw) > MAX_FILE or b"\0" in raw:
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
                raise ValueError("File changed or expected hash is incorrect; read it again")
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

    def execute(self, call):
        if call.name not in self.agent.tools or call.name not in SCHEMAS:
            raise PermissionError("Agent does not have this tool")
        args = SCHEMAS[call.name].model_validate(call.arguments)
        if self.cancel.is_set():
            raise InterruptedError("Cancelled")
        if call.name == "write_file":
            if not self.agent.allow_writes:
                raise PermissionError("Writes disabled for this agent")
            diff = self.workspace.prepare_write(args)
            if not self.approve("write_file", {"path": args.path, "diff": diff}):
                raise PermissionError("User denied file change")
            if self.cancel.is_set():
                raise InterruptedError("Cancelled")
            return self.workspace.write(args)
        if call.name == "run_command":
            if not self.agent.allow_commands:
                raise PermissionError("Commands disabled for this agent")
            if not self.approve("run_command", args.model_dump() | {"cwd": str(self.workspace.root)}):
                raise PermissionError("User denied command")
            if self.cancel.is_set():
                raise InterruptedError("Cancelled")
            return run_command(self.workspace.root, args, self.cancel)
        if call.name == "list_files":
            return self.workspace.listing(args.path)
        if call.name == "read_file":
            return self.workspace.read(args.path)
        return self.workspace.search(args.query, self.cancel)
