"""Entry point — runs the CrewAI agent over all queries in data/queries.json."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crew_agent import run_agent


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_agent(limit=limit)
