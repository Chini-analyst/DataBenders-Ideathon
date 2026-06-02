"""CSV parser using pandas."""
from __future__ import annotations


def parse_csv(file_path: str) -> str:
    """
    Parse a CSV file and return a text representation.
    Each row is converted to a key=value sentence for downstream NLP.
    """
    try:
        import pandas as pd

        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        lines = []
        for _, row in df.iterrows():
            parts = [f"{col}: {val}" for col, val in row.items() if val.strip()]
            if parts:
                lines.append(". ".join(parts) + ".")
        return "\n".join(lines)
    except Exception as exc:
        raise ValueError(f"Failed to parse CSV file: {exc}") from exc
