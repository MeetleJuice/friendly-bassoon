"""Bounded, fresh lexical retrieval. No file contents or source index are persisted.

Each directory's .gitignore and .aigenticsignore use gitwildmatch rules, including
negation and directory pruning. The two ignore families are independent: a git
negation cannot override an application exclusion. Global Git configuration and
the Git index are not consulted. Unreadable or over-budget ignore rules exclude
their subtree, rather than silently exposing files those rules may protect.
For predictable regex work, a rule may have one ** directory segment and two *
per other segment; more complex wildcard rules also exclude their subtree.
Pattern matching also has a cumulative work allowance, including a quadratic
charge for segments containing two stars.
"""

import ast
import os
import re
import stat
from pathlib import PurePosixPath

from pathspec import GitIgnoreSpec

MAX_DIRECTORIES = 128
MAX_ENTRIES = 6000
MAX_FILES = 1000
MAX_BYTES = 2_000_000
MAX_FILE_BYTES = 100_000
MAX_IGNORE_BYTES = 16_000
MAX_IGNORE_RULES = 1000
MAX_IGNORE_MATCHES = 50_000
MAX_IGNORE_WORK = 20_000_000
MAX_PATH_CHARS = 512
MAX_MAP_FILES = 250
MAX_MAP_CHARS = 40_000
MAX_SYMBOLS_PER_FILE = 12
MAX_SNIPPETS = 12
MAX_CONTEXT_CHARS = 12_000
IGNORE_NAMES = (".gitignore", ".aigenticsignore")
SOURCE_SUFFIXES = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".cs",
}
DECLARATION = re.compile(
    r"^\s*(?:(?:export|default|public|private|protected|static|async|pub)\s+)*"
    r"(?P<kind>class|interface|function|def|struct|enum|trait|fn|func)\s+(?P<name>[A-Za-z_][\w$]{0,119})"
)


def _check_cancel(cancel):
    if cancel.is_set():
        raise InterruptedError("Cancelled")


class _Scan:
    def __init__(self, workspace, cancel):
        self.workspace, self.cancel = workspace, cancel
        self.scanned = {"directories": 0, "entries": 0, "files": 0, "bytes": 0}
        self.truncated = False
        self.ignore_rules = 0
        self.ignore_matches = 0
        self.ignore_work = 0
        self.exhausted = False

    def read(self, relative, limit=MAX_FILE_BYTES):
        _check_cancel(self.cancel)
        remaining = MAX_BYTES - self.scanned["bytes"]
        if remaining <= 0:
            self.truncated = self.exhausted = True
            return None
        try:
            path = self.workspace.path(relative)
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1:
                return None
            if info.st_size > limit:
                return None
            if info.st_size > remaining:
                self.truncated = self.exhausted = True
                return None
            read_limit = min(limit, remaining)
            # Failed binary/UTF-8 reads consume the same I/O budget. Reserve the
            # maximum attempted read, refunding unused bytes only on success.
            self.scanned["bytes"] += read_limit
            value = self.workspace.read(relative, max_bytes=read_limit)
        except (OSError, ValueError, UnicodeError):
            return None
        self.scanned["bytes"] -= read_limit - len(value["content"].encode("utf-8"))
        _check_cancel(self.cancel)
        return value

    def rules(self, directory, inherited):
        result = list(inherited)
        for name in IGNORE_NAMES:
            _check_cancel(self.cancel)
            relative = f"{directory}/{name}" if directory else name
            try:
                path = self.workspace.path(relative)
                # lstat distinguishes an absent ignore file from a broken link.
                path.lstat()
            except FileNotFoundError:
                continue
            except OSError:
                self.truncated = True
                return None
            value = self.read(relative, MAX_IGNORE_BYTES)
            if value is None:
                self.truncated = True
                return None
            lines = value["content"].splitlines()
            if self.ignore_rules + len(lines) > MAX_IGNORE_RULES:
                self.truncated = True
                return None
            self.ignore_rules += len(lines)
            quadratic = 0
            for line in lines:
                if not line or line.startswith("#"):
                    continue
                parts = line.split("/")
                if (
                    len(line) > MAX_PATH_CHARS
                    or parts.count("**") > 1
                    or any(part != "**" and part.count("*") > 2 for part in parts)
                ):
                    self.truncated = True
                    return None
                quadratic += any(part != "**" and part.count("*") == 2 for part in parts)
            try:
                spec = GitIgnoreSpec.from_lines(lines)
            except (ValueError, re.error):
                self.truncated = True
                return None
            result.append((directory, name, spec, quadratic))
        return result

    def ignored(self, relative, directory, rules):
        ignored = dict.fromkeys(IGNORE_NAMES, False)
        for base, family, spec, quadratic in rules:
            _check_cancel(self.cancel)
            self.ignore_matches += len(spec.patterns)
            if self.ignore_matches > MAX_IGNORE_MATCHES:
                self.truncated = self.exhausted = True
                return True
            local = relative[len(base) + 1 :] if base else relative
            self.ignore_work += (len(spec.patterns) - quadratic) * (len(local) + 1) + quadratic * (
                len(local) + 1
            ) ** 2
            if self.ignore_work > MAX_IGNORE_WORK:
                self.truncated = self.exhausted = True
                return True
            match = spec.check_file(local + ("/" if directory else ""))
            if match.include is not None:
                ignored[family] = match.include
        return any(ignored.values())

    def files(self):
        pending = [("", ())]
        while pending and not self.exhausted:
            _check_cancel(self.cancel)
            if self.scanned["directories"] >= MAX_DIRECTORIES:
                self.truncated = True
                break
            directory, inherited = pending.pop()
            try:
                root = self.workspace.path(directory or ".")
            except OSError:
                continue
            rules = self.rules(directory, inherited)
            if rules is None:
                continue
            self.scanned["directories"] += 1
            entries = []
            entry_limit = False
            try:
                with os.scandir(root) as stream:
                    for entry in stream:
                        _check_cancel(self.cancel)
                        if self.scanned["entries"] >= MAX_ENTRIES:
                            self.truncated = entry_limit = True
                            break
                        self.scanned["entries"] += 1
                        entries.append(entry.name)
            except OSError:
                continue
            children = []
            for name in sorted(entries):
                _check_cancel(self.cancel)
                relative = f"{directory}/{name}" if directory else name
                if len(relative) > MAX_PATH_CHARS:
                    self.truncated = True
                    continue
                try:
                    path = self.workspace.path(relative)
                    info = path.stat()
                    is_directory = stat.S_ISDIR(info.st_mode)
                    if self.ignored(relative, is_directory, rules):
                        continue
                    if is_directory:
                        children.append((relative, rules))
                        continue
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1 or name in IGNORE_NAMES:
                        continue
                except OSError:
                    continue
                if self.scanned["files"] >= MAX_FILES:
                    self.truncated = self.exhausted = True
                    break
                self.scanned["files"] += 1
                yield relative, info.st_size
                if self.exhausted:
                    break
            pending.extend(reversed(children))
            if entry_limit:
                self.exhausted = True


