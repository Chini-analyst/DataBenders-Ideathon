"""Excel parser using openpyxl / pandas."""
from __future__ import annotations


def parse_excel(file_path: str) -> str:
    """
    Parse an Excel file (.xlsx / .xls) and return a text representation.
    All sheets are concatenated.
    """
    try:
        import pandas as pd

        xl = pd.ExcelFile(file_path)
        all_text = []

        for sheet_name in xl.sheet_names:
            df = xl.parse(sheet_name, dtype=str, keep_default_na=False)
            if df.empty:
                continue
            all_text.append(f"Sheet: {sheet_name}")
            for _, row in df.iterrows():
                parts = [f"{col}: {val}" for col, val in row.items() if str(val).strip()]
                if parts:
                    all_text.append(". ".join(parts) + ".")

        return "\n".join(all_text)
    except Exception as exc:
        raise ValueError(f"Failed to parse Excel file: {exc}") from exc
