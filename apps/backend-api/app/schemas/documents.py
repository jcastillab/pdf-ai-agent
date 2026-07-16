from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = "application/pdf"
    size_bytes: int = Field(gt=0)

    @field_validator("filename")
    @classmethod
    def pdf_extension(cls, value: str) -> str:
        cleaned = value.strip().replace("\\", "/").split("/")[-1]
        if not cleaned.lower().endswith(".pdf"):
            raise ValueError("El archivo debe tener extensión .pdf")
        return cleaned

    @field_validator("content_type")
    @classmethod
    def pdf_content_type(cls, value: str) -> str:
        if value.lower() != "application/pdf":
            raise ValueError("El tipo MIME debe ser application/pdf")
        return value.lower()


class UploadResponse(BaseModel):
    document_id: UUID
    upload_url: str
    method: str = "PUT"
    headers: dict[str, str]
    expires_in: int


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_name: str
    mime_type: str
    size_bytes: int
    page_count: int | None
    status: str
    confidence: float | None
    summary: str | None
    created_at: datetime
    processed_at: datetime | None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class UploadCompleteResponse(BaseModel):
    document: DocumentResponse
    job_id: UUID


class PageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_number: int
    text: str
    extraction_method: str
    confidence: float
