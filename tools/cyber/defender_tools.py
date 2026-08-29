"""Defender tools — inspection and response run on defender-vm over SSH.

Each tool SSHes into the defender VM and runs a read/response command there.
In MOCK_MODE the SSH layer returns canned log/netstat output.

For authorized lab use only (see docs/VM_SETUP.md). block_ip needs passwordless
sudo for /usr/sbin/iptables on defender-vm (see VM_SETUP.md §5).
"""

from .config import DEFENDER_HOST
from .ssh_connector import run_on

TOOL_PREFIX = "Defender"


def read_auth_log() -> str:
    """Last 50 lines of /var/log/auth.log on defender-vm."""
    return run_on(DEFENDER_HOST, "tail -50 /var/log/auth.log")


def list_listening_ports() -> str:
    """Listening TCP sockets on defender-vm (ss -tlnp)."""
    return run_on(DEFENDER_HOST, "ss -tlnp")


def check_failed_logins() -> str:
    """Recent failed SSH password attempts on defender-vm."""
    return run_on(
        DEFENDER_HOST,
        'grep "Failed password" /var/log/auth.log | tail -20',
    )


def block_ip(ip_address: str) -> str:
    """Drop all inbound traffic from an IP via iptables on defender-vm."""
    ip = ip_address.strip()
    out = run_on(DEFENDER_HOST, f"sudo iptables -A INPUT -s {ip} -j DROP")
    if out.startswith("SSH error"):
        return out
    return f"Blocked {ip} (iptables -A INPUT -s {ip} -j DROP applied on defender-vm)."


def list_processes() -> str:
    """Top processes by CPU on defender-vm (ps aux, top 20)."""
    return run_on(DEFENDER_HOST, "ps aux --sort=-%cpu | head -20")
