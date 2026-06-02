"""
Domain-agnostic ingestion pipeline.

Routing
───────
  Structured  (.csv, .xlsx, .xls)  → Neo4j
  Unstructured (.pdf, .docx, …)    → ChromaDB

Structured ingestion — pipeline per sheet
──────────────────────────────────────────
  Step 1  Groq schema analysis  (REQUIRED — raises HTTP 503 on failure)
          Groq receives column names, per-column statistics and sample rows.
          It returns a complete graph schema:
            • primary key column
            • primary node label
            • per column: property | relationship, target node label,
              relationship verb, multi-value flag

  Step 2  Graph construction
          Execute the schema against every row — primary nodes, property values,
          relationship nodes, edges.  Node IDs are content-addressed so the
          same value from different files merges into one node automatically.

  If Groq is unreachable or GROQ_API_KEY is missing, ingestion is aborted
  with HTTP 503 and a clear error message.  No silent fallbacks.

Unstructured ingestion
──────────────────────
  Chunk → embed (Ollama nomic-embed-text) → store in ChromaDB.
  Note: Groq does not provide an embedding API, so Ollama is still used
  for embeddings only.
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from loguru import logger

from core.config import settings
from core.database import get_chroma_client, get_neo4j_driver, get_or_create_chroma_collection
from models.upload import UploadRecord
from services.graph_service import upsert_edge, upsert_node

# ── File routing ──────────────────────────────────────────────────────────
STRUCTURED_EXTENSIONS   = {".csv", ".xlsx", ".xls"}
UNSTRUCTURED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".rst", ".pptx"}

# ── Multi-value cell delimiter pattern ───────────────────────────────────
_MULTI_DELIM    = re.compile(r"[|;]\s*")          # | and ; are unambiguous
_COMMA_DELIM    = re.compile(r",\s*")             # commas only when flagged
_EMPTY_VALS     = {"nan", "none", "", "n/a", "n/a", "-", "null"}


# ──────────────────────────────────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────────────────────────────────

def _node_id(node_type: str, value: str) -> str:
    """Deterministic, content-addressed node ID (cross-file stable)."""
    return hashlib.md5(f"{node_type.lower()}:{value.lower().strip()}".encode()).hexdigest()[:16]


def _safe_label(s: str) -> str:
    """Sanitise a string to a valid Neo4j node label."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", s)
    if cleaned and cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned or "Entity"


