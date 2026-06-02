"""
Ollama wrapper for answer generation.
Uses the chat model configured in settings (default: llama3.2).
Raises HTTP 503 if Ollama is unreachable.
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
    Generate an answer using Ollama.
    Returns (answer_text, generation_time_ms).
    Raises HTTP 503 if Ollama is unreachable.
    """
    import requests

    prompt = _build_prompt(question, sources)
    payload = {
        "model": settings.ollama_chat_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 1024,
        },
    }

    start = time.perf_counter()
    try:
        resp = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        elapsed_ms = (time.perf_counter() - start) * 1000
        answer = resp.json().get("response", "").strip()
        logger.info("Ollama generated answer in {:.1f}ms", elapsed_ms)
        return answer, elapsed_ms

    except requests.exceptions.ConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama is not reachable at {settings.ollama_base_url}. "
                   f"Make sure Ollama is running: `ollama serve`. Error: {exc}",
        )
    except requests.exceptions.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama API error: {exc}",
        )
    except Exception as exc:
        logger.error("Ollama generate error: {}", exc)
        raise HTTPException(
            status_code=502,
            detail=f"Ollama request failed: {exc}",
        )
