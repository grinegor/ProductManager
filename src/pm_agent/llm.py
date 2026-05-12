from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import BadRequestError
from openai import NotFoundError
from openai import OpenAI


@dataclass
class UsageStats:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        embedding_model: str,
        fallback_model: str = "",
        reasoning_effort: str = "high",
    ) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.fallback_model = fallback_model
        self.active_model = model
        self.reasoning_effort = reasoning_effort
        self.embedding_model = embedding_model

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_completion_tokens: int = 900,
    ) -> tuple[str, UsageStats]:
        completion_kwargs: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_completion_tokens": max_completion_tokens,
        }
        if self.reasoning_effort:
            completion_kwargs["reasoning_effort"] = self.reasoning_effort

        def run_with_compat_retries(model_name: str, kwargs: dict[str, Any]):
            local_kwargs = dict(kwargs)
            tried_expand = False
            tried_concise = False

            while True:
                try:
                    return self.client.chat.completions.create(
                        model=model_name,
                        **local_kwargs,
                    )
                except BadRequestError as exc:
                    msg = str(exc)
                    if "temperature" in msg and "Only the default (1) value is supported" in msg:
                        local_kwargs.pop("temperature", None)
                        continue
                    if "max_tokens or model output limit was reached" in msg:
                        # First retry: give model more completion room.
                        if not tried_expand:
                            local_kwargs["max_completion_tokens"] = int(
                                max(local_kwargs.get("max_completion_tokens", 0) * 2, 700)
                            )
                            tried_expand = True
                            continue
                        # Second retry: force concise answer to fit model output limits.
                        if not tried_concise:
                            messages = list(local_kwargs.get("messages", []))
                            if messages and messages[-1].get("role") == "user":
                                messages[-1] = {
                                    "role": "user",
                                    "content": (
                                        f"{messages[-1].get('content', '')}\n\n"
                                        "IMPORTANT: Keep the response concise. "
                                        "Max 6 bullets, no long explanations."
                                    ),
                                }
                            local_kwargs["messages"] = messages
                            local_kwargs["max_completion_tokens"] = 500
                            tried_concise = True
                            continue
                    raise

        try:
            response = run_with_compat_retries(self.model, completion_kwargs)
            self.active_model = self.model
        except NotFoundError:
            if not self.fallback_model:
                raise
            response = run_with_compat_retries(self.fallback_model, completion_kwargs)
            self.active_model = self.fallback_model

        text = response.choices[0].message.content or ""
        usage = UsageStats(
            prompt_tokens=getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
            completion_tokens=getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
        )
        return text.strip(), usage

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.embedding_model, input=texts)
        # API returns embeddings in original order.
        return [item.embedding for item in response.data]

    @staticmethod
    def usage_to_dict(usage: UsageStats) -> dict[str, int]:
        return {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }

    @staticmethod
    def add_usage(accumulator: dict[str, int], usage: UsageStats | dict[str, Any]) -> dict[str, int]:
        if isinstance(usage, UsageStats):
            prompt = usage.prompt_tokens
            completion = usage.completion_tokens
        else:
            prompt = int(usage.get("prompt_tokens", 0))
            completion = int(usage.get("completion_tokens", 0))

        accumulator["prompt_tokens"] = accumulator.get("prompt_tokens", 0) + prompt
        accumulator["completion_tokens"] = accumulator.get("completion_tokens", 0) + completion
        accumulator["total_tokens"] = accumulator.get("total_tokens", 0) + prompt + completion
        return accumulator
