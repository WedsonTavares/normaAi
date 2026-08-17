"""Testes da extração estruturada, com o provedor de IA substituído por dublê."""

import json
from typing import Any

import pytest
from openai import APITimeoutError
from pydantic import ValidationError

from app.core.errors import ExternalServiceError
from app.schemas.extraction import ExtractedDocument
from app.services import extraction_service, llm_client

RESPOSTA_COMPLETA = {
    "title": "Portaria nº 123, de 5 de março de 2024",
    "issuing_body": "Ministério da Fazenda",
    "document_type": "Portaria",
    "published_at": "2024-03-05",
    "subjects": ["prazos de entrega"],
    "obligations": [{"description": "Entregar a declaração", "responsible": "Contribuinte"}],
    "deadlines": [{"description": "Entrega da declaração", "due": "30 dias"}],
    "related_articles": ["Lei nº 9.430/1996"],
}


class FakeCompletions:
    def __init__(self, content: str | None = None, error: Exception | None = None) -> None:
        self._content = content
        self._error = error
        self.chamada: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        self.chamada = kwargs
        if self._error is not None:
            raise self._error

        message = type("Message", (), {"content": self._content})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


def fake_client(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> FakeCompletions:
    completions = FakeCompletions(**kwargs)
    client = type("Client", (), {"chat": type("Chat", (), {"completions": completions})()})()
    monkeypatch.setattr(llm_client, "get_llm_client", lambda: client)
    monkeypatch.setattr(extraction_service, "get_llm_client", lambda: client)
    return completions


def test_saida_valida_vira_modelo_tipado(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client(monkeypatch, content=json.dumps(RESPOSTA_COMPLETA))

    data = extraction_service.extract_from_text("texto da norma", "prompt")

    assert data.issuing_body == "Ministério da Fazenda"
    assert data.published_at is not None
    assert data.published_at.year == 2024
    assert data.obligations[0].responsible == "Contribuinte"


def test_json_invalido_vira_erro_tratado(monkeypatch: pytest.MonkeyPatch) -> None:
    """RN-12: resposta que não é JSON não pode ser gravada."""
    fake_client(monkeypatch, content="isto nao e json")

    with pytest.raises(ExternalServiceError):
        extraction_service.extract_from_text("texto", "prompt")


def test_resposta_vazia_vira_erro_tratado(monkeypatch: pytest.MonkeyPatch) -> None:
    """O modelo de raciocínio devolve conteúdo vazio se o orçamento de tokens acabar."""
    fake_client(monkeypatch, content="")

    with pytest.raises(ExternalServiceError):
        extraction_service.extract_from_text("texto", "prompt")


def test_falha_do_provedor_nao_vaza_detalhe(monkeypatch: pytest.MonkeyPatch) -> None:
    """RN-81: a mensagem ao usuário é genérica."""
    fake_client(monkeypatch, error=APITimeoutError(request=None))  # type: ignore[arg-type]

    with pytest.raises(ExternalServiceError) as exc:
        extraction_service.extract_from_text("texto", "prompt")

    assert "indisponível" in str(exc.value)


def test_saida_fora_do_schema_e_rejeitada(monkeypatch: pytest.MonkeyPatch) -> None:
    """RN-12: obrigação sem descrição não cabe no contrato."""
    fake_client(monkeypatch, content=json.dumps({"obligations": [{"responsible": "X"}]}))

    with pytest.raises(ValidationError):
        extraction_service.extract_from_text("texto", "prompt")


def test_pede_json_e_orcamento_de_tokens_suficiente(monkeypatch: pytest.MonkeyPatch) -> None:
    completions = fake_client(monkeypatch, content=json.dumps(RESPOSTA_COMPLETA))

    extraction_service.extract_from_text("texto", "prompt")

    assert completions.chamada["response_format"] == {"type": "json_object"}
    assert completions.chamada["max_tokens"] >= 2000
    assert completions.chamada["temperature"] == 0


def test_texto_longo_e_cortado_no_limite() -> None:
    paginas = ["a" * 15_000, "b" * 15_000]

    texto = extraction_service.build_document_text(paginas)

    assert len(texto) == extraction_service.MAX_CHARS_SENT


def test_campos_ausentes_viram_nulo_ou_lista_vazia() -> None:
    """RN-11: o modelo não deve inventar, e o schema não deve exigir."""
    data = ExtractedDocument.model_validate({"title": "Lei X"})

    assert data.issuing_body is None
    assert data.subjects == []
    assert data.obligations == []


@pytest.mark.parametrize("valor", ["", "null", "não informado", "N/A"])
def test_texto_de_ausencia_do_modelo_vira_nulo(valor: str) -> None:
    data = ExtractedDocument.model_validate({"issuing_body": valor, "published_at": valor})

    assert data.issuing_body is None
    assert data.published_at is None
