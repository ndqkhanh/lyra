"""Agent retirement with knowledge extraction, state preservation, cleanup, and audit trail."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .lifecycle import AgentLifecycleManager, LifecycleState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class RetirementError(Exception):
    """Base exception for retirement errors."""


class AgentAlreadyRetiredError(RetirementError):
    """Raised when trying to retire an already-retired agent."""


class KnowledgeExtractionError(RetirementError):
    """Raised when knowledge extraction fails."""


class StatePreservationError(RetirementError):
    """Raised when state preservation fails."""


class HandoffError(RetirementError):
    """Raised when state handoff to a successor fails."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclass
class RetirementConfig:
    """Configuration for agent retirement.

    Attributes:
        extract_knowledge: Whether to extract knowledge before retirement.
        preserve_state: Whether to save agent state.
        handoff_target: Agent ID to hand off state to.
        cleanup_resources: Whether to release allocated resources.
        audit: Whether to create an audit trail.
        max_extraction_timeout: Timeout for knowledge extraction.
    """

    extract_knowledge: bool = True
    preserve_state: bool = True
    handoff_target: str | None = None
    cleanup_resources: bool = True
    audit: bool = True
    max_extraction_timeout: float = 30.0


@dataclass
class KnowledgeBundle:
    """Extracted knowledge from a retiring agent.

    Attributes:
        bundle_id: Unique bundle identifier.
        source_agent: The agent being retired.
        extracted_at: When knowledge was extracted.
        capabilities: Known capabilities.
        key_learnings: Summarized learnings.
        task_history_summary: Aggregated task performance data.
        metadata: Additional knowledge items.
    """

    bundle_id: str = field(default_factory=_new_id)
    source_agent: str = ""
    extracted_at: float = field(default_factory=_now)
    capabilities: list[str] = field(default_factory=list)
    key_learnings: list[dict[str, Any]] = field(default_factory=list)
    task_history_summary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetirementAuditEntry:
    """Audit trail entry for agent retirement.

    Attributes:
        audit_id: Unique audit entry identifier.
        agent_id: The retired agent.
        retired_at: When retirement occurred.
        reason: Why the agent was retired.
        knowledge_extracted: Whether knowledge was preserved.
        state_preserved: Whether state was saved.
        handoff_completed: Whether state was handed off.
        duration_ms: How long retirement took.
        metadata: Additional info.
    """

    audit_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    retired_at: float = field(default_factory=_now)
    reason: str = ""
    knowledge_extracted: bool = False
    state_preserved: bool = False
    handoff_completed: bool = False
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Knowledge Extraction
# ---------------------------------------------------------------------------


class KnowledgeExtractor:
    """Extracts knowledge from an agent before retirement.

    Runs registered extraction functions to collect capabilities,
    learnings, and performance history from the retiring agent.
    """

    def __init__(self) -> None:
        self._extractors: dict[str, Callable[[str], Awaitable[dict[str, Any]]]] = {}
        self._knowledge_store: dict[str, list[KnowledgeBundle]] = {}

    def register_extractor(
        self,
        name: str,
        extractor_fn: Callable[[str], Awaitable[dict[str, Any]]],
    ) -> None:
        """Register a knowledge extraction function."""
        self._extractors[name] = extractor_fn

    async def extract(
        self,
        agent_id: str,
        *,
        timeout: float = 30.0,
    ) -> KnowledgeBundle:
        """Extract all knowledge from an agent."""
        capabilities: list[str] = []
        learnings: list[dict[str, Any]] = []

        for name, extractor in self._extractors.items():
            try:
                result = await asyncio.wait_for(extractor(agent_id), timeout=timeout)
                if name == "capabilities":
                    capabilities = result.get("capabilities", [])
                else:
                    learnings.append({"source": name, "data": result})
            except asyncio.TimeoutError:
                logger.warning("Knowledge extractor '%s' timed out for %s", name, agent_id)
            except Exception as e:
                logger.warning("Knowledge extractor '%s' failed for %s: %s", name, agent_id, e)

        bundle = KnowledgeBundle(
            source_agent=agent_id,
            capabilities=capabilities,
            key_learnings=learnings,
        )

        # Store for future reference
        if agent_id not in self._knowledge_store:
            self._knowledge_store[agent_id] = []
        self._knowledge_store[agent_id].append(bundle)

        logger.debug("Extracted %d learnings from %s", len(learnings), agent_id)
        return bundle

    def get_knowledge(self, agent_id: str) -> list[KnowledgeBundle]:
        """Get extracted knowledge bundles for an agent."""
        return self._knowledge_store.get(agent_id, [])

    def transfer_knowledge(self, from_agent: str, to_agent: str) -> list[KnowledgeBundle]:
        """Transfer knowledge records from one agent to another."""
        bundles = self._knowledge_store.pop(from_agent, [])
        if to_agent not in self._knowledge_store:
            self._knowledge_store[to_agent] = []
        self._knowledge_store[to_agent].extend(bundles)
        logger.info(
            "Transferred %d knowledge bundles from %s to %s", len(bundles), from_agent, to_agent
        )
        return bundles


