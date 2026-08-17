"""Configuração da aplicação, carregada de variáveis de ambiente."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "test", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NormaAI"
    environment: Environment = "development"
    log_level: str = "INFO"

    # Origens permitidas para o frontend, separadas por vírgula na variável de ambiente.
    # NoDecode impede o pydantic-settings de tentar ler o valor como JSON.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    database_url: str = ""

    # Extração estruturada e respostas do RAG. A API do DeepSeek é compatível com o SDK da
    # OpenAI, então só muda a base_url.
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-pro"

    # Embeddings vêm de outro provedor: o DeepSeek não gera vetores.
    # Trocar de modelo exige alterar a dimensão da coluna `embedding` e regerar tudo (RN-40).
    embeddings_api_key: str = ""
    embeddings_base_url: str = "https://api.openai.com/v1"
    embeddings_model: str = "text-embedding-3-small"

    storage_dir: Path = Path("storage")
    max_upload_mb: int = 20

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_comma_separated(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        level = value.upper()
        if level not in allowed:
            raise ValueError(f"log_level inválido: {value}. Use um de {sorted(allowed)}.")
        return level


@lru_cache
def get_settings() -> Settings:
    """Configurações da aplicação.

    Use sempre esta função (via Depends nas rotas), nunca os.getenv espalhado no código.
    """
    return Settings()
