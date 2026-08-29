"""Cyber scenario — attacker / defender / shared agents over SSH tools.

For each query an LLM (Llama 3.2 3B) is asked for a single-word tool name from
the querying role's tool set, and the chosen tool is dispatched through the
cyber logging_tool wrapper. Runs in MOCK_MODE by default (no VMs) — see
tools/cyber/__init__.py and docs/VM_SETUP.md.

All 11 tools across 3 roles are dispatched. Trajectories for the whole run go to
one file, data/trajectories/cyber_logs.csv, with schema:
    prompt, tool_predicted, tool_ground_truth, agent_role, difficulty, category, run_id
"""

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from tools.cyber import MOCK_MODE, cyber_logs, logging_tool
from tools.cyber import attacker_tools as atk
from tools.cyber import defender_tools as dfd
from tools.cyber import shared_tools as shd
from tools.cyber.ssh_connector import connect_ssh

QUERIES_PATH = ROOT / "data" / "cyber_queries.json"
LOGS_PATH = ROOT / "data" / "trajectories" / "cyber_logs.csv"
MODEL = "llama3.2:3b"

SCHEMA = ["prompt", "tool_predicted", "tool_ground_truth",
          "agent_role", "difficulty", "category", "run_id"]

# Per-role tool dispatch (all 11 tools). Each callable takes (query, **meta),
# logs to cyber_logs and executes the tool (canned output in MOCK_MODE). Tools
# are wrapped in lambdas so every entry has the same (query) signature; args
# that the tool needs but the query text does not supply use lab defaults.
ATTACKER_TOOLS = {
    "SSHConnect": logging_tool("SSHConnect", lambda q: connect_ssh(atk.ATTACKER_HOST)),
    "NmapScan": logging_tool("NmapScan", lambda q: atk.nmap_scan()),
    "PortScan": logging_tool("PortScan", lambda q: atk.port_scan()),
    "CheckVulnerability": logging_tool("CheckVulnerability", lambda q: atk.check_vulnerability("ssh", "8.2")),
}
DEFENDER_TOOLS = {
    "ReadAuthLog": logging_tool("ReadAuthLog", lambda q: dfd.read_auth_log()),
    "ListeningPorts": logging_tool("ListeningPorts", lambda q: dfd.list_listening_ports()),
    "BlockIP": logging_tool("BlockIP", lambda q: dfd.block_ip("192.168.56.101")),
    "CheckFailedLogins": logging_tool("CheckFailedLogins", lambda q: dfd.check_failed_logins()),
    "ListProcesses": logging_tool("ListProcesses", lambda q: dfd.list_processes()),
}
SHARED_TOOLS = {
    "GetSystemInfo": logging_tool("GetSystemInfo", lambda q: shd.get_system_info()),
    "ReadSyslog": logging_tool("ReadSyslog", lambda q: shd.read_syslog()),
}

ROLE_TOOLS = {
    "attacker": ATTACKER_TOOLS,
    "defender": DEFENDER_TOOLS,
    "shared": SHARED_TOOLS,
}

_ROLE_INTRO = {
    "attacker": "a penetration-testing agent",
    "defender": "a defensive security agent",
    "shared": "a system-inspection agent",
}


def _system_prompt(role):
    tools = ", ".join(ROLE_TOOLS[role])
    return (f"You are a tool selector for {_ROLE_INTRO[role]}. Given a task, "
            f"respond with exactly one word — the tool to use, chosen from: {tools}.")


def select_tool(query: str, role: str) -> str:
    """Ask the LLM which tool to use for this role. Returns tool name or 'Unknown'."""
    valid = set(ROLE_TOOLS[role])
    try:
        import ollama
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": _system_prompt(role)},
                {"role": "user", "content": query},
            ],
            options={"temperature": 0, "seed": 42},
        )
        raw = response["message"]["content"].strip()
    except Exception as e:
        print(f"  LLM unavailable ({e}); falling back to keyword heuristic")
        raw = _heuristic(query, role)
    for token in raw.replace(".", " ").replace(":", " ").replace(",", " ").split():
        if token in valid:
            return token
    return "Unknown"


