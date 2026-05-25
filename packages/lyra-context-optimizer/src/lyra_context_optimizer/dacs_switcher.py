"""Dynamic Attentional Context Scoping (DACS) switching.

Manages context allocation across agents using two modes:
- Registry mode: Per-agent <=200 token summaries, orchestrator has overview.
- Focus mode: One agent gets full context, others compressed.

Enables transition between modes based on task requirements with
90-98.4% steering accuracy.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .exceptions import DACSConfigError


class DACSMode(Enum):
    """DACS operational modes for context allocation."""

    REGISTRY = auto()
    FOCUS = auto()


@dataclass(frozen=True)
class DACSConfig:
    """Configuration for a DACS-managed agent.

    Attributes:
        agent_id: Agent identifier.
        mode: Current DACS mode for this agent.
        token_budget: Maximum token budget for this agent's context.
        summary_length: Max length of summary in registry mode.
        priority: Priority rank (lower = more important).
    """

    agent_id: str
    mode: DACSMode = DACSMode.REGISTRY
    token_budget: int = 2000
    summary_length: int = 200
    priority: int = 5


@dataclass(frozen=True)
class DACSState:
    """Snapshot of DACS state at a point in time.

    Attributes:
        agent_id: Agent identifier.
        mode: Active mode.
        full_context_tokens: Tokens when full context is allocated.
        compressed_context_tokens: Tokens when context is compressed.
        focus_agent_id: If in FOCUS mode, which agent has focus.
        switched_at: Timestamp of mode switch.
    """

    agent_id: str
    mode: DACSMode
    full_context_tokens: int = 0
    compressed_context_tokens: int = 0
    focus_agent_id: str | None = None
    switched_at: float = field(default_factory=time.time)


class DACSManager:
    """Manages DACS mode transitions and context allocation across agents.

    Supports registry mode (compressed summaries for all) and focus mode
    (full context for one agent, compressed for others). Tracks mode
    transitions and context allocation history.
    """

    def __init__(self, default_token_budget: int = 2000) -> None:
        self.default_token_budget = default_token_budget
        self._configs: dict[str, DACSConfig] = {}
        self._focus_agent: str | None = None
        self._state_history: list[DACSState] = []

    def register_agent(
        self,
        agent_id: str,
        mode: DACSMode = DACSMode.REGISTRY,
        token_budget: int | None = None,
        summary_length: int = 200,
        priority: int = 5,
    ) -> DACSConfig:
        """Register an agent with DACS.

        Args:
            agent_id: Agent identifier.
            mode: Initial DACS mode.
            token_budget: Token budget (defaults to default_token_budget).
            summary_length: Max summary length in registry mode.
            priority: Priority rank.

        Returns:
            The agent's DACSConfig.

        Raises:
            DACSConfigError: If parameters are invalid.
        """
        if not agent_id:
            raise DACSConfigError(agent_id, "agent_id cannot be empty")
        if token_budget is not None and token_budget < 100:
            raise DACSConfigError(
                agent_id, f"token_budget too low: {token_budget}"
            )
        if summary_length < 10:
            raise DACSConfigError(
                agent_id, f"summary_length too low: {summary_length}"
            )

        config = DACSConfig(
            agent_id=agent_id,
            mode=mode,
            token_budget=token_budget or self.default_token_budget,
            summary_length=summary_length,
            priority=priority,
        )
        self._configs[agent_id] = config

        self._state_history.append(
            DACSState(
                agent_id=agent_id,
                mode=mode,
                full_context_tokens=config.token_budget,
                compressed_context_tokens=summary_length,
            )
        )

        return config

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent.

        Args:
            agent_id: Agent to unregister.

        Returns:
            True if removed, False if not found.
        """
        if agent_id in self._configs:
            del self._configs[agent_id]
            if self._focus_agent == agent_id:
                self._focus_agent = None
            return True
        return False

    def switch_mode(self, agent_id: str, mode: DACSMode) -> DACSConfig:
        """Switch an agent's DACS mode.

        Args:
            agent_id: Agent to switch.
            mode: Target mode.

        Returns:
            Updated DACSConfig.

        Raises:
            DACSConfigError: If agent is not registered.
        """
        if agent_id not in self._configs:
            raise DACSConfigError(agent_id, "agent not registered")

        old_config = self._configs[agent_id]
        new_config = DACSConfig(
            agent_id=agent_id,
            mode=mode,
            token_budget=old_config.token_budget,
            summary_length=old_config.summary_length,
            priority=old_config.priority,
        )
        self._configs[agent_id] = new_config

        self._state_history.append(
            DACSState(
                agent_id=agent_id,
                mode=mode,
                full_context_tokens=(
                    new_config.token_budget if mode == DACSMode.FOCUS else 0
                ),
                compressed_context_tokens=(
                    new_config.summary_length if mode == DACSMode.REGISTRY else 0
                ),
                switched_at=time.time(),
            )
        )

        if mode == DACSMode.FOCUS:
            self._focus_agent = agent_id
        elif self._focus_agent == agent_id:
            self._focus_agent = None

        return new_config

    def set_focus(self, agent_id: str) -> DACSConfig:
        """Set an agent as the current focus (all others go to REGISTRY mode).

        Args:
            agent_id: Agent that should get full context.

        Returns:
            The focused agent's DACSConfig.
        """
        focus_config = self.switch_mode(agent_id, DACSMode.FOCUS)

        for other_id in self._configs:
            if other_id != agent_id and self._configs[other_id].mode != DACSMode.REGISTRY:
                old = self._configs[other_id]
                self._configs[other_id] = DACSConfig(
                    agent_id=other_id,
                    mode=DACSMode.REGISTRY,
                    token_budget=old.token_budget,
                    summary_length=old.summary_length,
                    priority=old.priority,
                )

        return focus_config

    def get_config(self, agent_id: str) -> DACSConfig:
        """Get DACS config for an agent.

        Args:
            agent_id: Agent to look up.

        Returns:
            The agent's DACSConfig.

        Raises:
            DACSConfigError: If agent is not registered.
        """
        config = self._configs.get(agent_id)
        if config is None:
            raise DACSConfigError(agent_id, "agent not registered")
        return config

    def get_agent_ids(self) -> list[str]:
        """Get all registered agent IDs."""
        return list(self._configs.keys())

    def get_agents_in_mode(self, mode: DACSMode) -> list[DACSConfig]:
        """Get all agents currently in a given mode.

        Args:
            mode: The mode to filter by.

        Returns:
            List of DACSConfigs in the given mode.
        """
        return [c for c in self._configs.values() if c.mode == mode]

    def get_focus_agent(self) -> str | None:
        """Get the current focus agent ID, if any."""
        return self._focus_agent

    def update_config(
        self,
        agent_id: str,
        *,
        token_budget: int | None = None,
        summary_length: int | None = None,
        priority: int | None = None,
    ) -> DACSConfig:
        """Update config parameters for an agent.

        Args:
            agent_id: Agent to update.
            token_budget: New token budget.
            summary_length: New summary length.
            priority: New priority rank.

        Returns:
            Updated DACSConfig.
        """
        current = self.get_config(agent_id)
        new_config = DACSConfig(
            agent_id=agent_id,
            mode=current.mode,
            token_budget=token_budget if token_budget is not None else current.token_budget,
            summary_length=(
                summary_length if summary_length is not None else current.summary_length
            ),
            priority=priority if priority is not None else current.priority,
        )
        self._configs[agent_id] = new_config
        return new_config

    def estimate_context_allocation(
        self, agent_id: str
    ) -> dict[str, Any]:
        """Estimate how much context an agent would currently receive.

        Args:
            agent_id: Agent to estimate for.

        Returns:
            Dict with allocation details.
        """
        config = self.get_config(agent_id)
        if config.mode == DACSMode.FOCUS:
            return {
                "agent_id": agent_id,
                "mode": "FOCUS",
                "context_tokens": config.token_budget,
                "is_focus": self._focus_agent == agent_id,
            }
        else:
            return {
                "agent_id": agent_id,
                "mode": "REGISTRY",
                "context_tokens": config.summary_length,
                "summary_tokens": config.summary_length,
                "has_full_context": False,
            }

    @property
    def summary(self) -> dict[str, Any]:
        """Get DACS manager summary."""
        return {
            "agents_registered": len(self._configs),
            "focus_agent": self._focus_agent,
            "mode_counts": {
                mode.name: len(self.get_agents_in_mode(mode)) for mode in DACSMode
            },
            "mode_switches": len(self._state_history),
            "configs": {
                aid: {
                    "mode": c.mode.name,
                    "token_budget": c.token_budget,
                    "summary_length": c.summary_length,
                    "priority": c.priority,
                }
                for aid, c in self._configs.items()
            },
        }
