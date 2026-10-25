"""Safe synthetic-contract diagnostics; strict scores remain unchanged.

Only application-owned target names, expected schema paths, static hints and type
names leave this module. Actual values, unexpected keys and parser errors never do.
No generated code is executed or imported.
"""

import ast
import re
from pathlib import Path

from .crew_cases import CASES, _equal_json, _json, evaluate_content
from .tools import Workspace

MAX_MISMATCHES = 8
MAX_POINTER = 240
MAX_DEPTH = 16
MAX_NODES = 256
MAX_FILE_BYTES = 100_000

HINTS = {
    "MISSING_OUTPUT": "Create the required output, then read the saved file back.",
    "UNREADABLE_OUTPUT": "The output is unavailable as a bounded UTF-8 project file.",
    "BYTE_MISMATCH": "Saved bytes differ from the exact content and formatting contract; compare the brief.",
    "FORMAT_ONLY": "Python syntax trees match, but exact whitespace, comments or newline formatting differs.",
    "PYTHON_SYNTAX": "The saved Python cannot be parsed; correct its syntax without running it.",
    "JSON_PARSE": "Write one valid JSON value without markdown fences, duplicate keys or trailing text.",
    "JSON_KEYS": "Match the required object keys exactly; remove extras and include every required key.",
    "JSON_MISSING": "Include the required field at this schema path.",
    "JSON_TYPE": "Use the required JSON type; booleans are distinct from numbers.",
    "JSON_LENGTH": "Match the requested array length and input order.",
    "JSON_VALUE": "Recompute the value at this schema path from the task specification.",
    "ANSWER_PARSE": "Return exactly one valid JSON answer without fences, duplicate keys or extra prose.",
    "PATH_SPELLING": "The citation identifies the same allowed path, but the contract requires its exact relative spelling.",
    "SOURCE_CHANGED": "Restore unrelated input content; only declared outputs may change.",
    "UNEXPECTED_FILE": "Keep only the original inputs and declared outputs; do not create unrelated files.",
    "STRUCTURE_LIMIT": "The artifact exceeds the bounded schema diagnostic depth or size.",
}
MISMATCH_CODES = frozenset(HINTS)
TYPE_NAMES = frozenset(("null", "boolean", "number", "string", "object", "array", "missing", "unknown"))


def _schema_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _schema_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _schema_keys(item)


SCHEMA_KEYS = frozenset(
    key
    for case in CASES
    for value in [case.answer, *case.output_json.values()]
    for key in _schema_keys(value)
    if isinstance(key, str)
)
KNOWN_TARGETS = frozenset(
    {
        "final_answer",
        "output.txt",
        "output.py",
        "unicode.txt",
        "empty.txt",
        "square.py",
        "src/report.txt",
        "first.txt",
        "second.txt",
        "combined.txt",
    }
    | {name for case in CASES for name in (*case.files, *case.outputs, *case.output_json)}
)


def _escape(key):
    return key.replace("~", "~0").replace("/", "~1")


def _pointer_safe(value, allowed_keys):
    if not isinstance(value, str) or len(value) > MAX_POINTER:
        return False
    if not value:
        return True
    if not value.startswith("/"):
        return False
    segments = value[1:].split("/")
    if len(segments) > MAX_DEPTH:
        return False
    for segment in segments:
        if re.search(r"~(?![01])", segment):
            return False
        key = segment.replace("~1", "/").replace("~0", "~")
        if key not in allowed_keys and not (re.fullmatch(r"0|[1-9][0-9]{0,3}", key) and int(key) < 1000):
            return False
    return True


def public_mismatches(value, allowed_targets=None):
    """Sanitize an old/malformed record before model feedback or ZIP export.

    Caller-provided targets must themselves be application-owned synthetic paths.
    Arbitrary actual JSON property names are never allowed as pointer segments.
    """
    targets = KNOWN_TARGETS if allowed_targets is None else frozenset(allowed_targets) | {"final_answer"}
    result = []
    for item in value[:MAX_MISMATCHES] if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        code, target = item.get("code"), item.get("target")
        if (
            not isinstance(code, str)
            or code not in HINTS
            or not isinstance(target, str)
            or target not in targets
        ):
            continue
        pointer = item.get("path", "")
        if not _pointer_safe(pointer, SCHEMA_KEYS):
            continue
        result.append(
            {
                "code": code,
                "target": target,
                "path": pointer,
                "expected_type": item.get("expected_type")
                if isinstance(item.get("expected_type"), str) and item.get("expected_type") in TYPE_NAMES
                else "unknown",
                "actual_type": item.get("actual_type")
                if isinstance(item.get("actual_type"), str) and item.get("actual_type") in TYPE_NAMES
                else "unknown",
                "hint": HINTS[code],
            }
        )
    return result


