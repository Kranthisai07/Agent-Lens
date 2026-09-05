"""Lab coordinates for the cyber scenario.

Two profiles:
- Real single VM (Path A, docs/VM_SETUP.md) — the confirmed SeedLabs VM over
  NAT, used for live SSH execution (cyber-04 onward). This is the default now.
- Host-only two-VM lab (Path B) — ATTACKER_HOST / DEFENDER_HOST, kept for the
  eventual full attacker/defender split.

Every value can be overridden by an environment variable.
"""

import os


def _env_bool(name, default):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() not in ("0", "false", "no", "off")


# --- Real VM (Path A: SeedLabs Ubuntu over VirtualBox NAT, confirmed working) ---
VM_HOST = os.environ.get("AGENTLENS_VM_HOST", "127.0.0.1")
VM_PORT = int(os.environ.get("AGENTLENS_VM_PORT", "2222"))
VM_USER = os.environ.get("AGENTLENS_VM_USER", "seed")
VM_PASS = os.environ.get("AGENTLENS_VM_PASS", "dees")

# The VM's own NAT address — attacker tools "target" the same box in the PoC.
VM_TARGET_IP = os.environ.get("AGENTLENS_VM_TARGET", "10.0.2.15")

# Real SSH is the default now. AGENTLENS_MOCK=1 still forces mock mode;
# unset or =0 -> real. (default False = real)
MOCK_MODE = _env_bool("AGENTLENS_MOCK", default=False)

# Per-command execution timeout (seconds).
SSH_TIMEOUT = float(os.environ.get("AGENTLENS_SSH_TIMEOUT", "10"))
CONNECT_TIMEOUT = float(os.environ.get("AGENTLENS_CONNECT_TIMEOUT", "10"))

# --- Host-only two-VM lab (Path B, not used by the single-VM real run) ---
ATTACKER_HOST = os.environ.get("AGENTLENS_ATTACKER_HOST", "192.168.56.101")
DEFENDER_HOST = os.environ.get("AGENTLENS_DEFENDER_HOST", "192.168.56.102")

# Back-compat aliases used by the older run_on() path and mock flow.
SSH_USER = os.environ.get("AGENTLENS_SSH_USER", VM_USER)
SSH_PASS = os.environ.get("AGENTLENS_SSH_PASS", VM_PASS)
SSH_PORT = int(os.environ.get("AGENTLENS_SSH_PORT", str(VM_PORT)))
