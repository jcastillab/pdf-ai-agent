from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    log_level: str = "INFO"
    worker_id: str = "local-worker-1"
    poll_interval_seconds: float = 2.0
    queue_visibility_seconds: int = 3600
    queue_name: str = "document_jobs"
    dead_letter_queue_name: str = "document_jobs_dlq"
    max_attempts: int = 3

    supabase_url: str = "http://localhost:54321"
    supabase_service_role_key: str = ""

    r2_endpoint_url: str = "http://localhost:9000"
    r2_access_key_id: str = "minioadmin"
    r2_secret_access_key: str = "minioadmin"
    r2_bucket: str = "pdf-documents"
    r2_region: str = "auto"

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3:8b"
    ollama_embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768
    ollama_timeout_seconds: int = 300

    max_pdf_size_bytes: int = 25 * 1024 * 1024
    max_pdf_pages: int = 300
    min_native_text_chars: int = 40
    chunk_size_chars: int = 1800
    chunk_overlap_chars: int = 250
    rag_top_k: int = 6
    tesseract_language: str = "spa+eng"
    ocr_enabled: bool = True
    clamav_enabled: bool = False
    clamav_host: str = "localhost"
    clamav_port: int = 3310
    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "pdf-ai-agent-worker"


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
