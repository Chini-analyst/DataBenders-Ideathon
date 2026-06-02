"""
Document ingestion pipeline.

CSV / Excel  →  row-level value graph
  • Every non-empty cell value becomes a typed node (type inferred from column name)
  • Every pair of values in the same row gets a directed edge
    (relationship label derived from the two column types)
  • Node IDs are content-addressed (hash of normalised value + inferred type)
    so the same value appearing in multiple files shares one node automatically

Other formats  →  regex NER pipeline (unchanged)

Embeddings via Ollama (nomic-embed-text) with hash fallback.
"""
from __future__ import annotations

import hashlib
import itertools
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from loguru import logger

from core.config import settings
from core.database import get_chroma_client, get_neo4j_driver, get_or_create_chroma_collection
from models.upload import UploadRecord
from services.graph_service import upsert_edge, upsert_node

# ---------------------------------------------------------------------------
# Column-type inference
# Normalised column name  →  semantic node type
# ---------------------------------------------------------------------------

# Each entry: (list-of-keywords-that-match-the-column-name, node-type-label)
# Checked in order; first match wins.
_COLUMN_TYPE_RULES: List[Tuple[List[str], str]] = [
    (["employee_id", "emp_id", "staff_id", "worker_id"], "EmployeeID"),
    # Person — only match columns that are explicitly about a person's name/identity
    # Use exact matches or very specific suffixes to avoid false positives
    (["full_name", "employee_name", "emp_name", "staff_name",
      "person_name", "candidate_name", "candidate"], "Person"),
    (["manager", "supervisor", "reports_to", "managed_by",
      "line_manager", "reporting_to"], "Person"),
    (["department", "dept", "division", "business_unit", "team"], "Department"),
    (["job_title", "title", "position", "role", "designation",
      "job_role", "job_function"], "JobTitle"),
    # Skill — explicit skill/tech columns only (not anything ending in _name)
    (["skill", "skill_name", "competency", "expertise",
      "technology", "tech_stack", "technology_stack", "tool"], "Skill"),
    # Project — explicit project columns only
    (["project", "project_name", "initiative", "programme",
      "program", "workstream", "project_id"], "Project"),
    (["location", "city", "office", "site", "country",
      "region", "base", "work_location"], "Location"),
    (["salary_band", "band", "grade", "pay_grade",
      "compensation_band"], "SalaryBand"),
    (["employment_type", "contract_type", "work_type",
      "engagement_type"], "EmploymentType"),
    (["performance_rating", "rating", "appraisal",
      "performance_score", "review_rating"], "PerformanceRating"),
    (["status", "hiring_status", "project_status",
      "recruitment_status", "state"], "Status"),
    (["priority", "urgency", "importance"], "Priority"),
    (["proficiency_level", "proficiency", "skill_level",
      "expertise_level"], "ProficiencyLevel"),
    (["certified", "certification", "certificate"], "Certification"),
    (["client", "customer", "account"], "Client"),
    (["budget", "budget_usd", "budget_allocated",
      "cost", "spend"], "Budget"),
    (["start_date", "end_date", "date", "hire_date",
      "joining_date", "last_assessed"], "Date"),
    (["team_size", "headcount", "headcount_current",
      "headcount_target"], "Headcount"),
    (["skill_category", "category", "domain", "area",
      "function"], "Category"),
    # Generic name column — only if nothing else matched
    (["name"], "Person"),
]


def _infer_node_type(column_name: str) -> str:
    """Return a semantic node type for a given column name."""
    col = column_name.lower().strip().replace(" ", "_").replace("-", "_")
    for keywords, node_type in _COLUMN_TYPE_RULES:
        for kw in keywords:
            # Exact match, or col IS the keyword, or col ends with _<kw> or starts with <kw>_
            if col == kw or col == kw.replace("_", "") \
                    or col.endswith("_" + kw) or col.startswith(kw + "_"):
                return node_type
    return "Entity"


# ---------------------------------------------------------------------------
# Relationship label derivation
# (source_type, target_type)  →  relationship label
# ---------------------------------------------------------------------------

