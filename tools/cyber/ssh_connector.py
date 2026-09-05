"""SSHConnect — paramiko SSH with a pooled connection and bounded-timeout exec.

Real mode (default): open_pool() opens ONE SSH connection to the VM
(config.VM_HOST:VM_PORT as VM_USER) and exec_pooled() runs every tool command
over that single connection, closing it once at the end of the run. This avoids
a fresh TCP+auth handshake per tool call (slow and unstable across 640 queries).

Mock mode (AGENTLENS_MOCK=1): open_pool() returns a MockSSHClient and
exec_pooled() returns canned output from mocks.py — no socket opened.

exec_pooled() bounds each command to `timeout` seconds of wall-clock (paramiko's
recv_exit_status does NOT honor the channel timeout, so we poll a deadline) and
returns {"output": ..., "success": bool}; on timeout {"output": "TIMEOUT",
"success": False}.
"""

import time

from . import MOCK_MODE, cyber_logs
from .config import (CONNECT_TIMEOUT, SSH_PASS, SSH_PORT, SSH_TIMEOUT, SSH_USER,
                     VM_HOST, VM_PASS, VM_PORT, VM_USER)
from .mocks import mock_for

TOOL_NAME = "SSHConnect"


class MockSSHClient:
    """Stand-in for paramiko.SSHClient used when MOCK_MODE is on."""

    def __init__(self, host, username):
        self.host = host
        self.username = username
        self.mock = True

    def close(self):
        pass


# --------------------------------------------------------------------------- #
# Pooled real connection (cyber-04)
# --------------------------------------------------------------------------- #
def open_pool(host=VM_HOST, port=VM_PORT, username=VM_USER, password=VM_PASS):
    """Open ONE SSH connection to the VM for the whole run. Returns a client
    (real or mock), or None if a real connection fails."""
    cyber_logs.append({
        "prompt": f"ssh {username}@{host}:{port}",
        "tool_predicted": TOOL_NAME, "event": "pool_open", "mock": MOCK_MODE,
    })
    if MOCK_MODE:
        return MockSSHClient(host, username)

    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=username,
                       password=password, timeout=CONNECT_TIMEOUT,
                       allow_agent=False, look_for_keys=False)
        return client
    except Exception as e:  # noqa: BLE001
        print(f"  SSH pool connect error to {username}@{host}:{port}: {e}")
        return None


def exec_pooled(client, command, timeout=SSH_TIMEOUT):
    """Run one command over the pooled client. Returns
    {"output": str, "success": bool}. Bounds wall-clock to `timeout` seconds."""
    if client is None:
        return {"output": "no SSH client (connection failed)", "success": False}
    if MOCK_MODE or getattr(client, "mock", False):
        return {"output": mock_for(command), "success": True}

    try:
        transport = client.get_transport()
        chan = transport.open_session()
        chan.settimeout(timeout)
        chan.exec_command(command)
    except Exception as e:  # noqa: BLE001
        return {"output": f"ERROR opening channel: {e}", "success": False}

    deadline = time.time() + timeout
    out, err = b"", b""
    try:
        while True:
            while chan.recv_ready():
                out += chan.recv(8192)
            while chan.recv_stderr_ready():
                err += chan.recv_stderr(8192)
            if chan.exit_status_ready():
                break
            if time.time() > deadline:
                chan.close()
                return {"output": "TIMEOUT", "success": False}
            time.sleep(0.05)
        while chan.recv_ready():
            out += chan.recv(8192)
        while chan.recv_stderr_ready():
            err += chan.recv_stderr(8192)
        code = chan.recv_exit_status()
    except Exception as e:  # noqa: BLE001
        return {"output": f"ERROR: {e}", "success": False}
    finally:
        try:
            chan.close()
        except Exception:  # noqa: BLE001
            pass

    o = out.decode("utf-8", errors="replace").strip()
    e = err.decode("utf-8", errors="replace").strip()
    return {"output": (o if o else e), "success": code == 0}


# --------------------------------------------------------------------------- #
# Legacy per-call helpers (kept for back-compat / older run_on() callers)
# --------------------------------------------------------------------------- #
def connect_ssh(host, username=SSH_USER, password=SSH_PASS, port=SSH_PORT):
    """Open a one-off SSH connection. Returns a client or None on failure."""
    cyber_logs.append({
        "prompt": f"ssh {username}@{host}", "tool_predicted": TOOL_NAME,
        "event": "connect_attempt", "mock": MOCK_MODE,
    })
    if MOCK_MODE:
        return MockSSHClient(host, username)
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=username,
                       password=password, timeout=SSH_TIMEOUT,
                       allow_agent=False, look_for_keys=False)
        return client
    except Exception as e:  # noqa: BLE001
        print(f"  SSH connect error to {username}@{host}: {e}")
        return None


def execute_command(client, command):
    """Legacy: (stdout, stderr, exit_code)."""
    if client is None:
        return "", "no SSH client (connection failed)", 1
    if MOCK_MODE or getattr(client, "mock", False):
        return mock_for(command), "", 0
    try:
        _stdin, stdout, stderr = client.exec_command(command, timeout=SSH_TIMEOUT)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return out, err, exit_code
    except Exception as e:  # noqa: BLE001
        return "", f"SSH exec error: {e}", 1


def run_on(host, command, username=SSH_USER, password=SSH_PASS):
    """Legacy convenience: connect, run one command, close; returns stdout str."""
    client = connect_ssh(host, username, password)
    if client is None:
        return f"SSH error: could not connect to {username}@{host}"
    try:
        out, err, code = execute_command(client, command)
    finally:
        client.close()
    if code != 0:
        return f"SSH error (exit {code}): {err.strip() or out.strip()}"
    return out
