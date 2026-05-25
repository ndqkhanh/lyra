"""Token usage tracking across agents and models."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class TokenUsage:
    """Records token usage for a single agent operation."""

    agent_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    timestamp: float


@dataclass(frozen=True)
class TokenSummary:
    """Aggregated token usage summary."""

    total_prompt: int
    total_completion: int
    total_tokens: int
    by_model: Tuple[Tuple[str, int], ...] = ()
    by_agent: Tuple[Tuple[str, int], ...] = ()
    window_seconds: float = 3600.0


@dataclass(frozen=True)
class TokenAlert:
    """Alert raised when token usage exceeds a threshold."""

    alert_type: str
    message: str
    threshold: int
    current_usage: int
    timestamp: float


class TokenTracker:
    """Tracks token usage across agents and models, with alert thresholds."""

    def __init__(self) -> None:
        self._usage_history: List[TokenUsage] = []
        self._alert_threshold: int | None = None

    async def record_usage(
        self,
        agent_id: str,
        model: str,
        prompt: int,
        completion: int,
    ) -> TokenUsage:
        """Record a token usage entry."""
        usage = TokenUsage(
            agent_id=agent_id,
            model=model,
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion,
            timestamp=time.time(),
        )
        self._usage_history.append(usage)
        return usage

    async def get_usage_summary(
        self,
        window_seconds: float = 3600.0,
    ) -> TokenSummary:
        """Get aggregated token usage summary for a time window."""
        now = time.time()
        cutoff = now - window_seconds

        recent = [u for u in self._usage_history if u.timestamp >= cutoff]

        total_prompt = sum(u.prompt_tokens for u in recent)
        total_completion = sum(u.completion_tokens for u in recent)
        total_tokens = total_prompt + total_completion

        # By model
        model_totals: Dict[str, int] = {}
        for u in recent:
            model_totals[u.model] = model_totals.get(u.model, 0) + u.total_tokens

        # By agent
        agent_totals: Dict[str, int] = {}
        for u in recent:
            agent_totals[u.agent_id] = agent_totals.get(u.agent_id, 0) + u.total_tokens

        return TokenSummary(
            total_prompt=total_prompt,
            total_completion=total_completion,
            total_tokens=total_tokens,
            by_model=tuple(sorted(model_totals.items())),
            by_agent=tuple(sorted(agent_totals.items())),
            window_seconds=window_seconds,
        )

    async def set_alert_threshold(self, max_tokens: int) -> None:
        """Set the alert threshold for token usage within the current window."""
        self._alert_threshold = max_tokens

    async def check_alerts(self) -> Tuple[TokenAlert, ...]:
        """Check if any alert thresholds have been exceeded."""
        if self._alert_threshold is None:
            return ()

        now = time.time()
        alerts: List[TokenAlert] = []

        # Check total tokens in the last hour
        window = 3600.0
        cutoff = now - window
        recent = [u for u in self._usage_history if u.timestamp >= cutoff]
        current_total = sum(u.total_tokens for u in recent)

        if self._alert_threshold is not None and current_total > self._alert_threshold:
            alerts.append(
                TokenAlert(
                    alert_type="threshold_exceeded",
                    message=f"Total token usage {current_total} exceeds threshold {self._alert_threshold}",
                    threshold=self._alert_threshold,
                    current_usage=current_total,
                    timestamp=now,
                )
            )

        return tuple(alerts)

    async def get_usage_history(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> Tuple[TokenUsage, ...]:
        """Get recent token usage history for a specific agent."""
        filtered = [u for u in self._usage_history if u.agent_id == agent_id]
        return tuple(filtered[-limit:])
