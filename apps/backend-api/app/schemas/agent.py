from uuid import UUID

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    conversation_id: UUID | None = None


class AgentRunAccepted(BaseModel):
    run_id: UUID
    job_id: UUID
    status: str = "queued"


class ExtractionRequest(BaseModel):
    fields: list[str] = Field(min_length=1, max_length=30)
