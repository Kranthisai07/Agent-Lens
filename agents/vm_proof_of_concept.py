"""VM proof-of-concept — real SSH into Dr. Calix's SeedLabs VM.

Clears Calix's minimum bar: SSH into the VM (NAT, 127.0.0.1:2222, seed/dees),
run a few commands including `ping -c 3 8.8.8.8`, and log the results. This is
REAL SSH (paramiko), not MOCK_MODE — the VM must be running and port-forwarded
per docs/VM_SETUP.md (Path A).

Standalone: uses Path A credentials directly, independent of tools/cyber/config
(which is wired for the Path B host-only lab). See the credential note in
docs/VM_SETUP.md.

Run: python agents/vm_proof_of_concept.py
"""

import csv
import socket
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "data" / "trajectories" / "real_vm_logs.csv"
LOG_FIELDS = ["command", "output", "success", "timestamp"]

# Path A — Calix's SeedLabs NAT config (docs/VM_SETUP.md)
HOST = "127.0.0.1"
PORT = 2222
USERNAME = "seed"
PASSWORD = "dees"
CONNECT_TIMEOUT = 10

# Calix's exact test commands
COMMANDS = [
    "ping -c 3 8.8.8.8",
    "ifconfig",
    "ls -l",
    "uname -a",
]

NOT_REACHABLE = (
    f"VM not reachable at {HOST}:{PORT}\n"
    "Follow docs/VM_SETUP.md to configure VirtualBox first"
)


def _append_log(rows):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)


def main():
    try:
        import paramiko
    except ImportError:
        print("paramiko is not installed. Run: pip install paramiko")
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=HOST, port=PORT, username=USERNAME, password=PASSWORD,
            timeout=CONNECT_TIMEOUT, allow_agent=False, look_for_keys=False,
        )
    except (paramiko.ssh_exception.NoValidConnectionsError, socket.timeout,
            socket.error, ConnectionError, TimeoutError, OSError):
        # VM not running / port forwarding not configured
        print(NOT_REACHABLE)
        return 1
    except paramiko.ssh_exception.AuthenticationException:
        print(f"SSH reached {HOST}:{PORT} but authentication failed for "
              f"'{USERNAME}'. Check the VM credentials (expected seed/dees).")
        return 1
    except Exception as e:  # noqa: BLE001 — any other connect failure
        print(f"SSH connection error to {HOST}:{PORT}: {e}")
        print(NOT_REACHABLE)
        return 1

    print(f"Connected to {USERNAME}@{HOST}:{PORT}\n")
    rows, all_ok = [], True
    try:
        for cmd in COMMANDS:
            ts = datetime.now().isoformat(timespec="seconds")
            try:
                _stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
                exit_code = stdout.channel.recv_exit_status()
                out = stdout.read().decode("utf-8", errors="replace")
                err = stderr.read().decode("utf-8", errors="replace")
                success = exit_code == 0
                combined = out if success else (out + err).strip()
            except Exception as e:  # noqa: BLE001
                success, combined = False, f"exec error: {e}"
            all_ok = all_ok and success

            print(f"$ {cmd}   [{'OK' if success else 'FAIL'}]")
            print(combined.rstrip() or "(no output)")
            print("-" * 60)
            rows.append({"command": cmd, "output": combined,
                         "success": success, "timestamp": ts})
    finally:
        client.close()
        _append_log(rows)

    print(f"\nLogged {len(rows)} commands to {LOG_PATH.relative_to(ROOT)}")
    if all_ok:
        print("VM CONNECTION SUCCESSFUL")
        return 0
    print("Connected, but one or more commands failed — see the log above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
