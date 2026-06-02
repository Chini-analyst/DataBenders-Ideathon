"""
Upload router — handles document ingestion.
Uses in-memory storage for upload tracking (no database required for metadata).
"""
from __future__ import annotations

import asyncio
import os
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
from services.ingestion import ingest_document

router = APIRouter(prefix="/api", tags=["upload"])

# In-memory store for demo
_uploads: dict[str, UploadRecord] = {}


def _get_upload_dir() -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


async def _run_ingestion(record: UploadRecord, file_path: str) -> None:
    """Background task: parse file and run ingestion pipeline."""
    try:
        record.status = IngestionStatus.PROCESSING
        _uploads[record.id] = record

        text_content = parse_file(file_path)
        if not text_content.strip():
            raise ValueError("No text content could be extracted from the file")

        chunk_count, node_count, edge_count = ingest_document(record, text_content)

        record.status = IngestionStatus.COMPLETED
        record.completed_at = datetime.utcnow()
        record.chunk_count = chunk_count
        record.node_count = node_count
        record.edge_count = edge_count
        _uploads[record.id] = record

        logger.info(
            "Ingestion complete for doc_id={}: {} chunks, {} nodes, {} edges",
            record.id, chunk_count, node_count, edge_count,
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
    # Validate extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Read content
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB",
        )

    # Save to disk
    doc_id = str(uuid.uuid4())
    safe_name = f"{doc_id}{ext}"
    upload_dir = _get_upload_dir()
    file_path = upload_dir / safe_name

    with open(file_path, "wb") as f:
        f.write(content)

    record = UploadRecord(
        id=doc_id,
        filename=safe_name,
        original_filename=file.filename or safe_name,
        file_type=ext.lstrip("."),
        file_size=len(content),
        status=IngestionStatus.PENDING,
    )
    _uploads[doc_id] = record

    # Kick off background ingestion
    background_tasks.add_task(_run_ingestion, record, str(file_path))

    logger.info("Accepted upload: {} ({})", file.filename, doc_id)
    return UploadResponse(
        success=True,
        message=f"File '{file.filename}' uploaded successfully. Processing in background.",
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
    upload_dir = _get_upload_dir()
    file_path = upload_dir / record.filename
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as exc:
            logger.warning("Could not delete file {}: {}", file_path, exc)

    # Remove from ChromaDB
    try:
        from adapters.chroma_adapter import get_chroma_adapter
        get_chroma_adapter().delete_by_doc_id(upload_id)
    except Exception as exc:
        logger.warning("Could not delete ChromaDB chunks for {}: {}", upload_id, exc)

    del _uploads[upload_id]
    logger.info("Deleted upload {}", upload_id)

    return DeleteResponse(
        success=True,
        message=f"Upload '{record.original_filename}' deleted successfully",
        id=upload_id,
    )
