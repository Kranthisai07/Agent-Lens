"""Direct Ollama tool-selection — bypasses CrewAI's ReAct loop.

For each query the LLM (Llama 3.2 3B) is asked for a single-word answer
naming the tool. The chosen tool is then invoked via the logging_tool
wrapper so the trajectory is appended to the shared logs list.

Each record carries both the LLM's prediction and the ground-truth label
from queries.json, plus a run_id, so the classifier can be trained on
truth while the prediction column serves as the LLM baseline.

(File kept named crew_agent.py for backwards-compat with run.py.)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ollama
import pandas as pd

from tools import logs, logging_tool
from tools.calculator import calculator
from tools.search import search
from tools.summarizer import table_summarizer

QUERIES_PATH = ROOT / "data" / "queries.json"
LOGS_PATH = ROOT / "data" / "trajectories" / "logs.csv"
MODEL = "llama3.2:3b"

SYSTEM_PROMPT = (
    "You are a tool selector. Given a query, respond with exactly one word — "
    "the tool to use: Calculator, Search, or TableSummarizer."
)

VALID_TOOLS = {"Calculator", "Search", "TableSummarizer"}

SCHEMA = ["prompt", "tool_predicted", "tool_ground_truth", "run_id"]


def select_tool(query: str) -> str:
    """Ask the LLM which tool to use; return the matched tool name or 'Unknown'."""
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            options={"temperature": 0, "seed": 42},
        )
    except Exception as e:
        print(f"  LLM error: {e}")
        return "Error"
    raw = response["message"]["content"].strip()
    for token in raw.replace(".", " ").replace(":", " ").replace(",", " ").split():
        if token in VALID_TOOLS:
            return token
    return "Unknown"


def _save_logs():
    """Append this run's trajectories to logs.csv, keyed by run_id.

    If an existing logs.csv predates the ground-truth schema it is archived
    rather than concatenated, so the two shapes never ragged-merge.
    """
    if not logs:
        print("No new trajectories to save.")
        return
    df = pd.DataFrame(logs)[SCHEMA]
    LOGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOGS_PATH.exists():
        existing = pd.read_csv(LOGS_PATH)
        if list(existing.columns) == SCHEMA:
            df_out = pd.concat([existing, df], ignore_index=True)
        else:
            archive = LOGS_PATH.with_name("logs_schema_v1.csv")
            LOGS_PATH.rename(archive)
            print(f"Archived {len(existing)} legacy-schema rows to {archive.name}")
            df_out = df
    else:
        df_out = df
    df_out.to_csv(LOGS_PATH, index=False)
    print(f"Saved {len(df)} new ({len(df_out)} total) trajectories to {LOGS_PATH}")


def run_agent(limit=None):
    run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    if limit is not None:
        queries = queries[:limit]
    print(f"Run {run_timestamp}: tool-selection over {len(queries)} queries...")

    tool_funcs = {
        "Calculator": logging_tool("Calculator", calculator),
        "Search": logging_tool("Search", search),
        "TableSummarizer": logging_tool("TableSummarizer", table_summarizer),
    }

    logs.clear()

    for i, q in enumerate(queries, 1):
        query_text = q["query"] if isinstance(q, dict) else str(q)
        ground_truth = q.get("tool") if isinstance(q, dict) else None
        chosen = select_tool(query_text)
        mark = "ok  " if chosen == ground_truth else "MISS"
        if i % 25 == 0 or i == len(queries):
            hits = sum(1 for r in logs if r["tool_predicted"] == r["tool_ground_truth"])
            print(f"[{i}/{len(queries)}] {mark} running accuracy: {hits/max(i-1,1):.1%}")
        if chosen in tool_funcs:
            try:
                tool_funcs[chosen](
                    query_text,
                    tool_ground_truth=ground_truth,
                    run_id=run_timestamp,
                )
            except Exception as e:
                print(f"  tool error: {e}")
        else:
            # Record the miss explicitly rather than dropping the row.
            logs.append({
                "prompt": query_text,
                "tool_predicted": chosen,
                "tool_ground_truth": ground_truth,
                "run_id": run_timestamp,
            })

    _save_logs()
    matched = sum(1 for r in logs if r["tool_predicted"] == r["tool_ground_truth"])
    print(f"\nRun {run_timestamp}: {len(logs)} trajectories collected")
    if logs:
        print(f"LLM vs ground truth: {matched}/{len(logs)} = {matched/len(logs):.1%}")


if __name__ == "__main__":
    cli_limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_agent(limit=cli_limit)
