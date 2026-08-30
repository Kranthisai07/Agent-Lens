"""Calculator tool — safely evaluates arithmetic expressions.

Uses ast.parse over a strict node whitelist instead of eval(). Only
numeric literals and arithmetic/comparison operators are permitted:
names, attribute access, calls, subscripts and imports all raise.
"""

import ast
import operator

TOOL_NAME = "Calculator"

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Guard against expressions like 9**9**9 that would hang the process.
_MAX_EXPONENT = 1000


def _evaluate(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError(f"unsupported literal: {node.value!r}")
        return node.value
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"unsupported operator: {type(node.op).__name__}")
        left, right = _evaluate(node.left), _evaluate(node.right)
        if op is operator.pow and abs(right) > _MAX_EXPONENT:
            raise ValueError(f"exponent too large: {right}")
        return op(left, right)
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"unsupported unary operator: {type(node.op).__name__}")
        return op(_evaluate(node.operand))
    raise ValueError(f"unsupported expression node: {type(node).__name__}")


def safe_eval(expression: str):
    """Evaluate an arithmetic expression without eval(). Raises on anything else."""
    try:
        return ast.literal_eval(expression)  # fast path: bare literals
    except (ValueError, SyntaxError, TypeError):
        pass
    tree = ast.parse(expression, mode="eval")
    return _evaluate(tree.body)


def calculator(expression: str) -> str:
    try:
        result = safe_eval(expression)
    except Exception as e:
        return f"Calculator error: {e}"
    return str(result)
