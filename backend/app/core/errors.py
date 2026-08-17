"""Erros da aplicação e seus handlers HTTP.

Regra: o usuário nunca recebe stack trace, SQL ou credencial. Detalhes vão para o log.
"""

import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.errors import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

# Erros que o próprio framework gera antes de chegar em uma rota.
FRAMEWORK_ERROR_CODES = {404: "not_found", 405: "method_not_allowed"}
FRAMEWORK_ERROR_MESSAGES = {
    404: "Recurso não encontrado.",
    405: "Método não permitido para este recurso.",
}


class AppError(Exception):
    """Erro esperado, com mensagem segura para exibir ao usuário."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidInputError(AppError):
    status_code = 400
    code = "invalid_input"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ExternalServiceError(AppError):
    """Falha em dependência externa (OpenAI, banco, storage)."""

    status_code = 502
    code = "external_service_error"


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _describe_invalid_fields(errors: Sequence[Any]) -> str:
    """Nomes dos campos inválidos, sem expor o valor enviado.

    `RequestValidationError.errors()` não é tipado pelo FastAPI, por isso os checks explícitos.
    """
    names = []
    for error in errors:
        location = error.get("loc") if isinstance(error, dict) else None
        if isinstance(location, tuple | list) and location:
            names.append(".".join(str(part) for part in location))
    return ", ".join(names)


def register_error_handlers(app: FastAPI) -> None:
    """Garante um formato único de erro em toda a API: {"error": {"code", "message"}}."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("%s em %s %s: %s", exc.code, request.method, request.url.path, exc.message)
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_framework_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = FRAMEWORK_ERROR_CODES.get(exc.status_code, "http_error")
        message = FRAMEWORK_ERROR_MESSAGES.get(exc.status_code) or str(exc.detail)
        return _error_response(exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = _describe_invalid_fields(exc.errors())
        message = f"Dados inválidos na requisição: {fields}." if fields else "Requisição inválida."
        return _error_response(422, "validation_error", message)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro inesperado em %s %s", request.method, request.url.path)
        return _error_response(500, "internal_error", "Erro interno. Tente novamente em instantes.")
