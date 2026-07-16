import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import sentry_sdk
import structlog
from opentelemetry import trace

from worker.clients.ollama import OllamaClient
from worker.clients.storage import ObjectStorage
from worker.clients.supabase import QueueMessage, SupabaseClient
from worker.config import get_settings
from worker.graph.processing import build_graph
from worker.services.tasks import JobCancelled, TaskService
from worker.telemetry import configure_telemetry

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper(), format="%(message)s")
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.app_env, send_default_pii=False)
configure_telemetry(settings)
tracer = trace.get_tracer("pdf-ai-agent-worker")


async def handle_message(message: QueueMessage, database: SupabaseClient, graph: Any) -> None:
    payload = message.message
    job_id = UUID(payload["job_id"])
    job = await database.get_one("processing_jobs", job_id)
    if not job:
        raise RuntimeError("Trabajo inexistente")
    if job["status"] in {"completed", "cancelled"}:
        await database.archive_message(settings.queue_name, message.msg_id)
        return
    state = {
        "job_id": str(job_id),
        "document_id": payload.get("document_id"),
        "owner_id": payload["owner_id"],
        "task_type": payload["task_type"],
        "agent_run_id": payload.get("agent_run_id") or job.get("payload", {}).get("agent_run_id"),
        "payload": job.get("payload", {}),
    }
    try:
        with tracer.start_as_current_span(
            "process_queue_message",
            attributes={
                "job.id": str(job_id),
                "job.task_type": payload["task_type"],
                "queue.message_id": message.msg_id,
                "queue.read_count": message.read_ct,
            },
        ):
            await graph.ainvoke(state)
        await database.archive_message(settings.queue_name, message.msg_id)
        logger.info("job_completed", job_id=str(job_id), task_type=payload["task_type"])
    except JobCancelled:
        await database.archive_message(settings.queue_name, message.msg_id)
        logger.info("job_cancelled", job_id=str(job_id))
    except Exception as exc:
        terminal = message.read_ct >= settings.max_attempts
        await database.patch(
            "processing_jobs",
            job_id,
            {
                "status": "failed" if terminal else "queued",
                "error_code": type(exc).__name__,
                "error_message": str(exc)[:2000],
                "attempts": message.read_ct,
                "current_step": "failed" if terminal else "retry_wait",
                "completed_at": datetime.now(UTC).isoformat() if terminal else None,
            },
        )
        if payload.get("document_id"):
            await database.patch(
                "documents",
                payload["document_id"],
                {"status": "failed" if terminal else "queued"},
            )
        if terminal:
            await database.send_message(
                settings.dead_letter_queue_name,
                {**payload, "source_message_id": message.msg_id, "error": str(exc)[:500]},
            )
            await database.archive_message(settings.queue_name, message.msg_id)
        sentry_sdk.capture_exception(exc)
        logger.exception(
            "job_failed",
            job_id=str(job_id),
            attempt=message.read_ct,
            terminal=terminal,
        )


async def main() -> None:
    if not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY es obligatoria")
    database = SupabaseClient(settings.supabase_url, settings.supabase_service_role_key)
    storage = ObjectStorage(settings)
    ollama = OllamaClient(
        settings.ollama_base_url,
        settings.ollama_chat_model,
        settings.ollama_embedding_model,
        settings.ollama_timeout_seconds,
    )
    if not await ollama.health_check():
        raise RuntimeError("Ollama no responde. Ejecuta ollama serve y descarga los modelos")
    graph = build_graph(TaskService(settings, database, storage, ollama))
    logger.info("worker_started", worker_id=settings.worker_id, queue=settings.queue_name)
    while True:
        messages = await database.read_queue(
            settings.queue_name, settings.queue_visibility_seconds, batch_size=1
        )
        if not messages:
            await asyncio.sleep(settings.poll_interval_seconds)
            continue
        await handle_message(messages[0], database, graph)


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("worker_stopped")


if __name__ == "__main__":
    run()
