"""
Configuration module for Silicon Citizens' Assembly backend.
Manages environment variables and application settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Silicon Citizens' Assembly"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    PERPLEXITY_API_KEY: str = ""

    # Database (SQLite for development, easy migration to PostgreSQL later)
    DATABASE_URL: str = "sqlite:///./assemblysim.db"
    DATABASE_ECHO: bool = False  # Set to True for SQL query logging

    # LLM Configuration
    LLM_PROVIDER: str = "openrouter"  # "openrouter", "openai", or "anthropic"

    # OpenRouter settings (https://openrouter.ai/docs)
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Model selection (OpenRouter model IDs)
    CITIZEN_MODEL: str = "anthropic/claude-3.5-sonnet"  # For persona agents
    WRITER_MODEL: str = "anthropic/claude-3.5-sonnet"   # For persona generation
    MODERATOR_MODEL: str = "anthropic/claude-3.5-sonnet"  # For moderator agent
    UTILITY_MODEL: str = "openai/gpt-4o-mini"           # For utility tasks (recorder)

    # LLM parameters
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 500
    WRITER_MAX_TOKENS: int = 1000  # Longer for persona generation

    # Assembly Parameters
    DEFAULT_NUM_CITIZENS: int = 40
    DEFAULT_NUM_GROUPS: int = 5
    DEFAULT_NUM_ROUNDS: int = 3

    # Data Paths
    DATA_DIR: Path = Path(__file__).parent.parent.parent.parent / "data"
    GSS_DATA_PATH: Path = DATA_DIR / "GSS_stata" / "gss7224_r2.dta"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        # .env is in the project root (one level up from backend/)
        env_file = Path(__file__).parent.parent.parent / ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
