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
    allowed_origins: str = "http://localhost:3000"

    # ── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/tngov"

    # ── LLM Settings ─────────────────────────────────────────
    llm_provider: str = "openai"
    openai_api_key: str = ""
    model_name: str = "gpt-4.1"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024
    max_query_length: int = 500

    # ── Embeddings ───────────────────────────────────────────
    embedding_model: str = "intfloat/multilingual-e5-large"

    # ── ChromaDB ─────────────────────────────────────────────
    chroma_db_path: str = "./chroma_db"
    chroma_collection_name: str = "tn_gov_schemes"

    # ── Ingestion ────────────────────────────────────────────
    chunk_size: int = 700
    chunk_overlap: int = 125
    embedding_batch_size: int = 32
    chroma_upsert_batch_size: int = 100
    data_dir: str = "../data"
    pipeline_version: str = "1.0"

    # ── Retrieval ────────────────────────────────────────────
    retrieval_vector_top_k: int = 5
    retrieval_bm25_top_k: int = 5
    retrieval_final_context_k: int = 4
    retrieval_min_score: float = 0.015
    retrieval_max_vector_distance: float = 0.25
    retrieval_min_bm25_score: float = 5.0
    rrf_k: int = 60
    bm25_index_path: str = "./bm25_index.json"

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
