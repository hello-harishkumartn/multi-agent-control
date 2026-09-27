from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Enterprise Agent Control Plane"
    environment: str = "development"
    database_url: str = "sqlite:///./agentplane.db"
    api_key: str = "local-dev-key"
    model_provider: str = "deterministic"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    max_requests_per_minute: int = 120
    default_run_budget_usd: float = 1.0
    data_dir: Path = Path(__file__).parents[2] / "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()

