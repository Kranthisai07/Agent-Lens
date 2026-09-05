"""Attacker tools — reconnaissance run over the pooled SSH connection.

Each tool takes the shared SSH client, runs its real command on the VM, and
returns {"command", "output", "success"}. In MOCK_MODE exec_pooled returns
canned output. For authorized lab use only (docs/VM_SETUP.md) — the target is
the VM's own NAT address in the single-VM PoC.
"""

from .config import VM_TARGET_IP, VM_USER
from .ssh_connector import exec_pooled

TOOL_PREFIX = "Attacker"

# Offline CVE table used when searchsploit/exploitdb is not installed on the VM.
_KNOWN_VULNS = {
    ("openssh", "7.2"): "CVE-2016-6210 - user enumeration via timing (OpenSSH < 7.3)",
    ("openssh", "8.2"): "No critical known CVE for OpenSSH 8.2p1 in this table",
    ("apache", "2.4.49"): "CVE-2021-41773 - path traversal and RCE",
    ("mysql", "8.0.32"): "No critical known CVE for MySQL 8.0.32 in this table",
    ("vsftpd", "2.3.4"): "CVE-2011-2523 - backdoor command execution in vsftpd 2.3.4",
}


def _result(command, r):
    return {"command": command, "output": r["output"], "success": r["success"]}


def _looks_missing(r, binary):
    o = r["output"].lower()
    return (not r["success"]) and ("not found" in o or f"{binary}: command" in o
                                   or "no such file" in o)


def nmap_scan(client, target=VM_TARGET_IP):
    """Service/version scan (nmap -sV). Installs nmap if missing, then retries."""
    cmd = f"nmap -sV {target}"
    r = exec_pooled(client, cmd)
    if _looks_missing(r, "nmap"):
        cmd = f"sudo apt-get install -y nmap && nmap -sV {target}"
        r = exec_pooled(client, cmd)
    return _result(cmd, r)


def port_scan(client, target=VM_TARGET_IP, port_range="1-1000"):
    """Port scan of a range (nmap -p)."""
    cmd = f"nmap -p {port_range} {target}"
    return _result(cmd, exec_pooled(client, cmd))


def ssh_connect(client, host=VM_TARGET_IP):
    """Prove SSH reachability of the target from the VM."""
    cmd = f"ssh -o ConnectTimeout=5 {VM_USER}@{host} echo connected"
    return _result(cmd, exec_pooled(client, cmd))


def check_vulnerability(client, service="ssh", version="OpenSSH_8.2"):
    """searchsploit lookup; falls back to the offline CVE table if exploitdb is
    not installed on the VM (SeedVM usually lacks it)."""
    cmd = f"searchsploit {service} {version}"
    r = exec_pooled(client, cmd)
    if _looks_missing(r, "searchsploit"):
        svc = service.strip().lower()
        hits = [f"{v}: {info}" for (s, v), info in _KNOWN_VULNS.items() if s == svc]
        body = "\n".join(hits) if hits else \
            f"No known vulnerability on record for {service} {version} (offline DB)."
        return {"command": cmd,
                "output": f"[searchsploit not installed; offline CVE table]\n{body}",
                "success": True}
    return _result(cmd, r)
