"""Thalamic Gateway — 6-channel salience filter inspired by thalamic sensory gating.

Before any memory enters long-term storage or working memory, it passes through
a "thalamic gateway" that evaluates salience across 6 independent channels.
Only memories that pass the gate threshold are stored; others are discarded
or routed to ephemeral scratch memory.

Channels:
    1. relevance      — How relevant to current goals/tasks?
    2. emotion        — Emotional significance
    3. urgency        — Time-critical?
    4. novelty        — How new/surprising is this?
    5. trust          — Source reliability
    6. goal_affinity  — How aligned with long-term objectives?

Source: Human-Like Lifelong Memory (QufkvHbQs7), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol


class LLMClient(Protocol):
    """Protocol for LLM interaction."""

    async def complete(self, prompt: str) -> str: ...


@dataclass
class ThalamicGateResult:
    """Result of thalamic filtering for a single memory."""

    passed: bool
    channel_scores: dict[str, float]
    average_score: float
    reason: str = ""


@dataclass
class ThalamicGateway:
    """6-channel salience gate inspired by thalamic filtering.

    The gateway evaluates memories across 6 independent cognitive channels. Each channel produces a
    0.0-1.0 score. The composite determines whether the memory reaches long-term storage.

    Default pass threshold is 0.4 (memories with low average salience across all channels are
    discarded).
    """

    CHANNELS = [
        "relevance",
        "emotion",
        "urgency",
        "novelty",
        "trust",
        "goal_affinity",
    ]

    llm: LLMClient
    pass_threshold: float = 0.4

    async def filter(
        self,
        content: str,
        context: dict[str, object] | None = None,
    ) -> ThalamicGateResult:
        """Evaluate memory through 6 cognitive channels.

        Args:
            content: The memory content to evaluate
            context: Optional dict with keys like 'goals', 'source', 'urgency'

        Returns:
            ThalamicGateResult with pass/fail decision and per-channel scores
        """
        ctx = context or {}
        goals = ctx.get("goals", "none specified")
        source = ctx.get("source", "unknown")
        identity = ctx.get("identity", "AI agent")

        prompt = (
            "Evaluate this memory through 6 cognitive channels"
            " (like the thalamus filters sensory input):\n"
            f"Memory: {content[:1500]}\n"
            f"Current goals: {goals}\n"
            f"Agent identity: {identity}\n"
            f"Source: {source}\n"
            "\n"
            "Score each channel 0.0-1.0:\n"
            "- relevance: How relevant is this to current goals/tasks?\n"
            "- emotion: Emotional significance of the content\n"
            "- urgency: How time-sensitive is this information?\n"
            "- novelty: How new/surprising/unexpected is this?\n"
            "- trust: Source reliability (user=1.0, verified=0.8, web=0.5, unknown=0.3)\n"
            "- goal_affinity: How aligned with long-term objectives?\n"
            "\n"
            "Output JSON only:\n"
            "{{\n"
            '    "scores": {{\n'
            '        "relevance": <float>,\n'
            '        "emotion": <float>,\n'
            '        "urgency": <float>,\n'
            '        "novelty": <float>,\n'
            '        "trust": <float>,\n'  # noqa: E501
            '        "goal_affinity": <float>\n'
            '    }},\n'
            '    "pass_through": true/false,\n'
            '    "reason": "brief explanation"\n'
            "}}"
        )

        response = await self.llm.complete(prompt)
        return self._parse_gate_result(response)

    def _parse_gate_result(self, response: str) -> ThalamicGateResult:
        try:
            data = json.loads(_extract_json(response))
        except (json.JSONDecodeError, TypeError):
            return ThalamicGateResult(
                passed=False,
                channel_scores={ch: 0.0 for ch in self.CHANNELS},
                average_score=0.0,
                reason="failed to parse LLM response",
            )

        scores = {ch: float(data.get("scores", {}).get(ch, 0.0)) for ch in self.CHANNELS}
        avg = sum(scores.values()) / len(self.CHANNELS) if self.CHANNELS else 0.0
        passed = bool(data.get("pass_through", avg >= self.pass_threshold))

        return ThalamicGateResult(
            passed=passed,
            channel_scores=scores,
            average_score=round(avg, 4),
            reason=data.get("reason", ""),
        )

    async def batch_filter(
        self,
        memories: list[tuple[str, dict | None]],
    ) -> list[ThalamicGateResult]:
        """Filter multiple memories through the thalamic gateway.

        Args:
            memories: List of (content, context) tuples

        Returns:
            List of ThalamicGateResults, one per input memory
        """
        results = []
        for content, context in memories:
            results.append(await self.filter(content, context))
        return results


def _extract_json(text: str) -> str:
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return text.strip()
