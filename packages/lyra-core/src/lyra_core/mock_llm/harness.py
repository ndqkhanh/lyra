"""Scripted LLM test double — deterministic, zero-network."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator

__all__ = [
    "MockLLMError",
    "ScenarioCase",
    "ScriptedLLM",
    "StreamChunk",
]


class MockLLMError(Exception):
    """Raised when the script and the actual call sequence diverge."""


@dataclass(frozen=True)
class StreamChunk:
    delta: str
    stop_reason: str | None = None
    tool_calls: tuple[dict[str, Any], ...] = ()


@dataclass
class ScenarioCase:
    """One full ``(messages -> response)`` turn in a scenario script."""

    expected_user_substring: str
    response: dict[str, Any]
    stream: tuple[StreamChunk, ...] = ()


@dataclass
class ScriptedLLM:
    """LLM-shaped object that replays a scripted sequence of turns."""

    scenario: list[ScenarioCase]
    calls: list[dict[str, Any]] = field(default_factory=list)
    strict: bool = True

    def generate(self, *, messages: list[dict[str, Any]], tools=None, **kwargs):
        self.calls.append({"messages": messages, "tools": tools, "kwargs": kwargs})
        if not self.scenario:
            raise MockLLMError(
                "scripted LLM exhausted; agent made more calls than the "
                "scenario declared"
            )
        case = self.scenario.pop(0)
        if self.strict and case.expected_user_substring:
            last_user = next(
                (m for m in reversed(messages) if m.get("role") == "user"),
                None,
            )
            if last_user is None:
                raise MockLLMError(
                    "scripted LLM expected a user message but got none"
                )
            content = last_user.get("content") or ""
            if isinstance(content, list):
                content = " ".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                )
            if case.expected_user_substring not in content:
                raise MockLLMError(
                    f"scripted LLM expected user substring "
                    f"{case.expected_user_substring!r} but got {content!r}"
                )
        return case.response

    def stream_generate(
        self, *, messages: list[dict[str, Any]], tools=None, **kwargs
    ) -> Iterator[StreamChunk]:
        self.calls.append({"messages": messages, "tools": tools, "kwargs": kwargs})
        if not self.scenario:
            raise MockLLMError(
                "scripted LLM exhausted (stream); scenario ran out of cases"
            )
        case = self.scenario.pop(0)
        if not case.stream:
            raise MockLLMError(
                "scripted case has no stream chunks; use generate() instead"
            )
        yield from case.stream

    def assert_exhausted(self) -> None:
        """Assert that every scripted case was consumed."""
        if self.scenario:
            remaining = [c.expected_user_substring for c in self.scenario]
            raise MockLLMError(
                f"scripted LLM has unused cases: {remaining}"
            )
