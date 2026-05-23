from __future__ import annotations

import json
import tempfile
from pathlib import Path

from pm_agent.config import Settings
from pm_agent.llm import UsageStats
from pm_agent.orchestrator import PMOrchestrator
from pm_agent.rag import RetrievedChunk


class EvalLLM:
    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float, max_completion_tokens: int):
        self.call_count += 1
        if "You are GrowthAgent" in system_prompt:
            if "MALFORMED" in user_prompt:
                return "growth prose without json", UsageStats(prompt_tokens=11, completion_tokens=5)
            return (
                '{"agent":"GrowthAgent","summary":"Growth diagnosis","key_findings":["drop at quiz"],'
                '"recommendations":[{"title":"Shorten quiz","rationale":"reduce drop","expected_impact":"high","effort":"S","success_metric":"quiz completion"}],'
                '"assumptions":["traffic is paid"],"compliance_flags":[],"experiments":[{"hypothesis":"shorter quiz increases completion","metric":"completion rate","guardrail_metric":"checkout CVR","decision_rule":"+10% completion with flat checkout"}]}'
            ), UsageStats(prompt_tokens=20, completion_tokens=15)
        if "You are SubscriptionAgent" in system_prompt:
            return (
                '{"agent":"SubscriptionAgent","summary":"Retention diagnosis","key_findings":["month1 churn high"],'
                '"recommendations":[{"title":"Improve D0-D7","rationale":"faster first value","expected_impact":"high","effort":"M","success_metric":"D7 activation"}],'
                '"assumptions":[],"compliance_flags":[],"experiments":[]}'
            ), UsageStats(prompt_tokens=20, completion_tokens=14)
        if "You are ComplianceAgent" in system_prompt:
            return (
                '{"agent":"ComplianceAgent","summary":"Compliance review","key_findings":["risky guarantee"],'
                '"recommendations":[{"title":"Qualify claims","rationale":"policy-safe copy","expected_impact":"med","effort":"S","success_metric":"ad approval rate"}],'
                '"assumptions":[],"compliance_flags":["guaranteed outcome"],"experiments":[]}'
            ), UsageStats(prompt_tokens=14, completion_tokens=12)
        return "Final PM recommendation", UsageStats(prompt_tokens=30, completion_tokens=25)


class EvalRAG:
    def retrieve(self, query: str, top_k: int | None = None):
        if not query.strip():
            return []
        return [
            RetrievedChunk(0, "docs/growth/funnel_basics.md", "funnel benchmark", 0.85),
            RetrievedChunk(1, "docs/retention/retention_playbook.md", "retention benchmark", 0.79),
        ]


def make_orchestrator() -> PMOrchestrator:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
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
    return PMOrchestrator(settings=settings, llm_client=EvalLLM(), rag_store=EvalRAG())


def check_schema(subagent_output: dict) -> bool:
    required = {"agent", "summary", "key_findings", "recommendations", "assumptions", "compliance_flags", "experiments", "raw_text"}
    return required.issubset(set(subagent_output.keys()))


def main() -> None:
    orchestrator = make_orchestrator()

    eval_cases = [
        {
            "name": "growth+subscription default",
            "query": "How to improve funnel conversion and retention in a weight loss subscription?",
            "must_include_agents": {"growth", "subscription"},
        },
        {
            "name": "compliance route",
            "query": "Need Meta policy-safe messaging for telehealth weight loss ads",
            "must_include_agents": {"growth", "subscription", "compliance"},
        },
        {
            "name": "malformed growth fallback",
            "query": "MALFORMED: analyze growth bottleneck",
            "must_include_agents": {"growth", "subscription"},
        },
    ]

    passed = 0
    total = 0
    report = []

    for case in eval_cases:
        total += 1
        result = orchestrator.run(user_query=case["query"], chat_history=[], memory_summary="")

        active_set = set(result.active_subagents)
        has_agents = case["must_include_agents"].issubset(active_set)
        schema_ok = all(check_schema(v) for v in result.subagent_outputs.values())
        has_answer = bool(result.final_answer.strip())
        malformed_handled = True
        if "MALFORMED" in case["query"]:
            malformed_handled = bool(result.subagent_outputs["growth"].get("raw_text"))

        ok = has_agents and schema_ok and has_answer and malformed_handled
        if ok:
            passed += 1

        report.append(
            {
                "case": case["name"],
                "ok": ok,
                "active_subagents": result.active_subagents,
                "schema_ok": schema_ok,
                "has_answer": has_answer,
                "malformed_handled": malformed_handled,
                "token_usage": result.token_usage,
            }
        )

    print("=== EVAL REPORT ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSummary: {passed}/{total} eval cases passed")


if __name__ == "__main__":
    main()
