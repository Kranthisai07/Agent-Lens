"""Static lab coordinates for the cyber scenario.

Matches docs/VM_SETUP.md. Every value can be overridden by an environment
variable so the same code runs against a different lab without edits.
"""

import os

# Host-only network from VM_SETUP.md
ATTACKER_HOST = os.environ.get("AGENTLENS_ATTACKER_HOST", "192.168.56.101")
DEFENDER_HOST = os.environ.get("AGENTLENS_DEFENDER_HOST", "192.168.56.102")

SSH_USER = os.environ.get("AGENTLENS_SSH_USER", "agentlens")
SSH_PASS = os.environ.get("AGENTLENS_SSH_PASS", "agentlens123")
SSH_PORT = int(os.environ.get("AGENTLENS_SSH_PORT", "22"))
SSH_TIMEOUT = float(os.environ.get("AGENTLENS_SSH_TIMEOUT", "10"))
