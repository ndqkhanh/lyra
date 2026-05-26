"""Phase 2.2 — 5-Slot Model Router.

Routes tasks to the optimal model slot based on task characteristics,
cost constraints, and slot health. Five specialized slots:

  NORMAL   — General-purpose coding (Sonnet-class)
  THINKING — Deep reasoning, architecture, planning (Opus-class)
  COMPACT  — Quick lookups, simple edits (Haiku-class)
  CRITIQUE — Code review, verification, testing
  VLM      — Vision tasks, screenshots, diagrams
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
class ModelSlot(Enum):
    """Five specialized model dispatch slots."""

    NORMAL = "normal"       # General-purpose coding
    THINKING = "thinking"   # Deep reasoning, planning
    COMPACT = "compact"     # Quick lookups, simple edits
    CRITIQUE = "critique"   # Review, verification
    VLM = "vlm"             # Vision / multimodal


class SlotHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SlotConfig:
    """Configuration for a single model slot."""

    slot: ModelSlot
    cost_multiplier: float          # Relative to NORMAL baseline (1.0)
    max_tokens: int                 # Context window ceiling
    default_temperature: float
    supports_vision: bool
    supports_extended_thinking: bool


@dataclass(frozen=True)
class RoutingDecision:
    """Result of model routing for a task."""

    decision_id: str
    task_description: str
    primary_slot: ModelSlot
    fallback_slot: ModelSlot | None
    reasoning: str
    estimated_cost_multiplier: float
    timestamp: float


@dataclass
class SlotHealthStatus:
    """Runtime health tracking for a slot."""

    slot: ModelSlot
    health: SlotHealth = SlotHealth.HEALTHY
    error_count: int = 0
    avg_latency_ms: float = 0.0
    last_error: str | None = None
    last_checked: float = field(default_factory=time.time)

    def record_success(self, latency_ms: float) -> None:
        self.avg_latency_ms = (self.avg_latency_ms * 0.7) + (latency_ms * 0.3)
        self.error_count = max(0, self.error_count - 1)
        self._recalculate_health()

    def record_error(self, error: str) -> None:
        self.error_count += 1
        self.last_error = error
        self.last_checked = time.time()
        self._recalculate_health()

    def _recalculate_health(self) -> None:
        if self.error_count >= 5:
            self.health = SlotHealth.UNAVAILABLE
        elif self.error_count >= 2:
            self.health = SlotHealth.DEGRADED
        else:
            self.health = SlotHealth.HEALTHY


_DEFAULT_SLOT_CONFIGS: dict[ModelSlot, SlotConfig] = {
    ModelSlot.NORMAL: SlotConfig(
        slot=ModelSlot.NORMAL,
        cost_multiplier=1.0,
        max_tokens=200_000,
        default_temperature=0.3,
        supports_vision=False,
        supports_extended_thinking=False,
    ),
    ModelSlot.THINKING: SlotConfig(
        slot=ModelSlot.THINKING,
        cost_multiplier=3.0,
        max_tokens=200_000,
        default_temperature=0.5,
        supports_vision=False,
        supports_extended_thinking=True,
    ),
    ModelSlot.COMPACT: SlotConfig(
        slot=ModelSlot.COMPACT,
        cost_multiplier=0.33,
        max_tokens=200_000,
        default_temperature=0.1,
        supports_vision=False,
        supports_extended_thinking=False,
    ),
    ModelSlot.CRITIQUE: SlotConfig(
        slot=ModelSlot.CRITIQUE,
        cost_multiplier=1.0,
        max_tokens=200_000,
        default_temperature=0.1,
        supports_vision=False,
        supports_extended_thinking=False,
    ),
    ModelSlot.VLM: SlotConfig(
        slot=ModelSlot.VLM,
        cost_multiplier=1.5,
        max_tokens=200_000,
        default_temperature=0.3,
        supports_vision=True,
        supports_extended_thinking=False,
    ),
}

# ── Task-type → slot mapping ──────────────────────────────────────────

_TASK_TYPE_MAP: dict[str, ModelSlot] = {
    "implement": ModelSlot.NORMAL,
    "refactor": ModelSlot.NORMAL,
    "debug": ModelSlot.NORMAL,
    "test": ModelSlot.CRITIQUE,
    "review": ModelSlot.CRITIQUE,
    "verify": ModelSlot.CRITIQUE,
    "architect": ModelSlot.THINKING,
    "design": ModelSlot.THINKING,
    "plan": ModelSlot.THINKING,
    "research": ModelSlot.THINKING,
    "analyze": ModelSlot.THINKING,
    "lookup": ModelSlot.COMPACT,
    "quick": ModelSlot.COMPACT,
    "simple": ModelSlot.COMPACT,
    "edit": ModelSlot.COMPACT,
    "fix_typo": ModelSlot.COMPACT,
    "screenshot": ModelSlot.VLM,
    "image": ModelSlot.VLM,
    "vision": ModelSlot.VLM,
    "diagram": ModelSlot.VLM,
    "ui_review": ModelSlot.VLM,
}

_COST_AWARE_SLOT_ORDER: tuple[ModelSlot, ...] = (
    ModelSlot.COMPACT,
    ModelSlot.NORMAL,
    ModelSlot.CRITIQUE,
    ModelSlot.VLM,
    ModelSlot.THINKING,
)


# Priority ordering: VLM first, then COMPACT, then THINKING, then rest
_PRIORITY_KEYWORDS: tuple[tuple[str, ModelSlot], ...] = (
    # VLM keywords (check first — overrides "analyze" match)
    ("screenshot", ModelSlot.VLM),
    ("image", ModelSlot.VLM),
    ("vision", ModelSlot.VLM),
    ("diagram", ModelSlot.VLM),
    ("ui_review", ModelSlot.VLM),
    # COMPACT keywords
    ("fix_typo", ModelSlot.COMPACT),
    ("lookup", ModelSlot.COMPACT),
    ("quick", ModelSlot.COMPACT),
    ("simple", ModelSlot.COMPACT),
    ("edit", ModelSlot.COMPACT),
    # THINKING keywords
    ("architect", ModelSlot.THINKING),
    ("design", ModelSlot.THINKING),
    ("plan", ModelSlot.THINKING),
    ("research", ModelSlot.THINKING),
    ("analyze", ModelSlot.THINKING),
    # CRITIQUE keywords
    ("test", ModelSlot.CRITIQUE),
    ("review", ModelSlot.CRITIQUE),
    ("verify", ModelSlot.CRITIQUE),
    # NORMAL keywords (default)
    ("implement", ModelSlot.NORMAL),
    ("refactor", ModelSlot.NORMAL),
    ("debug", ModelSlot.NORMAL),
)


def _classify_task_type(task: str) -> str:
    """Map a task description to a canonical task type."""
    task_lower = task.lower()
    for keyword, _ in _PRIORITY_KEYWORDS:
        if keyword in task_lower:
            return keyword
    return "implement"


def _find_fallback(
    primary: ModelSlot,
    health: dict[ModelSlot, SlotHealthStatus],
) -> ModelSlot | None:
    """Find the cheapest healthy alternative to the primary slot."""
    primary_idx = _COST_AWARE_SLOT_ORDER.index(primary)
    for slot in _COST_AWARE_SLOT_ORDER[primary_idx + 1:]:
        if health.get(slot, SlotHealthStatus(slot)).health != SlotHealth.UNAVAILABLE:
            return slot
    for slot in _COST_AWARE_SLOT_ORDER[:primary_idx]:
        if health.get(slot, SlotHealthStatus(slot)).health != SlotHealth.UNAVAILABLE:
            return slot
    return None


@dataclass
class ModelRouter:
    """Routes tasks to the optimal model slot based on task type,
    budget constraints, and slot health.

    Usage::

        router = ModelRouter()
        decision = router.route("Implement a login page")
        print(f"Routing to {decision.primary_slot.value}")

        # With budget constraint
        decision = router.route(
            "Quick typo fix in README",
            budget_multiplier=0.5,
        )
    """

    slot_configs: dict[ModelSlot, SlotConfig] = field(
        default_factory=lambda: dict(_DEFAULT_SLOT_CONFIGS)
    )
    health_status: dict[ModelSlot, SlotHealthStatus] = field(default_factory=dict)
    _history: list[RoutingDecision] = field(default_factory=list)

    def __post_init__(self) -> None:
        for slot in ModelSlot:
            if slot not in self.health_status:
                self.health_status[slot] = SlotHealthStatus(slot=slot)

    def route(
        self,
        task: str,
        *,
        budget_multiplier: float | None = None,
        require_vision: bool = False,
        require_thinking: bool = False,
        preferred_slot: ModelSlot | None = None,
    ) -> RoutingDecision:
        """Determine the best model slot for a task.

        Args:
            task: Natural-language description of the task.
            budget_multiplier: Max cost multiplier (None = no limit).
            require_vision: Task requires vision/multimodal capability.
            require_thinking: Task requires extended thinking capability.
            preferred_slot: User-specified slot preference (overrides auto).

        Returns:
            RoutingDecision with primary and fallback slots.
        """
        if require_vision:
            primary = ModelSlot.VLM
        elif require_thinking:
            primary = ModelSlot.THINKING
        elif preferred_slot is not None:
            primary = preferred_slot
        else:
            task_type = _classify_task_type(task)
            primary = _TASK_TYPE_MAP.get(task_type, ModelSlot.NORMAL)

        # Apply budget constraint
        if budget_multiplier is not None:
            config = self.slot_configs[primary]
            if config.cost_multiplier > budget_multiplier:
                for slot in _COST_AWARE_SLOT_ORDER:
                    if self.slot_configs[slot].cost_multiplier <= budget_multiplier:
                        hs = self.health_status.get(
                            slot, SlotHealthStatus(slot=slot)
                        )
                        if hs.health != SlotHealth.UNAVAILABLE:
                            primary = slot
                            break

        # Check slot health and find fallback
        primary_health = self.health_status.get(
            primary, SlotHealthStatus(slot=primary)
        )
        fallback = None

        if primary_health.health == SlotHealth.UNAVAILABLE:
            fallback = _find_fallback(primary, self.health_status)
            if fallback is None:
                raise RuntimeError(
                    f"All slots are unavailable. Primary slot {primary.value} "
                    "is down with no healthy fallback."
                )

        primary_config = self.slot_configs[primary]
        cost = primary_config.cost_multiplier

        reasoning = (
            f"Task classified as '{_classify_task_type(task)}' → "
            f"slot={primary.value} (cost={cost:.2f}x)."
        )
        if fallback is not None:
            reasoning += (
                f" Primary slot is {primary_health.health.value}, "
                f"falling back to {fallback.value}."
            )

        decision = RoutingDecision(
            decision_id=f"rd-{uuid.uuid4().hex[:12]}",
            task_description=task[:200],
            primary_slot=fallback or primary,
            fallback_slot=fallback,
            reasoning=reasoning,
            estimated_cost_multiplier=(
                self.slot_configs[fallback].cost_multiplier if fallback else cost
            ),
            timestamp=time.time(),
        )
        self._history.append(decision)
        return decision

    def record_slot_result(
        self,
        slot: ModelSlot,
        success: bool,
        latency_ms: float = 0.0,
        error: str | None = None,
    ) -> None:
        """Update slot health based on execution result."""
        hs = self.health_status.setdefault(slot, SlotHealthStatus(slot=slot))
        if success:
            hs.record_success(latency_ms)
        elif error:
            hs.record_error(error)

    def get_healthy_slots(self) -> tuple[ModelSlot, ...]:
        """Return all currently healthy or degraded slots."""
        return tuple(
            slot
            for slot in ModelSlot
            if self.health_status.get(
                slot, SlotHealthStatus(slot=slot)
            ).health != SlotHealth.UNAVAILABLE
        )

    def get_cost_estimate(self, task: str) -> float:
        """Estimate relative cost for a task without creating a decision."""
        task_type = _classify_task_type(task)
        slot = _TASK_TYPE_MAP.get(task_type, ModelSlot.NORMAL)
        return self.slot_configs[slot].cost_multiplier

    @property
    def history(self) -> tuple[RoutingDecision, ...]:
        return tuple(self._history)

    def reset_health(self) -> None:
        """Reset all slot health to HEALTHY."""
        for slot in ModelSlot:
            self.health_status[slot] = SlotHealthStatus(slot=slot)


__all__ = [
    "ModelRouter",
    "ModelSlot",
    "RoutingDecision",
    "SlotConfig",
    "SlotHealth",
    "SlotHealthStatus",
]
