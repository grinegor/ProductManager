from __future__ import annotations

from .llm import OpenAIClient, UsageStats
from .utils import format_history


MEMORY_SUMMARY_SYSTEM = """
You maintain compact conversation memory for a Senior Product Manager AI.

Produce a short, factual summary that preserves:
- company/business context
- funnel and retention metrics mentioned
- active experiments, decisions, and hypotheses
- constraints and risks

Do not include fluff. Keep it under 180 words.
""".strip()


class ConversationMemory:
    def __init__(self, llm_client: OpenAIClient, refresh_after_messages: int = 8) -> None:
        self.llm_client = llm_client
        self.refresh_after_messages = refresh_after_messages

    def maybe_refresh_summary(
        self,
        history: list[dict[str, str]],
        previous_summary: str,
    ) -> tuple[str, UsageStats]:
        if len(history) < self.refresh_after_messages:
            return previous_summary, UsageStats()

        prompt = (
            "Existing summary:\n"
            f"{previous_summary or '(none)'}\n\n"
            "Recent conversation:\n"
            f"{format_history(history, max_messages=12)}\n\n"
            "Update the summary for future context."
        )
        summary, usage = self.llm_client.complete(
            system_prompt=MEMORY_SUMMARY_SYSTEM,
            user_prompt=prompt,
            temperature=0.1,
            max_completion_tokens=250,
        )
        return summary, usage
