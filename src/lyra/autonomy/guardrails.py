"""Quota governor — per-session resource limits for autonomous agents.

Provides the :class:`QuotaGovernor` that enforces token, cost, time, and
step budgets on a per-session basis. Supports soft warnings at configurable
percentages, hard blocks at 100%, and configurable reset policies.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class QuotaKind(str, Enum):
    """The type of resource being governed."""

    MAX_TOKENS = "max_tokens"
    MAX_COST = "max_cost"
    MAX_TIME = "max_time"          # Wall-clock seconds
    MAX_STEPS = "max_steps"


class QuotaExceededAction(str, Enum):
    """What happens when a quota is exceeded."""

    WARN = "warn"     # Log a warning, let the session continue
    PAUSE = "pause"   # Pause the session until the next reset window
    ABORT = "abort"   # Forcefully abort the session


class ResetPolicy(str, Enum):
    """When quota counters are reset to zero."""

    DAILY = "daily"           # Reset every day at UTC midnight
    WEEKLY = "weekly"         # Reset every Monday at UTC midnight
    PER_SESSION = "per_session"  # Reset at the start of each new session


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuotaLimit:
    """A single quota limit.

    Attributes:
        kind: What resource this limit governs.
        hard_limit: The absolute cap (tokens, cost in cents, seconds, steps).
        soft_warning_at_pct: Fraction (0-1) of the hard limit that triggers
            a warning. Default 0.8 (80%).
        action: What to do when the limit is reached.
        reset: When the counter resets.
    """

    kind: QuotaKind
    hard_limit: float
    soft_warning_at_pct: float = 0.8
    action: QuotaExceededAction = QuotaExceededAction.WARN
    reset: ResetPolicy = ResetPolicy.DAILY


@dataclass
class QuotaUsage:
    """Usage snapshot for a single quota.

    Attributes:
        kind: The quota kind.
        used: Current usage value.
        hard_limit: The configured hard limit.
        usage_pct: Usage as a fraction of the hard limit (0-1).
        is_warning: Whether usage is above the soft warning threshold.
        is_exceeded: Whether usage meets or exceeds the hard limit.
        action_taken: The action that was taken (None if within limits).
    """

    kind: QuotaKind
    used: float
    hard_limit: float
    usage_pct: float
    is_warning: bool
    is_exceeded: bool
    action_taken: QuotaExceededAction | None = None


@dataclass
class AgentQuotaConfig:
    """Quota limits for a specific agent type.

    Attributes:
        agent_type: The agent type identifier (e.g. ``"code"``, ``"research"``, ``"chat"``).
        limits: Mapping of quota kind to limit configuration.
    """

    agent_type: str
    limits: dict[QuotaKind, QuotaLimit] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Default quotas per agent type
# ---------------------------------------------------------------------------

_DEFAULT_CODE_LIMITS: dict[QuotaKind, QuotaLimit] = {
    QuotaKind.MAX_TOKENS: QuotaLimit(
        kind=QuotaKind.MAX_TOKENS,
        hard_limit=500_000,
        soft_warning_at_pct=0.8,
        action=QuotaExceededAction.PAUSE,
        reset=ResetPolicy.DAILY,
    ),
    QuotaKind.MAX_COST: QuotaLimit(
        kind=QuotaKind.MAX_COST,
        hard_limit=500.0,  # $5.00 in cents
        soft_warning_at_pct=0.8,
        action=QuotaExceededAction.PAUSE,
        reset=ResetPolicy.DAILY,
    ),
    QuotaKind.MAX_TIME: QuotaLimit(
        kind=QuotaKind.MAX_TIME,
        hard_limit=7200.0,  # 2 hours
        soft_warning_at_pct=0.8,
        action=QuotaExceededAction.WARN,
        reset=ResetPolicy.PER_SESSION,
    ),
    QuotaKind.MAX_STEPS: QuotaLimit(
        kind=QuotaKind.MAX_STEPS,
        hard_limit=200,
        soft_warning_at_pct=0.8,
        action=QuotaExceededAction.PAUSE,
        reset=ResetPolicy.PER_SESSION,
    ),
}

_DEFAULT_RESEARCH_LIMITS: dict[QuotaKind, QuotaLimit] = {
    QuotaKind.MAX_TOKENS: QuotaLimit(
        kind=QuotaKind.MAX_TOKENS,
        hard_limit=1_000_000,
        soft_warning_at_pct=0.8,
        action=QuotaExceededAction.PAUSE,
        reset=ResetPolicy.DAILY,
    ),
    QuotaKind.MAX_COST: QuotaLimit(
        kind=QuotaKind.MAX_COST,
        hard_limit=1000.0,  # $10.00
        soft_warning_at_pct=0.85,
        action=QuotaExceededAction.PAUSE,
        reset=ResetPolicy.DAILY,
    ),
    QuotaKind.MAX_TIME: QuotaLimit(
        kind=QuotaKind.MAX_TIME,
        hard_limit=14400.0,  # 4 hours
        soft_warning_at_pct=0.8,
        action=QuotaExceededAction.WARN,
        reset=ResetPolicy.PER_SESSION,
    ),
    QuotaKind.MAX_STEPS: QuotaLimit(
        kind=QuotaKind.MAX_STEPS,
        hard_limit=400,
        soft_warning_at_pct=0.8,
        action=QuotaExceededAction.PAUSE,
        reset=ResetPolicy.PER_SESSION,
    ),
}

_DEFAULT_CHAT_LIMITS: dict[QuotaKind, QuotaLimit] = {
    QuotaKind.MAX_TOKENS: QuotaLimit(
        kind=QuotaKind.MAX_TOKENS,
        hard_limit=100_000,
        soft_warning_at_pct=0.8,
        action=QuotaExceededAction.PAUSE,
        reset=ResetPolicy.DAILY,
    ),
    QuotaKind.MAX_COST: QuotaLimit(
        kind=QuotaKind.MAX_COST,
        hard_limit=100.0,  # $1.00
        soft_warning_at_pct=0.8,
        action=QuotaExceededAction.PAUSE,
        reset=ResetPolicy.DAILY,
    ),
    QuotaKind.MAX_TIME: QuotaLimit(
        kind=QuotaKind.MAX_TIME,
        hard_limit=1800.0,  # 30 minutes
        soft_warning_at_pct=0.8,
        action=QuotaExceededAction.ABORT,
        reset=ResetPolicy.PER_SESSION,
    ),
    QuotaKind.MAX_STEPS: QuotaLimit(
        kind=QuotaKind.MAX_STEPS,
        hard_limit=50,
        soft_warning_at_pct=0.8,
        action=QuotaExceededAction.ABORT,
        reset=ResetPolicy.PER_SESSION,
    ),
}

_DEFAULT_AGENT_QUOTAS: dict[str, dict[QuotaKind, QuotaLimit]] = {
    "code": _DEFAULT_CODE_LIMITS,
    "research": _DEFAULT_RESEARCH_LIMITS,
    "chat": _DEFAULT_CHAT_LIMITS,
}


# ---------------------------------------------------------------------------
# QuotaGovernor
# ---------------------------------------------------------------------------


class QuotaGovernor:
    """Enforces per-session resource quotas for autonomous agents.

    Tracks usage per session, compares against configured limits, and
    returns the action to take (warn, pause, abort).

    Usage::

        governor = QuotaGovernor()
        governor.register_session("sess-1", agent_type="code")

        # On each step:
        action = governor.check("sess-1", tokens_used=5000, cost=0.02)
        if action == QuotaExceededAction.PAUSE:
            await pause_session()
        elif action == QuotaExceededAction.ABORT:
            await abort_session()
    """

    def __init__(
        self,
        agent_quotas: dict[str, dict[QuotaKind, QuotaLimit]] | None = None,
    ) -> None:
        """
        Args:
            agent_quotas: Per-agent-type quota limits. Falls back to built-in
                defaults for ``"code"``, ``"research"``, and ``"chat"``.
        """
        self._agent_quotas = agent_quotas or dict(_DEFAULT_AGENT_QUOTAS)
        self._usage: dict[str, dict[QuotaKind, float]] = {}  # session_id -> kind -> used
        self._sessions: dict[str, str] = {}  # session_id -> agent_type
        self._start_times: dict[str, float] = {}  # session_id -> start time
        self._session_numbers: dict[str, int] = {}  # session_id -> session number (for per-session reset)

    # ── Session lifecycle ─────────────────────────────────────────────

    def register_session(
        self,
        session_id: str,
        agent_type: str = "code",
    ) -> None:
        """Register a new session for quota tracking.

        Args:
            session_id: Unique session identifier.
            agent_type: Type of agent (``"code"``, ``"research"``, ``"chat"``).
                Falls back to ``"code"`` if the type is not configured.
        """
        if agent_type not in self._agent_quotas:
            logger.warning(
                "Unknown agent type '%s' for session '%s', falling back to 'code'",
                agent_type, session_id,
            )
            agent_type = "code"

        self._sessions[session_id] = agent_type
        self._start_times[session_id] = time.time()

        # Track session number for per-session reset detection
        self._session_numbers[session_id] = self._session_numbers.get(session_id, 0) + 1

        # Initialise all quota counters to 0
        limits = self._agent_quotas[agent_type]
        self._usage[session_id] = {kind: 0.0 for kind in limits}

        logger.debug(
            "Session '%s' registered as type '%s'", session_id, agent_type
        )

    def unregister_session(self, session_id: str) -> None:
        """Remove a session from quota tracking.

        Args:
            session_id: The session to remove.
        """
        self._usage.pop(session_id, None)
        self._sessions.pop(session_id, None)
        self._start_times.pop(session_id, None)
        self._session_numbers.pop(session_id, None)

    # ── Usage recording ───────────────────────────────────────────────

    def record_usage(
        self,
        session_id: str,
        tokens: int = 0,
        cost: float = 0.0,
        steps: int = 1,
    ) -> list[QuotaUsage]:
        """Record resource consumption and return the current quota status.

        All positional usage values are additive — each call accumulates.

        Args:
            session_id: The session consuming resources.
            tokens: Additional tokens consumed since last check.
            cost: Additional cost (in your chosen unit, e.g. cents) incurred.
            steps: Additional steps taken since last check.

        Returns:
            A list of :class:`QuotaUsage` snapshots for all governed quotas.
        """
        if session_id not in self._usage:
            logger.warning(
                "Session '%s' not registered, ignoring usage recording", session_id
            )
            return []

        agent_type = self._sessions[session_id]
        limits = self._agent_quotas[agent_type]
        counters = self._usage[session_id]

        # Accumulate usage — only for kinds tracked by this agent type
        if QuotaKind.MAX_TOKENS in counters:
            counters[QuotaKind.MAX_TOKENS] += tokens
        if QuotaKind.MAX_COST in counters:
            counters[QuotaKind.MAX_COST] += cost
        if QuotaKind.MAX_TIME in counters:
            counters[QuotaKind.MAX_TIME] = time.time() - self._start_times[session_id]
        if QuotaKind.MAX_STEPS in counters:
            counters[QuotaKind.MAX_STEPS] += steps

        # Build usage snapshots
        results: list[QuotaUsage] = []
        for kind, limit in limits.items():
            used = counters.get(kind, 0.0)
            usage_pct = used / limit.hard_limit if limit.hard_limit > 0 else 0.0
            is_warning = usage_pct >= limit.soft_warning_at_pct
            is_exceeded = usage_pct >= 1.0
            action_taken = limit.action if is_exceeded else None

            if is_exceeded:
                logger.warning(
                    "Quota exceeded for session '%s': %s %.1f/%.1f (%.1f%%) — action=%s",
                    session_id,
                    kind.value,
                    used,
                    limit.hard_limit,
                    usage_pct * 100,
                    action_taken.value if action_taken else "none",
                )

            results.append(QuotaUsage(
                kind=kind,
                used=used,
                hard_limit=limit.hard_limit,
                usage_pct=usage_pct,
                is_warning=is_warning,
                is_exceeded=is_exceeded,
                action_taken=action_taken,
            ))

        return results

    # ── Limit checks ──────────────────────────────────────────────────

    def check(
        self,
        session_id: str,
        tokens_used: int = 0,
        cost: float = 0.0,
        steps: int = 0,
    ) -> list[QuotaUsage]:
        """Check quota status for a session **without** recording usage.

        This is a read-only check.  Use :meth:`record_usage` to both
        record and check.

        Args:
            session_id: The session to check.
            tokens_used: Total tokens consumed so far.
            cost: Total cost incurred so far.
            steps: Total steps taken so far.

        Returns:
            A list of :class:`QuotaUsage` snapshots.
        """
        if session_id not in self._usage:
            return []

        agent_type = self._sessions.get(session_id, "code")
        limits = self._agent_quotas.get(agent_type, {})

        results: list[QuotaUsage] = []
        for kind, limit in limits.items():
            used = {
                QuotaKind.MAX_TOKENS: tokens_used,
                QuotaKind.MAX_COST: cost,
                QuotaKind.MAX_TIME: time.time() - self._start_times.get(session_id, time.time()),
                QuotaKind.MAX_STEPS: steps,
            }.get(kind, 0.0)

            usage_pct = used / limit.hard_limit if limit.hard_limit > 0 else 0.0
            is_warning = usage_pct >= limit.soft_warning_at_pct
            is_exceeded = usage_pct >= 1.0

            results.append(QuotaUsage(
                kind=kind,
                used=used,
                hard_limit=limit.hard_limit,
                usage_pct=usage_pct,
                is_warning=is_warning,
                is_exceeded=is_exceeded,
                action_taken=limit.action if is_exceeded else None,
            ))

        return results

    def highest_action(
        self,
        usage_list: list[QuotaUsage],
    ) -> QuotaExceededAction | None:
        """Return the most severe action from a list of quota usage snapshots.

        Severity order: ``abort`` > ``pause`` > ``warn`` > ``None``.

        Args:
            usage_list: Output of :meth:`record_usage` or :meth:`check`.

        Returns:
            The most severe action to take, or None if all within limits.
        """
        actions = [
            u.action_taken
            for u in usage_list
            if u.action_taken is not None
        ]

        if QuotaExceededAction.ABORT in actions:
            return QuotaExceededAction.ABORT
        if QuotaExceededAction.PAUSE in actions:
            return QuotaExceededAction.PAUSE
        if QuotaExceededAction.WARN in actions:
            return QuotaExceededAction.WARN
        return None

    # ── Quota config ──────────────────────────────────────────────────

    def set_quota(
        self,
        agent_type: str,
        kind: QuotaKind,
        limit: QuotaLimit,
    ) -> None:
        """Set or update a quota limit for an agent type.

        Args:
            agent_type: Agent type identifier.
            kind: The quota kind to set.
            limit: The limit configuration.
        """
        if agent_type not in self._agent_quotas:
            self._agent_quotas[agent_type] = {}
        self._agent_quotas[agent_type][kind] = limit

    def get_limits(self, agent_type: str) -> dict[QuotaKind, QuotaLimit]:
        """Return all quota limits for an agent type.

        Args:
            agent_type: Agent type identifier.

        Returns:
            Dict of quota kind to limit, or empty dict if unknown.
        """
        return dict(self._agent_quotas.get(agent_type, {}))

    def get_usage(self, session_id: str) -> dict[QuotaKind, float] | None:
        """Return raw usage counters for a session.

        Args:
            session_id: The session identifier.

        Returns:
            Dict of quota kind to current usage value, or None if unknown.
        """
        usage = self._usage.get(session_id)
        if usage is None:
            return None
        return dict(usage)

    # ── Reset ─────────────────────────────────────────────────────────

    def reset_session(self, session_id: str) -> None:
        """Reset usage counters for a session (effective re-registration).

        Args:
            session_id: The session to reset.
        """
        agent_type = self._sessions.get(session_id)
        if agent_type is None:
            return
        self.unregister_session(session_id)
        self.register_session(session_id, agent_type)

    def reset_all(self) -> None:
        """Reset all tracked sessions."""
        snapshot = dict(self._sessions)
        self._usage.clear()
        self._sessions.clear()
        self._start_times.clear()
        for session_id, agent_type in snapshot.items():
            self.register_session(session_id, agent_type)

    # ── Statistics ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics for the quota governor.

        Returns:
            Dict with keys ``active_sessions``, ``agent_types``,
            ``total_usage``, ``exceeded_sessions``.
        """
        exceeded = 0
        total_usage: dict[str, float] = {
            "total_tokens": 0.0,
            "total_cost": 0.0,
            "total_steps": 0.0,
        }

        for session_id, agent_type in self._sessions.items():
            counters = self._usage.get(session_id, {})
            limits = self._agent_quotas.get(agent_type, {})
            total_usage["total_tokens"] += counters.get(QuotaKind.MAX_TOKENS, 0.0)
            total_usage["total_cost"] += counters.get(QuotaKind.MAX_COST, 0.0)
            total_usage["total_steps"] += counters.get(QuotaKind.MAX_STEPS, 0.0)

            for kind, limit in limits.items():
                used = counters.get(kind, 0.0)
                if limit.hard_limit > 0 and used >= limit.hard_limit:
                    exceeded += 1
                    break

        return {
            "active_sessions": len(self._sessions),
            "agent_types": list(set(self._sessions.values())),
            "total_usage": total_usage,
            "exceeded_sessions": exceeded,
        }
