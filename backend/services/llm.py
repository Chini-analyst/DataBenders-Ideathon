"""
Groq LLM wrappers:
  • generate_answer  — answer generation for the /query endpoint
  • analyse_schema   — full structural analysis for CSV/Excel ingestion
                       (primary key, node label, property vs relationship,
                        relationship verbs, multi-value flags)

Embeddings are handled separately in ingestion.py / retrieval.py via Ollama
(Groq does not provide an embedding API).
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from loguru import logger

from core.config import settings
from models.query import Source


# ──────────────────────────────────────────────────────────────────────────
# Shared Groq helper
# ──────────────────────────────────────────────────────────────────────────

def _get_groq_client():
    """Return an initialised Groq client. Raises HTTP 503 if key is missing."""
    try:
        from groq import Groq
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="groq package is not installed. Run: pip install groq==0.9.0",
        )
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "GROQ_API_KEY is not set. Add it to backend/.env: "
                "GROQ_API_KEY=your_key_here"
            ),
        )
    return Groq(api_key=settings.groq_api_key)


def _call_groq(prompt: str, temperature: float = 0.0, max_tokens: int = 2048) -> str:
    """
    Send a single user message to Groq and return the response text.
    Raises HTTP 503 / 502 on failure.
    """
    client = _get_groq_client()
    try:
        response = client.chat.completions.create(
            model=settings.groq_chat_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except HTTPException:
        raise
    except Exception as exc:
        # Surface the original Groq error message
        detail = str(exc)
        status = 503 if "connection" in detail.lower() or "auth" in detail.lower() else 502
        raise HTTPException(status_code=status, detail=f"Groq API error: {detail}")


# ──────────────────────────────────────────────────────────────────────────
# JSON extraction helpers
# ──────────────────────────────────────────────────────────────────────────

def _extract_json_object(text: str) -> Optional[dict]:
    """
    Pull the first JSON object from a model response.
    Handles markdown fences, surrounding prose, trailing commas.
    """
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    start = cleaned.find("{")
    end   = cleaned.rfind("}")
    if start == -1 or end == -1:
        return None
    candidate = cleaned[start: end + 1]
    # Strip trailing commas before } or ] (common LLM slip)
    candidate = re.sub(r",\s*([\]}])", r"\1", candidate)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


# ──────────────────────────────────────────────────────────────────────────
# Label / relationship sanitisers
# ──────────────────────────────────────────────────────────────────────────

def _safe_rel(rel: str) -> str:
    """Sanitise to SCREAMING_SNAKE_CASE relationship type."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", rel)
    s = re.sub(r"[^A-Z0-9_]", "_", s.upper())
    return s.strip("_") or "RELATED_TO"


def _safe_node_label(label: str) -> str:
    """Sanitise a string to a valid Neo4j node label."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", label)
    if cleaned and cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned or "Entity"


# ──────────────────────────────────────────────────────────────────────────
# Schema analysis prompt + public function
# ──────────────────────────────────────────────────────────────────────────

_SCHEMA_PROMPT = """\
You are a knowledge-graph architect. Analyse the tabular dataset described \
below and produce a complete graph schema for it.

=== DATASET ===
Name : {dataset_name}
Rows : {row_count}

=== COLUMNS ===
{column_stats}

=== SAMPLE ROWS (up to 8) ===
{sample_rows}

=== YOUR TASK ===
Return a single JSON object with this exact shape — no markdown, no prose:

{{
  "primary_key_column": "<column name that uniquely identifies each row>",
  "node_label": "<singular CamelCase label for the primary entity, e.g. Employee, Product, Invoice>",
  "columns": [
    {{
      "name": "<column name>",
      "role": "property" | "relationship" | "primary_key",
      "node_label": "<CamelCase label for the target node if role=relationship, else omit>",
      "relationship": "<SCREAMING_SNAKE_CASE verb if role=relationship, else omit>",
      "multi_value": true | false
    }}
  ]
}}

