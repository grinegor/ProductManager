from __future__ import annotations

from typing import Iterable


def estimate_tokens(text: str) -> int:
    # Fast approximation for budgeting/debug panel purposes.
    if not text:
        return 0
    return max(1, int(len(text) / 4))


def estimate_message_tokens(messages: Iterable[dict[str, str]]) -> int:
    return sum(estimate_tokens(m.get("content", "")) + 6 for m in messages)


def format_history(messages: list[dict[str, str]], max_messages: int = 8) -> str:
    clipped = messages[-max_messages:]
    if not clipped:
        return "(none)"
    lines: list[str] = []
    for message in clipped:
        role = message.get("role", "user").upper()
        content = message.get("content", "").strip()
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
