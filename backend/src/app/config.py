from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (and `.env` if present)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"

    # HS256 needs >= 32 bytes of key material (RFC 7518, section 3.2).
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"
    rate_limit_login: str = "5/minute"
    rate_limit_storage_uri: str = "memory://"

    overdue_scan_minutes: int = 15
    celery_task_always_eager: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values (incl. JWT_SECRET) come from the environment
