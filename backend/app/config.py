from pathlib import Path
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # App info
    app_name: str = "Role-Based RAG Interviewer"
    app_version: str = "1.0.0"
    debug: bool = False

    # Base paths
    backend_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"

    # Database & Storage (absolute paths by default)
    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'interview.db').as_posix()}"
    chroma_path: str = str(BASE_DIR / "data" / "chroma")
    knowledge_base_dir: str = str(BASE_DIR / "data" / "knowledge_base")

    # Embeddings & RAG
    embedding_model: str = "all-MiniLM-L6-v2"
    top_k: int = 5

    # LLM Settings
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # Interview Settings
    max_turns: int = 5

    # CORS Settings
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://frontend-eight-green-24.vercel.app",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

