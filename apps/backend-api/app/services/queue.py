from functools import lru_cache

import httpx

from app.core.config import get_settings


class QueueError(RuntimeError):
    pass


class SupabaseQueue:
    def __init__(self, url: str, service_key: str, queue_name: str) -> None:
        self.url = url.rstrip("/")
        self.service_key = service_key
        self.queue_name = queue_name

    async def send(self, message: dict, delay_seconds: int = 0) -> int:
        if not self.service_key:
            raise QueueError("SUPABASE_SERVICE_ROLE_KEY no está configurada")
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Profile": "pgmq_public",
            "Accept-Profile": "pgmq_public",
        }
        payload = {
            "queue_name": self.queue_name,
            "message": message,
            "sleep_seconds": delay_seconds,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/send", headers=headers, json=payload
            )
        if response.is_error:
            raise QueueError(f"No se pudo encolar el trabajo: HTTP {response.status_code}")
        data = response.json()
        return int(data[0] if isinstance(data, list) else data)


@lru_cache
def get_queue() -> SupabaseQueue:
    settings = get_settings()
    return SupabaseQueue(
        settings.supabase_url, settings.supabase_service_role_key, settings.queue_name
    )
