from pathlib import Path

import pytest
from PIL import Image

from worker.services.pdf_processing import (
    ExtractedPage,
    InvalidPdfError,
    available_tesseract_language,
    chunk_pages,
    normalize_text,
    ocr_with_orientation,
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


def test_tesseract_language_uses_installed_subset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pytesseract.get_languages", lambda config="": ["eng", "osd"])
    assert available_tesseract_language("spa+eng") == "eng"


def test_ocr_selects_best_right_angle_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    results = iter(
        [
            ("garbled", 0.15, 2),
            ("texto correcto de la tabla", 0.82, 20),
            ("garbled", 0.12, 2),
            ("garbled", 0.18, 3),
        ]
    )
    monkeypatch.setattr(
        "worker.services.pdf_processing._text_and_confidence",
        lambda image, language: next(results),
    )
    text, confidence, rotation = ocr_with_orientation(Image.new("RGB", (20, 10)), "eng")
    assert text == "texto correcto de la tabla"
    assert confidence == 0.82
    assert rotation == 90
