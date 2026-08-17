import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_origins_accepts_comma_separated_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, https://normaai.app")

    assert Settings().cors_origins == ["http://localhost:5173", "https://normaai.app"]


def test_log_level_is_normalized_to_uppercase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")

    assert Settings().log_level == "DEBUG"


def test_invalid_log_level_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "verbose")

    with pytest.raises(ValidationError):
        Settings()


def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")

    with pytest.raises(ValidationError):
        Settings()


def test_secrets_are_empty_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nenhuma credencial pode ter valor padrão embutido no código."""
    for variavel in ("LLM_API_KEY", "EMBEDDINGS_API_KEY", "DATABASE_URL"):
        monkeypatch.delenv(variavel, raising=False)

    settings = Settings(_env_file=None)

    assert settings.llm_api_key == ""
    assert settings.embeddings_api_key == ""
    assert settings.database_url == ""


def test_provedores_tem_endereco_padrao_mas_nao_chave() -> None:
    """URL de provedor é configuração pública; chave nunca tem padrão."""
    settings = Settings(_env_file=None)

    assert settings.llm_base_url.startswith("https://")
    assert settings.embeddings_base_url.startswith("https://")
