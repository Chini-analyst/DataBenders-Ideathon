"""
Connection managers for Neo4j and ChromaDB.
Returns None if a service is unreachable — callers are responsible for
raising an appropriate HTTP error when a live connection is required.
"""
from __future__ import annotations

from typing import Optional

from loguru import logger

from core.config import settings

# ---------------------------------------------------------------------------
# Neo4j
# ---------------------------------------------------------------------------
_neo4j_driver = None


def get_neo4j_driver():
    """Return a live Neo4j driver, or None if unavailable."""
    global _neo4j_driver
    if _neo4j_driver is not None:
        return _neo4j_driver
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        driver.verify_connectivity()
        _neo4j_driver = driver
        logger.info("Neo4j connected at {}", settings.neo4j_uri)
        return _neo4j_driver
    except Exception as exc:
        logger.warning("Neo4j unavailable — check that the service is running. Reason: {}", exc)
        return None


def close_neo4j_driver() -> None:
    global _neo4j_driver
    if _neo4j_driver is not None:
        try:
            _neo4j_driver.close()
        except Exception:
            pass
        _neo4j_driver = None
        logger.info("Neo4j driver closed")


# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------
_chroma_client = None


def get_chroma_client():
    """Return a live ChromaDB client, or None if unavailable."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client
    try:
        import chromadb

        client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        # Probe the server
        client.heartbeat()
        _chroma_client = client
        logger.info(
            "ChromaDB connected at {}:{}", settings.chroma_host, settings.chroma_port
        )
        return _chroma_client
    except Exception as exc:
        logger.warning("ChromaDB unavailable — check that the service is running. Reason: {}", exc)
        return None


def close_chroma_client() -> None:
    global _chroma_client
    _chroma_client = None
    logger.info("ChromaDB client released")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_or_create_chroma_collection(client, name: Optional[str] = None):
    """Get or create a ChromaDB collection."""
    collection_name = name or settings.chroma_collection
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
