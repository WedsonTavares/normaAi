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
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.openai_api_key == ""
    assert settings.database_url == ""
