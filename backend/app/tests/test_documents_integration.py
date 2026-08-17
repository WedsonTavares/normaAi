"""Testes contra um PostgreSQL real.

São pulados quando TEST_DATABASE_URL não está definida, para que a suíte rode em
qualquer máquina. Para executá-los:

    docker-compose up -d db
    TEST_DATABASE_URL=postgresql://normaai:normaai@localhost:5434/normaai .venv/bin/python -m pytest
"""

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from psycopg import Connection

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.database.connection import Row, close_pool, connection
from app.database.migrate import run_migrations
from app.schemas.extraction import ExtractedDocument
from app.services import document_service, extraction_service
from app.tests.test_pdf_text import blank_pdf, pdf_with_text

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL não definida")


@pytest.fixture
def conn(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Connection[Row]]:
    """Conexão real, com storage isolado e limpeza do que o teste criar."""
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL or "")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    close_pool()

    run_migrations()
    started_at = datetime.now(UTC)

    with connection() as connected:
        yield connected

    # Remove tudo o que o teste criou, inclusive quando ele falha no meio.
    with connection() as cleanup:
        cleanup.execute("delete from documents where created_at >= %s", (started_at,))

    close_pool()
    get_settings.cache_clear()


def _create(conn: Connection[Row], name: str, *pages: str) -> Row:
    """Cria e commita.

    O commit importa: `process_document` roda em outra conexão, como acontece de verdade
    quando a BackgroundTask executa depois que a resposta HTTP já fechou a transação.
    """
    # O identificador único evita que dois testes gerem PDFs idênticos e caiam na
    # deduplicação por hash, reusando o documento um do outro.
    unicas = (f"{pages[0]} [{uuid.uuid4()}]", *pages[1:])
    document, _ = document_service.create_document(
        conn, name, "application/pdf", pdf_with_text(*unicas)
    )
    conn.commit()
    return document


def test_upload_duplicado_devolve_o_mesmo_documento(conn: Connection[Row]) -> None:
    """RN-04."""
    content = pdf_with_text(f"Art. 1o Deduplicacao {uuid.uuid4()}.")

    first, existed_first = document_service.create_document(
        conn, "norma.pdf", "application/pdf", content
    )
    second, existed_second = document_service.create_document(
        conn, "outro-nome.pdf", "application/pdf", content
    )

    assert existed_first is False
    assert existed_second is True
    assert first["id"] == second["id"]


def test_processamento_concorrente_nao_reinicia(conn: Connection[Row]) -> None:
    """RN-08: o segundo pedido não inicia um novo processamento."""
    document = _create(conn, "norma.pdf", "Art. 1o Teste.")

    assert document_service.start_processing(conn, document["id"]) is True
    assert document_service.start_processing(conn, document["id"]) is False


def test_pipeline_deixa_documento_pronto_com_texto(
    conn: Connection[Row], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pipeline completo com a IA dublada — teste não gasta API nem depende de rede."""
    monkeypatch.setattr(
        extraction_service,
        "extract_from_text",
        lambda text, prompt: ExtractedDocument(title="Portaria de teste"),
    )
    document = _create(conn, "norma.pdf", "Art. 1o Primeira.", "Art. 2o Segunda.")

    document_service.process_document(document["id"])

    updated = document_service.get_document(conn, document["id"])
    assert updated["status"] == "ready"
    assert updated["page_count"] == 2
    assert "Primeira" in updated["page_texts"][0]

    extracao = extraction_service.get_current_extraction(conn, document["id"])
    assert extracao is not None
    assert extracao["data"]["title"] == "Portaria de teste"


def test_pdf_sem_texto_marca_documento_como_failed(conn: Connection[Row]) -> None:
    """RN-03 e RN-06: falha na extração não vira sucesso parcial."""
    document, _ = document_service.create_document(
        conn, "digitalizado.pdf", "application/pdf", blank_pdf(marker=str(uuid.uuid4()))
    )
    conn.commit()

    document_service.process_document(document["id"])

    updated = document_service.get_document(conn, document["id"])
    assert updated["status"] == "failed"
    assert "OCR" in updated["error_message"]


def test_exclusao_remove_registro_e_arquivo(conn: Connection[Row]) -> None:
    """RN-07."""
    document = _create(conn, "norma.pdf", "Art. 1o Teste.")
    stored = Path(document["storage_path"])
    assert stored.exists()

    document_service.delete_document(conn, document["id"])

    assert not stored.exists()
    with pytest.raises(NotFoundError):
        document_service.get_document(conn, document["id"])
