import json
import time
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter


class OllamaError(RuntimeError):
    pass


@dataclass(slots=True)
class Generation:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model: str


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        chat_model: str,
        embedding_model: str,
        timeout_seconds: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.timeout = timeout_seconds

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        reraise=True,
    )
    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.embedding_model, "input": texts, "truncate": True},
            )
        if response.is_error:
            raise OllamaError(f"Ollama embeddings HTTP {response.status_code}")
        embeddings = response.json().get("embeddings") or []
        if len(embeddings) != len(texts):
            raise OllamaError("Ollama devolvió una cantidad inesperada de embeddings")
        return embeddings

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(2),
        wait=wait_exponential_jitter(initial=1, max=5),
        reraise=True,
    )
    async def generate(
        self, system: str, prompt: str, *, json_schema: dict[str, Any] | None = None
    ) -> Generation:
        started = time.perf_counter()
        payload: dict[str, Any] = {
            "model": self.chat_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "think": False,
            "options": {"temperature": 0.1},
        }
        if json_schema:
            payload["format"] = json_schema
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
        if response.is_error:
            raise OllamaError(f"Ollama chat HTTP {response.status_code}")
        data = response.json()
        text = data.get("message", {}).get("content", "")
        if json_schema:
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                raise OllamaError("Ollama no devolvió JSON válido") from exc
        return Generation(
            text=text,
            input_tokens=int(data.get("prompt_eval_count", 0)),
            output_tokens=int(data.get("eval_count", 0)),
            latency_ms=int((time.perf_counter() - started) * 1000),
            model=data.get("model", self.chat_model),
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
            return response.is_success
        except httpx.HTTPError:
            return False
