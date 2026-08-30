"""AgentLens tools package — shared logs list and logging_tool wrapper."""

logs = []


def logging_tool(tool_name, func):
    """Wrap a tool function so every call appends a trajectory record to logs.

    Extra keyword args are merged into the record, letting the caller attach
    metadata such as the ground-truth label and a run id:

        calc = logging_tool("Calculator", calculator)
        calc(query, tool_ground_truth="Calculator", run_id="20260829-101500")
    """
    def wrapped(input, **meta):
        logs.append({"prompt": input, "tool_predicted": tool_name, **meta})
        return func(input)
    return wrapped
