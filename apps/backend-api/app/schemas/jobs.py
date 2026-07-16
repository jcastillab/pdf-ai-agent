from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID | None
    task_type: str
    status: str
    progress: int
    current_step: str | None
    result: dict
    error_code: str | None
    error_message: str | None
    attempts: int
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
