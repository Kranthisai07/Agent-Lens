"""Attacker tools — reconnaissance run from attacker-vm against a target.

Each tool SSHes into the attacker VM and runs the recon command there, so the
trajectory records what the attacker agent actually did. In MOCK_MODE the SSH
layer returns canned nmap output.

For authorized lab use only (see docs/VM_SETUP.md): the target must be a VM you
own on the isolated 192.168.56.0/24 host-only network.
"""

from .config import ATTACKER_HOST, DEFENDER_HOST
from .ssh_connector import run_on

TOOL_PREFIX = "Attacker"

# Small offline CVE table for check_vulnerability. TODO: query a real CVE
# source (NVD API / local vuln DB) once the lab has network policy for it.
_KNOWN_VULNS = {
    ("openssh", "7.2"): "CVE-2016-6210 — user enumeration via timing (OpenSSH < 7.3)",
    ("openssh", "8.2"): "No critical known CVE for OpenSSH 8.2p1 in this table",
    ("apache", "2.4.41"): "CVE-2021-41773 — path traversal/RCE (Apache 2.4.49/50; verify build)",
    ("apache", "2.4.49"): "CVE-2021-41773 — path traversal and RCE",
    ("mysql", "8.0.32"): "No critical known CVE for MySQL 8.0.32 in this table",
    ("vsftpd", "2.3.4"): "CVE-2011-2523 — backdoor command execution in vsftpd 2.3.4",
}


def nmap_scan(target_ip=DEFENDER_HOST) -> str:
    """Service/version scan (nmap -sV) of the target, launched from attacker-vm."""
    return run_on(ATTACKER_HOST, f"nmap -sV {target_ip}")


def port_scan(target_ip=DEFENDER_HOST, port_range="1-1000") -> str:
    """Port scan of a range (nmap -p) on the target, launched from attacker-vm."""
    return run_on(ATTACKER_HOST, f"nmap -p {port_range} {target_ip}")


def check_vulnerability(service: str, version: str = "") -> str:
    """Look up known CVEs for a service/version. Mock table for now."""
    key = (service.strip().lower(), version.strip())
    if key in _KNOWN_VULNS:
        return _KNOWN_VULNS[key]
    # fall back to any version match on the service name
    svc = service.strip().lower()
    hits = [f"{v}: {info}" for (s, v), info in _KNOWN_VULNS.items() if s == svc]
    if hits:
        return f"No exact match for {service} {version}. Related:\n" + "\n".join(hits)
    return f"No known vulnerability on record for {service} {version} (mock DB)."
