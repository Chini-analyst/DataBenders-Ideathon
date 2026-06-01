"""
Neo4j Cypher query helpers.
All functions require a live Neo4j connection and raise HTTP 503 if unavailable.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from loguru import logger

from core.database import get_neo4j_driver
from models.graph import Edge, GraphData, Node


def _require_driver():
    driver = get_neo4j_driver()
    if driver is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j is not available. Please ensure the service is running (docker compose up -d).",
        )
    return driver


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_nodes() -> List[Node]:
    driver = _require_driver()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (n) RETURN n, labels(n) AS labels, elementId(n) AS eid LIMIT 500"
            )
            nodes = []
            for record in result:
                neo_node = record["n"]
                labels = record["labels"]
                eid = record["eid"]
                node_type = labels[0] if labels else "Unknown"
                props = dict(neo_node.items())
                node_id = props.pop("id", eid)
                nodes.append(
                    Node(
                        id=str(node_id),
                        label=props.pop("name", props.pop("label", str(node_id))),
                        type=node_type,
                        properties=props,
                        doc_id=props.get("doc_id"),
                    )
                )
            return nodes
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Neo4j get_all_nodes error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch nodes: {exc}")


def get_all_edges() -> List[Edge]:
    driver = _require_driver()
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (a)-[r]->(b)
                RETURN
                    elementId(r) AS eid,
                    a.id AS src_id, elementId(a) AS src_eid,
                    b.id AS tgt_id, elementId(b) AS tgt_eid,
                    type(r) AS rel_type,
                    properties(r) AS props
                LIMIT 1000
                """
            )
            edges = []
            for record in result:
                src = str(record["src_id"] or record["src_eid"])
                tgt = str(record["tgt_id"] or record["tgt_eid"])
                edges.append(
                    Edge(
                        id=str(record["eid"]),
                        source=src,
                        target=tgt,
                        relationship=record["rel_type"],
                        properties=dict(record["props"] or {}),
                    )
                )
            return edges
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Neo4j get_all_edges error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch edges: {exc}")


def get_subgraph_for_doc(doc_id: str) -> GraphData:
    driver = _require_driver()
    try:
        with driver.session() as session:
            node_result = session.run(
                "MATCH (n {doc_id: $doc_id}) RETURN n, labels(n) AS labels, elementId(n) AS eid",
                doc_id=doc_id,
            )
            nodes = []
            node_ids = set()
            for record in node_result:
                neo_node = record["n"]
                labels = record["labels"]
                eid = record["eid"]
                node_type = labels[0] if labels else "Unknown"
                props = dict(neo_node.items())
                node_id = str(props.pop("id", eid))
                node_ids.add(node_id)
                nodes.append(
                    Node(
                        id=node_id,
                        label=props.pop("name", props.pop("label", node_id)),
                        type=node_type,
                        properties=props,
                        doc_id=doc_id,
                    )
                )

            edges = []
            if node_ids:
                edge_result = session.run(
                    """
                    MATCH (a)-[r]->(b)
                    WHERE a.id IN $ids AND b.id IN $ids
                    RETURN elementId(r) AS eid, a.id AS src, b.id AS tgt,
                           type(r) AS rel_type, properties(r) AS props
                    """,
                    ids=list(node_ids),
                )
                for record in edge_result:
                    edges.append(
                        Edge(
                            id=str(record["eid"]),
                            source=str(record["src"]),
                            target=str(record["tgt"]),
                            relationship=record["rel_type"],
                            properties=dict(record["props"] or {}),
                            doc_id=doc_id,
                        )
                    )

            return GraphData(nodes=nodes, edges=edges)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Neo4j get_subgraph_for_doc error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch subgraph: {exc}")


def upsert_node(
    node_id: str,
    label: str,
    node_type: str,
    properties: Dict[str, Any],
    doc_id: Optional[str] = None,
) -> bool:
    driver = get_neo4j_driver()
    if driver is None:
        return False
    try:
        with driver.session() as session:
            props = {**properties, "id": node_id, "name": label}
            if doc_id:
                props["doc_id"] = doc_id
            session.run(
                f"MERGE (n:{node_type} {{id: $id}}) SET n += $props",
                id=node_id,
                props=props,
            )
        return True
    except Exception as exc:
        logger.error("Neo4j upsert_node error: {}", exc)
        return False


def upsert_edge(
    src_id: str,
    tgt_id: str,
    relationship: str,
    properties: Dict[str, Any],
    doc_id: Optional[str] = None,
) -> bool:
    driver = get_neo4j_driver()
    if driver is None:
        return False
    try:
        with driver.session() as session:
            props = dict(properties)
            if doc_id:
                props["doc_id"] = doc_id
            session.run(
                f"""
                MATCH (a {{id: $src}}), (b {{id: $tgt}})
                MERGE (a)-[r:{relationship}]->(b)
                SET r += $props
                """,
                src=src_id,
                tgt=tgt_id,
                props=props,
            )
        return True
    except Exception as exc:
        logger.error("Neo4j upsert_edge error: {}", exc)
        return False
