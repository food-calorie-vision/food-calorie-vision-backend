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
    database_url: str = "mysql+asyncmy://fcv_user:password@localhost:3306/food_calorie"
    cors_allow_origins: list[str] = ["*"]
    jwt_secret: str = "replace-this-secret"
    jwt_expire_minutes: int = 60
    openai_api_key: str | None = None
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

