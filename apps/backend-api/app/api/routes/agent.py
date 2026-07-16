from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserDependency
from app.db.session import get_db
from app.models import AgentRun, ProcessingJob
from app.schemas.agent import AgentRunAccepted, AskRequest, ExtractionRequest
from app.services.documents import get_owned_document
from app.services.queue import SupabaseQueue, get_queue

router = APIRouter(tags=["agente"])
DbDependency = Annotated[AsyncSession, Depends(get_db)]
QueueDependency = Annotated[SupabaseQueue, Depends(get_queue)]


async def enqueue_agent_task(
    document_id: UUID,
    task_type: str,
    payload: dict,
    user: UserDependency,
    db: AsyncSession,
    queue: SupabaseQueue,
) -> AgentRunAccepted:
    document = await get_owned_document(db, document_id, user.id)
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if document.status != "completed":
        raise HTTPException(status_code=409, detail="El documento aún no termina de procesarse")
    job = ProcessingJob(
        document_id=document_id,
        owner_id=user.id,
        organization_id=user.organization_id,
        task_type=task_type,
        status="queued",
        progress=0,
        current_step="queued",
        payload=payload,
    )
    db.add(job)
    await db.flush()
    run = AgentRun(
        document_id=document_id,
        job_id=job.id,
        owner_id=user.id,
        run_type=task_type,
        status="queued",
        input_json=payload,
    )
    db.add(run)
    await db.flush()
    job.payload = {**payload, "agent_run_id": str(run.id)}
    await queue.send(
        {
            "schema_version": 1,
            "job_id": str(job.id),
            "agent_run_id": str(run.id),
            "task_type": task_type,
            "document_id": str(document_id),
            "owner_id": str(user.id),
        }
    )
    await db.commit()
    return AgentRunAccepted(run_id=run.id, job_id=job.id)


@router.post(
    "/documents/{document_id}/ask",
    response_model=AgentRunAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ask_document(
    document_id: UUID,
    body: AskRequest,
    user: UserDependency,
    db: DbDependency,
    queue: QueueDependency,
) -> AgentRunAccepted:
    return await enqueue_agent_task(
        document_id,
        "answer_question",
        {
            "question": body.question,
            "conversation_id": str(body.conversation_id) if body.conversation_id else None,
        },
        user,
        db,
        queue,
    )


@router.post(
    "/documents/{document_id}/summarize",
    response_model=AgentRunAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def summarize_document(
    document_id: UUID,
    user: UserDependency,
    db: DbDependency,
    queue: QueueDependency,
) -> AgentRunAccepted:
    return await enqueue_agent_task(document_id, "summarize_document", {}, user, db, queue)


@router.post(
    "/documents/{document_id}/extract",
    response_model=AgentRunAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def extract_fields(
    document_id: UUID,
    body: ExtractionRequest,
    user: UserDependency,
    db: DbDependency,
    queue: QueueDependency,
) -> AgentRunAccepted:
    return await enqueue_agent_task(
        document_id, "extract_fields", {"fields": body.fields}, user, db, queue
    )
