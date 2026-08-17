"""Clientes das APIs de IA.

Dois provedores, porque o DeepSeek não gera embeddings. Ambos falam o protocolo da OpenAI,
então muda apenas a base_url. Este é o único lugar que cria clientes e traduz falha de
integração em erro da aplicação.
"""

import logging
from functools import lru_cache

from openai import OpenAI, OpenAIError

from app.core.config import get_settings
from app.core.errors import ExternalServiceError

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 120.0


@lru_cache
def get_llm_client() -> OpenAI:
    """Cliente do modelo de linguagem (extração estruturada e respostas do RAG)."""
    settings = get_settings()
    if not settings.llm_api_key:
        raise ExternalServiceError("Modelo de linguagem não configurado.")
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


@lru_cache
def get_embeddings_client() -> OpenAI:
    """Cliente usado somente para gerar embeddings."""
    settings = get_settings()
    if not settings.embeddings_api_key:
        raise ExternalServiceError("Provedor de embeddings não configurado.")
    return OpenAI(
        api_key=settings.embeddings_api_key,
        base_url=settings.embeddings_base_url,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def translate_provider_error(operation: str, exc: OpenAIError) -> ExternalServiceError:
    """Loga a causa real e devolve um erro sem detalhes internos (RN-81)."""
    logger.error("Falha na chamada de IA (%s): %s", operation, exc)
    return ExternalServiceError("O serviço de IA está indisponível no momento.")


def reset_clients() -> None:
    """Descarta os clientes em cache. Usado quando a configuração muda, nos testes."""
    get_llm_client.cache_clear()
    get_embeddings_client.cache_clear()
