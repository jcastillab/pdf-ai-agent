from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(tags=["operación"])


@router.get("/health")
@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}


@router.get("/version")
async def version() -> dict[str, str]:
    return {"version": "0.1.0"}
