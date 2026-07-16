import re
from uuid import UUID, uuid4

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document


def safe_object_name(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0].lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")[:80]
    return f"{normalized or 'documento'}.pdf"


def build_object_key(environment: str, owner_id: UUID, document_id: UUID, filename: str) -> str:
    return f"{environment}/{owner_id}/{document_id}/{uuid4().hex}-{safe_object_name(filename)}"


def owned_document_query(document_id: UUID, owner_id: UUID) -> Select[tuple[Document]]:
    return select(Document).where(
        and_(
            Document.id == document_id,
            Document.owner_id == owner_id,
            Document.deleted_at.is_(None),
        )
    )


async def get_owned_document(
    db: AsyncSession, document_id: UUID, owner_id: UUID
) -> Document | None:
    return await db.scalar(owned_document_query(document_id, owner_id))
