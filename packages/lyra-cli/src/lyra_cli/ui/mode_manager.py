"""Mode manager — controls Lyra's operational mode and behavior profiles.

Manages transitions between operational modes (plan, execute, review, etc.)
and enforces mode-specific permission and behavior constraints.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class AgentMode(StrEnum):
    PLAN = "plan"
    EXECUTE = "execute"
    REVIEW = "review"
    RESEARCH = "research"
    CHAT = "chat"
    AUTOPILOT = "autopilot"


@dataclass(frozen=True)
class ModeConfig:
    mode: AgentMode
    allow_writes: bool
    allow_network: bool
    max_parallel_tasks: int
    require_approval: bool
    auto_commit: bool


@dataclass(frozen=True)
class ModeTransition:
    from_mode: AgentMode
    to_mode: AgentMode
    reason: str
    timestamp: float


class ModeManager:
    """Manages Lyra's operational mode and enforces mode constraints.

    Each mode has specific capabilities. Transitions are logged
    and can be validated against allowed state transitions.
    """

    DEFAULT_CONFIGS: dict[AgentMode, ModeConfig] = {
        AgentMode.PLAN: ModeConfig(
            mode=AgentMode.PLAN,
            allow_writes=False,
            allow_network=False,
            max_parallel_tasks=1,
            require_approval=True,
            auto_commit=False,
        ),
        AgentMode.EXECUTE: ModeConfig(
            mode=AgentMode.EXECUTE,
            allow_writes=True,
            allow_network=True,
            max_parallel_tasks=4,
            require_approval=False,
            auto_commit=False,
        ),
        AgentMode.REVIEW: ModeConfig(
            mode=AgentMode.REVIEW,
            allow_writes=False,
            allow_network=False,
            max_parallel_tasks=1,
            require_approval=True,
            auto_commit=False,
        ),
        AgentMode.RESEARCH: ModeConfig(
            mode=AgentMode.RESEARCH,
            allow_writes=False,
            allow_network=True,
            max_parallel_tasks=5,
            require_approval=False,
            auto_commit=False,
        ),
        AgentMode.CHAT: ModeConfig(
            mode=AgentMode.CHAT,
            allow_writes=False,
            allow_network=False,
            max_parallel_tasks=1,
            require_approval=False,
            auto_commit=False,
        ),
        AgentMode.AUTOPILOT: ModeConfig(
            mode=AgentMode.AUTOPILOT,
            allow_writes=True,
            allow_network=True,
            max_parallel_tasks=8,
            require_approval=False,
            auto_commit=True,
        ),
    }

    ALLOWED_TRANSITIONS: dict[AgentMode, set[AgentMode]] = {
        AgentMode.PLAN: {AgentMode.EXECUTE, AgentMode.CHAT, AgentMode.RESEARCH},
        AgentMode.EXECUTE: {AgentMode.REVIEW, AgentMode.PLAN, AgentMode.CHAT},
        AgentMode.REVIEW: {AgentMode.PLAN, AgentMode.EXECUTE, AgentMode.CHAT},
        AgentMode.RESEARCH: {AgentMode.PLAN, AgentMode.CHAT},
        AgentMode.CHAT: {AgentMode.PLAN, AgentMode.RESEARCH, AgentMode.EXECUTE},
        AgentMode.AUTOPILOT: {AgentMode.CHAT, AgentMode.REVIEW},
    }

    def __init__(self, initial_mode: AgentMode = AgentMode.CHAT) -> None:
        self._current = initial_mode
        self._transitions: list[ModeTransition] = []

    @property
    def current_mode(self) -> AgentMode:
        return self._current

    @property
    def config(self) -> ModeConfig:
        return self.DEFAULT_CONFIGS[self._current]

    def transition(self, to_mode: AgentMode, reason: str = "") -> ModeTransition:
        if to_mode not in self.ALLOWED_TRANSITIONS.get(self._current, set()):
            raise ValueError(
                f"Cannot transition from {self._current.value} to {to_mode.value}"
            )

        transition = ModeTransition(
            from_mode=self._current,
            to_mode=to_mode,
            reason=reason,
            timestamp=time.time(),
        )
        self._current = to_mode
        self._transitions.append(transition)
        return transition

    def can_transition(self, to_mode: AgentMode) -> bool:
        return to_mode in self.ALLOWED_TRANSITIONS.get(self._current, set())

    def get_allowed_transitions(self) -> list[AgentMode]:
        return list(self.ALLOWED_TRANSITIONS.get(self._current, set()))

    def is_write_allowed(self) -> bool:
        return self.config.allow_writes

    def is_network_allowed(self) -> bool:
        return self.config.allow_network

    def get_history(self) -> list[ModeTransition]:
        return list(self._transitions)

    def stats(self) -> dict:
        return {
            "current_mode": self._current.value,
            "total_transitions": len(self._transitions),
            "allowed_transitions": [m.value for m in self.get_allowed_transitions()],
            "config": {
                "allow_writes": self.config.allow_writes,
                "allow_network": self.config.allow_network,
                "max_parallel": self.config.max_parallel_tasks,
            },
        }
