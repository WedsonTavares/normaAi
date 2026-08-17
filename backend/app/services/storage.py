"""Gravação dos PDFs em disco.

O nome do arquivo é o hash do conteúdo, então o mesmo PDF nunca ocupa espaço duas vezes.
"""

import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import NotFoundError

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
    """Lê o PDF gravado.

    Arquivo ausente com registro presente acontece quando o disco é efêmero ou foi limpo.
    A mensagem precisa dizer isso, senão o usuário vê "falha inesperada" sem pista nenhuma.
    """
    path = Path(storage_path)
    if not path.exists():
        logger.error("Arquivo ausente no disco: %s", storage_path)
        raise NotFoundError(
            "O arquivo deste documento não está mais disponível. Envie o PDF novamente."
        )
    return path.read_bytes()
