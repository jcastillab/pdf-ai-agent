from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx


class SupabaseError(RuntimeError):
    pass


@dataclass(slots=True)
class QueueMessage:
    msg_id: int
    read_ct: int
    message: dict[str, Any]


class SupabaseClient:
    def __init__(self, base_url: str, service_key: str, timeout: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        return {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        extra_headers = kwargs.pop("headers", {})
        headers = {**self.headers, **extra_headers}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method, f"{self.base_url}{path}", headers=headers, **kwargs
            )
        if response.is_error:
            raise SupabaseError(f"Supabase HTTP {response.status_code}: {response.text[:300]}")
        if not response.content:
            return None
        return response.json()

    async def rpc(self, function: str, payload: dict, schema: str = "public") -> Any:
        headers = {**self.headers, "Content-Profile": schema, "Accept-Profile": schema}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/rest/v1/rpc/{function}", headers=headers, json=payload
            )
        if response.is_error:
            raise SupabaseError(
                f"RPC {function} HTTP {response.status_code}: {response.text[:300]}"
            )
        return response.json() if response.content else None

    async def read_queue(
        self, queue_name: str, visibility_seconds: int, batch_size: int = 1
    ) -> list[QueueMessage]:
        rows = await self.rpc(
            "read",
            {"queue_name": queue_name, "sleep_seconds": visibility_seconds, "n": batch_size},
            schema="pgmq_public",
        )
        return [
            QueueMessage(
                msg_id=int(row["msg_id"]),
                read_ct=int(row.get("read_ct", 1)),
                message=row["message"],
            )
            for row in (rows or [])
        ]

    async def archive_message(self, queue_name: str, message_id: int) -> None:
        await self.rpc(
            "archive",
            {"queue_name": queue_name, "message_id": message_id},
            schema="pgmq_public",
        )

    async def send_message(self, queue_name: str, message: dict, delay_seconds: int = 0) -> None:
        await self.rpc(
            "send",
            {
                "queue_name": queue_name,
                "message": message,
                "sleep_seconds": delay_seconds,
            },
            schema="pgmq_public",
        )

    async def get_one(self, table: str, row_id: UUID) -> dict | None:
        rows = await self._request("GET", f"/rest/v1/{table}?id=eq.{row_id}&select=*&limit=1")
        return rows[0] if rows else None

    async def patch(self, table: str, row_id: UUID | str, values: dict) -> None:
        await self._request(
            "PATCH",
            f"/rest/v1/{table}?id=eq.{row_id}",
            headers={**self.headers, "Prefer": "return=minimal"},
            json=values,
        )

    async def insert(self, table: str, values: list[dict] | dict) -> None:
        await self._request(
            "POST",
            f"/rest/v1/{table}",
            headers={**self.headers, "Prefer": "return=minimal"},
            json=values,
        )

    async def delete_where(self, table: str, column: str, value: UUID | str) -> None:
        await self._request(
            "DELETE",
            f"/rest/v1/{table}?{column}=eq.{value}",
            headers={**self.headers, "Prefer": "return=minimal"},
        )

    async def match_chunks(
        self, document_id: UUID, query_text: str, embedding: list[float], count: int
    ) -> list[dict]:
        result = await self.rpc(
            "match_document_chunks",
            {
                "query_embedding": embedding,
                "query_text": query_text,
                "match_document_id": str(document_id),
                "match_count": count,
            },
        )
        return result or []

    async def checkpoint(self, job_id: UUID, node: str, state: dict) -> None:
        await self.insert(
            "graph_checkpoints",
            {"job_id": str(job_id), "node": node, "state": state},
        )
