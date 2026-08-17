import pytest

from app.core.errors import InvalidInputError
from app.services.document_service import content_hash, validate_pdf_upload


def test_aceita_pdf_valido() -> None:
    validate_pdf_upload("norma.pdf", "application/pdf")


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("norma.docx", "application/pdf"),
        ("norma.pdf", "text/plain"),
        ("norma.pdf", None),
        ("norma", "application/pdf"),
    ],
)
def test_rejeita_o_que_nao_e_pdf(filename: str, content_type: str | None) -> None:
    with pytest.raises(InvalidInputError):
        validate_pdf_upload(filename, content_type)


def test_extensao_maiuscula_e_aceita() -> None:
    validate_pdf_upload("NORMA.PDF", "application/pdf")


def test_hash_identifica_o_mesmo_conteudo() -> None:
    """RN-04: a deduplicação depende de conteúdo igual gerar hash igual."""
    assert content_hash(b"lei 1234") == content_hash(b"lei 1234")
    assert content_hash(b"lei 1234") != content_hash(b"lei 1235")
