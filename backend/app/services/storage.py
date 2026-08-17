"""Gravação dos PDFs em disco.

O nome do arquivo é o hash do conteúdo, então o mesmo PDF nunca ocupa espaço duas vezes.
"""

import logging
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def save_pdf(content: bytes, content_hash: str) -> Path:
    """Grava o PDF e devolve o caminho onde ficou."""
    directory = get_settings().storage_dir
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / f"{content_hash}.pdf"
    path.write_bytes(content)
    return path


def delete_pdf(storage_path: str) -> None:
    """Remove o arquivo. Arquivo já ausente não é erro."""
    Path(storage_path).unlink(missing_ok=True)


def read_pdf(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()
