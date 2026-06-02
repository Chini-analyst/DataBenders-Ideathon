"""
Document ingestion pipeline.
Parses uploaded files into text chunks, extracts entities and relationships
via regex NER, embeds chunks with Gemini text-embedding-004, and stores
everything in ChromaDB (vectors) and Neo4j (graph).
"""
from __future__ import annotations

import hashlib
import math
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from loguru import logger

from core.config import settings
from core.database import get_chroma_client, get_neo4j_driver, get_or_create_chroma_collection
from models.upload import IngestionStatus, UploadRecord
from services.graph_service import upsert_edge, upsert_node

# ---------------------------------------------------------------------------
# NER patterns — HR & general domain
# ---------------------------------------------------------------------------

_ENTITY_PATTERNS = {
    "Organization": [
        r"\b[A-Z][a-z]+ (?:&|and) [A-Z][a-z]+\b",
        r"\b[A-Z][A-Z]{2,}\b",  # Acronyms: HR, L&D, HRBP, etc.
    ],
    "Person": [
        r"\b(?:Mr\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+ [A-Z][a-z]+\b",
        r"\b[A-Z][a-z]+ [A-Z][a-z]+(?:,\s+(?:CEO|CFO|CTO|CHRO|Partner|Director|Manager|Analyst|Recruiter|Specialist))?\b",
    ],
    "Location": [
        r"\b(?:Singapore|London|New York|Hong Kong|Tokyo|Sydney|Dubai|Mumbai|Shanghai|Beijing|Remote|Berlin|Paris|Amsterdam|Toronto|Chicago|Los Angeles|San Francisco)\b",
    ],
    "Concept": [
        r"\b(?:Talent Acquisition|Workforce Planning|Performance Management|"
        r"Learning and Development|Employee Relations|Compensation and Benefits|"
        r"Onboarding|Headcount Planning|Attrition|Succession Planning|"
        r"Diversity and Inclusion|HR Analytics|Employer Branding|"
        r"Organisational Design|Change Management|Digital Transformation|"
        r"Artificial Intelligence|Machine Learning|Data Analytics)\b",
    ],
}

_RELATIONSHIP_PATTERNS = [
    (r"(\w[\w\s]+)\s+(?:works? for|employed by|joined|reports? to)\s+(\w[\w\s]+)", "WORKS_FOR"),
    (r"(\w[\w\s]+)\s+(?:located in|based in|office in)\s+(\w[\w\s]+)", "BASED_IN"),
    (r"(\w[\w\s]+)\s+(?:manages?|leads?|heads?)\s+(\w[\w\s]+)", "MANAGES"),
    (r"(\w[\w\s]+)\s+(?:requires?|needs?)\s+(\w[\w\s]+)", "REQUIRES_SKILL"),
    (r"(\w[\w\s]+)\s+(?:part of|within|belongs? to)\s+(\w[\w\s]+)", "BELONGS_TO"),
]


def _extract_entities(text: str) -> List[Dict[str, Any]]:
    entities = []
    seen_labels: set = set()
    for entity_type, patterns in _ENTITY_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                label = match.group(0).strip()
                if label and label not in seen_labels and len(label) > 2:
                    seen_labels.add(label)
                    node_id = hashlib.md5(label.lower().encode()).hexdigest()[:12]
                    entities.append({"id": node_id, "label": label, "type": entity_type})
    return entities


def _extract_relationships(
    text: str, entities: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    relationships = []
    entity_map = {e["label"].lower(): e for e in entities}
    for pattern, rel_type in _RELATIONSHIP_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            src_text = match.group(1).strip().lower()
            tgt_text = match.group(2).strip().lower()
            src_entity = next(
                (e for lbl, e in entity_map.items() if src_text in lbl or lbl in src_text), None
            )
            tgt_entity = next(
                (e for lbl, e in entity_map.items() if tgt_text in lbl or lbl in tgt_text), None
            )
            if src_entity and tgt_entity and src_entity["id"] != tgt_entity["id"]:
                relationships.append({
                    "source": src_entity["id"],
                    "target": tgt_entity["id"],
                    "relationship": rel_type,
                })
    return relationships


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end >= len(words):
            break
        start += chunk_size - overlap
    return chunks


def _get_embedding(text: str) -> List[float]:
    """
    Embed text using Gemini text-embedding-004.
    Falls back to a deterministic hash-based vector if the API key is absent
    (allows ingestion to proceed; queries will use the same fallback).
    """
    try:
        import google.generativeai as genai
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
    except Exception as exc:
        logger.warning("Gemini embedding failed, using hash fallback: {}", exc)

    # Hash-based fallback — consistent with retrieval.py fallback
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
    vec = [math.sin(seed * (i + 1) * 0.001) for i in range(384)]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


# ---------------------------------------------------------------------------
# Main ingestion pipeline
# ---------------------------------------------------------------------------

def ingest_document(
    record: UploadRecord,
    text_content: str,
) -> Tuple[int, int, int]:
    """
    Ingest a document through the pipeline.
    Returns (chunk_count, node_count, edge_count).
    Raises HTTP 503 if Neo4j or ChromaDB are unavailable.
    """
    doc_id = record.id
    filename = record.original_filename

    logger.info("Starting ingestion for doc_id={} filename={}", doc_id, filename)

    chroma_client = get_chroma_client()
    neo4j_driver = get_neo4j_driver()

    if chroma_client is None:
        raise HTTPException(
            status_code=503,
            detail="ChromaDB is not available. Please ensure the service is running (docker compose up -d).",
        )
    if neo4j_driver is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j is not available. Please ensure the service is running (docker compose up -d).",
        )

    # 1. Chunk the text
    chunks = _chunk_text(text_content)
    logger.info("Created {} chunks from document", len(chunks))

    # 2. Extract entities and relationships
    entities = _extract_entities(text_content)
    relationships = _extract_relationships(text_content, entities)
    logger.info("Extracted {} entities and {} relationships", len(entities), len(relationships))

    # 3. Store chunks in ChromaDB
    chunk_count = 0
    try:
        collection = get_or_create_chroma_collection(chroma_client)
        chunk_ids, embeddings, documents, metadatas = [], [], [], []

        for i, chunk in enumerate(chunks):
            chunk_ids.append(f"{doc_id}-chunk-{i}")
            embeddings.append(_get_embedding(chunk))
            documents.append(chunk)
            metadatas.append({
                "doc_id": doc_id,
                "filename": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

        for batch_start in range(0, len(chunk_ids), 100):
            batch_end = batch_start + 100
            collection.upsert(
                ids=chunk_ids[batch_start:batch_end],
                embeddings=embeddings[batch_start:batch_end],
                documents=documents[batch_start:batch_end],
                metadatas=metadatas[batch_start:batch_end],
            )
        chunk_count = len(chunks)
        logger.info("Stored {} chunks in ChromaDB", chunk_count)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("ChromaDB ingestion error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Failed to store chunks in ChromaDB: {exc}")

    # 4. Store entities and relationships in Neo4j
    node_count = 0
    edge_count = 0
    for entity in entities:
        if upsert_node(entity["id"], entity["label"], entity["type"], {}, doc_id):
            node_count += 1
    for rel in relationships:
        if upsert_edge(rel["source"], rel["target"], rel["relationship"], {}, doc_id):
            edge_count += 1

    logger.info("Stored {} nodes and {} edges in Neo4j", node_count, edge_count)
    return chunk_count, node_count, edge_count
