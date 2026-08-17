import io

import pytest
from pypdf import PdfWriter

from app.core.errors import InvalidInputError
from app.services.pdf_text import extract_page_texts

FONT_ID = 3
FIRST_PAGE_ID = 4


def pdf_with_text(*page_texts: str) -> bytes:
    """PDF válido com o texto pedido em cada página.

    Escrito à mão porque o pypdf lê PDFs mas não cria conteúdo de texto, e trazer uma
    biblioteca de geração de PDF só para os testes não se justifica.
    Objetos: 1 catálogo, 2 páginas, 3 fonte, depois pares (página, conteúdo).
    """
    page_ids = [FIRST_PAGE_ID + index * 2 for index in range(len(page_texts))]
    kids = b" ".join(b"%d 0 R" % page_id for page_id in page_ids)

    bodies: list[bytes] = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[" + kids + b"]/Count %d>>" % len(page_texts),
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    for page_id, text in zip(page_ids, page_texts, strict=True):
        stream = b"BT /F1 12 Tf 72 720 Td (" + text.encode("latin-1") + b") Tj ET"
        bodies.append(
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents %d 0 R"
            b"/Resources<</Font<</F1 %d 0 R>>>>>>" % (page_id + 1, FONT_ID)
        )
        bodies.append(b"<</Length %d>>stream\n" % len(stream) + stream + b"\nendstream")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(bodies, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj" % number + body + b"endobj\n"

    # Tabela xref: o pypdf recusa o arquivo sem ela.
    xref_offset = len(pdf)
    size = len(bodies) + 1
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for offset in offsets:
        pdf += b"%010d 00000 n \n" % offset

    pdf += b"trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (size, xref_offset)
    return bytes(pdf)


def blank_pdf(pages: int = 1, marker: str = "") -> bytes:
    """PDF válido sem nenhum texto — simula documento digitalizado.

    `marker` entra nos metadados só para mudar os bytes: dois testes que gerassem PDFs
    idênticos cairiam na deduplicação por hash e reusariam o documento um do outro.
    """
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    if marker:
        writer.add_metadata({"/Keywords": marker})

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_extrai_texto_de_cada_pagina() -> None:
    pages = extract_page_texts(pdf_with_text("Art. 1o Primeira", "Art. 2o Segunda"))

    assert len(pages) == 2
    assert "Primeira" in pages[0]
    assert "Segunda" in pages[1]


def test_pdf_corrompido_vira_erro_tratado() -> None:
    with pytest.raises(InvalidInputError) as exc:
        extract_page_texts(b"isto nao e um pdf")

    assert "corrompido" in str(exc.value)


def test_pdf_sem_texto_extraivel_e_rejeitado() -> None:
    with pytest.raises(InvalidInputError) as exc:
        extract_page_texts(blank_pdf())

    assert "OCR" in str(exc.value)
