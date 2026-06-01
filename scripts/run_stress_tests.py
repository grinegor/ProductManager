from __future__ import annotations

import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pm_agent.config import Settings
from pm_agent.llm import UsageStats
from pm_agent.orchestrator import PMOrchestrator
from pm_agent.rag import RetrievedChunk


class StressLLM:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float, max_completion_tokens: int):
        self.calls += 1
        if "You are GrowthAgent" in system_prompt:
            return (
                '{"agent":"GrowthAgent","summary":"ok","key_findings":["f"],"recommendations":[],"assumptions":[],"compliance_flags":[],"experiments":[]}',
                UsageStats(prompt_tokens=8, completion_tokens=6),
            )
        if "You are SubscriptionAgent" in system_prompt:
            return (
                '{"agent":"SubscriptionAgent","summary":"ok","key_findings":["f"],"recommendations":[],"assumptions":[],"compliance_flags":[],"experiments":[]}',
                UsageStats(prompt_tokens=8, completion_tokens=6),
            )
        if "You are ComplianceAgent" in system_prompt:
            return (
                '{"agent":"ComplianceAgent","summary":"ok","key_findings":["f"],"recommendations":[],"assumptions":[],"compliance_flags":[],"experiments":[]}',
                UsageStats(prompt_tokens=8, completion_tokens=6),
            )
        return "final answer", UsageStats(prompt_tokens=12, completion_tokens=10)


class StressRAG:
    def retrieve(self, query: str, top_k: int | None = None):
        if not query.strip():
            return []
        return [RetrievedChunk(0, "docs/growth/funnel_basics.md", "funnel", 0.88)]


def make_orchestrator() -> PMOrchestrator:
    settings = Settings(
        openai_api_key="test",
        openai_model="test",
        fallback_openai_model="",
        openai_reasoning_effort="high",
        embedding_model="test",
        docs_dir=Path("docs"),
        data_dir=Path("data"),
        top_k=4,
        max_history_messages=8,
    )
    return PMOrchestrator(settings=settings, llm_client=StressLLM(), rag_store=StressRAG())


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    idx = max(0, min(len(values) - 1, int(round((p / 100.0) * (len(values) - 1)))))
    return sorted(values)[idx]


def main() -> None:
    orchestrator = make_orchestrator()

    queries = [
        "How to improve funnel CVR?",
        "Need retention and churn strategy",
        "Meta compliance for health claims",
        "Pricing and LTV tradeoffs",
        "Onboarding activation plan",
    ]

    # Boundary inputs
    long_query = "retention " * 2500
    empty_query = "   "

    runs = 300
    durations_ms: list[float] = []
    failures = 0

    for i in range(runs):
        if i == 0:
            query = long_query
        elif i == 1:
            query = empty_query
        else:
            query = random.choice(queries)

        start = time.perf_counter()
        try:
            result = orchestrator.run(user_query=query, chat_history=[], memory_summary="")
            if not result.final_answer:
                failures += 1
        except Exception:
            failures += 1
        finally:
            durations_ms.append((time.perf_counter() - start) * 1000.0)

    success = runs - failures
    print("=== STRESS REPORT ===")
    print(f"runs={runs}")
    print(f"success={success}")
    print(f"failures={failures}")
    print(f"error_rate={failures / runs:.4f}")
    print(f"latency_ms_min={min(durations_ms):.2f}")
    print(f"latency_ms_p50={percentile(durations_ms, 50):.2f}")
    print(f"latency_ms_p95={percentile(durations_ms, 95):.2f}")
    print(f"latency_ms_max={max(durations_ms):.2f}")
    print(f"latency_ms_avg={statistics.mean(durations_ms):.2f}")


if __name__ == "__main__":
    main()
