"""Small real-VM test — run a handful of queries against the live VM before the
full 640-query run. Exercises real SSH execution across the tool suite.

Picks one clean (easy/direct) query per tool so selection reliably lands on the
intended tool, runs each through the real pipeline, prints query / tool /
command / output, and saves data/trajectories/real_vm_test.csv.

Run: python agents/test_real_vm.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

import pandas as pd

from tools.cyber import MOCK_MODE
from tools.cyber.config import VM_HOST, VM_PORT, VM_USER
from tools.cyber.ssh_connector import open_pool
from cyber_agent import run_one

QUERIES_PATH = ROOT / "data" / "cyber_queries.json"
OUT_PATH = ROOT / "data" / "trajectories" / "real_vm_test.csv"

# One query per tool (SSHConnect omitted: ssh-to-self has no non-interactive
# auth and always fails, which would just be noise in a smoke test).
TARGET_TOOLS = [
    "NmapScan", "PortScan", "CheckVulnerability",
    "ReadAuthLog", "ListeningPorts", "CheckFailedLogins", "ListProcesses",
    "BlockIP", "GetSystemInfo", "ReadSyslog",
]


def _pick_queries():
    data = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    picked = []
    for tool in TARGET_TOOLS:
        q = next((d for d in data if d["tool"] == tool and d.get("difficulty") == "easy"), None)
        q = q or next((d for d in data if d["tool"] == tool), None)
        if q:
            picked.append(q)
    return picked


def main():
    if MOCK_MODE:
        print("MOCK_MODE is on — this test is meant for the real VM. "
              "Unset AGENTLENS_MOCK (or set =0) to hit the live VM.")
    queries = _pick_queries()
    print(f"Real-VM test: {len(queries)} queries — "
          f"{VM_USER}@{VM_HOST}:{VM_PORT} (MOCK_MODE={MOCK_MODE})\n")

    client = open_pool()
    if client is None:
        print("VM not reachable at "
              f"{VM_HOST}:{VM_PORT}\nFollow docs/VM_SETUP.md to start the VM first.")
        return 1

    rows, ok = [], 0
    try:
        for i, q in enumerate(queries, 1):
            chosen, res = run_one(client, q["query"], q["agent"])
            ok += 1 if res["success"] else 0
            out = res["output"]
            preview = (out[:400] + " …") if len(out) > 400 else out
            print(f"[{i}/{len(queries)}] query: {q['query']!r}")
            print(f"         tool selected : {chosen}  (ground truth {q['tool']})")
            print(f"         command       : {res['command']}")
            print(f"         success       : {res['success']}")
            print(f"         output        : {preview.strip()}")
            print("-" * 66)
            rows.append({"query": q["query"], "tool_selected": chosen,
                         "tool_ground_truth": q["tool"], "command": res["command"],
                         "output": out[:2000], "success": res["success"],
                         "timestamp": datetime.now().isoformat(timespec="seconds")})
    finally:
        client.close()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT_PATH, index=False)
    print(f"\n{ok}/{len(rows)} commands executed successfully.")
    print(f"Saved -> {OUT_PATH.relative_to(ROOT)}")
    return 0 if ok == len(rows) else 2


if __name__ == "__main__":
    sys.exit(main())
