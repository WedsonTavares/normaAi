"""Rotas de documentos."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status

from app.core.config import Settings, get_settings
from app.core.errors import InvalidInputError, NotFoundError, PayloadTooLargeError
from app.database.connection import connection
from app.schemas.documents import (
    DocumentDetail,
    DocumentSummary,
    ProcessResult,
    UploadResult,
)
from app.schemas.extraction import ExtractedDocument, ExtractionResponse
from app.services import document_service, extraction_service

router = APIRouter(prefix="/documents", tags=["documents"])

CHUNK_SIZE = 1024 * 1024


async def _read_upload(file: UploadFile, max_bytes: int) -> bytes:
    """Lê o arquivo em blocos e aborta assim que passar do limite (RN-02)."""
    content = bytearray()
    while block := await file.read(CHUNK_SIZE):
        content.extend(block)
        if len(content) > max_bytes:
            raise PayloadTooLargeError(
                f"Arquivo maior que o limite de {max_bytes // (1024 * 1024)} MB."
            )
    if not content:
        raise InvalidInputError("O arquivo enviado está vazio.")
    return bytes(content)


@router.post("", response_model=UploadResult, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File()],
) -> UploadResult:
    content = await _read_upload(file, settings.max_upload_mb * 1024 * 1024)

    with connection() as conn:
        document, already_existed = document_service.create_document(
            conn, file.filename or "sem-nome.pdf", file.content_type, content
        )
        if not already_existed:
            document_service.start_processing(conn, document["id"])

    if not already_existed:
        background_tasks.add_task(document_service.process_document, document["id"])

    return UploadResult(
        document=DocumentDetail.model_validate(document),
        already_existed=already_existed,
    )


@router.get("", response_model=list[DocumentSummary])
def list_documents() -> list[DocumentSummary]:
    with connection() as conn:
        rows = document_service.list_documents(conn)
    return [DocumentSummary.model_validate(row) for row in rows]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: UUID) -> DocumentDetail:
    with connection() as conn:
        row = document_service.get_document(conn, document_id)
    return DocumentDetail.model_validate(row)


@router.get("/{document_id}/extraction", response_model=ExtractionResponse)
def get_extraction(document_id: UUID) -> ExtractionResponse:
    """Extração estruturada vigente do documento (RN-14)."""
    with connection() as conn:
        document_service.get_document(conn, document_id)
        row = extraction_service.get_current_extraction(conn, document_id)

    if row is None:
        raise NotFoundError("Este documento ainda não possui extração estruturada.")

    return ExtractionResponse(
        document_id=row["document_id"],
        model=row["model"],
        prompt_version=row["prompt_version"],
        data=ExtractedDocument.model_validate(row["data"]),
    )


@router.post("/{document_id}/process", response_model=ProcessResult)
def process_document(document_id: UUID, background_tasks: BackgroundTasks) -> ProcessResult:
    """Dispara o processamento. Idempotente: ver RN-08."""
    with connection() as conn:
        started = document_service.start_processing(conn, document_id)

    if started:
        background_tasks.add_task(document_service.process_document, document_id)

    return ProcessResult(document_id=document_id, status="processing")


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID) -> None:
    with connection() as conn:
        document_service.delete_document(conn, document_id)
