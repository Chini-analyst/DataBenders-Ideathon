from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RetrievalMode(str, Enum):
    SEMANTIC = "semantic"
    GRAPH = "graph"
    HYBRID = "hybrid"


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    mode: RetrievalMode = RetrievalMode.HYBRID
    top_k: int = Field(default=5, ge=1, le=20)
    doc_filter: Optional[List[str]] = None  # Filter by document IDs


class Source(BaseModel):
    id: str
    text: str
    score: float
    doc_id: Optional[str] = None
    filename: Optional[str] = None
    source_type: str = "semantic"  # "semantic" | "graph"
    metadata: Dict[str, Any] = {}


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[Source]
    mode: RetrievalMode
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
