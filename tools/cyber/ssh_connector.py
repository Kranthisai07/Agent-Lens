"""SSHConnect — paramiko-based SSH connection and command execution.

In MOCK_MODE no socket is opened: connect_ssh returns a sentinel client and
execute_command returns canned output from mocks.py, so the whole cyber
pipeline runs with no VMs. Set MOCK_MODE=False (or AGENTLENS_MOCK=0) once the
lab in docs/VM_SETUP.md is up.
"""

from . import MOCK_MODE, cyber_logs
from .config import SSH_PASS, SSH_PORT, SSH_TIMEOUT, SSH_USER
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


def connect_ssh(host, username=SSH_USER, password=SSH_PASS, port=SSH_PORT):
    """Open an SSH connection. Returns a client, or None on failure.

    Logs the attempt (host + user, never the password) to cyber_logs.
    """
    cyber_logs.append({
        "prompt": f"ssh {username}@{host}",
        "tool_predicted": TOOL_NAME,
        "event": "connect_attempt",
        "mock": MOCK_MODE,
    })

    if MOCK_MODE:
        return MockSSHClient(host, username)

    import paramiko  # imported lazily so mock mode needs no paramiko at import
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=SSH_TIMEOUT,
            allow_agent=False,
            look_for_keys=False,
        )
        return client
    except Exception as e:  # noqa: BLE001 — surface any connect failure uniformly
        print(f"  SSH connect error to {username}@{host}: {e}")
        return None


def execute_command(client, command):
    """Run a command over an SSH client.

    Returns (stdout, stderr, exit_code). In MOCK_MODE the command is matched to
    a canned output and exit_code is 0. On a missing/failed client returns a
    non-zero exit_code with the error on stderr rather than raising.
    """
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
    """Convenience: connect, run one command, close. Returns stdout (or an
    'SSH error: ...' string on failure) so tool functions stay one-liners."""
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
