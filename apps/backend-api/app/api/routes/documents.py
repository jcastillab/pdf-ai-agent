from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

import anyio
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import UserDependency
from app.db.session import get_db
from app.models import Document, DocumentPage, ProcessingJob
from app.schemas.documents import (
    DocumentListResponse,
    DocumentResponse,
    PageResponse,
    UploadCompleteResponse,
    UploadRequest,
    UploadResponse,
)
from app.services.documents import build_object_key, get_owned_document
from app.services.queue import QueueError, SupabaseQueue, get_queue
from app.services.storage import ObjectStorage, get_storage

router = APIRouter(prefix="/documents", tags=["documentos"])
DbDependency = Annotated[AsyncSession, Depends(get_db)]
StorageDependency = Annotated[ObjectStorage, Depends(get_storage)]
QueueDependency = Annotated[SupabaseQueue, Depends(get_queue)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(
    body: UploadRequest,
    user: UserDependency,
    db: DbDependency,
    storage: StorageDependency,
    settings: SettingsDependency,
) -> UploadResponse:
    if body.size_bytes > settings.max_pdf_size_bytes:
        raise HTTPException(status_code=413, detail="El PDF supera el límite configurado")
    document_id = uuid4()
    object_key = build_object_key(settings.app_env, user.id, document_id, body.filename)
    document = Document(
        id=document_id,
        owner_id=user.id,
        organization_id=user.organization_id,
        original_name=body.filename,
        object_key=object_key,
        mime_type=body.content_type,
        size_bytes=body.size_bytes,
        status="awaiting_upload",
    )
    db.add(document)
    await db.commit()
    upload_url = storage.presign_put(object_key, body.content_type, settings.upload_url_ttl_seconds)
    return UploadResponse(
        document_id=document_id,
        upload_url=upload_url,
        headers={"Content-Type": body.content_type},
        expires_in=settings.upload_url_ttl_seconds,
    )


@router.post(
    "/{document_id}/upload-complete",
    response_model=UploadCompleteResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def complete_upload(
    document_id: UUID,
    user: UserDependency,
    db: DbDependency,
    storage: StorageDependency,
    queue: QueueDependency,
) -> UploadCompleteResponse:
    document = await get_owned_document(db, document_id, user.id)
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if document.status != "awaiting_upload":
        raise HTTPException(status_code=409, detail="La carga ya fue confirmada")
    try:
        head = await anyio.to_thread.run_sync(storage.head, document.object_key)
    except ClientError as exc:
        raise HTTPException(status_code=409, detail="El objeto aún no existe en R2") from exc
    if int(head.get("ContentLength", -1)) != document.size_bytes:
        raise HTTPException(status_code=409, detail="El tamaño cargado no coincide")

    job = ProcessingJob(
        document_id=document.id,
        owner_id=user.id,
        organization_id=user.organization_id,
        task_type="process_document",
        status="queued",
        progress=0,
        current_step="queued",
        payload={"document_id": str(document.id)},
    )
    document.status = "queued"
    db.add(job)
    await db.flush()
    try:
        await queue.send(
            {
                "schema_version": 1,
                "job_id": str(job.id),
                "task_type": job.task_type,
                "document_id": str(document.id),
                "owner_id": str(user.id),
            }
        )
    except QueueError as exc:
        job.status = "failed"
        job.error_code = "QUEUE_UNAVAILABLE"
        job.error_message = str(exc)
        document.status = "upload_complete"
        await db.commit()
        raise HTTPException(status_code=503, detail="La cola no está disponible") from exc
    await db.commit()
    await db.refresh(document)
    return UploadCompleteResponse(document=DocumentResponse.model_validate(document), job_id=job.id)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user: UserDependency,
    db: DbDependency,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> DocumentListResponse:
    filters = and_(Document.owner_id == user.id, Document.deleted_at.is_(None))
    total = await db.scalar(select(func.count()).select_from(Document).where(filters)) or 0
    items = list(
        (
            await db.scalars(
                select(Document)
                .where(filters)
                .order_by(Document.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID, user: UserDependency, db: DbDependency) -> Document:
    document = await get_owned_document(db, document_id, user.id)
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return document


@router.get("/{document_id}/status", response_model=DocumentResponse)
async def document_status(document_id: UUID, user: UserDependency, db: DbDependency) -> Document:
    return await get_document(document_id, user, db)


@router.get("/{document_id}/pages", response_model=list[PageResponse])
async def document_pages(document_id: UUID, user: UserDependency, db: DbDependency) -> list:
    document = await get_owned_document(db, document_id, user.id)
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return list(
        (
            await db.scalars(
                select(DocumentPage)
                .where(DocumentPage.document_id == document_id)
                .order_by(DocumentPage.page_number)
            )
        ).all()
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    user: UserDependency,
    db: DbDependency,
    storage: StorageDependency,
    settings: SettingsDependency,
) -> dict[str, str | int]:
    document = await get_owned_document(db, document_id, user.id)
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return {
        "url": storage.presign_get(document.object_key, settings.download_url_ttl_seconds),
        "expires_in": settings.download_url_ttl_seconds,
    }


@router.post("/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_document(
    document_id: UUID,
    user: UserDependency,
    db: DbDependency,
    queue: QueueDependency,
) -> dict[str, str]:
    document = await get_owned_document(db, document_id, user.id)
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    job = ProcessingJob(
        document_id=document.id,
        owner_id=user.id,
        organization_id=user.organization_id,
        task_type="process_document",
        status="queued",
        progress=0,
        current_step="queued",
        payload={"document_id": str(document.id), "reprocess": True},
    )
    db.add(job)
    await db.flush()
    await queue.send(
        {
            "schema_version": 1,
            "job_id": str(job.id),
            "task_type": job.task_type,
            "document_id": str(document.id),
            "owner_id": str(user.id),
        }
    )
    document.status = "queued"
    await db.commit()
    return {"job_id": str(job.id), "status": "queued"}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    user: UserDependency,
    db: DbDependency,
    storage: StorageDependency,
) -> None:
    document = await get_owned_document(db, document_id, user.id)
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    await anyio.to_thread.run_sync(storage.delete, document.object_key)
    document.deleted_at = datetime.now(UTC)
    document.status = "deleted"
    await db.commit()
