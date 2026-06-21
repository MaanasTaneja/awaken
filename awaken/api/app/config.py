from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://awaken:awaken@db:5432/awaken"
    redis_url: str = "redis://redis:6379/0"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    hydra_api_key: str | None = None
    hydra_project_id: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
