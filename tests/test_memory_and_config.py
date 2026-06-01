from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pm_agent.config import load_settings
from pm_agent.llm import UsageStats
from pm_agent.memory import ConversationMemory


class FakeMemoryLLM:
    def __init__(self):
        self.calls = 0

    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float, max_completion_tokens: int):
        self.calls += 1
        return "updated memory summary", UsageStats(prompt_tokens=7, completion_tokens=3)


class MemoryTests(unittest.TestCase):
    def test_does_not_refresh_before_threshold(self) -> None:
        llm = FakeMemoryLLM()
        memory = ConversationMemory(llm_client=llm, refresh_after_messages=4)
        summary, usage = memory.maybe_refresh_summary(
            history=[{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}],
            previous_summary="prev",
        )
        self.assertEqual(summary, "prev")
        self.assertEqual(usage.total_tokens, 0)
        self.assertEqual(llm.calls, 0)

    def test_refreshes_at_threshold(self) -> None:
        llm = FakeMemoryLLM()
        memory = ConversationMemory(llm_client=llm, refresh_after_messages=2)
        summary, usage = memory.maybe_refresh_summary(
            history=[{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}],
            previous_summary="prev",
        )
        self.assertEqual(summary, "updated memory summary")
        self.assertEqual(usage.total_tokens, 10)
        self.assertEqual(llm.calls, 1)


class ConfigTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_load_settings_requires_api_key(self) -> None:
        with patch("pm_agent.config.load_dotenv", return_value=None):
            with self.assertRaises(ValueError):
                load_settings()

    def test_load_settings_reads_env(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_MODEL": "m1",
                "OPENAI_FALLBACK_MODEL": "m2",
                "OPENAI_REASONING_EFFORT": "high",
                "OPENAI_EMBEDDING_MODEL": "e1",
                "DOCS_DIR": str(Path(td) / "docs"),
                "DATA_DIR": str(Path(td) / "data"),
                "TOP_K": "6",
                "MAX_HISTORY_MESSAGES": "11",
            }
            with patch.dict(os.environ, env, clear=True):
                settings = load_settings()

            self.assertEqual(settings.openai_api_key, "test-key")
            self.assertEqual(settings.openai_model, "m1")
            self.assertEqual(settings.fallback_openai_model, "m2")
            self.assertEqual(settings.openai_reasoning_effort, "high")
            self.assertEqual(settings.embedding_model, "e1")
            self.assertEqual(settings.top_k, 6)
            self.assertEqual(settings.max_history_messages, 11)
            self.assertTrue(settings.data_dir.exists())

    @patch.dict(os.environ, {"DEMO_MODE": "true"}, clear=True)
    def test_load_settings_allows_demo_mode_without_api_key(self) -> None:
        with patch("pm_agent.config.load_dotenv", return_value=None):
            settings = load_settings()

        self.assertTrue(settings.demo_mode)
        self.assertEqual(settings.openai_api_key, "demo-mode-no-api-key")
        self.assertEqual(settings.openai_model, "gpt-5.4")
        self.assertEqual(settings.fallback_openai_model, "gpt-5.4-mini")


if __name__ == "__main__":
    unittest.main()
