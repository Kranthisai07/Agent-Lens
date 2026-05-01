"""Diagnostic — run the LLM tool-selector over every labeled query and
report which queries it gets wrong against the ground-truth labels.

Writes:
  data/full_predictions.csv  — all rows: prompt, ground_truth, predicted
  data/confused_queries.csv  — only rows where predicted != ground_truth
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agents"))

import pandas as pd
from crew_agent import select_tool

QUERIES_PATH = ROOT / "data" / "queries.json"
FULL_PATH = ROOT / "data" / "full_predictions.csv"
CONFUSED_PATH = ROOT / "data" / "confused_queries.csv"


def main():
    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    print(f"Running predictions on {len(queries)} queries...")

    rows = []
    for i, q in enumerate(queries, 1):
        prompt, gt = q["query"], q["tool"]
        pred = select_tool(prompt)
        rows.append({"prompt": prompt, "ground_truth": gt, "predicted": pred})
        if i % 50 == 0:
            so_far = sum(1 for r in rows if r["ground_truth"] == r["predicted"])
            print(f"  [{i}/{len(queries)}] running accuracy: {so_far/i:.1%}")

    df = pd.DataFrame(rows)
    df.to_csv(FULL_PATH, index=False)

    confused = df[df["ground_truth"] != df["predicted"]].copy()
    confused.to_csv(CONFUSED_PATH, index=False)

    correct = int((df["ground_truth"] == df["predicted"]).sum())
    wrong = len(df) - correct

    print()
    print("=== Summary ===")
    print(f"Total queries: {len(df)}")
    print(f"Correct:       {correct}")
    print(f"Wrong:         {wrong}")
    print(f"Accuracy:      {correct / len(df):.1%}")

    print()
    print("=== Confusion breakdown (ground_truth -> predicted) ===")
    pairs = Counter(zip(confused["ground_truth"], confused["predicted"]))
    for (gt, pred), count in sorted(pairs.items(), key=lambda kv: -kv[1]):
        example = confused[
            (confused["ground_truth"] == gt) & (confused["predicted"] == pred)
        ]["prompt"].iloc[0]
        print(f"  {gt} -> {pred}: {count}")
        print(f"    e.g. {example!r}")

    print()
    print(f"Wrote {FULL_PATH} ({len(df)} rows)")
    print(f"Wrote {CONFUSED_PATH} ({len(confused)} rows)")


if __name__ == "__main__":
    main()
