"""TableSummarizer tool — describes and previews a CSV file."""

import pandas as pd

TOOL_NAME = "TableSummarizer"


def table_summarizer(file_path: str) -> str:
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        return f"TableSummarizer error: file not found: {file_path}"
    except Exception as e:
        return f"TableSummarizer error: {e}"
    return df.describe().to_string() + "\n" + df.head().to_string()
