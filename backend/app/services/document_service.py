"""Regras de negócio dos documentos. Ver docs/BUSINESS_RULES.md, seção 1."""

import hashlib
import logging
from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Json

from app.core.config import get_settings
from app.core.errors import AppError, InvalidInputError, NotFoundError
from app.database.connection import Row, connection
from app.services import extraction_service, prompt_service, storage
from app.services.pdf_text import extract_page_texts

logger = logging.getLogger(__name__)


def validate_pdf_upload(filename: str, content_type: str | None) -> None:
    """RN-01: extensão e content-type precisam indicar PDF."""
    if not filename.lower().endswith(".pdf"):
        raise InvalidInputError("Somente arquivos PDF são aceitos.")
    if content_type != "application/pdf":
        raise InvalidInputError("Somente arquivos PDF são aceitos.")


def content_hash(content: bytes) -> str:
    """RN-04: identidade do arquivo é o SHA-256 do conteúdo."""
    return hashlib.sha256(content).hexdigest()


# --- leitura ---------------------------------------------------------------


def list_documents(conn: Connection[Row]) -> list[Row]:
    return conn.execute("select * from documents order by created_at desc").fetchall()


def get_document(conn: Connection[Row], document_id: UUID) -> Row:
    row = conn.execute("select * from documents where id = %s", (document_id,)).fetchone()
    if row is None:
        raise NotFoundError("Documento não encontrado.")
    return row


def _find_by_hash(conn: Connection[Row], digest: str) -> Row | None:
    return conn.execute("select * from documents where content_hash = %s", (digest,)).fetchone()


# --- escrita ---------------------------------------------------------------


def create_document(
    conn: Connection[Row], filename: str, content_type: str | None, content: bytes
) -> tuple[Row, bool]:
    """Cria o documento. Devolve (documento, já_existia) — ver RN-04."""
    validate_pdf_upload(filename, content_type)

    digest = content_hash(content)
    existing = _find_by_hash(conn, digest)
    if existing is not None:
        logger.info("Upload duplicado ignorado: documento %s", existing["id"])
        return existing, True

    path = storage.save_pdf(content, digest)
    row = conn.execute(
        """
        insert into documents (filename, storage_path, content_hash, status)
        values (%s, %s, %s, 'pending')
        returning *
        """,
        (filename, str(path), digest),
    ).fetchone()
    assert row is not None  # insert ... returning sempre devolve uma linha

    logger.info("Documento %s criado a partir de %s", row["id"], filename)
    return row, False


def start_processing(conn: Connection[Row], document_id: UUID) -> bool:
    """Marca o documento como `processing`.

    RN-08: devolve False se ele já estava processando, sem reiniciar nada. A condição está
    dentro do UPDATE para que dois pedidos simultâneos não iniciem dois processamentos.
    """
    get_document(conn, document_id)

    row = conn.execute(
        """
        update documents
           set status = 'processing', error_message = null, updated_at = now()
         where id = %s and status <> 'processing'
        returning id
        """,
        (document_id,),
    ).fetchone()
    return row is not None


def delete_document(conn: Connection[Row], document_id: UUID) -> None:
    """RN-07: remove o registro (chunks e extrações caem em cascata) e o arquivo."""
    document = get_document(conn, document_id)
    conn.execute("delete from documents where id = %s", (document_id,))
    storage.delete_pdf(document["storage_path"])
    logger.info("Documento %s removido", document_id)


# --- processamento ---------------------------------------------------------


def process_document(document_id: UUID) -> None:
    """Pipeline de processamento. Roda em background, com conexão própria.

    Hoje: texto e extração estruturada. Chunking e embeddings entram nesta mesma sequência.
    Só vira `ready` quando todas as etapas passam (RN-06).
    """
    try:
        with connection() as conn:
            document = get_document(conn, document_id)

        page_texts = extract_page_texts(storage.read_pdf(document["storage_path"]))

        with connection() as conn:
            _save_page_texts(conn, document_id, page_texts)
            prompt = prompt_service.get_active_prompt(conn, prompt_service.EXTRACTION_PROMPT)

        # A chamada ao modelo fica fora de qualquer transação: leva dezenas de segundos e
        # seguraria uma conexão do pool sem necessidade.
        text = extraction_service.build_document_text(page_texts)
        data = extraction_service.extract_from_text(text, prompt["content"])

        with connection() as conn:
            extraction_service.save_extraction(
                conn, document_id, prompt["id"], get_settings().llm_model, data
            )
            _mark_ready(conn, document_id)

        logger.info(
            "Documento %s pronto: %d páginas, prompt v%s",
            document_id,
            len(page_texts),
            prompt["version"],
        )

    except AppError as exc:
        # Erro esperado (PDF ilegível, IA indisponível): a mensagem é segura para o usuário.
        _mark_failed(document_id, exc.message)
    except Exception:
        logger.exception("Falha inesperada ao processar documento %s", document_id)
        _mark_failed(document_id, "Falha inesperada ao processar o documento.")


def _save_page_texts(conn: Connection[Row], document_id: UUID, page_texts: list[str]) -> None:
    conn.execute(
        """
        update documents
           set page_texts = %s, page_count = %s, updated_at = now()
         where id = %s
        """,
        (Json(page_texts), len(page_texts), document_id),
    )


def _mark_ready(conn: Connection[Row], document_id: UUID) -> None:
    conn.execute(
        """
        update documents
           set status = 'ready', error_message = null, updated_at = now()
         where id = %s
        """,
        (document_id,),
    )


def _mark_failed(document_id: UUID, message: str) -> None:
    """RN-06: falha em qualquer etapa marca o documento como `failed`."""
    logger.warning("Documento %s marcado como failed: %s", document_id, message)
    try:
        with connection() as conn:
            conn.execute(
                """
                update documents
                   set status = 'failed', error_message = %s, updated_at = now()
                 where id = %s
                """,
                (message, document_id),
            )
    except Exception:
        logger.exception("Não foi possível registrar a falha do documento %s", document_id)