def _safe_rel(s: str) -> str:
    """Sanitise to SCREAMING_SNAKE_CASE relationship type."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"[^A-Z0-9_]", "_", s.upper())
    return s.strip("_") or "RELATED_TO"


def _to_camel(raw: str) -> str:
    """Convert a snake/space string to singular CamelCase."""
    raw = Path(raw).stem
    words = re.split(r"[^a-zA-Z0-9]+", raw.strip())
    label = "".join(w.capitalize() for w in words if w)
    if label.endswith("s") and not label.endswith("ss") and len(label) > 3:
        label = label[:-1]
    return label or "Entity"


def _split_cell(value: str, multi_value: bool) -> List[str]:
    """
    Split a cell value into fragments when multi_value is True.
    Tries | and ; first; falls back to , only when multi_value=True and
    the value actually contains a comma.
    """
    if not multi_value:
        return [value]
    parts = _MULTI_DELIM.split(value)
    if len(parts) == 1 and "," in value:
        parts = _COMMA_DELIM.split(value)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) >= 2]


# ──────────────────────────────────────────────────────────────────────────
# Structured ingestion (Neo4j)
# ──────────────────────────────────────────────────────────────────────────

def ingest_structured(
    record: UploadRecord,
    structured_meta: Dict[str, Any],
) -> Tuple[int, int]:
    """
    Ingest a CSV/Excel file into Neo4j using LLM-derived graph schema.
    Returns (node_count, edge_count).
    """
    from services.llm import analyse_schema   # avoid circular at module level

    neo4j_driver = get_neo4j_driver()
    if neo4j_driver is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j is not available. Please ensure the service is running (docker compose up -d).",
        )

    doc_id   = record.id
    filename = record.original_filename
    total_nodes = total_edges = 0

    # Normalise: Excel → {sheet_name: meta}, CSV → {stem: meta}
    sheets: Dict[str, Any] = structured_meta.get("sheets", {
        Path(filename).stem: structured_meta
    })

    for sheet_name, sheet_meta in sheets.items():
        columns: List[str] = sheet_meta.get("columns", [])
        rows: List[Dict[str, str]] = sheet_meta.get("rows", [])
        if not rows or not columns:
            continue

        # ── Step 1: ask LLM for the full schema ──────────────────────────
        logger.info("Requesting LLM schema analysis for sheet '{}'", sheet_name)
        schema = analyse_schema(sheet_name, columns, rows)

        # ── Step 2: raise if LLM failed — no fallback ────────────────────
        if schema is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Groq schema analysis failed for sheet '{sheet_name}'. "
                    f"Check that GROQ_API_KEY is set in backend/.env and "
                    f"the model '{settings.groq_chat_model}' is available."
                ),
            )

        pk_col      = schema["primary_key_column"]
        node_label  = schema["node_label"]

        # Index column definitions by name for fast lookup
        col_defs: Dict[str, Dict] = {c["name"]: c for c in schema["columns"]}

        logger.info(
            "Schema for '{}': label={}, pk='{}', rels={}, props={}",
            sheet_name, node_label, pk_col,
            [c["name"] for c in schema["columns"] if c["role"] == "relationship"],
            [c["name"] for c in schema["columns"] if c["role"] == "property"],
        )

        # ── Step 3: execute schema against every row ──────────────────────
        seen_nodes: set = set()

        for row in rows:
            pk_val = str(row.get(pk_col, "")).strip()
            if not pk_val or pk_val.lower() in _EMPTY_VALS:
                continue

            # Primary node — collect all property-role columns as node props
            primary_id = _node_id(node_label, pk_val)
            props: Dict[str, Any] = {"source_column": pk_col, "sheet": sheet_name}
            for cdef in schema["columns"]:
                if cdef["role"] != "property":
                    continue
                val = str(row.get(cdef["name"], "")).strip()
                if val and val.lower() not in _EMPTY_VALS:
                    props[cdef["name"]] = val

            if primary_id not in seen_nodes:
                if upsert_node(primary_id, pk_val, node_label, props, doc_id):
                    total_nodes += 1
                seen_nodes.add(primary_id)

            # Relationship nodes
            for cdef in schema["columns"]:
                if cdef["role"] != "relationship":
                    continue

                cell_val = str(row.get(cdef["name"], "")).strip()
                if not cell_val or cell_val.lower() in _EMPTY_VALS:
                    continue

                rel_type    = cdef["relationship"]
                target_lbl  = cdef["node_label"]
                multi_value = cdef.get("multi_value", False)

                fragments = _split_cell(cell_val, multi_value) or [cell_val]

                for fragment in fragments:
                    target_id = _node_id(target_lbl, fragment)
                    if target_id not in seen_nodes:
                        t_props = {"source_column": cdef["name"], "sheet": sheet_name}
                        if upsert_node(target_id, fragment, target_lbl, t_props, doc_id):
                            total_nodes += 1
                        seen_nodes.add(target_id)

                    if upsert_edge(
                        primary_id, target_id, rel_type,
                        {"sheet": sheet_name, "source_column": cdef["name"]},
                        doc_id,
                    ):
                        total_edges += 1

        logger.info(
            "Sheet '{}' complete: {} nodes, {} edges written to Neo4j",
            sheet_name, total_nodes, total_edges,
        )

    return total_nodes, total_edges


# ──────────────────────────────────────────────────────────────────────────
# Unstructured ingestion (ChromaDB)
# ──────────────────────────────────────────────────────────────────────────

def _get_embedding(text: str) -> List[float]:
    """Embed via Ollama; deterministic hash fallback if unreachable."""
    try:
        import requests
        resp = requests.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
    except Exception as exc:
        logger.warning("Ollama embedding failed, using hash fallback: {}", exc)
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
    vec  = [math.sin(seed * (i + 1) * 0.001) for i in range(384)]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end >= len(words):
            break
        start += chunk_size - overlap
    return chunks


def ingest_unstructured(record: UploadRecord, text_content: str) -> int:
    """Embed and store document chunks in ChromaDB. Returns chunk_count."""
    chroma_client = get_chroma_client()
    if chroma_client is None:
        raise HTTPException(
            status_code=503,
            detail="ChromaDB is not available. Please ensure the service is running (docker compose up -d).",
        )

    doc_id   = record.id
    filename = record.original_filename
    chunks   = _chunk_text(text_content)
    logger.info("doc_id={} → {} chunks to embed", doc_id, len(chunks))

    try:
        collection = get_or_create_chroma_collection(chroma_client)
        ids, embeddings, documents, metadatas = [], [], [], []
        for i, chunk in enumerate(chunks):
            ids.append(f"{doc_id}-chunk-{i}")
            embeddings.append(_get_embedding(chunk))
            documents.append(chunk)
            metadatas.append({
                "doc_id": doc_id, "filename": filename,
                "chunk_index": i, "total_chunks": len(chunks),
            })
        for bs in range(0, len(ids), 100):
            collection.upsert(
                ids=ids[bs:bs+100], embeddings=embeddings[bs:bs+100],
                documents=documents[bs:bs+100], metadatas=metadatas[bs:bs+100],
            )
        logger.info("Stored {} chunks in ChromaDB for doc_id={}", len(chunks), doc_id)
        return len(chunks)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("ChromaDB ingestion error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Failed to store chunks: {exc}")


# ──────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────

def ingest_document(
    record: UploadRecord,
    text_content: str,
    structured_meta: Optional[Dict[str, Any]] = None,
) -> Tuple[int, int, int]:
    """
    Route to the correct pipeline based on file extension.
    Returns (chunk_count, node_count, edge_count).
    """
    ext = Path(record.original_filename).suffix.lower()

    if ext in STRUCTURED_EXTENSIONS and structured_meta is not None:
        logger.info("doc_id={} → structured pipeline (Neo4j)", record.id)
        node_count, edge_count = ingest_structured(record, structured_meta)
        return 0, node_count, edge_count
    else:
        logger.info("doc_id={} → unstructured pipeline (ChromaDB)", record.id)
        chunk_count = ingest_unstructured(record, text_content)
        return chunk_count, 0, 0
