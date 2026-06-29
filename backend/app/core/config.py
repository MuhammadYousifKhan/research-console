from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Axiom — An Autonomous AI Research Agent"
    app_env: str = "development"
    database_url: str = "sqlite:///./research.db"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    tavily_api_key: str = ""
    # --- RAG (retrieval-augmented generation) ---
    # When enabled, gathered evidence is chunked, embedded into a per-run
    # in-memory Chroma index, and only the top-k query-relevant chunks are fed
    # to synthesis. Disable to fall back to feeding all evidence (the old path).
    rag_enabled: bool = True
    rag_top_k: int = 8
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    cors_allow_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:5175,http://127.0.0.1:5175"
    )

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
