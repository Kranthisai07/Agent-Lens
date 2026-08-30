"""Generate and validate data/cyber_queries.json — 600+ labelled cyber queries.

Two agents (attacker, defender) plus shared tools, 11 tools total. Every query
carries two extra fields beyond {query, tool, agent}:

  difficulty : easy | hard
  category   : direct | ambiguous | opposite | multistep | natural | trick

`direct` queries (difficulty=easy) have one unambiguous tool cue — the control /
baseline. The five `hard` categories are distinct ways of confusing tool
selection, so the paper can report a category -> LLM-accuracy breakdown (which
query styles fool the small LLM most), not just a single number:

  ambiguous  — plausibly fits two+ tools; the label is defensible, not unique
  opposite   — surface verb/keyword leans toward a sibling tool; the actual ask
               still resolves to the labelled tool
  multistep  — describes a mini workflow; labelled with the PRIMARY step
  natural    — casual human phrasing, no security jargon
  trick      — contains an explicit decoy keyword / negation for another tool

Designed so the LLM lands ~65-75% on the hard subset (vs the saturated general
dataset — see MEMORY.md Phase 4-5 Results), giving the trained classifier real
headroom. Seeded for reproducibility.

Run: python scripts/generate_cyber_queries.py
"""

import json
import random
from collections import Counter
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "cyber_queries.json"

AGENT_OF = {
    "SSHConnect": "attacker", "NmapScan": "attacker",
    "PortScan": "attacker", "CheckVulnerability": "attacker",
    "ReadAuthLog": "defender", "ListeningPorts": "defender",
    "BlockIP": "defender", "CheckFailedLogins": "defender",
    "ListProcesses": "defender",
    "GetSystemInfo": "shared", "ReadSyslog": "shared",
}

TARGET_EASY = 40          # per tool (-> 440 direct)
TARGET_HARD_CAT = 40      # per hard category (-> ~200 hard)

TARGETS = ["192.168.56.102", "the target", "the defender", "the defender host",
           "the target machine", "the target VM", "192.168.56.102"]
IPS = ["192.168.56.101", "the attacker IP", "the suspicious IP",
       "the malicious host", "10.0.0.66", "the flagged address", "192.168.56.101"]
SERVICES = ["ssh", "OpenSSH", "Apache", "http", "MySQL", "nginx", "vsftpd", "the web server"]
VERSIONS = ["8.2", "2.4.49", "8.0.32", "2.3.4", "7.2", "1.18"]
RANGES = ["1-1000", "1-65535", "22-443", "80-8080", "1-1024"]
RECENT = ["", " recently", " in the last hour", " today", " since boot",
          " right now", " this morning", " over the past day", " just now", " lately"]
# host-scope suffix so log/system tools (few other slots) reach unique counts
HOSTS = ["", " on this host", " on the defender", " on this box",
         " on the server", " here", " on this machine"]


