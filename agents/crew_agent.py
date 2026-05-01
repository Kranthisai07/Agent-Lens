"""Direct Ollama tool-selection — bypasses CrewAI's ReAct loop.

For each query the LLM (Llama 3.2 3B) is asked for a single-word answer
naming the tool. The chosen tool is then invoked via the logging_tool
wrapper so (query, tool) is appended to the shared logs list.

(File kept named crew_agent.py for backwards-compat with run.py.)
"""

import json
import sys
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


def select_tool(query: str) -> str:
    """Ask the LLM which tool to use; return the matched tool name or 'Unknown'."""
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        options={"temperature": 0},
    )
    raw = response["message"]["content"].strip()
    for token in raw.replace(".", " ").replace(":", " ").replace(",", " ").split():
        if token in VALID_TOOLS:
            return token
    return "Unknown"


def _save_logs():
    if not logs:
        print("No new trajectories to save.")
        return
    df = pd.DataFrame(logs)
    LOGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOGS_PATH.exists():
        existing = pd.read_csv(LOGS_PATH)
        df_out = pd.concat([existing, df], ignore_index=True)
    else:
        df_out = df
    df_out.to_csv(LOGS_PATH, index=False)
    print(f"Saved {len(df_out)} total trajectories to {LOGS_PATH}")


def run_agent(limit=None):
    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    if limit is not None:
        queries = queries[:limit]
    print(f"Running tool-selection over {len(queries)} queries...")

    tool_funcs = {
        "Calculator": logging_tool("Calculator", calculator),
        "Search": logging_tool("Search", search),
        "TableSummarizer": logging_tool("TableSummarizer", table_summarizer),
    }

    logs.clear()

    for i, q in enumerate(queries, 1):
        query_text = q["query"] if isinstance(q, dict) else str(q)
        chosen = select_tool(query_text)
        print(f"[{i}/{len(queries)}] {query_text!r} -> {chosen}")
        if chosen in tool_funcs:
            try:
                tool_funcs[chosen](query_text)
            except Exception as e:
                print(f"  tool error: {e}")
        else:
            print(f"  unrecognized tool name from LLM; skipping (no log entry)")

    _save_logs()
    print(f"\nTotal trajectories collected this run: {len(logs)}")


if __name__ == "__main__":
    cli_limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_agent(limit=cli_limit)
