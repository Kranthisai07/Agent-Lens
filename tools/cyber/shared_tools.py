"""Shared tools — usable by either agent, run over SSH on a given host.

Defaults to the defender host but accepts any lab host so both roles can
inspect their own machine.
"""

from .config import DEFENDER_HOST
from .ssh_connector import run_on

TOOL_PREFIX = "Shared"


def get_system_info(host=DEFENDER_HOST) -> str:
    """Hostname, kernel/OS and uptime/load (uname -a && uptime)."""
    return run_on(host, "uname -a && uptime")


def read_syslog(lines=20, host=DEFENDER_HOST) -> str:
    """Recent /var/log/syslog entries."""
    try:
        n = int(lines)
    except (TypeError, ValueError):
        n = 20
    return run_on(host, f"tail -{n} /var/log/syslog")
