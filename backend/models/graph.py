from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Node(BaseModel):
    id: str
    label: str
    type: str  # e.g. "Organization", "Person", "Concept", "Location", "Document"
    properties: Dict[str, Any] = {}
    doc_id: Optional[str] = None


class Edge(BaseModel):
    id: str
    source: str  # Node id
    target: str  # Node id
    relationship: str  # e.g. "WORKS_FOR", "LOCATED_IN"
    properties: Dict[str, Any] = {}
    doc_id: Optional[str] = None


class GraphData(BaseModel):
    nodes: List[Node]
    edges: List[Edge]


class SubgraphResponse(BaseModel):
    doc_id: str
    graph: GraphData
    node_count: int
    edge_count: int


class GraphStatsResponse(BaseModel):
    total_nodes: int
    total_edges: int
    node_types: Dict[str, int]
    relationship_types: Dict[str, int]
