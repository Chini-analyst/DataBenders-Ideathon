from fastapi import APIRouter, HTTPException

from models.graph import GraphData, GraphStatsResponse, SubgraphResponse
from services.graph_service import get_all_edges, get_all_nodes, get_subgraph_for_doc

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/nodes")
def get_nodes():
    nodes = get_all_nodes()
    return {"nodes": [n.model_dump() for n in nodes], "total": len(nodes)}


@router.get("/edges")
def get_edges():
    edges = get_all_edges()
    return {"edges": [e.model_dump() for e in edges], "total": len(edges)}


@router.get("/data", response_model=GraphData)
def get_graph_data():
    """Return full graph (nodes + edges) in one call."""
    nodes = get_all_nodes()
    edges = get_all_edges()
    return GraphData(nodes=nodes, edges=edges)


@router.get("/stats", response_model=GraphStatsResponse)
def get_graph_stats():
    nodes = get_all_nodes()
    edges = get_all_edges()

    node_types: dict[str, int] = {}
    for n in nodes:
        node_types[n.type] = node_types.get(n.type, 0) + 1

    rel_types: dict[str, int] = {}
    for e in edges:
        rel_types[e.relationship] = rel_types.get(e.relationship, 0) + 1

    return GraphStatsResponse(
        total_nodes=len(nodes),
        total_edges=len(edges),
        node_types=node_types,
        relationship_types=rel_types,
    )


@router.get("/subgraph/{doc_id}", response_model=SubgraphResponse)
def get_subgraph(doc_id: str):
    graph = get_subgraph_for_doc(doc_id)
    return SubgraphResponse(
        doc_id=doc_id,
        graph=graph,
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
    )
