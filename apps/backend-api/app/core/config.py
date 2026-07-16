from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "PDF AI Agent API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:4200"])

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pdf_agent"
    database_pool_size: int = 5
    database_max_overflow: int = 5

    supabase_url: str = "http://localhost:54321"
    supabase_service_role_key: str = ""
    supabase_jwt_audience: str = "authenticated"
    queue_name: str = "document_jobs"

    r2_endpoint_url: str = "http://localhost:9000"
    r2_access_key_id: str = "minioadmin"
    r2_secret_access_key: str = "minioadmin"
    r2_bucket: str = "pdf-documents"
    r2_region: str = "auto"
    upload_url_ttl_seconds: int = 900
    download_url_ttl_seconds: int = 300

    max_pdf_size_bytes: int = 25 * 1024 * 1024
    max_pdf_pages: int = 300
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "pdf-ai-agent-api"
    auth_disabled: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
