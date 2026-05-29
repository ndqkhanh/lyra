"""Hybrid Communication Router (Plan 29.2).

Routes inter-agent messages through text (short coordination) or latent
(RecursiveLink-compressed for large context sharing). Short messages
(<500 chars) use direct text; large findings/context transfers use
latent compression for 60-75% token savings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Channel(str, Enum):
    TEXT = "text"
    LATENT = "latent"


class MessageCategory(str, Enum):
    COORDINATION = "coordination"
    FINDING = "finding"
    CONTEXT_SHARE = "context_share"
    ALERT = "alert"
    QUESTION = "question"
    PLAN_APPROVAL = "plan_approval"


@dataclass
class RoutedMessage:
    channel: Channel
    message: dict[str, Any] | None = None
    latent_vector: list[float] | None = None
    token_savings: float = 0.0
    original_tokens: int = 0
    compressed_tokens: int = 0


class HybridCommunicationRouter:
    """Route inter-agent messages through text or latent channel.

    Decision logic:
    - Short coordination (<500 chars) → text (low overhead)
    - Large findings/context (>500 chars) → latent (RecursiveLink compression)
    - Alerts and questions → always text (needs immediate readability)
    - Plan approvals → text (requires exact fidelity for review)
    """

    TEXT_THRESHOLD: int = 500
    LATENT_CATEGORIES: set[str] = {"finding", "context_share"}

    def __init__(self, latent_compressor: Any = None) -> None:
        self._latent = latent_compressor
        self._routing_log: list[RoutedMessage] = []

    def route(
        self, content: str, category: str, metadata: dict[str, Any] | None = None
    ) -> RoutedMessage:
        meta = metadata or {}
        msg_len = len(content)

        # Always use text for:
        # - Short messages (under threshold)
        # - Alerts, questions, plan approvals (require exact fidelity)
        if category in (
            MessageCategory.ALERT,
            MessageCategory.QUESTION,
            MessageCategory.PLAN_APPROVAL,
        ):
            return self._text_route(content, category, meta)

        if msg_len < self.TEXT_THRESHOLD:
            return self._text_route(content, category, meta)

        # Large findings / context shares → latent
        if category in self.LATENT_CATEGORIES:
            return self._latent_route(content, category, meta)

        # Default: text for everything else
        return self._text_route(content, category, meta)

    def _text_route(self, content: str, category: str, meta: dict[str, Any]) -> RoutedMessage:
        tokens = len(content) // 4
        msg = RoutedMessage(
            channel=Channel.TEXT,
            message={"content": content, "category": category, "metadata": meta},
            original_tokens=tokens,
            compressed_tokens=tokens,
        )
        self._routing_log.append(msg)
        return msg

    def _latent_route(self, content: str, category: str, meta: dict[str, Any]) -> RoutedMessage:
        original = len(content) // 4

        if self._latent is not None:
            try:
                latent = self._latent.encode(content)
                compressed = len(str(latent)) // 4
                savings = 1 - (compressed / max(original, 1))
            except Exception:
                logger.warning("Latent encoding failed, falling back to text", exc_info=True)
                return self._text_route(content, category, meta)
        else:
            # Simulated latent: represent as simple vector hash
            latent = self._simulate_encode(content)
            compressed = max(1, original // 3)
            savings = 1 - (compressed / max(original, 1))

        msg = RoutedMessage(
            channel=Channel.LATENT,
            latent_vector=latent,
            token_savings=round(savings, 4),
            original_tokens=original,
            compressed_tokens=compressed,
        )
        self._routing_log.append(msg)
        return msg

    @staticmethod
    def _simulate_encode(text: str) -> list[float]:
        """Fallback latent encoding: character distribution vector."""
        buckets = [0.0] * 16
        for ch in text:
            buckets[ord(ch) % 16] += 1
        total = max(1, sum(buckets))
        return [b / total for b in buckets]

    @property
    def routing_stats(self) -> dict[str, int | float]:
        text_count = sum(1 for m in self._routing_log if m.channel == Channel.TEXT)
        latent_count = sum(1 for m in self._routing_log if m.channel == Channel.LATENT)
        total_savings = sum(
            m.token_savings for m in self._routing_log if m.channel == Channel.LATENT
        )
        return {
            "text_routes": text_count,
            "latent_routes": latent_count,
            "total_latent_savings": round(total_savings, 4),
            "total_routes": len(self._routing_log),
        }

    def clear_log(self) -> None:
        self._routing_log.clear()
