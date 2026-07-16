import asyncio
import json
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from worker.clients.ollama import Generation
from worker.clients.supabase import QueueMessage, SupabaseClient
from worker.config import WorkerSettings, get_settings
from worker.main import handle_message, main, run, settings
from worker.services.tasks import JobCancelled, TaskService

JOB_ID = UUID("00000000-0000-0000-0000-000000000010")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000020")
OWNER_ID = UUID("00000000-0000-0000-0000-000000000030")
RUN_ID = UUID("00000000-0000-0000-0000-000000000040")


def queue_message(*, read_count: int = 1) -> QueueMessage:
    return QueueMessage(
        msg_id=7,
        read_ct=read_count,
        message={
            "job_id": str(JOB_ID),
            "document_id": str(DOCUMENT_ID),
            "owner_id": str(OWNER_ID),
            "task_type": "process_document",
        },
    )


@pytest.mark.asyncio
async def test_handle_message_success_and_already_completed() -> None:
    database = AsyncMock()
    database.get_one.return_value = {"status": "queued", "payload": {}}
    graph = AsyncMock()

    await handle_message(queue_message(), database, graph)

    graph.ainvoke.assert_awaited_once()
    database.archive_message.assert_awaited_once_with(settings.queue_name, 7)

    database.reset_mock()
    database.get_one.return_value = {"status": "completed"}
    await handle_message(queue_message(), database, graph)
    database.archive_message.assert_awaited_once_with(settings.queue_name, 7)


@pytest.mark.asyncio
async def test_handle_message_missing_cancelled_and_terminal_failure() -> None:
    database = AsyncMock()
    graph = AsyncMock()
    database.get_one.return_value = None
    with pytest.raises(RuntimeError, match="inexistente"):
        await handle_message(queue_message(), database, graph)

    database.get_one.return_value = {"status": "queued", "payload": {}}
    graph.ainvoke.side_effect = JobCancelled("cancelled")
    await handle_message(queue_message(), database, graph)
    database.archive_message.assert_awaited()

    database.reset_mock()
    graph.ainvoke.side_effect = ValueError("boom")
    await handle_message(queue_message(read_count=settings.max_attempts), database, graph)
    database.patch.assert_any_await("documents", str(DOCUMENT_ID), {"status": "failed"})
    database.send_message.assert_awaited_once()
    database.archive_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_requires_service_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "supabase_service_role_key", "")
    with pytest.raises(RuntimeError, match="obligatoria"):
        await main()


def test_run_handles_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    def interrupt(coroutine: object) -> None:
        coroutine.close()  # type: ignore[attr-defined]
        raise KeyboardInterrupt

    monkeypatch.setattr(asyncio, "run", interrupt)
    run()


def test_settings_defaults_and_cache() -> None:
    configured = WorkerSettings(_env_file=None)
    assert configured.queue_name == "document_jobs"
    assert configured.embedding_dimensions == 768
    assert get_settings() is get_settings()


@pytest.mark.asyncio
async def test_supabase_queue_and_table_helpers() -> None:
    client = SupabaseClient("https://example.supabase.co/", "service-key")
    assert client.base_url == "https://example.supabase.co"
    assert client.headers["Authorization"] == "Bearer service-key"

    client.rpc = AsyncMock(
        return_value=[{"msg_id": "4", "read_ct": 2, "message": {"task": "demo"}}]
    )
    messages = await client.read_queue("document_jobs", 30, 2)
    assert messages[0].msg_id == 4
    await client.archive_message("document_jobs", 4)
    await client.send_message("document_jobs", {"task": "demo"}, 5)
    await client.match_chunks(DOCUMENT_ID, "pregunta", [0.1], 3)

    client._request = AsyncMock(return_value=[{"id": str(DOCUMENT_ID)}])
    assert await client.get_one("documents", DOCUMENT_ID)
    await client.patch("documents", DOCUMENT_ID, {"status": "completed"})
    await client.insert("documents", {"name": "demo"})
    await client.delete_where("documents", "owner_id", OWNER_ID)
    await client.checkpoint(JOB_ID, "extract", {"progress": 20})


def task_service() -> tuple[TaskService, AsyncMock, AsyncMock]:
    database = AsyncMock()
    ollama = AsyncMock()
    storage = Mock()
    service = TaskService(WorkerSettings(_env_file=None), database, storage, ollama)
    return service, database, ollama


@pytest.mark.asyncio
async def test_task_progress_cancellation_and_recording() -> None:
    service, database, _ = task_service()
    database.get_one.return_value = {"cancel_requested": False}
    await service._progress(JOB_ID, "indexing", 60, "embeddings")
    database.patch.assert_awaited()
    database.checkpoint.assert_awaited_once()

    database.get_one.return_value = {"cancel_requested": True}
    with pytest.raises(JobCancelled):
        await service._cancel_guard(JOB_ID)

    generation = Generation("respuesta", 10, 5, 12, "qwen3:8b")
    await service._record_llm(generation, "answer_question", OWNER_ID, DOCUMENT_ID, RUN_ID)
    database.insert.assert_awaited()


@pytest.mark.asyncio
async def test_agent_question_validates_citations() -> None:
    service, database, ollama = task_service()
    database.get_one.return_value = {"cancel_requested": False}
    database.match_chunks.return_value = [
        {"page_number": 2, "text": "El contrato vence el 30 de junio."}
    ]
    ollama.embed.return_value = [[0.1] * 768]
    ollama.generate.return_value = Generation(
        json.dumps(
            {
                "answer": "Vence el 30 de junio.",
                "citations": [{"page": 2, "quote": "vence el 30 de junio"}],
            }
        ),
        20,
        10,
        30,
        "qwen3:8b",
    )

    result = await service.answer_question(JOB_ID, DOCUMENT_ID, OWNER_ID, RUN_ID, "¿Cuándo vence?")
    assert result["citations"][0]["page"] == 2
    database.match_chunks.assert_awaited_once()
    database.patch.assert_awaited()

    ollama.generate.return_value = Generation(
        json.dumps({"answer": "inventada", "citations": [{"page": 9, "quote": "x"}]}),
        1,
        1,
        1,
        "qwen3:8b",
    )
    result = await service.answer_question(JOB_ID, DOCUMENT_ID, OWNER_ID, RUN_ID, "¿Otro dato?")
    assert result["answer"] == "No encontré información suficiente en el documento."


@pytest.mark.asyncio
async def test_summary_extraction_and_chunk_indexing() -> None:
    service, database, ollama = task_service()
    database.rpc.return_value = "Contenido del documento"
    ollama.generate.side_effect = [
        Generation("Resumen", 10, 4, 20, "qwen3:8b"),
        Generation(json.dumps({"fields": {"total": "100"}}), 10, 4, 20, "qwen3:8b"),
    ]

    summary = await service.summarize(JOB_ID, DOCUMENT_ID, OWNER_ID, RUN_ID)
    extracted = await service.extract_fields(JOB_ID, DOCUMENT_ID, OWNER_ID, RUN_ID, ["total"])
    assert summary == {"summary": "Resumen"}
    assert extracted["fields"]["total"] == "100"

    from worker.services.pdf_processing import Chunk

    chunk = Chunk(1, 0, "texto", 1, "hash")
    ollama.embed.return_value = [[0.2] * 768]
    await service._index_chunks(DOCUMENT_ID, [chunk])
    database.insert.assert_awaited()

    ollama.embed.return_value = [[0.2]]
    with pytest.raises(RuntimeError, match="dimensiones"):
        await service._index_chunks(DOCUMENT_ID, [chunk])
