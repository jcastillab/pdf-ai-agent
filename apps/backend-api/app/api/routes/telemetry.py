from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserDependency
from app.db.session import get_db
from app.models import Document, LlmCall, ProcessingJob

router = APIRouter(prefix="/telemetry", tags=["telemetría"])
DbDependency = Annotated[AsyncSession, Depends(get_db)]


@router.get("/overview")
async def overview(user: UserDependency, db: DbDependency) -> dict:
    documents = await db.execute(
        select(
            func.count(Document.id),
            func.sum(case((Document.status == "completed", 1), else_=0)),
        ).where(Document.owner_id == user.id)
    )
    total_docs, completed_docs = documents.one()
    jobs = await db.execute(
        select(
            func.count(ProcessingJob.id),
            func.sum(case((ProcessingJob.status == "failed", 1), else_=0)),
        ).where(ProcessingJob.owner_id == user.id)
    )
    total_jobs, failed_jobs = jobs.one()
    llm = await db.execute(
        select(
            func.coalesce(func.sum(LlmCall.input_tokens), 0),
            func.coalesce(func.sum(LlmCall.output_tokens), 0),
            func.coalesce(func.sum(LlmCall.estimated_cost_usd), 0),
            func.coalesce(func.avg(LlmCall.latency_ms), 0),
        ).where(LlmCall.owner_id == user.id)
    )
    input_tokens, output_tokens, cost, avg_latency = llm.one()
    return {
        "documents": {"total": total_docs or 0, "completed": completed_docs or 0},
        "jobs": {"total": total_jobs or 0, "failed": failed_jobs or 0},
        "llm": {
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "estimated_cost_usd": float(cost),
            "average_latency_ms": float(avg_latency),
        },
    }
