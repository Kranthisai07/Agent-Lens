"""Two-VM attacker/defender scenario — the core experiment.

Calix's requirement: firewall starts OFF, attacker sends traffic, defender
detects and blocks. Three rounds (recon -> escalation -> defense) run over live
SSH to two real VMs (config: ATTACKER_VM_* = 10.0.0.188, DEFENDER_VM_* =
10.0.0.114). Each defender round ends with an LLM (Llama 3.2 3B) analysis.

Every action is logged with schema:
  round, agent_role, tool, command, output, success, llm_prompt, llm_response,
  timestamp
-> data/trajectories/two_vm_scenario.csv

Deviations from the literal step list, for correctness (all flagged in output):
- `sudo ufw --force enable` (bare `ufw enable` hangs on an interactive y/n
  prompt over non-interactive SSH).
- A setup step `sudo ufw --force reset` so the premise "firewall starts OFF"
  holds on re-runs (a stale deny rule would otherwise pre-block the attacker).
- A post-block verification probe (attacker -> defender AFTER the block). `ufw
  deny from` blocks TCP/UDP but NOT ICMP echo (ufw before.rules accepts ping),
  so the authoritative probe is TCP:22; a ping is kept only to document ICMP.
- `sudo ufw allow 22/tcp` before enabling — otherwise default-deny locks out the
  next SSH connection (this happened once and required console recovery).
- `sudo ufw insert 1 deny from <attacker>` (not a plain append) so the deny is
  evaluated before the allow-22 rule and actually blocks the attacker's TCP:22.

Run: python agents/attacker_defender_scenario.py
"""

import socket
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from tools.cyber.config import (ATTACKER_VM_HOST, ATTACKER_VM_PASS,
                                ATTACKER_VM_PORT, ATTACKER_VM_USER,
                                DEFENDER_VM_HOST, DEFENDER_VM_PASS,
                                DEFENDER_VM_PORT, DEFENDER_VM_USER)
from tools.cyber.ssh_connector import exec_pooled, open_pool

OUT_PATH = ROOT / "data" / "trajectories" / "two_vm_scenario.csv"
MODEL = "llama3.2:3b"
SCHEMA = ["round", "agent_role", "tool", "command", "output", "success",
          "llm_prompt", "llm_response", "timestamp"]
OUTPUT_CAP = 2000

ATTACKER_IP = ATTACKER_VM_HOST  # 10.0.0.188
DEFENDER_IP = DEFENDER_VM_HOST  # 10.0.0.114

rows = []
_ollama_up = False


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _check_ollama():
    global _ollama_up
    s = socket.socket()
    s.settimeout(3)
    _ollama_up = s.connect_ex(("127.0.0.1", 11434)) == 0
    s.close()
    if not _ollama_up:
        print("WARNING: Ollama not responding on 127.0.0.1:11434 — LLM analysis "
              "will be logged as OLLAMA_UNAVAILABLE.\n")
    return _ollama_up


def act(rnd, role, client, tool, command, timeout=15):
    """Run a command on a VM and log the action. Returns the result dict."""
    res = exec_pooled(client, command, timeout=timeout)
    status = "TIMEOUT" if res["output"] == "TIMEOUT" else ("OK" if res["success"] else "FAIL")
    print(f"  [R{rnd} {role:8}] {tool:16} $ {command[:60]}  [{status}]")
    rows.append({"round": rnd, "agent_role": role, "tool": tool, "command": command,
                 "output": res["output"][:OUTPUT_CAP], "success": res["success"],
                 "llm_prompt": "", "llm_response": "", "timestamp": _now()})
    return res


