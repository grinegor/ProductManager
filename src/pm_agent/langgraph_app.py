from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pm_agent.config import load_settings
from pm_agent.llm import OpenAIClient
from pm_agent.orchestrator import PMOrchestrator
from pm_agent.rag import RAGStore


def build_graph():
    settings = load_settings()
    llm_client = OpenAIClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        embedding_model=settings.embedding_model,
        fallback_model=settings.fallback_openai_model,
        reasoning_effort=settings.openai_reasoning_effort,
    )
    rag_store = RAGStore(settings, llm_client)
    orchestrator = PMOrchestrator(settings, llm_client, rag_store)
    return orchestrator.graph


# LangGraph Studio entrypoint
graph = build_graph()
