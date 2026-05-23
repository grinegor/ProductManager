from __future__ import annotations

import unittest
from types import SimpleNamespace

import httpx
from openai import BadRequestError, NotFoundError

from pm_agent.llm import OpenAIClient


class FakeCompletions:
    def __init__(self, behaviors):
        self.behaviors = list(behaviors)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.behaviors:
            raise AssertionError("No behavior left for completion call")
        behavior = self.behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


class FakeEmbeddings:
    def create(self, **kwargs):
        return SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, 2.0, 3.0])])


class FakeOpenAIInnerClient:
    def __init__(self, completion_behaviors):
        self.chat = SimpleNamespace(completions=FakeCompletions(completion_behaviors))
        self.embeddings = FakeEmbeddings()


def fake_response(content: str, prompt_tokens: int = 10, completion_tokens: int = 5):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


def bad_request(message: str) -> BadRequestError:
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    resp = httpx.Response(400, request=req)
    return BadRequestError(message, response=resp, body={"error": {"message": message}})


def not_found(message: str) -> NotFoundError:
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    resp = httpx.Response(404, request=req)
    return NotFoundError(message, response=resp, body={"error": {"message": message}})


class OpenAIClientTests(unittest.TestCase):
    def make_client(self, behaviors, fallback_model: str = "") -> OpenAIClient:
        client = OpenAIClient(
            api_key="test",
            model="primary-model",
            embedding_model="embed-model",
            fallback_model=fallback_model,
            reasoning_effort="high",
        )
        client.client = FakeOpenAIInnerClient(behaviors)
        return client

    def test_temperature_retry_removes_temperature(self) -> None:
        behavior = [
            bad_request("Unsupported value: 'temperature' does not support 0.2 with this model. Only the default (1) value is supported."),
            fake_response("ok"),
        ]
        client = self.make_client(behavior)

        text, _ = client.complete(system_prompt="sys", user_prompt="usr", temperature=0.2, max_completion_tokens=100)
        self.assertEqual(text, "ok")

        calls = client.client.chat.completions.calls
        self.assertEqual(len(calls), 2)
        self.assertIn("temperature", calls[0])
        self.assertNotIn("temperature", calls[1])

    def test_max_tokens_retry_expands_budget(self) -> None:
        behavior = [
            bad_request("Could not finish the message because max_tokens or model output limit was reached. Please try again with higher max_tokens."),
            fake_response("ok"),
        ]
        client = self.make_client(behavior)

        text, _ = client.complete(system_prompt="sys", user_prompt="usr", max_completion_tokens=300)
        self.assertEqual(text, "ok")

        calls = client.client.chat.completions.calls
        self.assertEqual(len(calls), 2)
        self.assertGreaterEqual(calls[1]["max_completion_tokens"], 700)

    def test_max_tokens_second_retry_forces_concise(self) -> None:
        behavior = [
            bad_request("Could not finish the message because max_tokens or model output limit was reached. Please try again with higher max_tokens."),
            bad_request("Could not finish the message because max_tokens or model output limit was reached. Please try again with higher max_tokens."),
            fake_response("short answer"),
        ]
        client = self.make_client(behavior)

        text, _ = client.complete(system_prompt="sys", user_prompt="very long", max_completion_tokens=300)
        self.assertEqual(text, "short answer")

        calls = client.client.chat.completions.calls
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[2]["max_completion_tokens"], 500)
        self.assertIn("IMPORTANT: Keep the response concise", calls[2]["messages"][1]["content"])

    def test_fallback_model_used_on_not_found(self) -> None:
        behavior = [
            not_found("model not found"),
            fake_response("fallback response"),
        ]
        client = self.make_client(behavior, fallback_model="fallback-model")

        text, _ = client.complete(system_prompt="sys", user_prompt="usr")
        self.assertEqual(text, "fallback response")
        self.assertEqual(client.active_model, "fallback-model")

        calls = client.client.chat.completions.calls
        self.assertEqual(calls[0]["model"], "primary-model")
        self.assertEqual(calls[1]["model"], "fallback-model")


if __name__ == "__main__":
    unittest.main()
