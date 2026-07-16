from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.documents import UploadRequest
from app.services.documents import build_object_key, safe_object_name


def test_upload_request_accepts_pdf() -> None:
    request = UploadRequest(filename="Informe 2026.pdf", size_bytes=1234)
    assert request.content_type == "application/pdf"
    assert request.filename == "Informe 2026.pdf"


@pytest.mark.parametrize("filename", ["documento.exe", "archivo", "imagen.png"])
def test_upload_request_rejects_non_pdf(filename: str) -> None:
    with pytest.raises(ValidationError):
        UploadRequest(filename=filename, size_bytes=1234)


def test_object_key_does_not_preserve_user_path() -> None:
    owner = UUID("00000000-0000-0000-0000-000000000001")
    document = UUID("00000000-0000-0000-0000-000000000002")
    key = build_object_key("test", owner, document, "../../Mi Factura.pdf")
    assert ".." not in key
    assert key.startswith(f"test/{owner}/{document}/")
    assert key.endswith("mi-factura.pdf")


def test_safe_object_name_handles_symbols() -> None:
    assert safe_object_name("áé Factura # 10.pdf") == "factura-10.pdf"
