from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pm_agent.config import Settings
from pm_agent.llm import UsageStats
from pm_agent.orchestrator import PMOrchestrator
from pm_agent.rag import RetrievedChunk


class FakeLLMForOrchestrator:
    def __init__(self, malformed_growth: bool = False) -> None:
        self.malformed_growth = malformed_growth
        self.calls: list[tuple[str, str]] = []

    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float, max_completion_tokens: int):
        self.calls.append((system_prompt, user_prompt))

        if "You are GrowthAgent" in system_prompt:
            if self.malformed_growth:
                return "growth notes without json", UsageStats(prompt_tokens=11, completion_tokens=5)
            return (
                '{"agent":"GrowthAgent","summary":"Growth summary","key_findings":["f1","f2"],'
                '"recommendations":[{"title":"r1","rationale":"why","expected_impact":"high","effort":"M","success_metric":"CVR"}],'
                '"assumptions":["a1"],"compliance_flags":[],"experiments":[{"hypothesis":"h1","metric":"m1","guardrail_metric":"g1","decision_rule":"d1"}]}'
            ), UsageStats(prompt_tokens=10, completion_tokens=4)

        if "You are SubscriptionAgent" in system_prompt:
            return (
                '{"agent":"SubscriptionAgent","summary":"Sub summary","key_findings":["retention bottleneck"],'
                '"recommendations":[{"title":"save flow","rationale":"reduce churn","expected_impact":"high","effort":"S","success_metric":"M2 retention"}],'
                '"assumptions":[],"compliance_flags":[],"experiments":[]}'
            ), UsageStats(prompt_tokens=12, completion_tokens=4)

        if "You are ComplianceAgent" in system_prompt:
            return (
                '{"agent":"ComplianceAgent","summary":"Risk review","key_findings":["claim risk"],'
                '"recommendations":[{"title":"copy rewrite","rationale":"policy safety","expected_impact":"med","effort":"S","success_metric":"ad approval"}],'
                '"assumptions":[],"compliance_flags":["guaranteed outcomes"],"experiments":[]}'
            ), UsageStats(prompt_tokens=9, completion_tokens=3)

        return "Final synthesized answer.", UsageStats(prompt_tokens=20, completion_tokens=10)


class FakeRAGStore:
    def retrieve(self, query: str, top_k: int | None = None):
        if not query.strip():
            return []
        return [
            RetrievedChunk(chunk_id=0, source="docs/growth/funnel_basics.md", text="funnel insight", score=0.81),
            RetrievedChunk(chunk_id=1, source="docs/retention/retention_playbook.md", text="retention insight", score=0.74),
        ]


class OrchestratorTests(unittest.TestCase):
    def make_settings(self) -> Settings:
        with tempfile.TemporaryDirectory() as td:
            pass
        root = Path(tempfile.gettempdir()) / "pm_agent_test"
        root.mkdir(parents=True, exist_ok=True)
        return Settings(
            openai_api_key="test",
            openai_model="test-model",
            fallback_openai_model="",
            openai_reasoning_effort="high",
            embedding_model="test-embed",
            docs_dir=root,
            data_dir=root,
            top_k=2,
            max_history_messages=8,
        )

    def test_route_defaults_growth_and_subscription(self) -> None:
        orch = PMOrchestrator(self.make_settings(), FakeLLMForOrchestrator(), FakeRAGStore())
        route = orch._route_node({"user_query": "What should we do next?"})
        self.assertIn("growth", route["active_subagents"])
        self.assertIn("subscription", route["active_subagents"])

    def test_route_adds_compliance_for_policy_query(self) -> None:
        orch = PMOrchestrator(self.make_settings(), FakeLLMForOrchestrator(), FakeRAGStore())
        route = orch._route_node({"user_query": "Need Meta policy-safe claims"})
        self.assertIn("compliance", route["active_subagents"])

    def test_extract_json_object_with_wrapped_text(self) -> None:
        orch = PMOrchestrator(self.make_settings(), FakeLLMForOrchestrator(), FakeRAGStore())
        parsed = orch._extract_json_object("preface {\"agent\":\"GrowthAgent\",\"summary\":\"ok\"} suffix")
        self.assertEqual(parsed["agent"], "GrowthAgent")

    def test_run_end_to_end(self) -> None:
        orch = PMOrchestrator(self.make_settings(), FakeLLMForOrchestrator(), FakeRAGStore())
        result = orch.run(
            user_query="How to improve funnel and retention?",
            chat_history=[{"role": "user", "content": "Hello"}],
            memory_summary="",
        )
        self.assertTrue(result.final_answer)
        self.assertIn("growth", result.subagent_outputs)
        self.assertIn("subscription", result.subagent_outputs)
        self.assertGreater(result.token_usage["total_tokens"], 0)
        self.assertEqual(result.subagent_outputs["growth"]["agent"], "GrowthAgent")

    def test_malformed_growth_output_is_normalized(self) -> None:
        orch = PMOrchestrator(self.make_settings(), FakeLLMForOrchestrator(malformed_growth=True), FakeRAGStore())
        result = orch.run(
            user_query="funnel question",
            chat_history=[],
            memory_summary="",
        )
        growth = result.subagent_outputs["growth"]
        self.assertEqual(growth["agent"], "GrowthAgent")
        self.assertTrue(growth["summary"])
        self.assertEqual(growth["raw_text"], "growth notes without json")


if __name__ == "__main__":
    unittest.main()
