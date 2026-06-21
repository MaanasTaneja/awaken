from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_FILE, override=False)


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://awaken:awaken@db:5432/awaken"
    redis_url: str = "redis://redis:6379/0"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    hydra_db_api_key: str | None = None
    hydra_tenant_id: str = "awaken"
    hydra_index_timeout_seconds: float = 30.0
    hydra_index_poll_interval_seconds: float = 1.0

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


settings = Settings()
