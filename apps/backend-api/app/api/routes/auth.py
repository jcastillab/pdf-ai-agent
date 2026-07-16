from fastapi import APIRouter

from app.core.security import UserDependency

router = APIRouter(prefix="/auth", tags=["autenticación"])


@router.get("/me")
async def me(user: UserDependency) -> dict[str, str | None]:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "organization_id": str(user.organization_id) if user.organization_id else None,
    }
