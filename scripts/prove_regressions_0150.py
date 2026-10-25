"""Development-only green/red/green proof against immutable v0.14.1 behavior.

Run from the repository root with QT_QPA_PLATFORM=offscreen .venv/bin/python
scripts/prove_regressions_0150.py. Requires the local v0.14.1 Git tag and dev deps.
Never writes source files and never runs as part of the installed application.
"""

import ast
import math
from pathlib import Path
import subprocess
import sys
import types

import pytest


def main():
    root = Path(__file__).resolve().parents[1]
    if Path.cwd() != root:
        raise SystemExit("Run from the repository root")
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "tests"))
    import test_runtime_diagnostics_0150 as runtime_tests
    import aigentics.crew_cases as cases

    def source(path):
        return subprocess.check_output(["git", "show", f"v0.14.1:{path}"], text=True)

    legacy = types.ModuleType("aigentics._legacy_runtime_proof")
    legacy.__package__ = "aigentics"
    exec(compile(source("aigentics/runtime.py"), "<v0.14.1-runtime>", "exec"), legacy.__dict__)
    node = next(
        node
        for node in ast.parse(source("aigentics/crew_cases.py")).body
        if isinstance(node, ast.FunctionDef) and node.name == "_equal_json"
    )
    namespace = {"math": math}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<v0.14.1-grader>", "exec"), namespace)
    paths = ["tests/test_runtime_diagnostics_0150.py", "tests/test_grader_numeric_0150.py", "-q"]
    print("GREEN: current behavior", flush=True)
    assert pytest.main(paths) == 0
    current_runtime, current_equal = runtime_tests.Runtime, cases._equal_json
    try:
        runtime_tests.Runtime, cases._equal_json = legacy.Runtime, namespace["_equal_json"]
        print("RED: immutable pre-fix behavior, isolated process only", flush=True)
        assert pytest.main(paths) == 1
    finally:
        runtime_tests.Runtime, cases._equal_json = current_runtime, current_equal
    print("GREEN: restored current behavior", flush=True)
    assert pytest.main(paths) == 0


if __name__ == "__main__":
    main()
