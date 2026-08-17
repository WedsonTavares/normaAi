from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError, NotFoundError, register_error_handlers

SECRET_IN_TRACEBACK = "sk-chave-secreta-123"


def build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/not-found")
    def raise_not_found() -> None:
        raise NotFoundError("Documento não encontrado.")

    @app.get("/invalid")
    def raise_invalid() -> None:
        raise InvalidInputError("Somente arquivos PDF são aceitos.")

    @app.get("/boom")
    def raise_unexpected() -> None:
        raise RuntimeError(f"falha ao conectar usando {SECRET_IN_TRACEBACK}")

    @app.get("/items")
    def list_items(limit: int) -> dict[str, int]:
        return {"limit": limit}

    return app


def test_app_error_uses_its_own_status_and_code() -> None:
    client = TestClient(build_app())

    response = client.get("/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Documento não encontrado."}
    }


def test_invalid_input_returns_400() -> None:
    client = TestClient(build_app())

    response = client.get("/invalid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_input"


def test_unexpected_error_returns_generic_message_without_leaking_details() -> None:
    client = TestClient(build_app(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "Erro interno. Tente novamente em instantes.",
        }
    }
    assert SECRET_IN_TRACEBACK not in response.text
    assert "Traceback" not in response.text


def test_unknown_route_uses_the_same_error_format(client: TestClient) -> None:
    response = client.get("/rota-inexistente")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Recurso não encontrado."}}


def test_wrong_method_uses_the_same_error_format(client: TestClient) -> None:
    response = client.post("/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_validation_error_reports_the_field_without_echoing_the_value() -> None:
    client = TestClient(build_app())

    response = client.get("/items", params={"limit": "abc"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "query.limit" in body["error"]["message"]
    assert "abc" not in body["error"]["message"]
