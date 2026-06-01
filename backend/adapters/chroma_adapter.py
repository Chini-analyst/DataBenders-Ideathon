"""
Custom ChromaDB storage adapter for LightRAG-style pipelines.
Provides a unified interface for storing and querying vector embeddings.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from core.config import settings
from core.database import get_chroma_client, get_or_create_chroma_collection


class ChromaAdapter:
    """
    Adapter that wraps ChromaDB operations with graceful fallback.
    Maintains an in-memory store when ChromaDB is unavailable.
    """

    def __init__(self, collection_name: Optional[str] = None):
        self.collection_name = collection_name or settings.chroma_collection
        self._memory_store: Dict[str, Dict[str, Any]] = {}

    def _get_collection(self):
        client = get_chroma_client()
        if client is None:
            return None
        return get_or_create_chroma_collection(client, self.collection_name)

    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Store documents with their embeddings."""
        collection = self._get_collection()

        if collection is None:
            # Fall back to in-memory
            for i, doc_id in enumerate(ids):
                self._memory_store[doc_id] = {
                    "embedding": embeddings[i],
                    "document": documents[i],
                    "metadata": (metadatas[i] if metadatas else {}),
                }
            logger.debug("ChromaAdapter: stored {} docs in memory", len(ids))
            return True

        try:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas or [{} for _ in ids],
            )
            logger.debug("ChromaAdapter: upserted {} docs to ChromaDB", len(ids))
            return True
        except Exception as exc:
            logger.error("ChromaAdapter upsert error: {}", exc)
            return False

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, str, float, Dict[str, Any]]]:
        """
        Query for similar documents.
        Returns list of (id, document, score, metadata).
        """
        collection = self._get_collection()

        if collection is None:
            return self._memory_query(query_embedding, n_results)

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
            output = []
            ids = results.get("ids", [[]])[0]
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for rid, doc, meta, dist in zip(ids, docs, metas, distances):
                score = max(0.0, 1.0 - dist)
                output.append((rid, doc, round(score, 4), meta or {}))
            return output
        except Exception as exc:
            logger.error("ChromaAdapter query error: {}", exc)
            return self._memory_query(query_embedding, n_results)

    def _memory_query(
        self, query_embedding: List[float], n_results: int
    ) -> List[Tuple[str, str, float, Dict[str, Any]]]:
        """Cosine similarity search over in-memory store."""
        import math

        def cosine_sim(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
            norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
            return dot / (norm_a * norm_b)

        scored = []
        for doc_id, entry in self._memory_store.items():
            sim = cosine_sim(query_embedding, entry["embedding"])
            scored.append((doc_id, entry["document"], sim, entry["metadata"]))

        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:n_results]

    def delete_by_doc_id(self, doc_id: str) -> bool:
        """Delete all chunks belonging to a document."""
        collection = self._get_collection()

        if collection is None:
            before = len(self._memory_store)
            self._memory_store = {
                k: v for k, v in self._memory_store.items()
                if v.get("metadata", {}).get("doc_id") != doc_id
            }
            logger.debug(
                "ChromaAdapter: removed {} in-memory chunks for doc_id={}",
                before - len(self._memory_store), doc_id,
            )
            return True

        try:
            collection.delete(where={"doc_id": doc_id})
            logger.info("ChromaAdapter: deleted chunks for doc_id={}", doc_id)
            return True
        except Exception as exc:
            logger.error("ChromaAdapter delete error: {}", exc)
            return False

    def count(self) -> int:
        """Return total number of stored documents."""
        collection = self._get_collection()
        if collection is None:
            return len(self._memory_store)
        try:
            return collection.count()
        except Exception:
            return 0


# Singleton adapter instance
_adapter: Optional[ChromaAdapter] = None


def get_chroma_adapter() -> ChromaAdapter:
    global _adapter
    if _adapter is None:
        _adapter = ChromaAdapter()
    return _adapter