def _type(value):
    if value is None:
        return "null"
    if type(value) is bool:
        return "boolean"
    if type(value) in (int, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "unknown"


def _same_allowed_path(workspace, actual, expected):
    try:
        return workspace.path(actual) == workspace.path(expected)
    except (OSError, ValueError, PermissionError):
        return False


def evaluate_contract(case, root: Path, finaltext: str):
    """Return original strict checks plus bounded safe mismatch explanations."""
    root = Path(root)
    checks = evaluate_content(case, root, finaltext)
    workspace = Workspace(root)
    mismatches = []
    nodes = 0

    def add(code, target, path="", expected_type="unknown", actual_type="unknown"):
        if len(mismatches) < MAX_MISMATCHES:
            mismatches.append(
                {
                    "code": code,
                    "target": target,
                    "path": path,
                    "expected_type": expected_type,
                    "actual_type": actual_type,
                    "hint": HINTS[code],
                }
            )

    def compare(actual, expected, target, path="", depth=0):
        nonlocal nodes
        if len(mismatches) >= MAX_MISMATCHES:
            return
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH or len(path) > MAX_POINTER:
            add("STRUCTURE_LIMIT", target)
            return
        atype, etype = _type(actual), _type(expected)
        if atype != etype:
            add("JSON_TYPE", target, path, etype, atype)
            return
        if isinstance(expected, dict):
            if actual.keys() != expected.keys():
                add("JSON_KEYS", target, path, "object", "object")
            for key, item in expected.items():
                child = path + "/" + _escape(key)
                if key not in actual:
                    add("JSON_MISSING", target, child, _type(item), "missing")
                else:
                    compare(actual[key], item, target, child, depth + 1)
        elif isinstance(expected, list):
            if len(actual) != len(expected):
                add("JSON_LENGTH", target, path, "array", "array")
            for index, (left, right) in enumerate(zip(actual, expected)):
                compare(left, right, target, path + "/" + str(index), depth + 1)
        elif not _equal_json(actual, expected):
            code = "JSON_VALUE"
            if path.endswith("/file") and isinstance(actual, str) and isinstance(expected, str):
                if _same_allowed_path(workspace, actual, expected):
                    code = "PATH_SPELLING"
            add(code, target, path, etype, atype)

    def read(name):
        try:
            return workspace.read(name)["content"].encode("utf-8")
        except FileNotFoundError:
            add("MISSING_OUTPUT", name, expected_type="string", actual_type="missing")
        except (OSError, ValueError, UnicodeError):
            add("UNREADABLE_OUTPUT", name)
        return None

    for name, expected in case.outputs.items():
        data = read(name)
        if data is None or data == expected:
            continue
        code = "BYTE_MISMATCH"
        if name.lower().endswith(".py"):
            try:
                left, right = ast.parse(data), ast.parse(expected)
                if ast.dump(left) == ast.dump(right):
                    code = "FORMAT_ONLY"
            except SyntaxError:
                code = "PYTHON_SYNTAX"
            except (ValueError, RecursionError, MemoryError):
                code = "STRUCTURE_LIMIT"
        add(code, name, expected_type="string", actual_type="string")
    for name, expected in case.output_json.items():
        data = read(name)
        if data is None:
            continue
        try:
            actual = _json(data)
        except (ValueError, UnicodeError, TypeError, RecursionError):
            add("JSON_PARSE", name, expected_type=_type(expected))
        else:
            compare(actual, expected, name)
    if case.answer is not None:
        try:
            if not isinstance(finaltext, str) or len(finaltext) > 16000:
                raise ValueError("Answer exceeds its bound")
            actual = _json(finaltext)
        except (ValueError, UnicodeError, TypeError, RecursionError):
            add("ANSWER_PARSE", "final_answer", expected_type=_type(case.answer))
        else:
            compare(actual, case.answer, "final_answer")
    if not checks["INPUTS_UNCHANGED"]:
        for name, expected in case.files.items():
            if name in case.outputs or name in case.output_json:
                continue
            try:
                changed = workspace.read(name)["content"].encode("utf-8") != expected
            except (OSError, ValueError, UnicodeError):
                changed = True
            if changed:
                add("SOURCE_CHANGED", name)
    if not checks["NO_UNEXPECTED_FILES"]:
        # Unknown discovered filenames are deliberately not copied into diagnostics.
        add("UNEXPECTED_FILE", "final_answer")
    targets = {*case.files, *case.outputs, *case.output_json, "final_answer"}
    return {"checks": checks, "mismatches": public_mismatches(mismatches, targets)}


def contract_prompt(case):
    """Clarify machine contracts for a separately versioned measurement track.

    Return a full prompt, with no expected answer values or artifact contents.
    Legacy discovery prompts remain untouched unless the caller opts in.
    """
    notes = []
    if case.output_json:
        notes.append(
            "Output artifacts must contain JSON only, without markdown fences, duplicate or extra keys. "
            "Use exactly the requested root and item keys, array order and JSON types. "
            "Numbers and booleans are distinct; equivalent numeric spellings are accepted."
        )
    if case.outputs:
        notes.append(
            "This exercise checks exact file bytes as well as workflow. Preserve existing formatting "
            "unless the brief requests a change. Use real LF newlines and a final newline for nonempty "
            "text outputs. Use four spaces for Python indentation; no surrounding markdown."
        )
    if case.answer is not None:
        notes.append(
            "Return the requested JSON object only, without extra keys or prose. Use canonical relative "
            "filename spelling for citations, without a leading './'."
        )
    return case.prompt + ("\nExplicit acceptance contract: " + " ".join(notes) if notes else "")
