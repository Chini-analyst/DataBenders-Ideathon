from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IngestionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadRecord(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: IngestionStatus = IngestionStatus.PENDING
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    chunk_count: int = 0
    node_count: int = 0
    edge_count: int = 0


class UploadResponse(BaseModel):
    success: bool
    message: str
    record: Optional[UploadRecord] = None


class UploadListResponse(BaseModel):
    uploads: list[UploadRecord]
    total: int


class DeleteResponse(BaseModel):
    success: bool
    message: str
    id: str