_REL_MAP: Dict[Tuple[str, str], str] = {
    # Person ↔ everything
    ("Person",          "Department"):       "WORKS_IN",
    ("Person",          "JobTitle"):         "HAS_TITLE",
    ("Person",          "Person"):           "REPORTS_TO",
    ("Person",          "Location"):         "BASED_IN",
    ("Person",          "Skill"):            "HAS_SKILL",
    ("Person",          "Project"):          "WORKS_ON",
    ("Person",          "SalaryBand"):       "ON_BAND",
    ("Person",          "EmploymentType"):   "EMPLOYED_AS",
    ("Person",          "PerformanceRating"):"RATED",
    ("Person",          "Status"):           "HAS_STATUS",
    ("Person",          "Client"):           "SERVES",
    ("Person",          "Category"):         "IN_CATEGORY",
    ("Person",          "EmployeeID"):       "IDENTIFIED_BY",
    # Department ↔ everything
    ("Department",      "JobTitle"):         "HAS_ROLE",
    ("Department",      "Location"):         "LOCATED_IN",
    ("Department",      "Project"):          "OWNS_PROJECT",
    ("Department",      "Status"):           "HAS_STATUS",
    ("Department",      "Budget"):           "HAS_BUDGET",
    ("Department",      "Headcount"):        "HAS_HEADCOUNT",
    ("Department",      "Priority"):         "HAS_PRIORITY",
    # Project ↔ everything
    ("Project",         "Status"):           "HAS_STATUS",
    ("Project",         "Client"):           "FOR_CLIENT",
    ("Project",         "Budget"):           "HAS_BUDGET",
    ("Project",         "Location"):         "BASED_IN",
    ("Project",         "Skill"):            "REQUIRES_SKILL",
    ("Project",         "Priority"):         "HAS_PRIORITY",
    ("Project",         "Date"):             "SCHEDULED",
    ("Project",         "Headcount"):        "HAS_TEAM_SIZE",
    # Skill ↔ everything
    ("Skill",           "Category"):         "IN_CATEGORY",
    ("Skill",           "ProficiencyLevel"): "AT_LEVEL",
    ("Skill",           "Certification"):    "HAS_CERTIFICATION",
    ("Skill",           "Department"):       "USED_IN",
    # JobTitle ↔ everything
    ("JobTitle",        "Department"):       "ROLE_IN",
    ("JobTitle",        "Location"):         "BASED_IN",
    ("JobTitle",        "Status"):           "HAS_STATUS",
    ("JobTitle",        "Priority"):         "HAS_PRIORITY",
    ("JobTitle",        "Headcount"):        "HAS_HEADCOUNT",
    # EmployeeID ↔ everything
    ("EmployeeID",      "Person"):           "IDENTIFIES",
    ("EmployeeID",      "Department"):       "IN_DEPARTMENT",
    ("EmployeeID",      "Skill"):            "HAS_SKILL",
    ("EmployeeID",      "Project"):          "WORKS_ON",
}


def _get_relationship(type_a: str, type_b: str) -> str:
    """Return a relationship label for an ordered pair of node types."""
    if (type_a, type_b) in _REL_MAP:
        return _REL_MAP[(type_a, type_b)]
    # Try reverse
    if (type_b, type_a) in _REL_MAP:
        return _REL_MAP[(type_b, type_a)] + "_REV"
    # Generic fallback
    return "RELATED_TO"


# ---------------------------------------------------------------------------
# Node ID — content-addressed so same value = same node across files
# ---------------------------------------------------------------------------

def _make_value_node_id(value: str, node_type: str) -> str:
    key = f"{node_type.lower()}:{value.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Row-level graph builder
# ---------------------------------------------------------------------------

def _build_row_graph(
    rows: List[Dict[str, str]],
    columns: List[str],
    doc_id: str,
    sheet_name: str = "default",
) -> Tuple[int, int]:
    """
    For each row, create a node per non-empty cell value and connect
    every pair of values in that row with a typed relationship.
    Returns (node_count, edge_count).
    """
    node_count = 0
    edge_count = 0

    # Pre-compute column → node type mapping
    col_type: Dict[str, str] = {col: _infer_node_type(col) for col in columns}

    # Track which node IDs we've already upserted this run to avoid redundant calls
    seen_nodes: set = set()

    for row in rows:
        # Collect (node_id, label, type) for all non-empty cells in this row
        row_nodes: List[Tuple[str, str, str]] = []
        for col in columns:
            val = str(row.get(col, "")).strip()
            if not val or val.lower() in ("nan", "none", "", "n/a", "-"):
                continue
            ntype = col_type[col]
            nid = _make_value_node_id(val, ntype)
            row_nodes.append((nid, val, ntype))

            # Upsert node (once per unique ID)
            if nid not in seen_nodes:
                props = {"column": col, "sheet": sheet_name}
                if upsert_node(nid, val, ntype, props, doc_id):
                    node_count += 1
                seen_nodes.add(nid)

        # Connect every pair of values in this row
        for (src_id, src_val, src_type), (tgt_id, tgt_val, tgt_type) in itertools.combinations(row_nodes, 2):
            if src_id == tgt_id:
                continue
            rel = _get_relationship(src_type, tgt_type)
            props = {"sheet": sheet_name, "row_context": f"{src_val} → {tgt_val}"}
            if upsert_edge(src_id, tgt_id, rel, props, doc_id):
                edge_count += 1

    return node_count, edge_count


# ---------------------------------------------------------------------------
# Ollama embedding
# ---------------------------------------------------------------------------

