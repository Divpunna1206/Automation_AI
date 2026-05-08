from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = Field(default="sqlite:///data/jobhunt.db")
    profile_path: Path = ROOT_DIR / "profile.yaml"
    preferences_path: Path = ROOT_DIR / "preferences.yaml"
    answers_path: Path = ROOT_DIR / "answers.yaml"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    llm_provider: str = "local"
    artifacts_dir: Path = ROOT_DIR / "backend" / "artifacts"
    enable_web_scraping: bool = False
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
