"""
Excel parser — returns flat text for embedding AND structured per-sheet
row data used by the ingestion pipeline to build the value-level graph.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def parse_excel(file_path: str) -> str:
    text, _ = parse_excel_structured(file_path)
    return text


def parse_excel_structured(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Returns:
      text  — flat text for ChromaDB embedding
      meta  — {"sheets": {sheet_name: {columns, rows, row_count}}}
    """
    try:
        import pandas as pd

        xl = pd.ExcelFile(file_path)
        all_text: List[str] = []
        sheets_meta: Dict[str, Any] = {}

        for sheet_name in xl.sheet_names:
            df = xl.parse(sheet_name, dtype=str, keep_default_na=False)
            if df.empty:
                continue

            df = df.fillna("").map(str)
            all_text.append(f"Sheet: {sheet_name}")

            for _, row in df.iterrows():
                parts = [f"{col}: {val}" for col, val in row.items() if str(val).strip()]
                if parts:
                    all_text.append(". ".join(parts) + ".")

            sheets_meta[sheet_name] = {
                "columns": list(df.columns),
                "rows": df.to_dict(orient="records"),
                "row_count": len(df),
            }

        return "\n".join(all_text), {"sheets": sheets_meta}

    except Exception as exc:
        raise ValueError(f"Failed to parse Excel file: {exc}") from exc