def _symbols(path, text, cancel):
    suffix = PurePosixPath(path).suffix.lower()
    if suffix not in SOURCE_SUFFIXES:
        return []
    symbols = []
    if suffix in {".py", ".pyi"}:
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError, RecursionError):
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                _check_cancel(cancel)
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(
                        {
                            "name": node.name[:120],
                            "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                            "line": node.lineno,
                        }
                    )
                    if len(symbols) >= MAX_SYMBOLS_PER_FILE:
                        break
            return sorted(symbols, key=lambda item: item["line"])
    for number, line in enumerate(text.splitlines(), 1):
        _check_cancel(cancel)
        match = DECLARATION.match(line)
        if match:
            symbols.append({"name": match["name"], "kind": match["kind"], "line": number})
            if len(symbols) >= MAX_SYMBOLS_PER_FILE:
                break
    return symbols


def project_map(workspace, cancel):
    """Return bounded file metadata and optional source declarations, read fresh."""
    scan, files, characters = _Scan(workspace, cancel), [], 0
    for path, size in scan.files():
        if len(files) >= MAX_MAP_FILES:
            scan.truncated = True
            break
        symbols = []
        if PurePosixPath(path).suffix.lower() in SOURCE_SUFFIXES:
            value = scan.read(path)
            if value is not None:
                symbols = _symbols(path, value["content"], cancel)
        cost = len(path) + sum(len(symbol["name"]) + len(symbol["kind"]) + 24 for symbol in symbols) + 40
        if characters + cost > MAX_MAP_CHARS:
            scan.truncated = True
            break
        characters += cost
        files.append({"path": path, "bytes": size, "symbols": symbols})
    _check_cancel(cancel)
    return {"files": files, "scanned": scan.scanned, "truncated": scan.truncated}


