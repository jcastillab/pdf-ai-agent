import asyncio
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserDependency
from app.db.session import get_db
from app.models import ProcessingJob
from app.schemas.jobs import JobListResponse, JobResponse
from app.services.queue import SupabaseQueue, get_queue

router = APIRouter(prefix="/jobs", tags=["trabajos"])
DbDependency = Annotated[AsyncSession, Depends(get_db)]
QueueDependency = Annotated[SupabaseQueue, Depends(get_queue)]


async def owned_job(db: AsyncSession, job_id: UUID, owner_id: UUID) -> ProcessingJob:
    job = await db.scalar(
        select(ProcessingJob).where(
            and_(ProcessingJob.id == job_id, ProcessingJob.owner_id == owner_id)
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    return job


@router.get("", response_model=JobListResponse)
async def list_jobs(
    user: UserDependency,
    db: DbDependency,
    limit: int = Query(30, ge=1, le=100),
) -> JobListResponse:
    condition = ProcessingJob.owner_id == user.id
    total = await db.scalar(select(func.count()).select_from(ProcessingJob).where(condition)) or 0
    items = list(
        (
            await db.scalars(
                select(ProcessingJob)
                .where(condition)
                .order_by(ProcessingJob.created_at.desc())
                .limit(limit)
            )
        ).all()
    )
    return JobListResponse(items=[JobResponse.model_validate(item) for item in items], total=total)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, user: UserDependency, db: DbDependency) -> ProcessingJob:
    return await owned_job(db, job_id, user.id)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(job_id: UUID, user: UserDependency, db: DbDependency) -> ProcessingJob:
    job = await owned_job(db, job_id, user.id)
    if job.status in {"completed", "failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="El trabajo ya terminó")
    job.cancel_requested = True
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/{job_id}/retry", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_job(
    job_id: UUID,
    user: UserDependency,
    db: DbDependency,
    queue: QueueDependency,
) -> ProcessingJob:
    job = await owned_job(db, job_id, user.id)
    if job.status != "failed":
        raise HTTPException(status_code=409, detail="Solo se reintentan trabajos fallidos")
    job.status = "queued"
    job.error_code = None
    job.error_message = None
    job.cancel_requested = False
    await queue.send(
        {
            "schema_version": 1,
            "job_id": str(job.id),
            "task_type": job.task_type,
            "document_id": str(job.document_id) if job.document_id else None,
            "owner_id": str(user.id),
        }
    )
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/{job_id}/events")
async def job_events(job_id: UUID, user: UserDependency, db: DbDependency) -> StreamingResponse:
    await owned_job(db, job_id, user.id)

    async def stream():
        previous = ""
        for _ in range(300):
            db.expire_all()
            job = await owned_job(db, job_id, user.id)
            payload = JobResponse.model_validate(job).model_dump(mode="json")
            serialized = json.dumps(payload, ensure_ascii=False)
            if serialized != previous:
                yield f"event: progress\ndata: {serialized}\n\n"
                previous = serialized
            if job.status in {"completed", "failed", "cancelled"}:
                return
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream")
