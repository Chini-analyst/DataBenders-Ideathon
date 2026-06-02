"""
Dual retrieval: ChromaDB vector search + Neo4j graph traversal.
Raises HTTP 503 if the required service is unavailable.
"""
from __future__ import annotations

import hashlib
import math
import time
from typing import List, Optional

from fastapi import HTTPException
from loguru import logger

from core.database import get_chroma_client, get_or_create_chroma_collection, get_neo4j_driver
from models.query import RetrievalMode, Source


# ---------------------------------------------------------------------------
# Embedding — Ollama with local hash fallback
# ---------------------------------------------------------------------------

def _get_embedding(text: str) -> List[float]:
    """
    Embed text using Ollama (nomic-embed-text by default).
    Falls back to a deterministic hash-based vector if Ollama is unreachable.
    """
    try:
        import requests
        from core.config import settings
        payload = {"model": settings.ollama_embed_model, "prompt": text}
        resp = requests.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
    except Exception as exc:
        logger.warning("Ollama embedding failed, using hash fallback: {}", exc)

    # Hash-based fallback (no external dependency)
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
    vec = [math.sin(seed * (i + 1) * 0.001) for i in range(384)]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


# ---------------------------------------------------------------------------
# Semantic retrieval (ChromaDB)
# ---------------------------------------------------------------------------

def semantic_search(
    query: str,
    top_k: int = 5,
    doc_filter: Optional[List[str]] = None,
) -> List[Source]:
    client = get_chroma_client()
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="ChromaDB is not available. Please ensure the service is running (docker compose up -d).",
        )

    try:
        collection = get_or_create_chroma_collection(client)
        query_embedding = _get_embedding(query)

        where_filter = None
        if doc_filter:
            where_filter = {"doc_id": {"$in": doc_filter}}

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        sources = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        for doc, meta, dist, rid in zip(docs, metas, distances, ids):
            score = max(0.0, 1.0 - dist)  # cosine distance → similarity
            sources.append(
                Source(
                    id=rid,
                    text=doc,
                    score=round(score, 4),
                    doc_id=meta.get("doc_id"),
                    filename=meta.get("filename"),
                    source_type="semantic",
                    metadata=meta,
                )
            )
        return sources
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("ChromaDB semantic_search error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {exc}")


# ---------------------------------------------------------------------------
# Graph retrieval (Neo4j)
# ---------------------------------------------------------------------------

def graph_search(
    query: str,
    top_k: int = 5,
    doc_filter: Optional[List[str]] = None,
) -> List[Source]:
    driver = get_neo4j_driver()
    if driver is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j is not available. Please ensure the service is running (docker compose up -d).",
        )

    try:
        keywords = [w.lower() for w in query.split() if len(w) > 3]
        if not keywords:
            keywords = [query.lower()]

        with driver.session() as session:
            cypher = """
            MATCH (n)
            WHERE any(kw IN $keywords WHERE toLower(n.name) CONTAINS kw
                      OR toLower(coalesce(n.description, '')) CONTAINS kw)
            OPTIONAL MATCH (n)-[r]-(m)
            RETURN n.name AS name, n.id AS nid, labels(n) AS labels,
                   collect(DISTINCT {rel: type(r), other: m.name}) AS connections
            LIMIT $limit
            """
            result = session.run(cypher, keywords=keywords, limit=top_k)
            sources = []
            for record in result:
                connections = record["connections"] or []
                conn_text = "; ".join(
                    f"{c['rel']} {c['other']}"
                    for c in connections
                    if c.get("other")
                )
                text = f"{record['name']} ({', '.join(record['labels'])})"
                if conn_text:
                    text += f" — Relationships: {conn_text}"
                sources.append(
                    Source(
                        id=f"graph-{record['nid'] or record['name']}",
                        text=text,
                        score=0.75,
                        source_type="graph",
                        metadata={"node_id": record["nid"], "labels": record["labels"]},
                    )
                )
            return sources
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Neo4j graph_search error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Graph search failed: {exc}")


# ---------------------------------------------------------------------------
# Hybrid retrieval
# ---------------------------------------------------------------------------

def hybrid_search(
    query: str,
    top_k: int = 5,
    doc_filter: Optional[List[str]] = None,
) -> List[Source]:
    half = max(1, top_k // 2)
    semantic = semantic_search(query, top_k=half + 1, doc_filter=doc_filter)
    graph = graph_search(query, top_k=half, doc_filter=doc_filter)

    seen: set = set()
    combined = []
    for src in semantic + graph:
        if src.id not in seen:
            seen.add(src.id)
            combined.append(src)

    combined.sort(key=lambda s: s.score, reverse=True)
    return combined[:top_k]


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def retrieve(
    query: str,
    mode: RetrievalMode,
    top_k: int = 5,
    doc_filter: Optional[List[str]] = None,
) -> tuple[List[Source], float]:
    """Run retrieval and return (sources, elapsed_ms)."""
    start = time.perf_counter()

    if mode == RetrievalMode.SEMANTIC:
        sources = semantic_search(query, top_k=top_k, doc_filter=doc_filter)
    elif mode == RetrievalMode.GRAPH:
        sources = graph_search(query, top_k=top_k, doc_filter=doc_filter)
    else:
        sources = hybrid_search(query, top_k=top_k, doc_filter=doc_filter)

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("Retrieval mode={} returned {} sources in {:.1f}ms", mode, len(sources), elapsed_ms)
    return sources, elapsed_ms