=== RULES ===
1. Exactly one column must have role="primary_key".
2. "property" — high-cardinality values unique to each row (names, dates, \
amounts, free-text, IDs that are not the primary key).
3. "relationship" — low-cardinality shared values that categorise rows \
(department, status, location, type, tag, category) OR references to another \
entity (manager, assignee, supplier).
4. "multi_value": true if cells often contain delimiters like | ; or , \
separating multiple values.
5. "relationship" must be an active-voice verb: WORKS_IN, REPORTS_TO, \
HAS_SKILL, ASSIGNED_TO, CATEGORISED_AS, SUPPLIED_BY, etc.
6. "node_label" for a relationship column names the target concept: \
Department, Location, Skill, Status, Supplier, etc.
7. Do NOT invent columns. Only include the columns listed above.
8. Return ONLY the JSON object. No explanation, no markdown.
"""


def analyse_schema(
    dataset_name: str,
    columns: List[str],
    rows: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    """
    Ask Groq to produce a full graph schema for the dataset.

    Returns a validated schema dict on success, None on any failure
    (caller raises HTTP 503).

    Schema shape:
    {
        "primary_key_column": str,
        "node_label": str,
        "columns": [
            {
                "name": str,
                "role": "primary_key" | "property" | "relationship",
                "node_label": str | None,
                "relationship": str | None,
                "multi_value": bool,
            }
        ]
    }
    """
    total = max(len(rows), 1)

    # Per-column statistics
    col_stats_lines = []
    for col in columns:
        vals = [str(r.get(col, "")).strip() for r in rows if str(r.get(col, "")).strip()]
        distinct   = len(set(vals))
        has_multi  = any(re.search(r"[|;]", v) or v.count(",") >= 2 for v in vals)
        sample_vals = list(dict.fromkeys(v for v in vals if v))[:5]
        col_stats_lines.append(
            f"  - {col}: {distinct} distinct / {total} rows"
            + (" [multi-value delimiters detected]" if has_multi else "")
            + f"  | sample: {', '.join(repr(v) for v in sample_vals)}"
        )

    # Sample rows
    sample_rows_text = "\n".join(
        "  " + " | ".join(f"{col}: {str(row.get(col, ''))[:35]}" for col in columns)
        for row in rows[:8]
    )

    prompt = _SCHEMA_PROMPT.format(
        dataset_name=dataset_name,
        row_count=len(rows),
        column_stats="\n".join(col_stats_lines),
        sample_rows=sample_rows_text,
    )

    try:
        raw = _call_groq(prompt, temperature=0.0, max_tokens=2048)
        logger.debug("Groq schema raw response for '{}': {}", dataset_name, raw[:500])

        parsed = _extract_json_object(raw)
        if not parsed:
            logger.warning("Groq returned unparseable schema for '{}'", dataset_name)
            return None

        validated = _validate_schema(parsed, columns)
        if validated is None:
            logger.warning("Groq schema failed validation for '{}'", dataset_name)
            return None

        logger.info(
            "Groq schema for '{}': pk='{}', label='{}', {} rel-cols, {} prop-cols",
            dataset_name,
            validated["primary_key_column"],
            validated["node_label"],
            sum(1 for c in validated["columns"] if c["role"] == "relationship"),
            sum(1 for c in validated["columns"] if c["role"] == "property"),
        )
        return validated

    except HTTPException:
        raise   # propagate 503/502 from _call_groq directly
    except Exception as exc:
        logger.warning("Groq schema analysis failed for '{}': {}", dataset_name, exc)
        return None


def _validate_schema(raw: dict, columns: List[str]) -> Optional[Dict[str, Any]]:
    """
    Validate and normalise LLM schema output.
    Fixes common mistakes; returns None if unrecoverable.
    """
    col_set = set(columns)

    if "columns" not in raw or not isinstance(raw.get("columns"), list):
        return None

    pk_col   = raw.get("primary_key_column", "")
    node_lbl = raw.get("node_label", "")

    if pk_col not in col_set:
        pk_col = columns[0]

    node_lbl = (
        _safe_node_label(node_lbl) if node_lbl
        else _safe_node_label(pk_col.split("_")[0].capitalize() or "Entity")
    )

    validated_cols, seen_cols, has_pk = [], set(), False

    for item in raw["columns"]:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        if name not in col_set or name in seen_cols:
            continue
        seen_cols.add(name)

        role = item.get("role", "property")
        if role not in ("primary_key", "property", "relationship"):
            role = "property"
        if name == pk_col:
            role = "primary_key"
            has_pk = True

        multi_value = bool(item.get("multi_value", False))

        if role == "relationship":
            rel_raw   = item.get("relationship") or item.get("relationship_type") or ""
            tgt_label = item.get("node_label") or item.get("target_label") or ""
            rel_clean = _safe_rel(rel_raw) if rel_raw else _safe_rel(name)
            tgt_clean = (
                _safe_node_label(tgt_label) if tgt_label
                else _safe_node_label(name.replace("_", " ").title().replace(" ", ""))
            )
            validated_cols.append({
                "name": name, "role": "relationship",
                "node_label": tgt_clean, "relationship": rel_clean,
                "multi_value": multi_value,
            })
        else:
            validated_cols.append({
                "name": name, "role": role,
                "node_label": None, "relationship": None,
                "multi_value": multi_value,
            })

    # Add any columns the LLM omitted
    for col in columns:
        if col not in seen_cols:
            role = "primary_key" if col == pk_col and not has_pk else "property"
            if role == "primary_key":
                has_pk = True
            validated_cols.append({
                "name": col, "role": role,
                "node_label": None, "relationship": None, "multi_value": False,
            })

    if not has_pk:
        for c in validated_cols:
            if c["name"] == pk_col:
                c["role"] = "primary_key"
                break

    return {
        "primary_key_column": pk_col,
        "node_label": node_lbl,
        "columns": validated_cols,
    }


# ──────────────────────────────────────────────────────────────────────────
# Answer generation  (/api/query endpoint)
# ──────────────────────────────────────────────────────────────────────────

def _build_answer_prompt(question: str, sources: List[Source]) -> str:
    context_blocks = [
        f"[Source {i}] ({src.source_type})\n{src.text}"
        for i, src in enumerate(sources, 1)
    ]
    context = "\n\n".join(context_blocks)
    return (
        "You are StrategyShifu, an expert AI assistant specialising in "
        "HR, talent acquisition, workforce planning, and people operations.\n\n"
        "Use the following retrieved context to answer the user's question accurately "
        "and concisely. Cite source numbers where relevant. "
        "If the context does not contain enough information, say so clearly — "
        "do not fabricate answers.\n\n"
        f"--- CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
        f"Question: {question}\n\nAnswer:"
    )


def generate_answer(question: str, sources: List[Source]) -> tuple[str, float]:
    """
    Generate an answer using Groq.
    Returns (answer_text, generation_time_ms).
    Raises HTTP 503 if Groq is unreachable or the key is missing.
    """
    start = time.perf_counter()
    prompt = _build_answer_prompt(question, sources)
    answer = _call_groq(prompt, temperature=0.3, max_tokens=1024)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("Groq generated answer in {:.1f}ms", elapsed_ms)
    return answer, elapsed_ms
