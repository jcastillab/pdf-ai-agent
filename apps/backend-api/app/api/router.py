from fastapi import APIRouter

from app.api.routes import agent, auth, documents, health, jobs, telemetry

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(agent.router)
api_router.include_router(jobs.router)
api_router.include_router(telemetry.router)
