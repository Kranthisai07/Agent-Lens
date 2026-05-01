"""Manual smoke test for tools + logging_tool wrapper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import logs, logging_tool
from tools.calculator import calculator
from tools.search import search
from tools.summarizer import table_summarizer


def main():
    calc = logging_tool("Calculator", calculator)
    srch = logging_tool("Search", search)
    summ = logging_tool("TableSummarizer", table_summarizer)

    print("Calculator(2+2*5):", calc("2+2*5"))
    print("Search(who is Ada Lovelace):", srch("who is Ada Lovelace"))
    print("TableSummarizer(data/sample_sales.csv):")
    print(summ("data/sample_sales.csv"))

    print("\n--- logs ---")
    for entry in logs:
        print(entry)

    assert len(logs) == 3, f"expected 3 log entries, got {len(logs)}"
    print(f"\nOK: {len(logs)} log entries collected.")


if __name__ == "__main__":
    main()
