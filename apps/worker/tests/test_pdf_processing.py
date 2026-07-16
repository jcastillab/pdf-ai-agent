from pathlib import Path

import pytest

from worker.services.pdf_processing import (
    ExtractedPage,
    InvalidPdfError,
    chunk_pages,
    normalize_text,
    validate_pdf,
)


def test_normalize_text() -> None:
    assert normalize_text("Hola    mundo\n\n\nfin") == "Hola mundo\n\nfin"


def test_chunks_keep_page_number_and_overlap() -> None:
    pages = [ExtractedPage(3, "A" * 1200, "native", 1.0)]
    chunks = chunk_pages(pages, size=500, overlap=100)
    assert len(chunks) == 3
    assert all(chunk.page_number == 3 for chunk in chunks)
    assert chunks[0].text[-100:] == chunks[1].text[:100]


def test_invalid_magic_bytes(tmp_path: Path) -> None:
    path = tmp_path / "fake.pdf"
    path.write_bytes(b"not a pdf")
    with pytest.raises(InvalidPdfError, match="magic bytes"):
        validate_pdf(path, max_size=1000, max_pages=10)


def test_rejects_invalid_chunk_config() -> None:
    with pytest.raises(ValueError):
        chunk_pages([], size=100, overlap=100)
