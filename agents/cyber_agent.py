"""Cyber scenario — attacker and defender agents over SSH tools.

Same pattern as agents/crew_agent.py: for each query an LLM (Llama 3.2 3B) is
asked for a single-word tool name, and the chosen tool is dispatched through
the cyber logging_tool wrapper. Two agents each run their own query set and
write their own trajectory CSV.

Runs in MOCK_MODE by default (no VMs needed) — see tools/cyber/__init__.py and
docs/VM_SETUP.md. The trajectory schema is:
    prompt, tool_predicted, tool_ground_truth, agent_role, run_id
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from tools.cyber import MOCK_MODE, cyber_logs, logging_tool
from tools.cyber import attacker_tools as atk
from tools.cyber import defender_tools as dfd
from tools.cyber.ssh_connector import connect_ssh

QUERIES_PATH = ROOT / "data" / "cyber_queries.json"
TRAJ_DIR = ROOT / "data" / "trajectories"
MODEL = "llama3.2:3b"

SCHEMA = ["prompt", "tool_predicted", "tool_ground_truth", "agent_role", "run_id"]

# Per-role tool dispatch. The wrapped callables take (query, **meta) and log to
# cyber_logs. SSHConnect wraps a lambda so its signature matches the others.
ATTACKER_TOOLS = {
    "SSHConnect": logging_tool("SSHConnect", lambda q: connect_ssh(atk.ATTACKER_HOST)),
    "NmapScan": logging_tool("NmapScan", lambda q: atk.nmap_scan()),
    "PortScan": logging_tool("PortScan", lambda q: atk.port_scan()),
}
DEFENDER_TOOLS = {
    "ReadAuthLog": logging_tool("ReadAuthLog", lambda q: dfd.read_auth_log()),
    "ListeningPorts": logging_tool("ListeningPorts", lambda q: dfd.list_listening_ports()),
    "BlockIP": logging_tool("BlockIP", lambda q: dfd.block_ip("192.168.56.101")),
}

ROLE_TOOLS = {"attacker": ATTACKER_TOOLS, "defender": DEFENDER_TOOLS}

ROLE_SYSTEM_PROMPT = {
    "attacker": (
        "You are a tool selector for a penetration-testing agent. Given a task, "
        "respond with exactly one word naming the tool to use: "
        "SSHConnect, NmapScan, or PortScan."
    ),
    "defender": (
        "You are a tool selector for a defensive security agent. Given a task, "
        "respond with exactly one word naming the tool to use: "
        "ReadAuthLog, ListeningPorts, or BlockIP."
    ),
}


def select_tool(query: str, role: str) -> str:
    """Ask the LLM which tool to use for this role. Returns tool name or 'Unknown'."""
    valid = set(ROLE_TOOLS[role])
    try:
        import ollama
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": ROLE_SYSTEM_PROMPT[role]},
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
    """Offline fallback so the pipeline is testable without Ollama running."""
    q = query.lower()
    if role == "attacker":
        if "ssh" in q or "connect" in q or "shell" in q or "log in" in q:
            return "SSHConnect"
        if "service" in q or "version" in q or "software" in q or "fingerprint" in q:
            return "NmapScan"
        return "PortScan"
    if "block" in q or "drop" in q or "firewall" in q or "ban" in q or "deny" in q or "blacklist" in q or "stop traffic" in q:
        return "BlockIP"
    if "listen" in q or "port" in q or "socket" in q or "bound" in q:
        return "ListeningPorts"
    return "ReadAuthLog"


def _save(role, run_id):
    rows = [dict(r) for r in cyber_logs
            if r.get("agent_role") == role and r.get("run_id") == run_id
            and "tool_ground_truth" in r]
    if not rows:
        print(f"  no {role} trajectories to save")
        return None
    df = pd.DataFrame(rows)[SCHEMA]
    TRAJ_DIR.mkdir(parents=True, exist_ok=True)
    path = TRAJ_DIR / f"{role}_logs.csv"
    if path.exists():
        existing = pd.read_csv(path)
        if list(existing.columns) == SCHEMA:
            df = pd.concat([existing, df], ignore_index=True)
        else:
            archive = path.with_name(f"{role}_logs_v1.csv")
            path.rename(archive)
            print(f"  archived legacy {role} logs -> {archive.name}")
    df.to_csv(path, index=False)
    print(f"  saved {len(rows)} new ({len(df)} total) -> {path.relative_to(ROOT)}")
    return path


def run_role(role, queries, run_id):
    tools = ROLE_TOOLS[role]
    role_q = [q for q in queries if q.get("agent") == role]
    print(f"\n=== {role.upper()} — {len(role_q)} queries (MOCK_MODE={MOCK_MODE}) ===")
    hits = 0
    for i, q in enumerate(role_q, 1):
        query_text, gt = q["query"], q.get("tool")
        chosen = select_tool(query_text, role)
        if chosen == gt:
            hits += 1
        meta = {"tool_ground_truth": gt, "agent_role": role, "run_id": run_id}
        if chosen in tools:
            tools[chosen](query_text, **meta)
        else:
            cyber_logs.append({"prompt": query_text, "tool_predicted": chosen, **meta})
        if i % 10 == 0 or i == len(role_q):
            print(f"  [{i}/{len(role_q)}] running accuracy: {hits/i:.1%}")
    _save(role, run_id)
    return hits, len(role_q)


def run_agents():
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    cyber_logs.clear()
    print(f"Cyber run {run_id} — {len(queries)} queries total")
    totals = {}
    for role in ("attacker", "defender"):
        totals[role] = run_role(role, queries, run_id)
    print("\n=== Summary ===")
    for role, (hits, n) in totals.items():
        print(f"  {role:9} LLM vs ground truth: {hits}/{n} = {hits/max(n,1):.1%}")


if __name__ == "__main__":
    run_agents()