# ---------------------------------------------------------------------------
# State Preservation
# ---------------------------------------------------------------------------


class StatePreserver:
    """Preserves and restores agent state across retirement.

    Saves agent state before retirement so it can be handed off
    to successor agents or restored later.
    """

    def __init__(self, *, max_snapshots_per_agent: int = 10) -> None:
        self._max_snapshots = max_snapshots_per_agent
        self._state_store: dict[str, list[dict[str, Any]]] = {}
        self._latest_state: dict[str, dict[str, Any]] = {}

    async def save_state(
        self,
        agent_id: str,
        state: dict[str, Any],
        *,
        label: str = "",
    ) -> str:
        """Save agent state. Returns snapshot ID."""
        snapshot = {
            "snapshot_id": _new_id(),
            "agent_id": agent_id,
            "state": dict(state),
            "saved_at": _now(),
            "label": label,
        }

        if agent_id not in self._state_store:
            self._state_store[agent_id] = []

        self._state_store[agent_id].append(snapshot)
        if len(self._state_store[agent_id]) > self._max_snapshots:
            self._state_store[agent_id] = self._state_store[agent_id][-self._max_snapshots :]

        self._latest_state[agent_id] = snapshot
        logger.debug("Saved state for %s (%s)", agent_id, label)
        return snapshot["snapshot_id"]

    def get_latest_state(self, agent_id: str) -> dict[str, Any] | None:
        """Get the most recently saved state for an agent."""
        return self._latest_state.get(agent_id)

    def get_state_history(self, agent_id: str) -> list[dict[str, Any]]:
        """Get all saved states for an agent."""
        return list(self._state_store.get(agent_id, []))

    def restore_state(self, agent_id: str) -> dict[str, Any] | None:
        """Get the state for handoff to a successor."""
        return self.get_latest_state(agent_id)

    def cleanup_state(self, agent_id: str) -> None:
        """Remove all preserved state for an agent."""
        self._state_store.pop(agent_id, None)
        self._latest_state.pop(agent_id, None)

    def handoff_state(self, from_agent: str, to_agent: str) -> dict[str, Any] | None:
        """Transfer state from one agent to another."""
        state = self._latest_state.pop(from_agent, None)
        if state is None:
            return None

        state["agent_id"] = to_agent
        state["transferred_from"] = from_agent
        self._latest_state[to_agent] = state

        logger.info("Handed off state from %s to %s", from_agent, to_agent)
        return state


# ---------------------------------------------------------------------------
# Agent Retirement
# ---------------------------------------------------------------------------


