"""Small, bounded JSON-root contracts. Never rewrite content or execute schemas."""

import json
import math

JSON_TYPES = frozenset(("object", "array", "string", "number", "boolean", "null"))
PROPOSAL_POLICY_VERSION = "json-proposals-1"
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 10000


class JsonProposalError(ValueError):
    code = "JSON_PROPOSAL"

    def __init__(self, reason, expected):
        self.reason = reason
        super().__init__(
            f"JSON proposal rejected ({reason}); expected {expected} root. No file was written. Correct JSON using the declared contract, then read the final saved file."
        )


def json_type(value):
    if value is None:
        return "null"
    return {
        dict: "object",
        list: "array",
        str: "string",
        bool: "boolean",
        int: "number",
        float: "number",
    }.get(type(value))


def validate_proposal(content, expected):
    if expected not in JSON_TYPES:
        raise ValueError("Unknown application JSON contract")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("nonfinite")

    try:
        value = json.loads(content, object_pairs_hook=pairs, parse_constant=constant)
    except json.JSONDecodeError:
        raise JsonProposalError("syntax", expected) from None
    except RecursionError:
        raise JsonProposalError("structure_limit", expected) from None
    except ValueError:
        raise JsonProposalError("duplicate_or_nonfinite", expected) from None
    nodes = 0

    def inspect(item, depth=0):
        nonlocal nodes
        nodes += 1
        if depth > MAX_JSON_DEPTH or nodes > MAX_JSON_NODES:
            raise JsonProposalError("structure_limit", expected)
        if type(item) is float and not math.isfinite(item):
            raise JsonProposalError("duplicate_or_nonfinite", expected)
        if isinstance(item, dict):
            for value in item.values():
                inspect(value, depth + 1)
        elif isinstance(item, list):
            for value in item:
                inspect(value, depth + 1)

    inspect(value)
    if json_type(value) != expected:
        raise JsonProposalError("root_type", expected)
