from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Auth
    api_key: str

    # Database
    database_url: str

    # OpenRouter (OpenAI-compatible)
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Model config — swap models here without touching pipeline code
    injection_check_model: str = "openai/gpt-4o-mini"
    classification_model: str = "openai/gpt-4o-mini"
    # Confidence judge is a two-tier cascade: a cheap/fast model judges every
    # ticket first; only ambiguous scores get a second opinion from the
    # stronger model, keeping cost down without sacrificing quality on the
    # cases that actually need it.
    confidence_fast_model: str = "deepseek/deepseek-v4-flash"
    confidence_model: str = "anthropic/claude-haiku-4.5"
    language_fallback_model: str = "openai/gpt-4o-mini"

    # Pipeline tuning
    confidence_threshold: int = 70
    # If the fast judge's score falls in this band, it's treated as too
    # ambiguous to trust — escalate to the stronger model for a fresh opinion.
    confidence_escalation_low: int = 55
    confidence_escalation_high: int = 80
    max_llm_retries: int = 3
    fasttext_confidence_threshold: float = 0.7
    fasttext_model_path: str = "models/lid.176.ftz"

    # Validation limits
    min_ticket_length: int = 3
    max_ticket_length: int = 10_000

    # Rate limiting
    rate_limit: str = "10/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
