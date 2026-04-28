"""Calculator tool — evaluates arithmetic expressions."""

TOOL_NAME = "Calculator"


def calculator(expression: str) -> str:
    try:
        result = eval(expression)
    except Exception as e:
        return f"Calculator error: {e}"
    return str(result)
