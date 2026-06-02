"""
Neo4j Cypher query helpers.
All functions require a live Neo4j connection and raise HTTP 503 if unavailable.
"""
from __future__ import annotations

import re
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


def get_node_neighbourhood(node_id: str, depth: int = 2) -> GraphData:
    """
    Return all nodes and edges reachable from node_id within `depth` hops.
    depth=1 → direct neighbours, depth=2 → neighbours of neighbours, etc.
    """
    driver = _require_driver()
    try:
        with driver.session() as session:
            # Variable-length path up to `depth` hops in either direction
            result = session.run(
                """
                MATCH path = (start {id: $node_id})-[*1..$depth]-(neighbour)
                WITH nodes(path) AS ns, relationships(path) AS rs
                UNWIND ns AS n
                WITH collect(DISTINCT n) AS all_nodes, rs
                UNWIND rs AS r
                WITH all_nodes, collect(DISTINCT r) AS all_rels
                RETURN all_nodes, all_rels
                """,
                node_id=node_id,
                depth=depth,
            )
            record = result.single()
            if not record:
                return GraphData(nodes=[], edges=[])

            nodes: List[Node] = []
            seen_node_ids: set = set()
            for neo_node in record["all_nodes"]:
                labels = list(neo_node.labels)
                node_type = labels[0] if labels else "Unknown"
                props = dict(neo_node.items())
                nid = str(props.pop("id", neo_node.element_id))
                if nid in seen_node_ids:
                    continue
                seen_node_ids.add(nid)
                nodes.append(Node(
                    id=nid,
                    label=props.pop("name", props.pop("label", nid)),
                    type=node_type,
                    properties=props,
                    doc_id=props.get("doc_id"),
                ))

            edges: List[Edge] = []
            seen_edge_ids: set = set()
            for rel in record["all_rels"]:
                eid = str(rel.element_id)
                if eid in seen_edge_ids:
                    continue
                seen_edge_ids.add(eid)
                src_props = dict(rel.start_node.items())
                tgt_props = dict(rel.end_node.items())
                src_id = str(src_props.get("id", rel.start_node.element_id))
                tgt_id = str(tgt_props.get("id", rel.end_node.element_id))
                edges.append(Edge(
                    id=eid,
                    source=src_id,
                    target=tgt_id,
                    relationship=rel.type,
                    properties=dict(rel.items()),
                ))

            return GraphData(nodes=nodes, edges=edges)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Neo4j get_node_neighbourhood error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch neighbourhood: {exc}")


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
    # Sanitise the label: Neo4j labels must be alphanumeric + underscore
    # and must not start with a digit.
    safe_type = re.sub(r"[^a-zA-Z0-9_]", "_", node_type)
    if safe_type and safe_type[0].isdigit():
        safe_type = "_" + safe_type
    safe_type = safe_type or "Entity"
    try:
        with driver.session() as session:
            props = {**properties, "id": node_id, "name": label}
            if doc_id:
                props["doc_id"] = doc_id
            session.run(
                f"MERGE (n:`{safe_type}` {{id: $id}}) SET n += $props",
                id=node_id,
                props=props,
            )
        return True
    except Exception as exc:
        logger.error("Neo4j upsert_node error (type={}): {}", safe_type, exc)
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
    # Sanitise relationship type: SCREAMING_SNAKE_CASE, no special chars
    safe_rel = re.sub(r"[^a-zA-Z0-9_]", "_", relationship).upper().strip("_") or "RELATED_TO"
    try:
        with driver.session() as session:
            props = dict(properties)
            if doc_id:
                props["doc_id"] = doc_id
            session.run(
                f"""
                MATCH (a {{id: $src}}), (b {{id: $tgt}})
                MERGE (a)-[r:`{safe_rel}`]->(b)
                SET r += $props
                """,
                src=src_id,
                tgt=tgt_id,
                props=props,
            )
        return True
    except Exception as exc:
        logger.error("Neo4j upsert_edge error (rel={}): {}", safe_rel, exc)
        return False
