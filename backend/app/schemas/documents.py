"""Contratos da API de documentos."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

DocumentStatus = Literal["pending", "processing", "ready", "failed"]


class DocumentSummary(BaseModel):
    id: UUID
    filename: str
    status: DocumentStatus
    page_count: int | None
    error_message: str | None
    created_at: datetime


class DocumentDetail(DocumentSummary):
    page_texts: list[str] | None


class UploadResult(BaseModel):
    document: DocumentDetail
    already_existed: bool


class ProcessResult(BaseModel):
    document_id: UUID
    status: DocumentStatus
