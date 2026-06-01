"""Plain text / Markdown parser."""
from __future__ import annotations


def parse_text(file_path: str) -> str:
    """Read a plain text or markdown file and return its content."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
