"""
Gemini API wrapper for answer generation.
Requires GEMINI_API_KEY to be set in .env — raises HTTP 503 if missing.
"""
from __future__ import annotations

import time
from typing import List

from fastapi import HTTPException
from loguru import logger

from core.config import settings
from models.query import Source


def _build_prompt(question: str, sources: List[Source]) -> str:
    context_blocks = []
    for i, src in enumerate(sources, 1):
        context_blocks.append(f"[Source {i}] ({src.source_type})\n{src.text}")
    context = "\n\n".join(context_blocks)

    return f"""You are StrategyShifu, an expert AI assistant specialising in HR, talent acquisition, workforce planning, and people operations.

Use the following retrieved context to answer the user's question accurately and concisely.
Cite the source numbers where relevant. If the context does not contain enough information, say so clearly — do not fabricate answers.

--- CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Answer:"""


def generate_answer(question: str, sources: List[Source]) -> tuple[str, float]:
    """
    Generate an answer using Gemini 1.5 Flash.
    Returns (answer_text, generation_time_ms).
    Raises HTTP 503 if GEMINI_API_KEY is not configured.
    """
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not configured. Add it to backend/.env and restart the server.",
        )

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = _build_prompt(question, sources)

        start = time.perf_counter()
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        answer = response.text.strip()
        logger.info("Gemini generated answer in {:.1f}ms", elapsed_ms)
        return answer, elapsed_ms

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Gemini API error: {}", exc)
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API request failed: {exc}",
        )
