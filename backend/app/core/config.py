"""Application configuration loaded from environment variables.

Uses pydantic-settings to provide validated, typed access to all
configuration values. Environment variables are loaded from a .env
file at the project root (or from the system environment).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings.

    All fields map to environment variables. Defaults are provided
    where sensible; secrets (e.g. OPENAI_API_KEY) must be set
    explicitly in the environment or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = "TN Gov AI Scheme Assistant"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/tngov"

    # ── OpenAI / LLM (used in later milestones) ─────────────
    openai_api_key: str = ""
    model_name: str = "gpt-4.1"

    # ── Embeddings (used in later milestones) ────────────────
    embedding_model: str = "intfloat/multilingual-e5-large"

    # ── ChromaDB (used in later milestones) ──────────────────
    chroma_db_path: str = "./chroma_db"

    # ── Server ───────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_reload: bool = True

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://frontend:3000",
    ]


# Singleton instance — import this wherever config is needed.
settings = Settings()
