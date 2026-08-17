"""Extração do texto de um PDF, página a página.

Função pura: recebe bytes, devolve texto. Não toca em banco nem em disco, por isso é
simples de testar. OCR está fora do escopo — PDF só com imagem não produz texto.
"""

import io
import logging

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.core.errors import InvalidInputError

logger = logging.getLogger(__name__)


def extract_page_texts(pdf_bytes: bytes) -> list[str]:
    """Texto de cada página, na ordem. Página sem texto vira string vazia.

    Levanta InvalidInputError se o arquivo não for um PDF legível ou não tiver texto algum.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except (PyPdfError, ValueError, OSError) as exc:
        logger.warning("PDF ilegível: %s", exc)
        raise InvalidInputError(
            "Não foi possível ler o PDF. O arquivo pode estar corrompido."
        ) from exc

    if not pages:
        raise InvalidInputError("O PDF não possui páginas.")

    if not any(pages):
        raise InvalidInputError(
            "O PDF não possui texto extraível. Documentos digitalizados exigem OCR, "
            "que não faz parte do escopo atual."
        )

    return pages
