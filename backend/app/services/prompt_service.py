"""Versionamento dos prompts (RN-20, RN-21).

Prompt existente nunca é editado: uma alteração cria nova versão, por migração.
"""

import logging
from uuid import UUID

from psycopg import Connection

from app.core.errors import ExternalServiceError
from app.database.connection import Row

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = "document_extraction"


def get_active_prompt(conn: Connection[Row], name: str) -> Row:
    """Versão ativa do prompt. Sem versão ativa o sistema não deve adivinhar nada."""
    row = conn.execute(
        "select id, name, version, content from prompt_versions where name = %s and is_active",
        (name,),
    ).fetchone()

    if row is None:
        raise ExternalServiceError("Nenhuma versão ativa do prompt de extração foi encontrada.")
    return row


def get_prompt_version(conn: Connection[Row], prompt_version_id: UUID) -> Row | None:
    return conn.execute(
        "select id, name, version, content from prompt_versions where id = %s",
        (prompt_version_id,),
    ).fetchone()
