"""Contrato da extração estruturada (RN-10).

Este schema é a fronteira de confiança: a saída do modelo só é gravada se couber aqui.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

VAZIOS = {"", "null", "none", "n/a", "nao informado", "não informado"}


class Obligation(BaseModel):
    description: str
    responsible: str | None = None


class Deadline(BaseModel):
    description: str
    due: str | None = None


class ExtractedDocument(BaseModel):
    """Dados que a IA extrai de uma norma. Campo ausente é null ou lista vazia (RN-11)."""

    title: str | None = None
    issuing_body: str | None = None
    document_type: str | None = None
    published_at: date | None = None
    subjects: list[str] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    deadlines: list[Deadline] = Field(default_factory=list)
    related_articles: list[str] = Field(default_factory=list)

    @field_validator("title", "issuing_body", "document_type", mode="before")
    @classmethod
    def texto_vazio_vira_nulo(cls, value: object) -> object:
        """O modelo às vezes escreve "null" ou "não informado" em vez de devolver null."""
        if isinstance(value, str) and value.strip().lower() in VAZIOS:
            return None
        return value

    @field_validator("published_at", mode="before")
    @classmethod
    def data_invalida_vira_nula(cls, value: object) -> object:
        """Data ilegível não invalida a extração inteira — vira ausência de data."""
        if isinstance(value, str) and value.strip().lower() in VAZIOS:
            return None
        return value


class ExtractionResponse(BaseModel):
    """O que a API devolve ao consultar a extração vigente de um documento."""

    document_id: UUID
    model: str
    prompt_version: int
    data: ExtractedDocument
