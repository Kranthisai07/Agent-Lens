"""Defender tools — inspection and response run over the pooled SSH connection.

Each tool takes the shared SSH client, runs its real command on the VM, and
returns {"command", "output", "success"}. Authorized lab use only.
"""

from .ssh_connector import exec_pooled

TOOL_PREFIX = "Defender"

# NOTE: default block target is a harmless TEST-NET-1 address (RFC 5737), NOT
# the NAT gateway 10.0.2.2. Over VirtualBox NAT port-forwarding the pooled SSH
# connection appears to originate from 10.0.2.2 inside the guest, so blocking
# 10.0.2.2 would drop our own connection and break the rest of the run.
SAFE_BLOCK_IP = "192.0.2.1"


def _result(command, r):
    return {"command": command, "output": r["output"], "success": r["success"]}


def read_auth_log(client):
    cmd = "sudo tail -50 /var/log/auth.log"
    return _result(cmd, exec_pooled(client, cmd))


def list_listening_ports(client):
    cmd = "ss -tlnp"
    return _result(cmd, exec_pooled(client, cmd))


def check_failed_logins(client):
    cmd = "grep 'Failed password' /var/log/auth.log | tail -20"
    r = exec_pooled(client, cmd)
    # `grep | tail` exits 0 even with no matches; empty output means none found.
    if r["success"] and not r["output"].strip():
        return {"command": cmd, "output": "No failed login attempts found",
                "success": True}
    return _result(cmd, r)


def block_ip(client, ip=SAFE_BLOCK_IP):
    cmd = f"sudo iptables -A INPUT -s {ip} -j DROP && echo BLOCKED"
    return _result(cmd, exec_pooled(client, cmd))


def list_processes(client):
    cmd = "ps aux --sort=-%cpu | head -20"
    return _result(cmd, exec_pooled(client, cmd))
