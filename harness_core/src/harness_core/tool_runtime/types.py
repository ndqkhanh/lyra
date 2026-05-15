"""Types for tool_runtime — ToolExecution result record + retry Protocol."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

from ..messages import ToolResult
from ..verifier import CompositeVerdict


@dataclass(frozen=True)
class ToolExecution:
    """Single guarded tool invocation — full audit record.

    A ToolExecution is the output of :meth:`ToolEngine.execute`. It captures
    *what was called*, *what the gates decided*, *what the tool returned*, and
    *what it cost* — enough for audit replay or cost attribution.

    Fields:
        call_id: ToolCall.id (passes through from the original call).
        tool_name: ToolCall.name.
        args: ToolCall.args (a copy).
        result: Final :class:`ToolResult`. If gates blocked the call, this
            carries an error indicating the block reason.
        verdict: Pre-call composite verdict from the verifier composer
            (None if no composer was wired).
        cost_usd: Cost recorded for this call (0.0 if no tracker wired).
        duration_ms: Wall-clock time across all attempts (excludes retry sleep).
        n_attempts: 1 on success-without-retry; up to retry.max_attempts.
        witness_id: TOOL_RESULT witness ID (empty if no lattice wired).
        verdict_witness_id: VERIFIER_VERDICT witness ID (empty if no
            composer/lattice wired).
        blocked_by_verdict: True when the verifier composer blocked the call.
        blocked_by_budget: True when budget reservation failed before the call.
        retried_errors: Per-attempt error strings that triggered a retry.
    """

    call_id: str
    tool_name: str
    args: dict[str, Any]
    result: ToolResult
    verdict: Optional[CompositeVerdict] = None
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    n_attempts: int = 1
    witness_id: str = ""
    verdict_witness_id: str = ""
    blocked_by_verdict: bool = False
    blocked_by_budget: bool = False
    retried_errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def succeeded(self) -> bool:
        """True iff the tool ran and returned without error."""
        return (
            not self.blocked_by_verdict
            and not self.blocked_by_budget
            and not self.result.is_error
        )

    @property
    def blocked(self) -> bool:
        """True iff a pre-call gate prevented execution."""
        return self.blocked_by_verdict or self.blocked_by_budget


class RetryPolicy(Protocol):
    """Strategy for deciding whether and how long to wait before retrying."""

    max_attempts: int

    def should_retry(self, *, attempt: int, error: str) -> bool:
        """``attempt`` is 1-indexed; the call has just failed for that attempt."""
        ...

    def delay_seconds(self, *, attempt: int) -> float:
        """Sleep duration before the next attempt (after ``attempt`` failed)."""
        ...


__all__ = ["RetryPolicy", "ToolExecution"]