def _get_embedding(text: str) -> List[float]:
    try:
        import requests
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

    seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
    vec = [math.sin(seed * (i + 1) * 0.001) for i in range(384)]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end >= len(words):
            break
        start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Generic NER pipeline (PDF / DOCX / TXT)
# ---------------------------------------------------------------------------

_ENTITY_PATTERNS = {
    "Organization": [
        r"\b[A-Z][a-z]+ (?:&|and) [A-Z][a-z]+\b",
        r"\b[A-Z][A-Z]{2,}\b",
    ],
    "Person": [
        r"\b(?:Mr\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+ [A-Z][a-z]+\b",
        r"\b[A-Z][a-z]+ [A-Z][a-z]+(?:,\s+(?:CEO|CFO|CTO|CHRO|Partner|Director|Manager|Analyst|Recruiter|Specialist))?\b",
    ],
    "Location": [
        r"\b(?:Singapore|London|New York|Hong Kong|Tokyo|Sydney|Dubai|Mumbai|"
        r"Shanghai|Beijing|Remote|Berlin|Paris|Amsterdam|Toronto|Chicago|"
        r"Los Angeles|San Francisco)\b",
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
    entities, seen = [], set()
    for entity_type, patterns in _ENTITY_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                label = match.group(0).strip()
                if label and label not in seen and len(label) > 2:
                    seen.add(label)
                    nid = hashlib.md5(label.lower().encode()).hexdigest()[:12]
                    entities.append({"id": nid, "label": label, "type": entity_type})
    return entities


def _extract_relationships(text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rels = []
    entity_map = {e["label"].lower(): e for e in entities}
    for pattern, rel_type in _RELATIONSHIP_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            src_text = match.group(1).strip().lower()
            tgt_text = match.group(2).strip().lower()
            src = next((e for lbl, e in entity_map.items() if src_text in lbl or lbl in src_text), None)
            tgt = next((e for lbl, e in entity_map.items() if tgt_text in lbl or lbl in tgt_text), None)
            if src and tgt and src["id"] != tgt["id"]:
                rels.append({"source": src["id"], "target": tgt["id"], "relationship": rel_type})
    return rels


# ---------------------------------------------------------------------------
# Main ingestion pipeline
# ---------------------------------------------------------------------------

def ingest_document(
    record: UploadRecord,
    text_content: str,
    structured_meta: Optional[Dict[str, Any]] = None,
) -> Tuple[int, int, int]:
    """
    Ingest a document.  Returns (chunk_count, node_count, edge_count).

    structured_meta — present for CSV/Excel; triggers the row-level graph builder.
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

    # 1. Chunk + embed → ChromaDB
    chunks = _chunk_text(text_content)
    logger.info("Created {} chunks", len(chunks))

    chunk_count = 0
    try:
        collection = get_or_create_chroma_collection(chroma_client)
        ids, embeddings, documents, metadatas = [], [], [], []
        for i, chunk in enumerate(chunks):
            ids.append(f"{doc_id}-chunk-{i}")
            embeddings.append(_get_embedding(chunk))
            documents.append(chunk)
            metadatas.append({
                "doc_id": doc_id,
                "filename": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
            })
        for bs in range(0, len(ids), 100):
            collection.upsert(
                ids=ids[bs:bs+100],
                embeddings=embeddings[bs:bs+100],
                documents=documents[bs:bs+100],
                metadatas=metadatas[bs:bs+100],
            )
        chunk_count = len(chunks)
        logger.info("Stored {} chunks in ChromaDB", chunk_count)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("ChromaDB ingestion error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Failed to store chunks in ChromaDB: {exc}")

    # 2. Build graph → Neo4j
    node_count = edge_count = 0

    if structured_meta is not None:
        logger.info("Using row-level value graph builder for tabular file")
        # Excel has a "sheets" wrapper; CSV is flat
        sheets: Dict[str, Any] = structured_meta.get("sheets", {"Sheet1": structured_meta})
        for sheet_name, sheet_meta in sheets.items():
            rows: List[Dict[str, str]] = sheet_meta.get("rows", [])
            columns: List[str] = sheet_meta.get("columns", [])
            if not rows:
                continue
            nc, ec = _build_row_graph(rows, columns, doc_id, sheet_name)
            node_count += nc
            edge_count += ec
    else:
        entities = _extract_entities(text_content)
        rels = _extract_relationships(text_content, entities)
        logger.info("NER: {} entities, {} relationships", len(entities), len(rels))
        for e in entities:
            if upsert_node(e["id"], e["label"], e["type"], {}, doc_id):
                node_count += 1
        for r in rels:
            if upsert_edge(r["source"], r["target"], r["relationship"], {}, doc_id):
                edge_count += 1

    logger.info("Graph: {} nodes, {} edges written to Neo4j", node_count, edge_count)
    return chunk_count, node_count, edge_count
