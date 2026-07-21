import hashlib
import io
import re
import socket
from dataclasses import dataclass
from pathlib import Path

import fitz
import pytesseract
from PIL import Image


class InvalidPdfError(ValueError):
    pass


class MalwareDetectedError(ValueError):
    pass


@dataclass(slots=True)
class ExtractedPage:
    page_number: int
    text: str
    extraction_method: str
    confidence: float
    rotation_degrees: int = 0
    requires_review: bool = False
    uncertain_segments: tuple[str, ...] = ()


@dataclass(slots=True)
class Chunk:
    page_number: int
    chunk_index: int
    text: str
    token_count: int
    content_hash: str
    extraction_method: str = "native"
    confidence: float = 1.0


def validate_pdf(path: Path, max_size: int, max_pages: int) -> int:
    if path.stat().st_size > max_size:
        raise InvalidPdfError("El PDF supera el límite de tamaño")
    with path.open("rb") as file:
        if file.read(5) != b"%PDF-":
            raise InvalidPdfError("Los magic bytes no corresponden a un PDF")
    try:
        with fitz.open(path) as document:
            if document.needs_pass:
                raise InvalidPdfError("El PDF está protegido con contraseña")
            if document.page_count == 0:
                raise InvalidPdfError("El PDF no contiene páginas")
            if document.page_count > max_pages:
                raise InvalidPdfError("El PDF supera el límite de páginas")
            return document.page_count
    except fitz.FileDataError as exc:
        raise InvalidPdfError("El PDF está corrupto") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scan_clamav(path: Path, host: str, port: int, timeout: int = 60) -> None:
    size = path.stat().st_size
    with socket.create_connection((host, port), timeout=timeout) as connection:
        connection.sendall(b"zINSTREAM\0")
        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                connection.sendall(len(block).to_bytes(4, "big") + block)
        connection.sendall((0).to_bytes(4, "big"))
        response = connection.recv(4096).decode("utf-8", errors="replace")
    if "FOUND" in response:
        raise MalwareDetectedError(f"ClamAV detectó contenido malicioso en {size} bytes")
    if "OK" not in response:
        raise RuntimeError("ClamAV no devolvió un resultado válido")


def normalize_text(text: str) -> str:
    text = text.replace("\u0000", " ").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def available_tesseract_language(requested: str) -> str:
    """Return the requested installed languages, with a safe local fallback."""
    installed = set(pytesseract.get_languages(config=""))
    selected = [language for language in requested.split("+") if language in installed]
    if selected:
        return "+".join(selected)
    if "eng" in installed:
        return "eng"
    usable = sorted(installed - {"osd"})
    if usable:
        return usable[0]
    raise RuntimeError("Tesseract no tiene idiomas OCR instalados")


def _text_and_confidence(image: Image.Image, language: str) -> tuple[str, float, int]:
    data = pytesseract.image_to_data(
        image,
        lang=language,
        config="--psm 6",
        output_type=pytesseract.Output.DICT,
    )
    tokens: list[str] = []
    confidences: list[float] = []
    for token, raw_confidence in zip(data["text"], data["conf"], strict=True):
        token = str(token).strip()
        if not token:
            continue
        tokens.append(token)
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            continue
        if confidence >= 0:
            confidences.append(confidence / 100)
    text = normalize_text(" ".join(tokens))
    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return text, round(mean_confidence, 4), len(tokens)


def _orientation_score(text: str, confidence: float, token_count: int) -> float:
    token_factor = min(token_count / 40, 1)
    character_factor = min(len(text) / 200, 1)
    return confidence * 0.75 + token_factor * 0.20 + character_factor * 0.05


def ocr_with_orientation(image: Image.Image, language: str) -> tuple[str, float, int]:
    """Try right-angle rotations and keep the strongest OCR result."""
    candidates: list[tuple[float, str, float, int]] = []
    for rotation in (0, 90, 180, 270):
        rotated = image if rotation == 0 else image.rotate(rotation, expand=True)
        text, confidence, token_count = _text_and_confidence(rotated, language)
        candidates.append(
            (_orientation_score(text, confidence, token_count), text, confidence, rotation)
        )
    _, text, confidence, rotation = max(candidates, key=lambda item: item[0])
    return text, confidence, rotation


def render_page_image(
    path: Path, page_number: int, rotation_degrees: int = 0, scale: float = 2.0
) -> bytes:
    with fitz.open(path) as document:
        page = document[page_number - 1]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    image: Image.Image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    if rotation_degrees:
        image = image.rotate(rotation_degrees, expand=True)
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def extract_pages(
    path: Path, min_native_chars: int, ocr_enabled: bool, ocr_language: str
) -> list[ExtractedPage]:
    pages: list[ExtractedPage] = []
    selected_language = available_tesseract_language(ocr_language) if ocr_enabled else ""
    with fitz.open(path) as document:
        for index, page in enumerate(document):
            native = normalize_text(page.get_text("text"))
            if len(native) >= min_native_chars:
                pages.append(ExtractedPage(index + 1, native, "native", 1.0))
                continue
            if not ocr_enabled:
                pages.append(ExtractedPage(index + 1, native, "native_low_text", 0.35))
                continue
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            ocr_text, confidence, rotation = ocr_with_orientation(image, selected_language)
            requires_review = confidence < 0.68 or len(ocr_text) < min_native_chars
            pages.append(
                ExtractedPage(
                    index + 1,
                    ocr_text,
                    "ocr",
                    confidence,
                    rotation,
                    requires_review,
                )
            )
    return pages


def chunk_pages(pages: list[ExtractedPage], size: int, overlap: int) -> list[Chunk]:
    if size <= overlap:
        raise ValueError("chunk_size debe ser mayor que chunk_overlap")
    chunks: list[Chunk] = []
    chunk_index = 0
    for page in pages:
        text = page.text.strip()
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
                if boundary > start + size // 2:
                    end = boundary + 1
            content = text[start:end].strip()
            if content:
                chunks.append(
                    Chunk(
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        text=content,
                        token_count=max(1, len(content) // 4),
                        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        extraction_method=page.extraction_method,
                        confidence=page.confidence,
                    )
                )
                chunk_index += 1
            if end >= len(text):
                break
            start = end - overlap
    return chunks
