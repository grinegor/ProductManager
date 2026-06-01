from __future__ import annotations

from .llm import UsageStats
from .rag import RetrievedChunk


class DemoLLMClient:
    """Deterministic local client for portfolio demos without OpenAI calls."""

    active_model = "demo-local"

    def __init__(self) -> None:
        self.model = "demo-local"
        self.fallback_model = ""
        self.embedding_model = "demo-local-embeddings"

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_completion_tokens: int = 900,
    ) -> tuple[str, UsageStats]:
        if "GrowthAgent" in system_prompt:
            return (
                '{"agent":"GrowthAgent","summary":"Activation and checkout friction are likely constraining paid growth efficiency.",'
                '"key_findings":["Quiz completion and checkout conversion should be segmented by channel and offer.","Faster D0-D3 first value can improve both conversion confidence and retention."],'
                '"recommendations":[{"title":"Instrument funnel drop-off by channel and offer","rationale":"CAC decisions are unreliable without stage-level conversion visibility.","expected_impact":"High","effort":"S","success_metric":"Checkout CVR and CAC by cohort"},{"title":"Shorten first-value path","rationale":"Weight-loss subscriptions retain better when users see a concrete plan quickly.","expected_impact":"High","effort":"M","success_metric":"D1/D7 activation"}],'
                '"assumptions":["Paid social is the main acquisition channel."],"compliance_flags":[],"experiments":[{"hypothesis":"Reducing quiz friction increases checkout starts without lowering paid conversion quality.","metric":"Quiz completion rate","guardrail_metric":"Refund rate","decision_rule":"+10% completion with flat or better checkout CVR"}]}',
                UsageStats(prompt_tokens=520, completion_tokens=170),
            )

        if "SubscriptionAgent" in system_prompt:
            return (
                '{"agent":"SubscriptionAgent","summary":"The strongest economics lever is reducing month-1 churn before scaling spend.",'
                '"key_findings":["Payback should be measured on contribution margin, not revenue.","The first renewal is the highest-risk lifecycle moment."],'
                '"recommendations":[{"title":"Build first-renewal retention dashboard","rationale":"Cohort payback depends on D0-D30 activation and refund behavior.","expected_impact":"High","effort":"S","success_metric":"Payback P50/P75 and month-1 churn"},{"title":"Test transparent billing copy","rationale":"Clear renewal expectations can reduce refunds and support tickets.","expected_impact":"Medium","effort":"S","success_metric":"Refund rate and first renewal retention"}],'
                '"assumptions":["The product uses a monthly subscription after a trial or intro offer."],"compliance_flags":[],"experiments":[{"hypothesis":"Transparent renewal framing improves trust without materially reducing paid conversion.","metric":"First renewal retention","guardrail_metric":"Checkout CVR","decision_rule":"Ship if refunds fall and checkout CVR drops less than 3%"}]}',
                UsageStats(prompt_tokens=480, completion_tokens=155),
            )

        if "ComplianceAgent" in system_prompt:
            return (
                '{"agent":"ComplianceAgent","summary":"Messaging should avoid guaranteed outcomes and personal-attribute targeting.",'
                '"key_findings":["Health claims need qualification and substantiation.","Telehealth copy should not imply prescription eligibility is guaranteed."],'
                '"recommendations":[{"title":"Rewrite outcome claims as support claims","rationale":"Policy-safe language preserves conversion intent while reducing ad risk.","expected_impact":"Medium","effort":"S","success_metric":"Ad approval rate"}],'
                '"assumptions":[],"compliance_flags":["Avoid guaranteed weight-loss claims.","Avoid implying the viewer has obesity or a medical condition."],"experiments":[]}',
                UsageStats(prompt_tokens=360, completion_tokens=105),
            )

        return (
            "1. Executive Recommendation\n"
            "Focus the MVP on one measurable loop: acquire qualified users, get them to a credible first plan within D0-D3, and measure whether that improves first-renewal retention before scaling spend.\n\n"
            "2. Diagnosis\n"
            "The likely bottleneck is not only acquisition cost. It is the combined effect of funnel friction, unclear renewal expectations, and weak early activation. Optimize CAC against contribution-margin payback, segmented by channel, offer, and plan.\n\n"
            "3. Prioritized Action Plan\n"
            "P0: Instrument quiz to checkout to first renewal by cohort. Success metrics: CAC, checkout CVR, month-1 churn.\n"
            "P1: Improve D0-D3 first value. Success metrics: D1/D7 activation and first renewal retention.\n"
            "P2: Rewrite billing and outcome claims. Success metrics: refund rate and ad approval rate.\n\n"
            "4. Compliance Guardrails\n"
            "Avoid guaranteed weight-loss claims, medical promises, and copy that implies the viewer has a condition. Use qualified language such as designed to support, results vary, and eligibility is determined by a licensed provider.\n\n"
            "5. Next 14 Days\n"
            "Ship instrumentation, run one onboarding simplification test, and review ad/landing claims before increasing paid spend.",
            UsageStats(prompt_tokens=900, completion_tokens=330),
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text) % 17 + 1), float(text.lower().count("retention") + 1)] for text in texts]


class DemoRAGStore:
    def __init__(self) -> None:
        self._chunks = [
            RetrievedChunk(
                chunk_id=0,
                source="docs/growth/activation_framework.md",
                text="Activation should be measured by the first meaningful action that predicts retention, not by account creation alone.",
                score=0.91,
            ),
            RetrievedChunk(
                chunk_id=1,
                source="docs/retention/retention_playbook.md",
                text="Segment churn by channel, offer, cohort, tenure, usage, refund reason, and first-value completion.",
                score=0.87,
            ),
            RetrievedChunk(
                chunk_id=2,
                source="docs/compliance/ad_policy_guardrails.md",
                text="Avoid guaranteed health outcomes, personal-attribute targeting, and unsubstantiated weight-loss claims.",
                score=0.82,
            ),
        ]

    def has_index(self) -> bool:
        return True

    def build_from_docs(self) -> dict[str, int]:
        return {"documents": 3, "chunks": len(self._chunks)}

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        return self._chunks[: top_k or len(self._chunks)]