def _candidates(path, value, query, terms, cancel):
    lines = value["content"].splitlines()
    lowered_path = path.casefold()
    path_score = 4 * sum(term in lowered_path for term in terms) + (8 if query in lowered_path else 0)
    matches = []
    for index, line in enumerate(lines):
        _check_cancel(cancel)
        lowered = line.casefold()
        score = 2 * sum(min(lowered.count(term), 3) for term in terms) + (8 if query in lowered else 0)
        if score:
            if DECLARATION.match(line):
                score += 6
            matches.append((score + path_score, index))
    if not matches and path_score and lines:
        matches = [(path_score, 0)]
    selected = []
    for score, index in sorted(matches, key=lambda item: (-item[0], item[1])):
        if any(abs(index - previous) <= 4 for _, previous in selected):
            continue
        selected.append((score, index))
        if len(selected) == 2:
            break
    for score, index in selected:
        start, end = max(0, index - 2), min(len(lines), index + 3)
        excerpt = []
        for line in lines[start:end]:
            if len(line) > 500:
                lowered = line.casefold()
                positions = [lowered.find(term) for term in terms if term in lowered]
                offset = max(0, min(positions, default=0) - 100)
                line = ("…" if offset else "") + line[offset : offset + 498] + "…"
            excerpt.append(line)
        yield (
            score,
            {
                "path": path,
                "line": start + 1,
                "end_line": end,
                "text": "\n".join(excerpt),
                "sha256": value["sha256"],
            },
        )


def retrieve_context(workspace, query, cancel, max_chars=6000):
    """Return lexical snippets with full-file hashes; max_chars bounds snippet text.

    Paths/line/hash metadata and scan counts are additional, independently bounded
    output. The query is literal text/identifier terms, never a regex or command.
    Scanned bytes charge the attempted read limit for failed content reads, so
    binary/invalid files cannot bypass the shared I/O budget.
    """
    _check_cancel(cancel)
    if not isinstance(query, str) or len(query) > 200 or not query.strip():
        raise ValueError("Query must contain 1 to 200 characters")
    if (
        not isinstance(max_chars, int)
        or isinstance(max_chars, bool)
        or not 1 <= max_chars <= MAX_CONTEXT_CHARS
    ):
        raise ValueError(f"Context size must be between 1 and {MAX_CONTEXT_CHARS}")
    query = query.strip().casefold()
    terms = tuple(dict.fromkeys(re.findall(r"\w+", query)))[:16] or (query,)
    scan, candidates = _Scan(workspace, cancel), []
    for path, _ in scan.files():
        value = scan.read(path)
        if value is None:
            continue
        candidates.extend(_candidates(path, value, query, terms, cancel))
        # Keep only a bounded number of excerpts while ranking all scanned files.
        candidates.sort(key=lambda item: (-item[0], item[1]["path"], item[1]["line"]))
        if len(candidates) > MAX_SNIPPETS:
            candidates = candidates[:MAX_SNIPPETS]
            scan.truncated = True
    snippets, remaining = [], max_chars
    for _, snippet in candidates:
        _check_cancel(cancel)
        if remaining <= 0:
            scan.truncated = True
            break
        if len(snippet["text"]) > remaining:
            snippet["text"] = snippet["text"][:remaining]
            # A shortened excerpt cites only the source lines actually included.
            snippet["end_line"] = snippet["line"] + snippet["text"].count("\n")
            scan.truncated = True
        remaining -= len(snippet["text"])
        snippets.append(snippet)
    _check_cancel(cancel)
    return {"snippets": snippets, "scanned": scan.scanned, "truncated": scan.truncated}


def validate_snippets(workspace, snippets, cancel):
    """Recheck cited sources before reuse, independently of the map display cap.

    Current ignore rules, path/link protections and source hashes must all still
    agree. A source outside the bounded scan requires a new context preview.
    No source bodies are returned or retained.
    """
    _check_cancel(cancel)
    if not isinstance(snippets, list) or len(snippets) > MAX_SNIPPETS:
        raise ValueError("Invalid context citations; preview context again")
    expected = {}
    for snippet in snippets:
        if not isinstance(snippet, dict):
            raise ValueError("Invalid context citations; preview context again")
        path, sha256 = snippet.get("path"), snippet.get("sha256")
        if (
            not isinstance(path, str)
            or not 1 <= len(path) <= MAX_PATH_CHARS
            or not isinstance(sha256, str)
            or not re.fullmatch(r"[a-f0-9]{64}", sha256)
            or (path in expected and expected[path] != sha256)
        ):
            raise ValueError("Invalid context citations; preview context again")
        expected[path] = sha256
    if not expected:
        return
    scan = _Scan(workspace, cancel)
    for path, _ in scan.files():
        if path not in expected:
            continue
        value = scan.read(path)
        if value is None or value["sha256"] != expected[path]:
            raise ValueError("Context source changed or is unavailable; preview context again")
        del expected[path]
        if not expected:
            _check_cancel(cancel)
            return
    raise ValueError("Context source is ignored or unavailable; preview context again")
