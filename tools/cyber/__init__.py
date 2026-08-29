"""AgentLens cyber tools — SSH-driven attacker/defender tools + logging.

Mirrors tools/__init__.py: a shared cyber_logs list and a logging_tool wrapper
that records every tool call. Adds MOCK_MODE so the whole pipeline runs with no
VMs (canned outputs from mocks.py).

MOCK_MODE default is True; the AGENTLENS_MOCK env var overrides it
(AGENTLENS_MOCK=0 -> live SSH, =1 -> mock).
"""

import os

# ---- shared state (defined before tool submodules import from this package) ----
cyber_logs = []


def _env_mock(default=True):
    val = os.environ.get("AGENTLENS_MOCK")
    if val is None:
        return default
    return val.strip().lower() not in ("0", "false", "no", "off")


MOCK_MODE = _env_mock(default=True)


def logging_tool(tool_name, func):
    """Wrap a cyber tool so every call appends a trajectory record to cyber_logs.

    Extra keyword args are merged into the record (e.g. tool_ground_truth,
    agent_role, run_id), matching tools/__init__.py's wrapper.
    """
    def wrapped(input, **meta):
        cyber_logs.append({"prompt": input, "tool_predicted": tool_name, **meta})
        return func(input)
    return wrapped


# ---- tool imports (after MOCK_MODE / cyber_logs exist to avoid circular import) ----
from . import attacker_tools, defender_tools, shared_tools, ssh_connector  # noqa: E402
from .ssh_connector import connect_ssh, execute_command, run_on  # noqa: E402,F401

__all__ = [
    "cyber_logs", "logging_tool", "MOCK_MODE",
    "connect_ssh", "execute_command", "run_on",
    "attacker_tools", "defender_tools", "shared_tools", "ssh_connector",
]