class AgentRetirement:
    """Orchestrates the full agent retirement process.

    Workflow:
    1. Pause the agent
    2. Extract knowledge
    3. Preserve state
    4. Handoff to successor (if specified)
    5. Cleanup resources
    6. Transition to RETIRED
    7. Create audit trail
    """

    def __init__(
        self,
        lifecycle: AgentLifecycleManager,
        *,
        knowledge_extractor: KnowledgeExtractor | None = None,
        state_preserver: StatePreserver | None = None,
    ) -> None:
        self._lifecycle = lifecycle
        self._knowledge_extractor = knowledge_extractor or KnowledgeExtractor()
        self._state_preserver = state_preserver or StatePreserver()
        self._audit_log: list[RetirementAuditEntry] = []

    async def retire(
        self,
        agent_id: str,
        *,
        config: RetirementConfig | None = None,
        reason: str = "manual_retirement",
    ) -> RetirementAuditEntry:
        """Execute the full retirement process for an agent.

        Returns an audit entry documenting what was done.
        """
        config = config or RetirementConfig()
        start = _now()

        # Verify agent exists and is not already retired
        state = self._lifecycle.get_state(agent_id)
        if state is None:
            raise RetirementError(f"Agent {agent_id} not found")
        if state == LifecycleState.RETIRED:
            raise AgentAlreadyRetiredError(f"Agent {agent_id} is already retired")

        knowledge_extracted = False
        state_preserved = False
        handoff_completed = False

        # 1. Pause if active
        if state == LifecycleState.ACTIVE:
            await self._lifecycle.pause(agent_id, reason="retirement_preparation")
            await asyncio.sleep(0.1)

        # 2. Extract knowledge
        if config.extract_knowledge:
            try:
                bundle = await self._knowledge_extractor.extract(
                    agent_id,
                    timeout=config.max_extraction_timeout,
                )
                knowledge_extracted = True
                logger.debug(
                    "Knowledge extracted from %s: %d learnings", agent_id, len(bundle.key_learnings)
                )
            except Exception as e:
                logger.error("Knowledge extraction failed for %s: %s", agent_id, e)

        # 3. Preserve state
        if config.preserve_state:
            try:
                saved_state = {
                    "agent_id": agent_id,
                    "retired_at": _now(),
                    "reason": reason,
                    "knowledge_extracted": knowledge_extracted,
                }
                await self._state_preserver.save_state(agent_id, saved_state, label="retirement")
                state_preserved = True
            except Exception as e:
                logger.error("State preservation failed for %s: %s", agent_id, e)

        # 4. Handoff to successor
        if config.handoff_target and state_preserved:
            try:
                await self._handoff(agent_id, config.handoff_target)
                handoff_completed = True
            except Exception as e:
                logger.error("Handoff from %s to %s failed: %s", agent_id, config.handoff_target, e)

        # 5. Cleanup resources (handled by lifecycle)
        # 6. Transition to RETIRED
        await self._lifecycle.transition(
            agent_id,
            LifecycleState.RETIRED,
            reason=reason,
        )

        # 7. Create audit entry
        duration = (_now() - start) * 1000
        entry = RetirementAuditEntry(
            agent_id=agent_id,
            reason=reason,
            knowledge_extracted=knowledge_extracted,
            state_preserved=state_preserved,
            handoff_completed=handoff_completed,
            duration_ms=duration,
        )
        self._audit_log.append(entry)
        logger.info("Retired agent %s: %s (%.1fms)", agent_id, reason, duration)
        return entry

    async def retire_batch(
        self,
        agent_ids: list[str],
        *,
        config: RetirementConfig | None = None,
        reason: str = "batch_retirement",
    ) -> dict[str, RetirementAuditEntry]:
        """Retire multiple agents concurrently."""
        tasks = [self.retire(aid, config=config, reason=reason) for aid in agent_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outcomes: dict[str, RetirementAuditEntry] = {}
        for aid, result in zip(agent_ids, results, strict=False):
            if isinstance(result, Exception):
                logger.error("Failed to retire %s: %s", aid, result)
                continue
            outcomes[aid] = result
        return outcomes

    async def _handoff(self, from_agent: str, to_agent: str) -> None:
        """Hand off state and knowledge from one agent to another."""
        # Transfer knowledge
        self._knowledge_extractor.transfer_knowledge(from_agent, to_agent)

        # Transfer state
        self._state_preserver.handoff_state(from_agent, to_agent)

        logger.info("Handoff complete: %s -> %s", from_agent, to_agent)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_audit_log(
        self, agent_id: str | None = None, limit: int = 100
    ) -> list[RetirementAuditEntry]:
        """Query the retirement audit log."""
        entries = self._audit_log
        if agent_id is not None:
            entries = [e for e in entries if e.agent_id == agent_id]
        return entries[-limit:]

    def get_knowledge(self, agent_id: str) -> list[KnowledgeBundle]:
        """Get extracted knowledge for an agent."""
        return self._knowledge_extractor.get_knowledge(agent_id)

    def get_preserved_state(self, agent_id: str) -> dict[str, Any] | None:
        """Get preserved state for an agent."""
        return self._state_preserver.get_latest_state(agent_id)

    def snapshot(self) -> dict[str, Any]:
        """Return current state snapshot."""
        return {
            "total_retirements": len(self._audit_log),
            "knowledge_bundles": sum(
                len(bundles) for bundles in self._knowledge_extractor._knowledge_store.values()
            ),
            "preserved_states": len(self._state_preserver._latest_state),
            "recent_retirements": [
                {
                    "agent_id": e.agent_id,
                    "reason": e.reason,
                    "duration_ms": e.duration_ms,
                }
                for e in self._audit_log[-10:]
            ],
        }
