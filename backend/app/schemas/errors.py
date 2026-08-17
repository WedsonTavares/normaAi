"""Contrato de erro da API. Formato único para toda a aplicação."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
