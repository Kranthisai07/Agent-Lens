"""Two-VM reachability test — confirm both attacker and defender VMs answer SSH.

Connects to each VM over SSH (config: ATTACKER_VM_* / DEFENDER_VM_*), runs a
trivial command to prove a real shell, and prints:
  ATTACKER CONNECTED   if 10.0.0.188 responds
  DEFENDER CONNECTED   if 10.0.0.114 responds
  BOTH CONNECTED       if both work

Does NOT run the full scenario. Run: python agents/test_two_vm.py
"""

import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.cyber.config import (ATTACKER_VM_HOST, ATTACKER_VM_PASS,
                                ATTACKER_VM_PORT, ATTACKER_VM_USER,
                                CONNECT_TIMEOUT, DEFENDER_VM_HOST,
                                DEFENDER_VM_PASS, DEFENDER_VM_PORT,
                                DEFENDER_VM_USER)


def _probe(label, host, port, user, password):
    """Return (ok, detail). ok=True only if SSH connects AND a command runs."""
    try:
        import paramiko
    except ImportError:
        return False, "paramiko not installed (pip install paramiko)"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=user, password=password,
                       timeout=CONNECT_TIMEOUT, allow_agent=False, look_for_keys=False)
    except paramiko.ssh_exception.AuthenticationException:
        return False, f"reachable but auth failed for {user}@{host}:{port}"
    except (paramiko.ssh_exception.NoValidConnectionsError, socket.timeout,
            socket.error, ConnectionError, TimeoutError, OSError) as e:
        return False, f"not reachable at {host}:{port} ({type(e).__name__})"
    except Exception as e:  # noqa: BLE001
        return False, f"connection error to {host}:{port}: {e}"
    try:
        _in, out, _err = client.exec_command("hostname && whoami", timeout=10)
        detail = out.read().decode("utf-8", errors="replace").strip().replace("\n", " / ")
        return True, detail or "connected"
    except Exception as e:  # noqa: BLE001
        return False, f"connected but command failed: {e}"
    finally:
        client.close()


def main():
    print(f"Attacker VM: {ATTACKER_VM_USER}@{ATTACKER_VM_HOST}:{ATTACKER_VM_PORT}")
    print(f"Defender VM: {DEFENDER_VM_USER}@{DEFENDER_VM_HOST}:{DEFENDER_VM_PORT}\n")

    atk_ok, atk_detail = _probe("attacker", ATTACKER_VM_HOST, ATTACKER_VM_PORT,
                                ATTACKER_VM_USER, ATTACKER_VM_PASS)
    if atk_ok:
        print(f"ATTACKER CONNECTED  ({atk_detail})")
    else:
        print(f"ATTACKER NOT CONNECTED  — {atk_detail}")

    def_ok, def_detail = _probe("defender", DEFENDER_VM_HOST, DEFENDER_VM_PORT,
                                DEFENDER_VM_USER, DEFENDER_VM_PASS)
    if def_ok:
        print(f"DEFENDER CONNECTED  ({def_detail})")
    else:
        print(f"DEFENDER NOT CONNECTED  — {def_detail}")

    print()
    if atk_ok and def_ok:
        print("BOTH CONNECTED")
        return 0
    print("NOT both reachable — see docs/VM_SETUP.md; the full scenario needs both.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
