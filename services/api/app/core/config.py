from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_env_file() -> Path:
    # Find the repository .env when launched from services/api or the repo root.
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env.example").exists():
            return parent / ".env"
    return Path.cwd() / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_project_env_file(), extra="ignore")
    app_name: str = "ASTERA API"
    database_url: str = "postgresql+psycopg://astera:astera@localhost:5432/astera"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-env"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:3000"
    nasa_api_key: str = ""
    llm_provider: str = ""  # empty => ASTERA AI runs in labelled demo mode
    llm_api_key: str = ""


settings = Settings()
