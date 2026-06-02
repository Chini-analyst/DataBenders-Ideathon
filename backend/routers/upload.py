"""
Upload router — handles document ingestion.
Uses in-memory storage for upload tracking (resets on server restart).

Routing:
  .csv / .xlsx / .xls  →  Neo4j (structured graph pipeline)
  everything else      →  ChromaDB (unstructured vector pipeline)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from loguru import logger

from core.config import settings
from models.upload import (
    DeleteResponse,
    IngestionStatus,
    UploadListResponse,
    UploadRecord,
    UploadResponse,
)
from parsers import SUPPORTED_EXTENSIONS, parse_file
from services.ingestion import STRUCTURED_EXTENSIONS, ingest_document

router = APIRouter(prefix="/api", tags=["upload"])

# In-memory upload registry (keyed by doc_id)
_uploads: dict[str, UploadRecord] = {}


def _get_upload_dir() -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


async def _run_ingestion(record: UploadRecord, file_path: str) -> None:
    """
    Background task — detect file type and route to the correct pipeline:
      structured   → parse into rows/columns → Neo4j
      unstructured → extract text → ChromaDB
    """
    try:
        record.status = IngestionStatus.PROCESSING
        _uploads[record.id] = record

        ext = Path(file_path).suffix.lower()
        structured_meta = None

        if ext == ".csv":
            from parsers.csv_parser import parse_csv_structured
            text_content, structured_meta = parse_csv_structured(file_path)
        elif ext in (".xlsx", ".xls"):
            from parsers.excel_parser import parse_excel_structured
            text_content, structured_meta = parse_excel_structured(file_path)
        else:
            # Unstructured: extract plain text only
            text_content = parse_file(file_path)

        if not text_content.strip():
            raise ValueError("No text content could be extracted from the file")

        chunk_count, node_count, edge_count = ingest_document(
            record,
            text_content,
            structured_meta=structured_meta,
        )

        record.status = IngestionStatus.COMPLETED
        record.completed_at = datetime.utcnow()
        record.chunk_count = chunk_count
        record.node_count = node_count
        record.edge_count = edge_count
        _uploads[record.id] = record

        store = "Neo4j" if ext in STRUCTURED_EXTENSIONS else "ChromaDB"
        logger.info(
            "Ingestion complete for doc_id={} → {}: "
            "{} chunks, {} nodes, {} edges",
            record.id, store, chunk_count, node_count, edge_count,
        )

    except Exception as exc:
        logger.error("Ingestion failed for doc_id={}: {}", record.id, exc)
        record.status = IngestionStatus.FAILED
        record.error_message = str(exc)
        record.completed_at = datetime.utcnow()
        _uploads[record.id] = record


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb} MB",
        )

    doc_id = str(uuid.uuid4())
    safe_name = f"{doc_id}{ext}"
    file_path = _get_upload_dir() / safe_name

    with open(file_path, "wb") as fh:
        fh.write(content)

    record = UploadRecord(
        id=doc_id,
        filename=safe_name,
        original_filename=file.filename or safe_name,
        file_type=ext.lstrip("."),
        file_size=len(content),
        status=IngestionStatus.PENDING,
    )
    _uploads[doc_id] = record

    background_tasks.add_task(_run_ingestion, record, str(file_path))

    store = "Neo4j" if ext in STRUCTURED_EXTENSIONS else "ChromaDB"
    logger.info("Accepted upload: {} ({}) → {}", file.filename, doc_id, store)

    return UploadResponse(
        success=True,
        message=(
            f"File '{file.filename}' uploaded successfully. "
            f"Processing in background ({store})."
        ),
        record=record,
    )


@router.get("/uploads", response_model=UploadListResponse)
def list_uploads():
    uploads = sorted(_uploads.values(), key=lambda r: r.uploaded_at, reverse=True)
    return UploadListResponse(uploads=uploads, total=len(uploads))


@router.get("/uploads/{upload_id}", response_model=UploadRecord)
def get_upload(upload_id: str):
    record = _uploads.get(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Upload '{upload_id}' not found")
    return record


@router.delete("/uploads/{upload_id}", response_model=DeleteResponse)
def delete_upload(upload_id: str):
    record = _uploads.get(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Upload '{upload_id}' not found")

    # Remove file from disk
    file_path = _get_upload_dir() / record.filename
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as exc:
            logger.warning("Could not delete file {}: {}", file_path, exc)

    ext = Path(record.filename).suffix.lower()

    # Remove from the appropriate store
    if ext in STRUCTURED_EXTENSIONS:
        # Neo4j: delete all nodes tagged with this doc_id
        try:
            from core.database import get_neo4j_driver
            driver = get_neo4j_driver()
            if driver:
                with driver.session() as session:
                    session.run(
                        "MATCH (n {doc_id: $doc_id}) DETACH DELETE n",
                        doc_id=record.id,
                    )
                logger.info("Deleted Neo4j nodes for doc_id={}", record.id)
        except Exception as exc:
            logger.warning("Could not delete Neo4j nodes for {}: {}", record.id, exc)
    else:
        # ChromaDB: delete all chunks for this doc
        try:
            from adapters.chroma_adapter import get_chroma_adapter
            get_chroma_adapter().delete_by_doc_id(record.id)
        except Exception as exc:
            logger.warning("Could not delete ChromaDB chunks for {}: {}", record.id, exc)

    del _uploads[record.id]
    logger.info("Deleted upload {}", record.id)

    return DeleteResponse(
        success=True,
        message=f"Upload '{record.original_filename}' deleted successfully",
        id=record.id,
    )
