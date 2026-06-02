"""
Data management router — bulk clear operations.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from core.database import get_chroma_client, get_neo4j_driver, get_or_create_chroma_collection

router = APIRouter(prefix="/api/data", tags=["data"])


class ClearDataResponse(BaseModel):
    success: bool
    message: str
    neo4j_nodes_deleted: int
    chroma_chunks_deleted: int


@router.delete("/all", response_model=ClearDataResponse)
def clear_all_data():
    """
    Permanently delete all nodes/edges from Neo4j and all chunks from ChromaDB.
    Also clears the in-memory upload registry.
    """
    neo4j_deleted = 0
    chroma_deleted = 0
    errors: list[str] = []

    # --- Neo4j: delete all nodes (cascades to relationships) ---
    driver = get_neo4j_driver()
    if driver is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j is not available. Please ensure the service is running.",
        )
    try:
        with driver.session() as session:
            # Count first
            count_result = session.run("MATCH (n) RETURN count(n) AS cnt")
            neo4j_deleted = count_result.single()["cnt"]
            # Delete in batches to avoid memory issues on large graphs
            session.run("CALL apoc.periodic.iterate('MATCH (n) RETURN n', 'DETACH DELETE n', {batchSize: 1000})")
            logger.info("Neo4j: deleted {} nodes (all relationships cascaded)", neo4j_deleted)
    except Exception as exc:
        # apoc may not be available — fall back to plain Cypher
        logger.warning("apoc.periodic.iterate unavailable, using plain DETACH DELETE: {}", exc)
        try:
            with driver.session() as session:
                count_result = session.run("MATCH (n) RETURN count(n) AS cnt")
                neo4j_deleted = count_result.single()["cnt"]
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("Neo4j: deleted {} nodes via DETACH DELETE", neo4j_deleted)
        except Exception as exc2:
            errors.append(f"Neo4j error: {exc2}")
            logger.error("Neo4j clear failed: {}", exc2)

    # --- ChromaDB: delete the entire collection and recreate it empty ---
    chroma = get_chroma_client()
    if chroma is None:
        raise HTTPException(
            status_code=503,
            detail="ChromaDB is not available. Please ensure the service is running.",
        )
    try:
        from core.config import settings
        collection_name = settings.chroma_collection
        # Count chunks before deletion
        col = get_or_create_chroma_collection(chroma, collection_name)
        chroma_deleted = col.count()
        # Delete and recreate the collection (fastest way to wipe all data)
        chroma.delete_collection(collection_name)
        chroma.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB: deleted {} chunks, collection recreated", chroma_deleted)
    except Exception as exc:
        errors.append(f"ChromaDB error: {exc}")
        logger.error("ChromaDB clear failed: {}", exc)

    # --- Clear in-memory upload registry ---
    try:
        from routers.upload import _uploads
        _uploads.clear()
        logger.info("In-memory upload registry cleared")
    except Exception as exc:
        logger.warning("Could not clear upload registry: {}", exc)

    if errors:
        raise HTTPException(
            status_code=500,
            detail=f"Partial failure during clear: {'; '.join(errors)}",
        )

    return ClearDataResponse(
        success=True,
        message=f"All data cleared — {neo4j_deleted} nodes removed from Neo4j, {chroma_deleted} chunks removed from ChromaDB.",
        neo4j_nodes_deleted=neo4j_deleted,
        chroma_chunks_deleted=chroma_deleted,
    )
