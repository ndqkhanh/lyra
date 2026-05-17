"""Core data models for Auto-Spec-Kit."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Phase = Literal[
    "idle",
    "constitution_check",
    "drafting_spec",
    "drafting_plan",
    "drafting_tasks",
    "writing_disk",
    "executing",
    "cancelled",
    "failed",
]


@dataclass(frozen=True)
class Verdict:
    """Result of spec-worthiness detection."""
    spec_worthy: bool
    confidence: float  # 0.0 to 1.0
    reasoning: str
    exemption_reason: str | None = None
    latency_ms: float = 0.0


@dataclass
class SpecKitState:
    """In-memory state for spec-kit flow."""
    phase: Phase = "idle"
    spec_draft: str = ""
    plan_draft: str = ""
    tasks_draft: str = ""
    constitution_draft: str = ""
    feature_id: str | None = None
    original_prompt: str = ""
    error_message: str | None = None


@dataclass(frozen=True)
class InterceptResult:
    """Result of orchestrator.maybe_intercept()."""
    intercepted: bool
    feature_id: str | None = None
    error: str | None = None
