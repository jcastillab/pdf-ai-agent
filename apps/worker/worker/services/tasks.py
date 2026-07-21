import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import httpx
import structlog

from worker.clients.ollama import Generation, OllamaClient, OllamaError
from worker.clients.storage import ObjectStorage
from worker.clients.supabase import SupabaseClient
from worker.config import WorkerSettings
from worker.services.pdf_processing import (
    Chunk,
    ExtractedPage,
    chunk_pages,
    extract_pages,
    render_page_image,
    scan_clamav,
    sha256_file,
    validate_pdf,
)
from worker.services.prompts import (
    EXTRACTION_PROMPT,
    QUESTION_PROMPT,
    SUMMARY_PROMPT,
    SYSTEM_GUARDRAIL,
)

logger = structlog.get_logger()


class JobCancelled(RuntimeError):
    pass


class TaskService:
    def __init__(
        self,
        settings: WorkerSettings,
        database: SupabaseClient,
        storage: ObjectStorage,
        ollama: OllamaClient,
    ) -> None:
        self.settings = settings
        self.db = database
        self.storage = storage
        self.ollama = ollama

    async def _cancel_guard(self, job_id: UUID) -> None:
        job = await self.db.get_one("processing_jobs", job_id)
        if not job:
            raise RuntimeError("El trabajo no existe")
        if job.get("cancel_requested"):
            await self.db.patch(
                "processing_jobs",
                job_id,
                {"status": "cancelled", "current_step": "cancelled", "progress": 100},
            )
            raise JobCancelled("Cancelación solicitada")

    async def _progress(self, job_id: UUID, status: str, progress: int, step: str) -> None:
        await self._cancel_guard(job_id)
        await self.db.patch(
            "processing_jobs",
            job_id,
            {
                "status": status,
                "progress": progress,
                "current_step": step,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        await self.db.checkpoint(job_id, step, {"status": status, "progress": progress})

    async def _record_llm(
        self,
        generation: Generation,
        task_type: str,
        owner_id: UUID,
        document_id: UUID,
        agent_run_id: UUID | None,
    ) -> None:
        await self.db.insert(
            "llm_calls",
            {
                "agent_run_id": str(agent_run_id) if agent_run_id else None,
                "document_id": str(document_id),
                "owner_id": str(owner_id),
                "provider": "ollama",
                "model": generation.model,
                "task_type": task_type,
                "input_tokens": generation.input_tokens,
                "output_tokens": generation.output_tokens,
                "latency_ms": generation.latency_ms,
                "estimated_cost_usd": 0,
                "success": True,
            },
        )

    async def _apply_vision_ocr(
        self,
        pages: list[ExtractedPage],
        local_path: Path,
        owner_id: UUID,
        document_id: UUID,
    ) -> None:
        if not self.settings.vision_ocr_enabled:
            return
        for page in pages:
            if page.extraction_method != "ocr":
                continue
            if page.confidence >= self.settings.vision_ocr_confidence_threshold:
                continue
            try:
                image_png = await asyncio.to_thread(
                    render_page_image,
                    local_path,
                    page.page_number,
                    page.rotation_degrees,
                    self.settings.vision_ocr_render_scale,
                )
                generation = await self.ollama.transcribe_image(image_png, page.page_number)
                result = json.loads(generation.text)
                visual_text = str(result.get("text", "")).strip()
                visual_confidence = max(0.0, min(1.0, float(result.get("confidence", 0))))
                uncertain = tuple(
                    str(segment)[:300]
                    for segment in result.get("uncertain_segments", [])
                    if str(segment).strip()
                )
                if visual_text:
                    page.text = visual_text
                    page.extraction_method = "ocr_vision"
                    page.confidence = visual_confidence
                    page.uncertain_segments = uncertain
                    page.requires_review = (
                        bool(result.get("requires_review"))
                        or visual_confidence < self.settings.vision_ocr_confidence_threshold
                        or bool(uncertain)
                    )
                await self._record_llm(
                    generation, "handwritten_ocr", owner_id, document_id, None
                )
            except (OllamaError, httpx.HTTPError, ValueError, TypeError) as exc:
                page.requires_review = True
                logger.warning(
                    "vision_ocr_failed",
                    page_number=page.page_number,
                    error=str(exc)[:300],
                )

    async def process_document(self, job_id: UUID, document_id: UUID, owner_id: UUID) -> dict:
        document = await self.db.get_one("documents", document_id)
        if not document or document["owner_id"] != str(owner_id):
            raise RuntimeError("Documento no encontrado o sin permiso")
        await self.db.patch(
            "processing_jobs",
            job_id,
            {"status": "validating", "started_at": datetime.now(UTC).isoformat(), "attempts": 1},
        )
        await self.db.patch("documents", document_id, {"status": "validating"})
        with TemporaryDirectory(prefix="pdf-agent-") as temp_dir:
            local_path = Path(temp_dir) / "document.pdf"
            await self._progress(job_id, "validating", 5, "download")
            await asyncio.to_thread(self.storage.download, document["object_key"], local_path)
            page_count = await asyncio.to_thread(
                validate_pdf,
                local_path,
                self.settings.max_pdf_size_bytes,
                self.settings.max_pdf_pages,
            )
            digest = await asyncio.to_thread(sha256_file, local_path)
            await self.db.patch(
                "documents",
                document_id,
                {"sha256": digest, "page_count": page_count, "status": "extracting"},
            )
            if self.settings.clamav_enabled:
                await self._progress(job_id, "validating", 10, "antivirus")
                await asyncio.to_thread(
                    scan_clamav,
                    local_path,
                    self.settings.clamav_host,
                    self.settings.clamav_port,
                )

            await self._progress(job_id, "extracting", 20, "extract_text")
            pages = await asyncio.to_thread(
                extract_pages,
                local_path,
                self.settings.min_native_text_chars,
                self.settings.ocr_enabled,
                self.settings.tesseract_language,
            )
            await self._apply_vision_ocr(pages, local_path, owner_id, document_id)
            await self.db.patch("documents", document_id, {"status": "chunking"})
            await self._progress(job_id, "chunking", 45, "chunk")
            chunks = chunk_pages(
                pages, self.settings.chunk_size_chars, self.settings.chunk_overlap_chars
            )
            if not chunks:
                raise RuntimeError("No se extrajo texto suficiente para indexar")

            await self.db.delete_where("document_pages", "document_id", document_id)
            await self.db.delete_where("document_chunks", "document_id", document_id)
            await self.db.insert(
                "document_pages",
                [
                    {
                        "document_id": str(document_id),
                        "page_number": page.page_number,
                        "text": page.text,
                        "extraction_method": page.extraction_method,
                        "confidence": page.confidence,
                        "metadata": {
                            "rotation_degrees": page.rotation_degrees,
                            "requires_review": page.requires_review,
                            "uncertain_segments": list(page.uncertain_segments),
                        },
                    }
                    for page in pages
                ],
            )

            await self.db.patch("documents", document_id, {"status": "indexing"})
            await self._progress(job_id, "indexing", 60, "embeddings")
            await self._index_chunks(document_id, chunks)

            await self._progress(job_id, "classifying", 80, "summarize")
            context = "\n\n".join(f"[Página {page.page_number}] {page.text}" for page in pages)[
                :24000
            ]
            generation = await self.ollama.generate(
                SYSTEM_GUARDRAIL, SUMMARY_PROMPT.format(context=context)
            )
            await self._record_llm(generation, "summarize_document", owner_id, document_id, None)
            confidence = sum(page.confidence for page in pages) / len(pages)
            await self.db.patch(
                "documents",
                document_id,
                {
                    "status": "completed",
                    "summary": generation.text,
                    "confidence": round(confidence, 4),
                    "processed_at": datetime.now(UTC).isoformat(),
                },
            )
            result = {
                "page_count": page_count,
                "chunk_count": len(chunks),
                "sha256": digest,
                "summary": generation.text,
                "ocr_pages": sum(page.extraction_method == "ocr" for page in pages),
                "vision_ocr_pages": sum(
                    page.extraction_method == "ocr_vision" for page in pages
                ),
                "rotated_pages": [
                    page.page_number for page in pages if page.rotation_degrees != 0
                ],
                "review_pages": [page.page_number for page in pages if page.requires_review],
            }
            await self.db.patch(
                "processing_jobs",
                job_id,
                {
                    "status": "completed",
                    "progress": 100,
                    "current_step": "completed",
                    "result": result,
                    "completed_at": datetime.now(UTC).isoformat(),
                },
            )
            return result

    async def _index_chunks(self, document_id: UUID, chunks: list[Chunk]) -> None:
        batch_size = 16
        rows: list[dict] = []
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            embeddings = await self.ollama.embed([chunk.text for chunk in batch])
            for chunk, embedding in zip(batch, embeddings, strict=True):
                if len(embedding) != self.settings.embedding_dimensions:
                    raise RuntimeError(
                        f"Embedding de {len(embedding)} dimensiones, se esperaban "
                        f"{self.settings.embedding_dimensions}"
                    )
                rows.append(
                    {
                        "document_id": str(document_id),
                        "page_number": chunk.page_number,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "token_count": chunk.token_count,
                        "content_hash": chunk.content_hash,
                        "extraction_method": chunk.extraction_method,
                        "confidence": chunk.confidence,
                        "embedding_model": self.settings.ollama_embedding_model,
                        "embedding": embedding,
                    }
                )
            if len(rows) >= 64:
                await self.db.insert("document_chunks", rows)
                rows.clear()
        if rows:
            await self.db.insert("document_chunks", rows)

    async def answer_question(
        self,
        job_id: UUID,
        document_id: UUID,
        owner_id: UUID,
        agent_run_id: UUID,
        question: str,
    ) -> dict:
        await self._progress(job_id, "indexing", 20, "retrieve")
        query_embedding = (await self.ollama.embed([question]))[0]
        chunks = await self.db.match_chunks(
            document_id, question, query_embedding, self.settings.rag_top_k
        )
        context = "\n\n".join(
            f"[Página {chunk['page_number']}] {chunk['text']}" for chunk in chunks
        )
        schema = {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "citations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "page": {"type": "integer"},
                            "quote": {"type": "string"},
                        },
                        "required": ["page", "quote"],
                    },
                },
            },
            "required": ["answer", "citations"],
        }
        await self._progress(job_id, "generating", 55, "generate_answer")
        generation = await self.ollama.generate(
            SYSTEM_GUARDRAIL,
            QUESTION_PROMPT.format(question=question, context=context),
            json_schema=schema,
        )
        result = json.loads(generation.text)
        evidence_pages = {int(chunk["page_number"]) for chunk in chunks}
        evidence_by_page: dict[int, str] = {}
        for chunk in chunks:
            page = int(chunk["page_number"])
            evidence_by_page[page] = f"{evidence_by_page.get(page, '')} {chunk['text']}"
        result["citations"] = [
            citation
            for citation in result.get("citations", [])
            if int(citation.get("page", -1)) in evidence_pages
            and str(citation.get("quote", "")).strip()
            and str(citation["quote"]).strip().lower()
            in evidence_by_page[int(citation["page"])].lower()
        ]
        if not result["citations"]:
            result["answer"] = "No encontré información suficiente en el documento."
        await self._record_llm(generation, "answer_question", owner_id, document_id, agent_run_id)
        await self._complete_agent_job(job_id, agent_run_id, result)
        return result

    async def summarize(
        self, job_id: UUID, document_id: UUID, owner_id: UUID, agent_run_id: UUID
    ) -> dict:
        chunks = await self.db.rpc(
            "document_context", {"target_document_id": str(document_id), "max_chars": 24000}
        )
        context = chunks or ""
        generation = await self.ollama.generate(
            SYSTEM_GUARDRAIL, SUMMARY_PROMPT.format(context=context)
        )
        result = {"summary": generation.text}
        await self.db.patch("documents", document_id, result)
        await self._record_llm(
            generation, "summarize_document", owner_id, document_id, agent_run_id
        )
        await self._complete_agent_job(job_id, agent_run_id, result)
        return result

    async def extract_fields(
        self,
        job_id: UUID,
        document_id: UUID,
        owner_id: UUID,
        agent_run_id: UUID,
        fields: list[str],
    ) -> dict:
        context = await self.db.rpc(
            "document_context", {"target_document_id": str(document_id), "max_chars": 24000}
        )
        schema = {
            "type": "object",
            "properties": {"fields": {"type": "object"}},
            "required": ["fields"],
        }
        generation = await self.ollama.generate(
            SYSTEM_GUARDRAIL,
            EXTRACTION_PROMPT.format(fields=", ".join(fields), context=context or ""),
            json_schema=schema,
        )
        result = json.loads(generation.text)
        await self._record_llm(generation, "extract_fields", owner_id, document_id, agent_run_id)
        await self._complete_agent_job(job_id, agent_run_id, result)
        return result

    async def _complete_agent_job(self, job_id: UUID, agent_run_id: UUID, result: dict) -> None:
        now = datetime.now(UTC).isoformat()
        await self.db.patch(
            "processing_jobs",
            job_id,
            {
                "status": "completed",
                "progress": 100,
                "current_step": "completed",
                "result": result,
                "completed_at": now,
            },
        )
        await self.db.patch(
            "agent_runs",
            agent_run_id,
            {"status": "completed", "output_json": result, "updated_at": now},
        )
