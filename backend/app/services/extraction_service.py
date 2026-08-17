"""Extração estruturada dos dados da norma (RN-10 a RN-14)."""

import json
import logging
from uuid import UUID

from openai import OpenAIError
from psycopg import Connection
from psycopg.types.json import Json

from app.core.config import get_settings
from app.core.errors import ExternalServiceError
from app.database.connection import Row
from app.schemas.extraction import ExtractedDocument
from app.services import prompt_service
from app.services.llm_client import get_llm_client, translate_provider_error

logger = logging.getLogger(__name__)

# Trecho do documento enviado ao modelo. Normas longas passam do limite de contexto e do
# orçamento; o começo concentra título, órgão, tipo e data.
MAX_CHARS_SENT = 20_000

# O modelo raciocina antes de responder, e esses tokens contam aqui. Valor curto devolve
# resposta vazia.
MAX_OUTPUT_TOKENS = 4_000


def build_document_text(page_texts: list[str]) -> str:
    """Junta as páginas e corta no limite enviado ao modelo."""
    return "\n\n".join(page_texts)[:MAX_CHARS_SENT]


def extract_from_text(text: str, prompt: str) -> ExtractedDocument:
    """Chama o modelo e valida a resposta.

    RN-12: saída que não couber no schema é falha da etapa, nunca gravação parcial.
    """
    settings = get_settings()
    client = get_llm_client()

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0,
        )
    except OpenAIError as exc:
        raise translate_provider_error("extração estruturada", exc) from exc

    raw = response.choices[0].message.content
    if not raw:
        raise ExternalServiceError("O modelo devolveu uma resposta vazia na extração.")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Extração devolveu JSON inválido: %s", raw[:500])
        raise ExternalServiceError("O modelo devolveu uma resposta em formato inválido.") from exc

    return ExtractedDocument.model_validate(payload)


def save_extraction(
    conn: Connection[Row],
    document_id: UUID,
    prompt_version_id: UUID,
    model: str,
    data: ExtractedDocument,
) -> Row:
    """RN-13 e RN-14: registra modelo e versão do prompt, preservando extrações anteriores."""
    row = conn.execute(
        """
        insert into document_extractions (document_id, prompt_version_id, model, data)
        values (%s, %s, %s, %s)
        returning *
        """,
        (document_id, prompt_version_id, model, Json(data.model_dump(mode="json"))),
    ).fetchone()
    assert row is not None
    return row


def get_current_extraction(conn: Connection[Row], document_id: UUID) -> Row | None:
    """RN-14: a extração vigente é a mais recente."""
    return conn.execute(
        """
        select e.*, p.version as prompt_version
          from document_extractions e
          join prompt_versions p on p.id = e.prompt_version_id
         where e.document_id = %s
      order by e.created_at desc
         limit 1
        """,
        (document_id,),
    ).fetchone()


def extract_and_save(conn: Connection[Row], document_id: UUID, page_texts: list[str]) -> Row:
    """Etapa de extração dentro do pipeline de processamento."""
    prompt = prompt_service.get_active_prompt(conn, prompt_service.EXTRACTION_PROMPT)
    data = extract_from_text(build_document_text(page_texts), prompt["content"])

    logger.info(
        "Extração do documento %s concluída | prompt v%s | %d obrigações | %d prazos",
        document_id,
        prompt["version"],
        len(data.obligations),
        len(data.deadlines),
    )
    return save_extraction(conn, document_id, prompt["id"], get_settings().llm_model, data)
