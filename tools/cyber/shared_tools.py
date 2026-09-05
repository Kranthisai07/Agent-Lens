"""Shared tools — usable by either agent, run over the pooled SSH connection.

Each tool takes the shared SSH client, runs its real command on the VM, and
returns {"command", "output", "success"}.
"""

from .ssh_connector import exec_pooled

TOOL_PREFIX = "Shared"


def _result(command, r):
    return {"command": command, "output": r["output"], "success": r["success"]}


def get_system_info(client):
    cmd = "uname -a && uptime && df -h"
    return _result(cmd, exec_pooled(client, cmd))


def read_syslog(client, lines=20):
    try:
        n = int(lines)
    except (TypeError, ValueError):
        n = 20
    cmd = f"sudo tail -{n} /var/log/syslog"
    return _result(cmd, exec_pooled(client, cmd))
