"""Measure the LLM tool-selection baseline on data/cyber_queries.json.

Presents each agent's FULL corrected tool set to the LLM and records the
per-query prediction, then reports accuracy overall, by difficulty, and by
category (the paper's "which query types fool the LLM most" table).

Writes data/cyber_baseline_predictions.csv.
Run: python scripts/measure_cyber_baseline.py [limit]
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import pandas as pd

QUERIES = ROOT / "data" / "cyber_queries.json"
OUT = ROOT / "data" / "cyber_baseline_predictions.csv"
MODEL = "llama3.2:3b"

AGENT_TOOLS = {
    "attacker": ["SSHConnect", "NmapScan", "PortScan", "CheckVulnerability"],
    "defender": ["ReadAuthLog", "ListeningPorts", "BlockIP",
                 "CheckFailedLogins", "ListProcesses"],
    "shared": ["GetSystemInfo", "ReadSyslog"],
}


def select_tool(query, agent):
    tools = AGENT_TOOLS[agent]
    valid = set(tools)
    system = ("You are a tool selector for a security agent. Given a task, "
              "respond with exactly one word — the tool to use, chosen from: "
              + ", ".join(tools) + ".")
    try:
        import ollama
        r = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": query}],
            options={"temperature": 0, "seed": 42})
        raw = r["message"]["content"].strip()
    except Exception as e:
        return f"ERROR:{e}"
    for tok in raw.replace(".", " ").replace(":", " ").replace(",", " ").split():
        if tok in valid:
            return tok
    return "Unknown"


def main():
    rows = json.loads(QUERIES.read_text(encoding="utf-8"))
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if limit:
        rows = rows[:limit]
    print(f"Measuring LLM baseline on {len(rows)} queries...")

    out = []
    for i, r in enumerate(rows, 1):
        pred = select_tool(r["query"], r["agent"])
        out.append({**r, "predicted": pred, "correct": pred == r["tool"]})
        if i % 80 == 0 or i == len(rows):
            acc = sum(o["correct"] for o in out) / i
            print(f"  [{i}/{len(rows)}] running accuracy: {acc:.1%}")

    df = pd.DataFrame(out)
    df.to_csv(OUT, index=False)

    print("\n=== Overall ===")
    print(f"  accuracy: {df['correct'].mean():.1%}  ({df['correct'].sum()}/{len(df)})")
    print("\n=== By difficulty ===")
    for diff, g in df.groupby("difficulty"):
        print(f"  {diff:6} n={len(g):3}  acc={g['correct'].mean():.1%}")
    print("\n=== By category (paper table) ===")
    for cat in ["direct", "ambiguous", "opposite", "multistep", "natural", "trick"]:
        g = df[df["category"] == cat]
        if len(g):
            print(f"  {cat:10} n={len(g):3}  acc={g['correct'].mean():.1%}")

    hard = df[df["difficulty"] == "hard"]
    print(f"\nHARD subset accuracy: {hard['correct'].mean():.1%}  "
          f"(target 65-75%)")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
