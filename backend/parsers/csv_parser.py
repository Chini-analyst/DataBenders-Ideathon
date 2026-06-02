"""
CSV parser — returns flat text for embedding AND a structured row-level
dataframe used by the ingestion pipeline to build the value-level graph.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def parse_csv(file_path: str) -> str:
    text, _ = parse_csv_structured(file_path)
    return text


def parse_csv_structured(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Returns:
      text  — flat "col: val. col: val." sentences for ChromaDB embedding
      meta  — {columns, rows (list of dicts), row_count}
    """
    try:
        import pandas as pd

        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        df = df.fillna("").map(str)

        lines = []
        for _, row in df.iterrows():
            parts = [f"{col}: {val}" for col, val in row.items() if val.strip()]
            if parts:
                lines.append(". ".join(parts) + ".")

        rows = df.to_dict(orient="records")

        meta = {
            "columns": list(df.columns),
            "rows": rows,
            "row_count": len(df),
        }
        return "\n".join(lines), meta

    except Exception as exc:
        raise ValueError(f"Failed to parse CSV file: {exc}") from exc
