"""Cyber scenario — attacker / defender / shared agents over SSH tools.

For each query an LLM (Llama 3.2 3B) picks a tool from the querying role's tool
set; the chosen tool then runs its real command on the VM over ONE pooled SSH
connection (cyber-04). AGENTLENS_MOCK=1 forces the old mock flow.

Real run  -> data/trajectories/cyber_logs_real.csv (adds command/output/success)
Mock run  -> data/trajectories/cyber_logs.csv (7-field schema)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from tools.cyber import MOCK_MODE
from tools.cyber import attacker_tools as atk
from tools.cyber import defender_tools as dfd
from tools.cyber import shared_tools as shd
from tools.cyber.config import VM_HOST, VM_PORT, VM_USER
from tools.cyber.ssh_connector import open_pool

QUERIES_PATH = ROOT / "data" / "cyber_queries.json"
TRAJ_DIR = ROOT / "data" / "trajectories"
REAL_PATH = TRAJ_DIR / "cyber_logs_real.csv"
MOCK_PATH = TRAJ_DIR / "cyber_logs.csv"
MODEL = "llama3.2:3b"
MOCK_BASELINE = 0.794  # overall LLM accuracy from the mock run (cyber_logs.csv)
OUTPUT_CAP = 2000      # chars of tool output stored per row

REAL_SCHEMA = ["prompt", "tool_predicted", "tool_ground_truth", "agent_role",
               "difficulty", "category", "command", "output", "success", "run_id"]
MOCK_SCHEMA = ["prompt", "tool_predicted", "tool_ground_truth", "agent_role",
               "difficulty", "category", "run_id"]

# tool name -> callable(client) -> {"command","output","success"}
DISPATCH = {
    "SSHConnect": lambda c: atk.ssh_connect(c),
    "NmapScan": lambda c: atk.nmap_scan(c),
    "PortScan": lambda c: atk.port_scan(c),
    "CheckVulnerability": lambda c: atk.check_vulnerability(c),
    "ReadAuthLog": lambda c: dfd.read_auth_log(c),
    "ListeningPorts": lambda c: dfd.list_listening_ports(c),
    "BlockIP": lambda c: dfd.block_ip(c),
    "CheckFailedLogins": lambda c: dfd.check_failed_logins(c),
    "ListProcesses": lambda c: dfd.list_processes(c),
    "GetSystemInfo": lambda c: shd.get_system_info(c),
    "ReadSyslog": lambda c: shd.read_syslog(c),
}
ROLE_TOOLS = {
    "attacker": ["SSHConnect", "NmapScan", "PortScan", "CheckVulnerability"],
    "defender": ["ReadAuthLog", "ListeningPorts", "BlockIP",
                 "CheckFailedLogins", "ListProcesses"],
    "shared": ["GetSystemInfo", "ReadSyslog"],
}
_ROLE_INTRO = {"attacker": "a penetration-testing agent",
               "defender": "a defensive security agent",
               "shared": "a system-inspection agent"}


def _system_prompt(role):
    return (f"You are a tool selector for {_ROLE_INTRO[role]}. Given a task, "
            f"respond with exactly one word — the tool to use, chosen from: "
            f"{', '.join(ROLE_TOOLS[role])}.")


def select_tool(query, role):
    """LLM tool selection; falls back to a keyword heuristic if Ollama is down."""
    valid = set(ROLE_TOOLS[role])
    try:
        import ollama
        resp = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": _system_prompt(role)},
            {"role": "user", "content": query}],
            options={"temperature": 0, "seed": 42})
        raw = resp["message"]["content"].strip()
    except Exception as e:  # noqa: BLE001
        print(f"  LLM unavailable ({e}); using keyword heuristic")
        raw = _heuristic(query, role)
    for tok in raw.replace(".", " ").replace(":", " ").replace(",", " ").split():
        if tok in valid:
            return tok
    return "Unknown"


def _heuristic(query, role):
    q = query.lower()
    if role == "attacker":
        if any(w in q for w in ("ssh", "connect", "shell", "log in", "onto")):
            return "SSHConnect"
        if any(w in q for w in ("cve", "vulnerab", "exploit", "advisor")):
            return "CheckVulnerability"
        if any(w in q for w in ("version", "service", "software", "fingerprint")):
            return "NmapScan"
        return "PortScan"
    if role == "defender":
        if any(w in q for w in ("block", "drop", "firewall", "ban", "deny", "blacklist")):
            return "BlockIP"
        if any(w in q for w in ("failed", "brute", "guess")):
            return "CheckFailedLogins"
        if "listen" in q or "socket" in q or "bound" in q or ("port" in q and "open" in q):
            return "ListeningPorts"
        if any(w in q for w in ("process", "cpu", "running", "ps aux")):
            return "ListProcesses"
        return "ReadAuthLog"
    if "syslog" in q or "system log" in q or "logs" in q:
        return "ReadSyslog"
    return "GetSystemInfo"


def run_one(client, query, role):
    """Select a tool for the query and execute it. Returns (chosen, result)."""
    chosen = select_tool(query, role)
    if chosen in DISPATCH:
        res = DISPATCH[chosen](client)
    else:
        res = {"command": "", "output": f"unrecognized tool: {chosen}",
               "success": False}
    return chosen, res


def _status(res):
    if res["output"] == "TIMEOUT":
        return "TIMEOUT"
    return "OK" if res["success"] else "FAIL"


def run_agents(limit=None):
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    if limit:
        queries = queries[:limit]
    n = len(queries)
    print(f"Cyber run {run_id} — {n} queries — "
          f"{'MOCK' if MOCK_MODE else f'REAL SSH {VM_USER}@{VM_HOST}:{VM_PORT}'}")

    client = open_pool()
    if client is None:
        print("\nVM not reachable — cannot run real SSH.\n"
              "Follow docs/VM_SETUP.md (Path A) to start the VM, or set "
              "AGENTLENS_MOCK=1 for mock mode.")
        return None

    rows = []
    try:
        for i, q in enumerate(queries, 1):
            role, qt, gt = q["agent"], q["query"], q["tool"]
            chosen, res = run_one(client, qt, role)
            rows.append({
                "prompt": qt, "tool_predicted": chosen, "tool_ground_truth": gt,
                "agent_role": role, "difficulty": q.get("difficulty"),
                "category": q.get("category"), "command": res["command"],
                "output": res["output"][:OUTPUT_CAP], "success": res["success"],
                "run_id": run_id,
            })
            print(f"Query {i}/{n}: {chosen} [{_status(res)}]")
    finally:
        client.close()

    df = pd.DataFrame(rows)
    TRAJ_DIR.mkdir(parents=True, exist_ok=True)
    if MOCK_MODE:
        df[MOCK_SCHEMA].to_csv(MOCK_PATH, index=False)
        out = MOCK_PATH
    else:
        df[REAL_SCHEMA].to_csv(REAL_PATH, index=False)
        out = REAL_PATH
    print(f"\nSaved {len(df)} trajectories -> {out.relative_to(ROOT)}")
    _summary(df)
    return df


def _summary(df):
    acc = (df["tool_predicted"] == df["tool_ground_truth"]).mean()
    hard = df[df["difficulty"] == "hard"]
    hard_acc = (hard["tool_predicted"] == hard["tool_ground_truth"]).mean() if len(hard) else float("nan")
    print("\n" + "=" * 60)
    print("LLM tool-selection accuracy (real run)" if not MOCK_MODE
          else "LLM tool-selection accuracy (mock run)")
    print("=" * 60)
    print(f"  Overall: {acc:.1%}  ({(df['tool_predicted']==df['tool_ground_truth']).sum()}/{len(df)})")
    if len(hard):
        print(f"  Hard:    {hard_acc:.1%}  (n={len(hard)})")
    if not MOCK_MODE:
        print(f"\n  Mock LLM baseline: {MOCK_BASELINE:.1%}")
        print(f"  Real LLM baseline: {acc:.1%}")
        print(f"  Difference:        {(acc-MOCK_BASELINE)*100:+.1f} pp "
              "(same LLM+queries; large gap would suggest SSH latency hurt LLM output)")
    if "success" in df.columns:
        ok = df["success"].sum()
        to = (df["output"] == "TIMEOUT").sum()
        print(f"\n  Command execution: {ok}/{len(df)} succeeded, {to} timed out")


if __name__ == "__main__":
    cli_limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_agents(limit=cli_limit)