# ---------- EASY / direct: one unambiguous cue per tool ----------
EASY = {
    "SSHConnect": [
        "Connect to {t} via SSH", "Open an SSH session to {t}", "SSH into {t}",
        "Establish an SSH connection to {t}", "Log in to {t} over SSH",
        "Start a remote shell on {t} via SSH", "Authenticate to {t} over SSH",
        "Get an SSH connection to {t}", "Open a secure shell to {t}",
        "SSH to {t} and open a session",
    ],
    "NmapScan": [
        "Run an nmap -sV version scan of {t}",
        "Do a service and version detection scan on {t}",
        "Fingerprint the service versions on {t} with nmap",
        "What service versions are running on {t}?",
        "Enumerate services and their versions on {t}",
        "Use nmap -sV to detect software versions on {t}",
        "Identify the exact service versions exposed by {t}",
    ],
    "PortScan": [
        "Scan ports {r} on {t}", "Do a port scan of {t} over range {r}",
        "Which TCP ports in {r} are open on {t}?", "Run nmap -p {r} against {t}",
        "Enumerate open ports on {t} across {r}", "List the open TCP ports on {t}",
        "Port-scan {t} and report which ports are open",
    ],
    "CheckVulnerability": [
        "Look up known CVEs for {s} {v}",
        "Does {s} version {v} have any known vulnerabilities?",
        "Check {s} {v} against the vulnerability database",
        "Find published CVEs affecting {s} {v}",
        "Is {s} {v} vulnerable to any known exploits?",
        "Report known security advisories for {s} {v}",
    ],
    "ReadAuthLog": [
        "Show the recent authentication log{w}{h}", "Read the last entries in /var/log/auth.log{h}",
        "Display the tail of the auth log{w}{h}", "Dump the recent lines of auth.log{h}",
        "Show me the SSH authentication events{w}{h}", "Read the system authentication log{h}",
    ],
    "ListeningPorts": [
        "Which local ports are in LISTEN state{w}{h}?", "Run ss -tlnp and show the listening sockets{h}",
        "List the ports in LISTEN state{w}{h}", "Show the open listening TCP sockets{h}",
        "What server ports are bound and listening{w}{h}?", "Enumerate the listening ports{w}{h}",
    ],
    "BlockIP": [
        "Block {ip} with iptables", "Add an iptables DROP rule for {ip}",
        "Firewall off {ip}", "Drop all incoming traffic from {ip}",
        "Deny network access from {ip} at the firewall", "Blacklist {ip} on the firewall",
        "Ban {ip} using iptables",
    ],
    "CheckFailedLogins": [
        "Grep auth.log for failed password attempts{w}{h}", "How many failed SSH logins were there{w}{h}?",
        "Count the failed login attempts{w}{h}", "Show the failed password entries from auth.log{h}",
        "List recent failed login attempts{w}{h}", "Find failed SSH authentication attempts{w}{h}",
    ],
    "ListProcesses": [
        "List the running processes sorted by CPU{w}{h}", "Run ps aux and show the top processes{w}{h}",
        "Which processes are using the most CPU{w}{h}?", "Show the top processes by CPU usage{h}",
        "Enumerate the running processes{w}{h}", "Give me the process list sorted by CPU{h}",
    ],
    "GetSystemInfo": [
        "Show the hostname, kernel and uptime{w}{h}", "Run uname -a and uptime{h}",
        "What OS and kernel is this machine running{h}?", "Report the system info: hostname, OS, uptime{h}",
        "Give me the uname and load average{w}{h}", "Show basic system information{w}{h}",
    ],
    "ReadSyslog": [
        "Show the last entries of /var/log/syslog{w}{h}", "Read the recent syslog messages{w}{h}",
        "Tail the system log (syslog){w}{h}", "Dump recent /var/log/syslog lines{h}",
        "Display the tail of the syslog{w}{h}", "Show me the recent general system log entries{w}{h}",
    ],
}

# ---------- HARD: keyed by category, each entry is (tool, template) ----------
HARD = {
    "ambiguous": [
        # genuinely 2+ tools plausible — the disambiguating keyword is REMOVED
        ("PortScan", "Scan {t} and see what comes back"),
        ("NmapScan", "Run a scan against {t}"),
        ("PortScan", "Do some recon on {t}"),
        ("NmapScan", "Check {t} over the network"),
        ("PortScan", "Probe {t} for me"),
        ("CheckVulnerability", "Look at {s} on {t} from a security angle"),
        ("ReadAuthLog", "Check this host for suspicious activity{w}"),
        ("CheckFailedLogins", "Look for signs of an attack in the logs{w}"),
        ("ReadSyslog", "Review the logs for anything unusual{w}"),
        ("ListeningPorts", "Check what's exposed on this host{w}"),
        ("ListProcesses", "See what's active on this box{w}"),
        ("GetSystemInfo", "Give me an overview of this host{w}"),
        ("ReadSyslog", "Show me what the system has been up to{w}"),
    ],
    "opposite": [
        ("CheckFailedLogins", "Read the auth log and pull out just the failed password lines"),
        ("NmapScan", "Do a port scan of {t} that also reports the service version on each port"),
        ("PortScan", "Run nmap on {t} but I only care which ports are open, not versions"),
        ("ReadAuthLog", "Check the failed logins — actually, just show me the whole auth log"),
        ("ReadSyslog", "Forget the auth log, show me the general system log instead"),
        ("ListeningPorts", "Never mind the processes — which sockets are in LISTEN state{w}?"),
        ("ListProcesses", "I don't need the listening ports, just the processes eating CPU"),
        ("CheckVulnerability", "Don't just scan {t} — tell me if {s} {v} is actually exploitable"),
        ("GetSystemInfo", "Skip the logs, I only want the uptime and kernel of this host"),
    ],
    "multistep": [
        ("PortScan", "First scan {t} for open ports, then we'll look at versions"),
        ("NmapScan", "After the port scan, run version detection on {t}"),
        ("CheckFailedLogins", "Find the failed SSH logins so we can block the source"),
        ("BlockIP", "We identified {ip} as the attacker — now block it"),
        ("ReadAuthLog", "Pull the auth log first, then we'll count the failures"),
        ("ListeningPorts", "List listening ports, then we'll map them to processes"),
        ("GetSystemInfo", "Grab the system info before we dig into the logs"),
        ("CheckVulnerability", "Once we know it's {s} {v}, check it for known CVEs"),
        ("ListProcesses", "Show the processes, then we'll decide what to kill"),
    ],
    "natural": [
        ("CheckFailedLogins", "Someone keeps trying to get into the server{w} — can you check?"),
        ("ReadAuthLog", "Who's been logging into this machine lately?"),
        ("ListeningPorts", "What's my server got open to the network right now?"),
        ("ListProcesses", "Why is this box so slow? What's hogging it?"),
        ("BlockIP", "{ip} is clearly bad news — get rid of it"),
        ("NmapScan", "What's actually running on {t}?"),
        ("PortScan", "Can you see what doors are open on {t}?"),
        ("GetSystemInfo", "How long has this thing been running, and what is it?"),
        ("ReadSyslog", "Anything weird in the logs{w}?"),
        ("CheckVulnerability", "Is that old {s} on there going to get us hacked?"),
        ("SSHConnect", "Can you get me onto {t}?"),
    ],
    "trick": [
        ("ListProcesses", "Don't scan any ports — just tell me what processes are running{w}"),
        ("ReadSyslog", "This isn't about failed logins — show me the plain syslog"),
        ("PortScan", "No need for service versions, only tell me which ports are open on {t}"),
        ("ListeningPorts", "Ignore the running processes; I want the listening ports{w}"),
        ("CheckFailedLogins", "Not the whole auth log — only the failed password attempts"),
        ("NmapScan", "Skip the plain port list, I need the service versions on {t}"),
        ("GetSystemInfo", "I don't want the process list, just uptime and kernel"),
        ("BlockIP", "Don't just log it — actually block {ip} at the firewall"),
        ("ReadAuthLog", "Not the syslog — I mean the authentication log{w}"),
    ],
}


