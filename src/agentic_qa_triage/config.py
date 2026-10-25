from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Agentic QA Triage"
    database_url: str = "sqlite:///./agentic_qa_triage.db"
    agent_provider: Literal["demo", "openai"] = "demo"
    openai_model: str = "gpt-5-mini"
    max_agent_turns: int = Field(default=4, ge=1, le=10)
    max_input_chars: int = Field(default=12_000, ge=500, le=50_000)

    openai_input_usd_per_million: float | None = Field(default=None, ge=0)
    openai_cached_input_usd_per_million: float | None = Field(default=None, ge=0)
    openai_output_usd_per_million: float | None = Field(default=None, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
