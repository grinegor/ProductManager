from __future__ import annotations

import unittest

from pm_agent.utils import estimate_message_tokens, estimate_tokens, format_history


class UtilsTests(unittest.TestCase):
    def test_estimate_tokens_handles_empty(self) -> None:
        self.assertEqual(estimate_tokens(""), 0)

    def test_estimate_tokens_minimum_one_for_non_empty(self) -> None:
        self.assertEqual(estimate_tokens("a"), 1)

    def test_estimate_message_tokens_adds_per_message_overhead(self) -> None:
        messages = [{"role": "user", "content": "abcd"}, {"role": "assistant", "content": "12345678"}]
        # 1 + 6, 2 + 6
        self.assertEqual(estimate_message_tokens(messages), 15)

    def test_format_history_clips_to_max_messages(self) -> None:
        messages = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
        ]
        out = format_history(messages, max_messages=2)
        self.assertEqual(out, "ASSISTANT: a1\nUSER: q2")

    def test_format_history_empty(self) -> None:
        self.assertEqual(format_history([], max_messages=3), "(none)")


if __name__ == "__main__":
    unittest.main()
