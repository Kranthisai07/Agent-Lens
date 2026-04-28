"""AgentLens tools package — shared logs list and logging_tool wrapper."""

logs = []


def logging_tool(tool_name, func):
    """Wrap a tool function so every call appends (prompt, tool) to logs."""
    def wrapped(input):
        logs.append({"prompt": input, "tool": tool_name})
        return func(input)
    return wrapped