def _fill(tmpl):
    q = tmpl.format(
        t=random.choice(TARGETS), r=random.choice(RANGES),
        s=random.choice(SERVICES), v=random.choice(VERSIONS),
        ip=random.choice(IPS), w=random.choice(RECENT), h=random.choice(HOSTS),
    )
    # collapse any double spaces left by empty fillers, and fix " ?" spacing
    return " ".join(q.split()).replace(" ?", "?")


def _build_easy(pool, target, seen):
    out, attempts = [], 0
    while len(out) < target and attempts < target * 80:
        attempts += 1
        q = _fill(random.choice(pool)).strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _build_hard(pairs, target, seen):
    """pairs: list of (tool, template). Returns list of (tool, query)."""
    out, attempts = [], 0
    while len(out) < target and attempts < target * 120:
        attempts += 1
        tool, tmpl = random.choice(pairs)
        q = _fill(tmpl).strip()
        if q and q not in seen:
            seen.add(q)
            out.append((tool, q))
    return out


def main():
    seen = set()
    rows = []

    for tool, pool in EASY.items():
        for q in _build_easy(pool, TARGET_EASY, seen):
            rows.append({"query": q, "tool": tool, "agent": AGENT_OF[tool],
                         "difficulty": "easy", "category": "direct"})

    for cat, pairs in HARD.items():
        for tool, q in _build_hard(pairs, TARGET_HARD_CAT, seen):
            rows.append({"query": q, "tool": tool, "agent": AGENT_OF[tool],
                         "difficulty": "hard", "category": cat})

    random.shuffle(rows)
    OUT_PATH.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    by_tool = Counter(r["tool"] for r in rows)
    by_agent = Counter(r["agent"] for r in rows)
    by_diff = Counter(r["difficulty"] for r in rows)
    by_cat = Counter(r["category"] for r in rows)
    dupes = [q for q, c in Counter(r["query"] for r in rows).items() if c > 1]

    print(f"Wrote {OUT_PATH.relative_to(ROOT)} with {len(rows)} queries.")
    print(f"By agent      : {dict(by_agent)}")
    print(f"By difficulty : {dict(by_diff)}")
    print(f"By category   : {dict(by_cat)}")
    print("Per tool:")
    for tool in AGENT_OF:
        print(f"  {tool:20} {by_tool[tool]:3}")
    print(f"Duplicates: {len(dupes)}")

    assert len(rows) >= 600, f"need >=600, got {len(rows)}"
    assert not dupes, f"duplicates: {dupes[:3]}"
    for tool in AGENT_OF:
        assert by_tool[tool] >= 40, f"{tool} only {by_tool[tool]}"
    for cat in HARD:
        assert by_cat[cat] >= 30, f"category {cat} only {by_cat[cat]}"
    print("Validation passed.")


if __name__ == "__main__":
    main()
