"""
Explicit per-layer failure modes — CRITICAL-3 resolution.

Defines whether each safety layer fails OPEN (allow, degraded) or CLOSED
(block, safe) when its service is unreachable. Per ARCHITECTURE-DEBATE.md:
all layers default to fail-CLOSED for safety-critical operations.

Layer 1 (Input Guard): Fail CLOSED — block message if classifier unavailable
Layer 2 (CaMeL): Fail CLOSED — structural separation has no external dependency
Layer 3 (NeMo): Fail CLOSED for tool calls, fail OPEN for output filtering
Layer 4 (Progent): Fail CLOSED — deny if SMT solver cannot verify

Circuit breaker: if a layer fails >5 times in 60 seconds, enter degraded mode.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class FailureMode(str, Enum):
    """What happens when a safety layer is unreachable."""
    FAIL_CLOSED = "fail_closed"  # Block operation (safe)
    FAIL_OPEN = "fail_open"      # Allow operation (degraded — use sparingly)


class LayerState(str, Enum):
    """Operational state of a safety layer."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Circuit breaker tripped
    DOWN = "down"          # Completely unavailable


@dataclass
class CircuitBreaker:
    """Circuit breaker: trip after `threshold` failures in `window_seconds`."""

    threshold: int = 5
    window_seconds: float = 60.0
    failures: list[float] = field(default_factory=list)

    @property
    def is_tripped(self) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        self.failures = [f for f in self.failures if f > cutoff]
        return len(self.failures) >= self.threshold

    def record_failure(self) -> None:
        self.failures.append(time.time())

    def reset(self) -> None:
        self.failures.clear()


# ── Per-layer failure mode configuration ──────────────────────────────────

LAYER_FAILURE_MODES = {
    # Layer 1: Input Guard (LlamaFirewall)
    # Blocks prompt injection, PII leakage, and code shield violations.
    # If the classifier is unreachable, block the message — safe default.
    "input_guard": {
        "input": FailureMode.FAIL_CLOSED,   # Block input if unavailable
        "output": FailureMode.FAIL_OPEN,    # Allow output (log for async review)
    },

    # Layer 2: CaMeL — Control/data separation
    # Structural separation has no external dependency. If the parser crashes,
    # this is a code bug and must halt — fail CLOSED.
    "camel": {
        "structural": FailureMode.FAIL_CLOSED,  # Halt — this is a code bug
    },

    # Layer 3: NeMo Guardrails — Runtime rails
    # Tool calls are safety-critical (block if guard unavailable).
    # Output filtering is less critical (allow with async review).
    "nemo": {
        "tool_call": FailureMode.FAIL_CLOSED,   # Block tool call
        "output": FailureMode.FAIL_OPEN,        # Allow with async review
    },

    # Layer 4: Progent — Least-privilege SMT policies
    # If the SMT solver cannot verify a tool call, deny it.
    # Never default-allow.
    "progent": {
        "tool_call": FailureMode.FAIL_CLOSED,   # Deny unverified calls
    },
}


def get_failure_mode(layer: str, operation: str) -> FailureMode:
    """Get the failure mode for a specific layer + operation combination.

    Returns FAIL_CLOSED (safe default) if not explicitly configured.
    """
    layer_config = LAYER_FAILURE_MODES.get(layer, {})
    return layer_config.get(operation, FailureMode.FAIL_CLOSED)


def should_block_on_failure(layer: str, operation: str) -> bool:
    """Check whether a specific layer+operation should block on failure."""
    return get_failure_mode(layer, operation) == FailureMode.FAIL_CLOSED