def _heuristic(query: str, role: str) -> str:
    """Offline fallback so the pipeline is testable without Ollama running.

    Only a safety net — the LLM is the real baseline. Deliberately simple, so on
    hard/ambiguous queries it will be wrong (as the LLM sometimes is).
    """
    q = query.lower()
    if role == "attacker":
        if "ssh" in q or "connect" in q or "shell" in q or "log in" in q or "onto" in q:
            return "SSHConnect"
        if "cve" in q or "vulnerab" in q or "exploit" in q or "advisor" in q:
            return "CheckVulnerability"
        if "version" in q or "service" in q or "software" in q or "fingerprint" in q:
            return "NmapScan"
        return "PortScan"
    if role == "defender":
        if "block" in q or "drop" in q or "firewall" in q or "ban" in q or "deny" in q or "blacklist" in q:
            return "BlockIP"
        if "failed" in q or "brute" in q or "guess" in q:
            return "CheckFailedLogins"
        if "listen" in q or "socket" in q or "bound" in q or ("port" in q and "open" in q):
            return "ListeningPorts"
        if "process" in q or "cpu" in q or "running" in q or "ps aux" in q:
            return "ListProcesses"
        return "ReadAuthLog"
    # shared
    if "syslog" in q or "system log" in q or "logs" in q:
        return "ReadSyslog"
    return "GetSystemInfo"


def _save(run_id):
    """Overwrite cyber_logs.csv with this run's rows (single deterministic pass;
    run_id is stored so history can be reconstructed if rows are ever appended)."""
    rows = [dict(r) for r in cyber_logs if r.get("run_id") == run_id
            and "tool_ground_truth" in r]
    df = pd.DataFrame(rows)[SCHEMA]
    LOGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(LOGS_PATH, index=False)
    print(f"\nSaved {len(df)} trajectories -> {LOGS_PATH.relative_to(ROOT)}")
    return df


def run_role(role, queries, run_id):
    tools = ROLE_TOOLS[role]
    role_q = [q for q in queries if q.get("agent") == role]
    print(f"\n=== {role.upper()} — {len(role_q)} queries "
          f"({len(tools)} tools, MOCK_MODE={MOCK_MODE}) ===")
    hits = 0
    for i, q in enumerate(role_q, 1):
        query_text, gt = q["query"], q.get("tool")
        chosen = select_tool(query_text, role)
        if chosen == gt:
            hits += 1
        meta = {
            "tool_ground_truth": gt, "agent_role": role,
            "difficulty": q.get("difficulty"), "category": q.get("category"),
            "run_id": run_id,
        }
        if chosen in tools:
            tools[chosen](query_text, **meta)
        else:
            cyber_logs.append({"prompt": query_text, "tool_predicted": chosen, **meta})
        if i % 40 == 0 or i == len(role_q):
            print(f"  [{i}/{len(role_q)}] running accuracy: {hits/i:.1%}")
    return hits, len(role_q)


def _summary(df):
    print("\n" + "=" * 60)
    print("Cyber trajectory collection — summary")
    print("=" * 60)
    print(f"Total rows: {len(df)}")

    print("\nPer-tool distribution (ground truth):")
    for tool, n in df["tool_ground_truth"].value_counts().items():
        print(f"  {tool:20} {n:3}")

    correct = df["tool_predicted"] == df["tool_ground_truth"]
    print("\nPer-difficulty LLM accuracy:")
    for diff, g in df.groupby("difficulty"):
        c = (g["tool_predicted"] == g["tool_ground_truth"]).mean()
        print(f"  {diff:6} n={len(g):3}  acc={c:.1%}")

    print("\nPer-category LLM accuracy:")
    order = ["direct", "ambiguous", "opposite", "multistep", "natural", "trick"]
    for cat in order:
        g = df[df["category"] == cat]
        if len(g):
            c = (g["tool_predicted"] == g["tool_ground_truth"]).mean()
            print(f"  {cat:10} n={len(g):3}  acc={c:.1%}")

    hard = df[df["difficulty"] == "hard"]
    hard_acc = (hard["tool_predicted"] == hard["tool_ground_truth"]).mean()
    print(f"\nOverall LLM baseline accuracy: {correct.mean():.1%}  ({correct.sum()}/{len(df)})")
    print(f"Hard-subset accuracy: {hard_acc:.1%}  (dataset-gen measured 72.5%)")


def run_agents():
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    cyber_logs.clear()
    print(f"Cyber run {run_id} — {len(queries)} queries total")
    for role in ("attacker", "defender", "shared"):
        run_role(role, queries, run_id)
    df = _save(run_id)
    _summary(df)


if __name__ == "__main__":
    run_agents()
