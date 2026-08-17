"""Ponto de entrada da API do NormaAI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import health
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Cria o app. Receber `settings` explicitamente permite testar com outra configuração."""
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)

    app = FastAPI(title=resolved.app_name, version=__version__)

    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(health.router)

    return app


app = create_app()