def analyze(rnd, prompt):
    """Defender LLM analysis; logs its own row. Degrades to OLLAMA_UNAVAILABLE."""
    response = "OLLAMA_UNAVAILABLE"
    if _ollama_up:
        try:
            import ollama
            r = ollama.chat(model=MODEL, messages=[
                {"role": "system", "content": "You are a cybersecurity defender. "
                 "Be concise and specific."},
                {"role": "user", "content": prompt}],
                options={"temperature": 0, "seed": 42})
            response = r["message"]["content"].strip()
        except Exception as e:  # noqa: BLE001
            response = f"OLLAMA_ERROR: {e}"
    print(f"  [R{rnd} defender  LLM analysis] -> {response[:70]!r}")
    rows.append({"round": rnd, "agent_role": "defender", "tool": "LLMAnalysis",
                 "command": "", "output": "", "success": response not in
                 ("OLLAMA_UNAVAILABLE",) and not response.startswith("OLLAMA_ERROR"),
                 "llm_prompt": prompt[:OUTPUT_CAP], "llm_response": response[:OUTPUT_CAP],
                 "timestamp": _now()})
    return response


def _have(client, binary):
    return exec_pooled(client, f"command -v {binary} || which {binary}",
                       timeout=8)["success"]


def main():
    _check_ollama()
    print(f"Attacker {ATTACKER_VM_USER}@{ATTACKER_IP}:{ATTACKER_VM_PORT}  |  "
          f"Defender {DEFENDER_VM_USER}@{DEFENDER_IP}:{DEFENDER_VM_PORT}\n")

    atk = open_pool(ATTACKER_IP, ATTACKER_VM_PORT, ATTACKER_VM_USER, ATTACKER_VM_PASS)
    dfd = open_pool(DEFENDER_IP, DEFENDER_VM_PORT, DEFENDER_VM_USER, DEFENDER_VM_PASS)
    if atk is None or dfd is None:
        print(f"\nCannot open both connections (attacker={'ok' if atk else 'FAIL'}, "
              f"defender={'ok' if dfd else 'FAIL'}). Run agents/test_two_vm.py; "
              "see docs/VM_SETUP.md.")
        if atk:
            atk.close()
        if dfd:
            dfd.close()
        return 1

    nmap_ok = _have(atk, "nmap")
    nc_ok = _have(atk, "nc")

    try:
        # ---- Setup: ensure firewall starts OFF and clean (reproducible premise) ----
        print("Setup: ensuring defender firewall starts OFF")
        act(0, "defender", dfd, "ResetFirewall", "sudo ufw --force reset", timeout=25)

        # ================= ROUND 1 — Reconnaissance =================
        print("\n=== ROUND 1 — Reconnaissance ===")
        r1_ping = act(1, "attacker", atk, "PingTarget",
                      f"ping -c 5 {DEFENDER_IP}", timeout=15)
        if nmap_ok:
            act(1, "attacker", atk, "NmapScan",
                f"nmap -p 22,80,443 {DEFENDER_IP}", timeout=20)
        else:
            act(1, "attacker", atk, "NmapScan", "nmap (unavailable, skipped)", timeout=5)

        auth1 = act(1, "defender", dfd, "ReadAuthLog",
                    "sudo tail -20 /var/log/auth.log", timeout=12)
        ports1 = act(1, "defender", dfd, "ListeningPorts", "ss -tlnp", timeout=10)
        analyze(1, "You are a cybersecurity defender. Analyze this auth log and "
                   "network state. Is there suspicious activity? What should you do?\n\n"
                   f"AUTH LOG:\n{auth1['output']}\n\nLISTENING PORTS:\n{ports1['output']}")

        # ================= ROUND 2 — Attack escalation =================
        print("\n=== ROUND 2 — Attack escalation ===")
        act(2, "attacker", atk, "PingFlood", f"ping -c 10 {DEFENDER_IP}", timeout=20)
        if nc_ok:
            act(2, "attacker", atk, "PortProbe",
                f"for port in 22 80 443 3306 5432; do nc -zv {DEFENDER_IP} $port 2>&1; done",
                timeout=25)
        else:
            act(2, "attacker", atk, "PortProbe", "nc (unavailable, skipped)", timeout=5)

        auth2 = act(2, "defender", dfd, "ReadAuthLog",
                    "sudo tail -30 /var/log/auth.log", timeout=12)
        # Allow management SSH BEFORE enabling — otherwise ufw's default deny
        # (incoming) locks out all NEW SSH connections. The in-session connection
        # survives via the ESTABLISHED rule, but the next run cannot reconnect
        # (this happened once: the defender had to be recovered from the console).
        act(2, "defender", dfd, "AllowSSH", "sudo ufw allow 22/tcp", timeout=12)
        act(2, "defender", dfd, "EnableFirewall", "sudo ufw --force enable", timeout=20)
        stat2 = act(2, "defender", dfd, "FirewallStatus", "sudo ufw status", timeout=12)
        analyze(2, "You are a cybersecurity defender. The firewall is now enabled. "
                   f"The suspected attacker IP is {ATTACKER_IP}. What rule should you "
                   "add to block the attacker?\n\n"
                   f"RECENT AUTH LOG:\n{auth2['output']}\n\nUFW STATUS:\n{stat2['output']}")

        # ================= ROUND 3 — Defense response =================
        print("\n=== ROUND 3 — Defense response ===")
        # (spec) attacker pings BEFORE the block is applied -> expected to succeed
        r3_ping_pre = act(3, "attacker", atk, "PingTarget",
                          f"ping -c 5 {DEFENDER_IP}", timeout=15)

        # insert at position 1 so the deny precedes the "allow 22/tcp" rule;
        # a plain `ufw deny from` would be appended AFTER the allow and the
        # attacker's TCP:22 would still match the allow first.
        block = act(3, "defender", dfd, "BlockAttackerIP",
                    f"sudo ufw insert 1 deny from {ATTACKER_IP}", timeout=15)
        stat3 = act(3, "defender", dfd, "FirewallStatus",
                    "sudo ufw status verbose", timeout=12)
        act(3, "defender", dfd, "ReadAuthLog",
            "sudo tail -10 /var/log/auth.log", timeout=12)
        analyze(3, f"You are a cybersecurity defender. Attacker IP {ATTACKER_IP} has "
                   "been blocked. Summarize what happened and what was defended.\n\n"
                   f"UFW STATUS:\n{stat3['output']}")

        # (added) verify the block AFTER the deny rule. `ufw deny from` blocks
        # TCP/UDP but NOT ICMP echo (ufw before.rules accepts ping ahead of user
        # rules), so the authoritative probe is TCP:22; ping is kept for the record
        # to document that ICMP still passes.
        r3_tcp_post = act(3, "attacker", atk, "VerifyBlockedTCP",
                          f"timeout 6 bash -c 'echo > /dev/tcp/{DEFENDER_IP}/22' "
                          f"&& echo REACHABLE || echo BLOCKED", timeout=12)
        r3_ping_post = act(3, "attacker", atk, "VerifyBlockedPing",
                           f"ping -c 3 {DEFENDER_IP}", timeout=12)
    finally:
        atk.close()
        dfd.close()

    df = pd.DataFrame(rows)[SCHEMA]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)

    # ---- summary ----
    fw_enabled = any(r["tool"] == "EnableFirewall" and r["success"] for r in rows)
    tcp_blocked = "BLOCKED" in r3_tcp_post["output"]   # authoritative: TCP:22
    print("\n=== SCENARIO COMPLETE ===")
    print(f"Round 1: Attacker pinged defender [{'OK' if r1_ping['success'] else 'FAIL'}]")
    print(f"Round 2: Defender enabled firewall [{'OK' if fw_enabled else 'FAIL'}]")
    print(f"Round 3: Attacker blocked [{'OK' if tcp_blocked else 'FAIL'}]")
    print(f"  post-block TCP:22 -> {'BLOCKED' if tcp_blocked else 'REACHABLE'}; "
          f"post-block ICMP ping -> "
          f"{'still passes (ufw permits ICMP echo)' if r3_ping_post['success'] else 'blocked'}")
    print(f"Total actions logged: {len(rows)}")
    print(f"Saved to: {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
