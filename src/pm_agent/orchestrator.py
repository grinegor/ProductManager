from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .config import Settings
from .llm import OpenAIClient, UsageStats
from .prompts import (
    COMPLIANCE_SYSTEM,
    COMPRESSED_SUBAGENT_SCHEMA,
    GROWTH_SYSTEM,
    PM_STRATEGIST_SYSTEM,
    ROUTER_KEYWORDS,
    SUBSCRIPTION_SYSTEM,
)
from .rag import RAGStore, RetrievedChunk
from .utils import estimate_tokens, format_history


@dataclass
class OrchestratorResult:
    final_answer: str
    active_subagents: list[str]
    retrieved_chunks: list[RetrievedChunk]
    subagent_outputs: dict[str, dict[str, Any]]
    token_usage: dict[str, int]


class PMState(TypedDict, total=False):
    user_query: str
    chat_history: list[dict[str, str]]
    memory_summary: str
    retrieved_chunks: list[RetrievedChunk]
    active_subagents: list[str]
    growth_output: dict[str, Any]
    subscription_output: dict[str, Any]
    compliance_output: dict[str, Any]
    final_answer: str
    token_usage: dict[str, int]


class PMOrchestrator:
    def __init__(self, settings: Settings, llm_client: OpenAIClient, rag_store: RAGStore) -> None:
        self.settings = settings
        self.llm_client = llm_client
        self.rag_store = rag_store
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(PMState)

        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("route", self._route_node)
        graph.add_node("growth", self._growth_node)
        graph.add_node("subscription", self._subscription_node)
        graph.add_node("compliance", self._compliance_node)
        graph.add_node("synthesize", self._synthesis_node)

        graph.add_edge(START, "retrieve")
        graph.add_edge("retrieve", "route")
        graph.add_edge("route", "growth")
        graph.add_edge("growth", "subscription")
        graph.add_edge("subscription", "compliance")
        graph.add_edge("compliance", "synthesize")
        graph.add_edge("synthesize", END)

        return graph.compile()

    @staticmethod
    def _usage_dict() -> dict[str, int]:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    @staticmethod
    def _merge_usage(current: dict[str, int], usage: UsageStats) -> dict[str, int]:
        current["prompt_tokens"] += usage.prompt_tokens
        current["completion_tokens"] += usage.completion_tokens
        current["total_tokens"] += usage.total_tokens
        return current

    def _retrieve_node(self, state: PMState) -> PMState:
        query = state.get("user_query", "")
        chunks = self.rag_store.retrieve(query, top_k=self.settings.top_k)
        return {"retrieved_chunks": chunks}

    def _route_node(self, state: PMState) -> PMState:
        query = state.get("user_query", "").lower()

        active = ["pm_strategist"]

        if any(keyword in query for keyword in ROUTER_KEYWORDS["growth"]):
            active.append("growth")

        if any(keyword in query for keyword in ROUTER_KEYWORDS["subscription"]):
            active.append("subscription")

        if any(keyword in query for keyword in ROUTER_KEYWORDS["compliance"]):
            active.append("compliance")

        # Default to growth + subscription so answers are not shallow.
        if "growth" not in active:
            active.append("growth")
        if "subscription" not in active:
            active.append("subscription")

        return {"active_subagents": active}

    def _build_context_prompt(self, state: PMState) -> str:
        history = format_history(state.get("chat_history", []), max_messages=self.settings.max_history_messages)
        memory_summary = state.get("memory_summary", "") or "(none)"

        chunks = state.get("retrieved_chunks", [])
        if chunks:
            evidence_lines = []
            for chunk in chunks:
                snippet = chunk.text[:500].strip()
                evidence_lines.append(
                    f"- Source: {chunk.source} | score={chunk.score:.3f}\n  {snippet}"
                )
            evidence_block = "\n".join(evidence_lines)
        else:
            evidence_block = "(no retrieved knowledge chunks)"

        return (
            f"User question:\n{state.get('user_query', '')}\n\n"
            f"Conversation memory summary:\n{memory_summary}\n\n"
            f"Recent chat:\n{history}\n\n"
            f"Retrieved evidence:\n{evidence_block}\n"
        )

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any] | None:
        raw = (text or "").strip()
        if not raw:
            return None

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            parsed = json.loads(raw[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None
        return None

    def _normalize_subagent_output(self, parsed: dict[str, Any] | None, *, agent: str, raw: str) -> dict[str, Any]:
        def as_list(value: Any, limit: int) -> list:
            if not isinstance(value, list):
                return []
            return value[:limit]

        parsed = parsed or {}

        recs: list[dict[str, str]] = []
        for rec in as_list(parsed.get("recommendations", []), 3):
            if not isinstance(rec, dict):
                continue
            recs.append(
                {
                    "title": str(rec.get("title", "")).strip(),
                    "rationale": str(rec.get("rationale", "")).strip(),
                    "expected_impact": str(rec.get("expected_impact", "")).strip(),
                    "effort": str(rec.get("effort", "")).strip(),
                    "success_metric": str(rec.get("success_metric", "")).strip(),
                }
            )

        exps: list[dict[str, str]] = []
        for exp in as_list(parsed.get("experiments", []), 2):
            if not isinstance(exp, dict):
                continue
            exps.append(
                {
                    "hypothesis": str(exp.get("hypothesis", "")).strip(),
                    "metric": str(exp.get("metric", "")).strip(),
                    "guardrail_metric": str(exp.get("guardrail_metric", "")).strip(),
                    "decision_rule": str(exp.get("decision_rule", "")).strip(),
                }
            )

        return {
            "agent": str(parsed.get("agent", agent)).strip() or agent,
            "summary": str(parsed.get("summary", "")).strip() or raw[:280],
            "key_findings": [str(x).strip() for x in as_list(parsed.get("key_findings", []), 3)],
            "recommendations": recs,
            "assumptions": [str(x).strip() for x in as_list(parsed.get("assumptions", []), 5)],
            "compliance_flags": [str(x).strip() for x in as_list(parsed.get("compliance_flags", []), 5)],
            "experiments": exps,
            "raw_text": raw if not parsed else "",
        }

    def _growth_node(self, state: PMState) -> PMState:
        if "growth" not in state.get("active_subagents", []):
            return {
                "growth_output": self._normalize_subagent_output(
                    {
                        "agent": "GrowthAgent",
                        "summary": "Skipped by router.",
                        "key_findings": [],
                        "recommendations": [],
                        "assumptions": [],
                        "compliance_flags": [],
                        "experiments": [],
                    },
                    agent="GrowthAgent",
                    raw="Skipped by router.",
                )
            }

        prompt = (
            self._build_context_prompt(state)
            + "\nReturn your growth diagnosis and top experiments.\n\n"
            + COMPRESSED_SUBAGENT_SCHEMA
            + '\nSet "agent" to "GrowthAgent".'
        )
        response, usage = self.llm_client.complete(
            system_prompt=GROWTH_SYSTEM,
            user_prompt=prompt,
            temperature=0.2,
            max_completion_tokens=450,
        )
        parsed = self._extract_json_object(response)
        normalized = self._normalize_subagent_output(parsed, agent="GrowthAgent", raw=response)
        token_usage = self._merge_usage(state.get("token_usage", self._usage_dict()), usage)
        return {"growth_output": normalized, "token_usage": token_usage}

    def _subscription_node(self, state: PMState) -> PMState:
        if "subscription" not in state.get("active_subagents", []):
            return {
                "subscription_output": self._normalize_subagent_output(
                    {
                        "agent": "SubscriptionAgent",
                        "summary": "Skipped by router.",
                        "key_findings": [],
                        "recommendations": [],
                        "assumptions": [],
                        "compliance_flags": [],
                        "experiments": [],
                    },
                    agent="SubscriptionAgent",
                    raw="Skipped by router.",
                )
            }

        prompt = (
            self._build_context_prompt(state)
            + "\nReturn churn/retention and subscription-economics recommendations.\n\n"
            + COMPRESSED_SUBAGENT_SCHEMA
            + '\nSet "agent" to "SubscriptionAgent".'
        )
        response, usage = self.llm_client.complete(
            system_prompt=SUBSCRIPTION_SYSTEM,
            user_prompt=prompt,
            temperature=0.2,
            max_completion_tokens=450,
        )
        parsed = self._extract_json_object(response)
        normalized = self._normalize_subagent_output(parsed, agent="SubscriptionAgent", raw=response)
        token_usage = self._merge_usage(state.get("token_usage", self._usage_dict()), usage)
        return {"subscription_output": normalized, "token_usage": token_usage}

    def _compliance_node(self, state: PMState) -> PMState:
        if "compliance" not in state.get("active_subagents", []):
            return {
                "compliance_output": self._normalize_subagent_output(
                    {
                        "agent": "ComplianceAgent",
                        "summary": "Skipped by router.",
                        "key_findings": [],
                        "recommendations": [],
                        "assumptions": [],
                        "compliance_flags": [],
                        "experiments": [],
                    },
                    agent="ComplianceAgent",
                    raw="Skipped by router.",
                )
            }

        prompt = (
            self._build_context_prompt(state)
            + "\nFlag risky claims and provide compliant alternatives.\n\n"
            + COMPRESSED_SUBAGENT_SCHEMA
            + '\nSet "agent" to "ComplianceAgent".'
        )
        response, usage = self.llm_client.complete(
            system_prompt=COMPLIANCE_SYSTEM,
            user_prompt=prompt,
            temperature=0.1,
            max_completion_tokens=350,
        )
        parsed = self._extract_json_object(response)
        normalized = self._normalize_subagent_output(parsed, agent="ComplianceAgent", raw=response)
        token_usage = self._merge_usage(state.get("token_usage", self._usage_dict()), usage)
        return {"compliance_output": normalized, "token_usage": token_usage}

    def _synthesis_node(self, state: PMState) -> PMState:
        growth_output = json.dumps(state.get("growth_output", {}), ensure_ascii=False, indent=2)
        subscription_output = json.dumps(state.get("subscription_output", {}), ensure_ascii=False, indent=2)
        compliance_output = json.dumps(state.get("compliance_output", {}), ensure_ascii=False, indent=2)
        prompt = (
            self._build_context_prompt(state)
            + "\nSubagent outputs:\n"
            + f"GrowthAgent:\n{growth_output}\n\n"
            + f"SubscriptionAgent:\n{subscription_output}\n\n"
            + f"ComplianceAgent:\n{compliance_output}\n\n"
            + "Produce the final PM answer with practical prioritization."
        )

        response, usage = self.llm_client.complete(
            system_prompt=PM_STRATEGIST_SYSTEM,
            user_prompt=prompt,
            temperature=0.2,
            max_completion_tokens=1500,
        )
        token_usage = self._merge_usage(state.get("token_usage", self._usage_dict()), usage)
        return {"final_answer": response, "token_usage": token_usage}

    def run(
        self,
        *,
        user_query: str,
        chat_history: list[dict[str, str]],
        memory_summary: str,
    ) -> OrchestratorResult:
        initial_state: PMState = {
            "user_query": user_query,
            "chat_history": chat_history,
            "memory_summary": memory_summary,
            "token_usage": self._usage_dict(),
        }

        state = self.graph.invoke(initial_state)
        final_answer = state.get("final_answer", "")

        token_usage = state.get("token_usage", self._usage_dict())
        if token_usage.get("total_tokens", 0) == 0:
            fallback = estimate_tokens(final_answer + user_query + memory_summary)
            token_usage = {
                "prompt_tokens": int(fallback * 0.65),
                "completion_tokens": int(fallback * 0.35),
                "total_tokens": fallback,
            }

        return OrchestratorResult(
            final_answer=final_answer,
            active_subagents=state.get("active_subagents", ["pm_strategist"]),
            retrieved_chunks=state.get("retrieved_chunks", []),
            subagent_outputs={
                "growth": state.get("growth_output", ""),
                "subscription": state.get("subscription_output", ""),
                "compliance": state.get("compliance_output", ""),
            },
            token_usage=token_usage,
        )
