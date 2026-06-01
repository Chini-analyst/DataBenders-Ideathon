"""PDF parser using PyMuPDF (fitz)."""
from __future__ import annotations


def parse_pdf(file_path: str) -> str:
    """
    Parse a PDF file and return its text content.
    Uses PyMuPDF for fast, accurate text extraction.
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        pages_text = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                pages_text.append(f"[Page {page_num + 1}]\n{text.strip()}")

        doc.close()
        return "\n\n".join(pages_text)
    except Exception as exc:
        raise ValueError(f"Failed to parse PDF file: {exc}") from exc
