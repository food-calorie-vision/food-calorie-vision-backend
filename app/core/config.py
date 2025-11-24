from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    api_prefix: str = "/api"
    api_version: str = "v1"
    port: int = 8000
    database_url: str = "mysql+asyncmy://root:dufdjwnj@10.43.40.99:3306/tempdb"
    cors_allow_origins: list[str] = ["http://localhost:3000"]
    
    # Session settings
    session_secret_key: str = "replace-this-session-secret-key-in-production"
    session_cookie_name: str = "fcv_session"
    session_max_age: int = 600  # 10 minutes in seconds
    session_https_only: bool = False  # Set to True in production with HTTPS
    session_same_site: str = "lax"  # lax, strict, or none
    
    # Redis settings (optional, for distributed session storage)
    redis_url: str | None = None  # e.g., "redis://localhost:6379/0"
    
    # AI/ML Settings
    openai_api_key: str | None = "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"  # OpenAI API Key
    vision_model_path: str | None = "models/yolo11n.pt"

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if not value:
            return ["*"]
        return [origin.strip() for origin in value.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()

