from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str = "gpt-5.4"
    fallback_openai_model: str = "gpt-5.4-mini"
    openai_reasoning_effort: str = "high"
    embedding_model: str = "text-embedding-3-small"
    docs_dir: Path = Path("docs")
    data_dir: Path = Path("data")
    top_k: int = 4
    max_history_messages: int = 8
    demo_mode: bool = False

    @property
    def faiss_index_path(self) -> Path:
        return self.data_dir / "faiss.index"

    @property
    def chunk_store_path(self) -> Path:
        return self.data_dir / "chunks.json"


def load_settings() -> Settings:
    load_dotenv()

    demo_mode = os.getenv("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key and not demo_mode:
        raise ValueError("OPENAI_API_KEY is required. Add it to .env or environment variables.")

    docs_dir = Path(os.getenv("DOCS_DIR", "docs"))
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        openai_api_key=api_key or "demo-mode-no-api-key",
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4"),
        fallback_openai_model=os.getenv("OPENAI_FALLBACK_MODEL", "gpt-5.4-mini").strip(),
        openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "high").strip(),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        docs_dir=docs_dir,
        data_dir=data_dir,
        top_k=int(os.getenv("TOP_K", "4")),
        max_history_messages=int(os.getenv("MAX_HISTORY_MESSAGES", "8")),
        demo_mode=demo_mode,
    )
