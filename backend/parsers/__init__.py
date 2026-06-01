"""
Document parser dispatcher.
"""
from __future__ import annotations

import os
from pathlib import Path

from loguru import logger


def parse_file(file_path: str) -> str:
    """
    Dispatch to the appropriate parser based on file extension.
    Returns extracted text content.
    """
    ext = Path(file_path).suffix.lower()

    if ext in (".txt", ".md", ".rst"):
        from parsers.text_parser import parse_text
        return parse_text(file_path)

    elif ext == ".csv":
        from parsers.csv_parser import parse_csv
        return parse_csv(file_path)

    elif ext in (".xlsx", ".xls"):
        from parsers.excel_parser import parse_excel
        return parse_excel(file_path)

    elif ext == ".docx":
        from parsers.docx_parser import parse_docx
        return parse_docx(file_path)

    elif ext == ".pdf":
        from parsers.pdf_parser import parse_pdf
        return parse_pdf(file_path)

    else:
        raise ValueError(f"Unsupported file type: {ext}")


SUPPORTED_EXTENSIONS = {".txt", ".md", ".rst", ".csv", ".xlsx", ".xls", ".docx", ".pdf"}
