"""Bounded Python checks: compile/inspect only, never import or run project code."""

import ast

PYTHON_CHECK_CODES = frozenset(
    (
        "PYTHON_STATIC_OK",
        "PYTHON_SYNTAX_ERROR",
        "LITERAL_UNPACK_MISMATCH",
        "PYTHON_CHECK_LIMIT",
        "CHECK_REVISION_CHANGED",
    )
)


def check_python(workspace, relative):
    if not relative.lower().endswith(".py"):
        raise ValueError("Choose a Python (.py) file")
    source = workspace.read(relative)
    result = {
        "status": "passed",
        "code": "PYTHON_STATIC_OK",
        "line": None,
        "sha256": source["sha256"],
        "executed": False,
    }
    try:
        # compile catches errors ast.parse alone accepts, e.g. return outside a function.
        compile(source["content"], "<project file>", "exec", dont_inherit=True)
        tree = ast.parse(source["content"])
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, (ast.Tuple, ast.List)):
                continue
            if any(isinstance(item, ast.Starred) for item in node.value.elts):
                continue
            for target in node.targets:
                if (
                    isinstance(target, (ast.Tuple, ast.List))
                    and not any(isinstance(item, ast.Starred) for item in target.elts)
                    and len(target.elts) != len(node.value.elts)
                ):
                    return result | {
                        "status": "failed",
                        "code": "LITERAL_UNPACK_MISMATCH",
                        "line": node.lineno,
                    }
    except SyntaxError as exc:
        return result | {"status": "failed", "code": "PYTHON_SYNTAX_ERROR", "line": exc.lineno}
    except (RecursionError, MemoryError, ValueError):
        return result | {"status": "failed", "code": "PYTHON_CHECK_LIMIT", "line": None}
    return result


def describe_python(result):
    labels = {
        "PYTHON_STATIC_OK": "Python syntax and basic static checks passed. The program was not run.",
        "PYTHON_SYNTAX_ERROR": "Python syntax check failed. Fix the reported line before running the program.",
        "LITERAL_UNPACK_MISMATCH": "An assignment has a different number of values and variables.",
        "PYTHON_CHECK_LIMIT": "Python checking reached a parser limit; this file remains unverified.",
        "CHECK_REVISION_CHANGED": "The file changed after saving. Check its current contents again.",
    }
    text = labels.get(result.get("code"), "Python check unavailable.")
    if result.get("line"):
        text += " Line " + str(result["line"]) + "."
    return text
