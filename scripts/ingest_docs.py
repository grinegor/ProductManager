from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pm_agent.config import load_settings
from pm_agent.llm import OpenAIClient
from pm_agent.rag import RAGStore


def main() -> None:
    settings = load_settings()
    llm_client = OpenAIClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        embedding_model=settings.embedding_model,
    )
    rag_store = RAGStore(settings=settings, llm_client=llm_client)

    stats = rag_store.build_from_docs(docs_dir=settings.docs_dir)
    print(
        f"Indexed {stats['documents']} documents into {stats['chunks']} chunks. "
        f"Saved index at {settings.faiss_index_path}."
    )


if __name__ == "__main__":
    main()
