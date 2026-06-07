"""
Fleet Dashboard — Agent View-style desktop dashboard for monitoring all
active sessions across the Lyra agent fleet.

Provides real-time session cards, cost breakdown, message peek/reply,
and WebSocket push integration.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from lyra.observability.dashboard import MetricsDashboard
from lyra.sessions.persist import SessionManager, SessionStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & config
# ---------------------------------------------------------------------------


class SortBy(str, Enum):
    """Sort order for the fleet view."""

    STATUS = "status"
    COST = "cost"
    TOKENS = "tokens"
    RECENT = "recent"
    MODEL = "model"


@dataclass
class DashboardConfig:
    """Configuration for the fleet dashboard.

    Attributes:
        refresh_interval: Seconds between automatic refreshes.
        max_cards: Maximum number of session cards to display.
        sort_by: Default sort order for sessions.
        enable_websocket: Whether to enable WebSocket push.
        websocket_url: WebSocket endpoint URL (used when push is enabled).
        peek_message_count: Number of recent messages to show on peek.
    """

    refresh_interval: int = 5
    max_cards: int = 50
    sort_by: SortBy = SortBy.RECENT
    enable_websocket: bool = False
    websocket_url: str = ""
    peek_message_count: int = 20

    def merge(self, overrides: dict[str, Any]) -> DashboardConfig:
        """Return a new DashboardConfig with overridden values."""
        current = {
            "refresh_interval": self.refresh_interval,
            "max_cards": self.max_cards,
            "sort_by": self.sort_by.value if isinstance(self.sort_by, SortBy) else self.sort_by,
            "enable_websocket": self.enable_websocket,
            "websocket_url": self.websocket_url,
            "peek_message_count": self.peek_message_count,
        }
        for key, value in overrides.items():
            if key in current:
                current[key] = value
        sort_val = current["sort_by"]
        if isinstance(sort_val, str):
            current["sort_by"] = SortBy(sort_val)
        return DashboardConfig(**current)

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to dictionary."""
        return {
            "refresh_interval": self.refresh_interval,
            "max_cards": self.max_cards,
            "sort_by": self.sort_by.value,
            "enable_websocket": self.enable_websocket,
            "websocket_url": self.websocket_url,
            "peek_message_count": self.peek_message_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DashboardConfig:
        """Create config from dictionary."""
        sort_val = data.get("sort_by", "recent")
        return cls(
            refresh_interval=data.get("refresh_interval", 5),
            max_cards=data.get("max_cards", 50),
            sort_by=SortBy(sort_val) if isinstance(sort_val, str) else sort_val,
            enable_websocket=data.get("enable_websocket", False),
            websocket_url=data.get("websocket_url", ""),
            peek_message_count=data.get("peek_message_count", 20),
        )


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class SessionCard:
    """A single session card rendered in the fleet view.

    Attributes:
        session_id: Unique session identifier.
        status: Current session lifecycle status.
        agent_id: The agent that owns this session.
        model: Model identifier used by this session.
        total_cost: Accumulated cost in dollars.
        total_tokens: Total tokens consumed.
        tool_calls: Number of tool calls made.
        errors: Number of errors encountered.
        latency: Total latency in seconds.
        last_message: Preview of the most recent message.
        started_at: ISO-formatted session start timestamp.
        updated_at: ISO-formatted last-updated timestamp.
        expanded: Whether the card is currently expanded in the UI.
        metadata: Arbitrary additional card metadata.
    """

    session_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    agent_id: str = ""
    model: str = ""
    total_cost: float = 0.0
    total_tokens: int = 0
    tool_calls: int = 0
    errors: int = 0
    latency: float = 0.0
    last_message: str = ""
    started_at: str = ""
    updated_at: str = ""
    expanded: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize card to dictionary."""
        status_val = self.status.value if isinstance(self.status, Enum) else self.status
        return {
            "session_id": self.session_id,
            "status": status_val,
            "agent_id": self.agent_id,
            "model": self.model,
            "total_cost": round(self.total_cost, 6),
            "total_tokens": self.total_tokens,
            "tool_calls": self.tool_calls,
            "errors": self.errors,
            "latency": round(self.latency, 4),
            "last_message": self.last_message[:120],
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "expanded": self.expanded,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionCard:
        """Create card from dictionary."""
        status_val = data.get("status", "active")
        return cls(
            session_id=data["session_id"],
            status=SessionStatus(status_val) if isinstance(status_val, str) else status_val,
            agent_id=data.get("agent_id", ""),
            model=data.get("model", ""),
            total_cost=data.get("total_cost", 0.0),
            total_tokens=data.get("total_tokens", 0),
            tool_calls=data.get("tool_calls", 0),
            errors=data.get("errors", 0),
            latency=data.get("latency", 0.0),
            last_message=data.get("last_message", ""),
            started_at=data.get("started_at", ""),
            updated_at=data.get("updated_at", ""),
            expanded=data.get("expanded", False),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DashboardState:
    """The full rendered state of the fleet dashboard.

    Attributes:
        cards: All session cards currently displayed.
        total_sessions: Total session count (including those beyond max_cards).
        total_cost: Aggregate cost across all tracked sessions.
        total_tokens: Aggregate tokens across all tracked sessions.
        total_errors: Aggregate errors across all tracked sessions.
        total_tool_calls: Aggregate tool calls across all tracked sessions.
        cost_by_model: Per-model cost breakdown.
        last_updated: Timestamp of last dashboard refresh.
        config: The active dashboard configuration.
    """

    cards: list[SessionCard] = field(default_factory=list)
    total_sessions: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    total_errors: int = 0
    total_tool_calls: int = 0
    cost_by_model: dict[str, float] = field(default_factory=dict)
    last_updated: str = ""
    config: DashboardConfig = field(default_factory=DashboardConfig)

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary."""
        return {
            "cards": [c.to_dict() for c in self.cards],
            "total_sessions": self.total_sessions,
            "total_cost": round(self.total_cost, 6),
            "total_tokens": self.total_tokens,
            "total_errors": self.total_errors,
            "total_tool_calls": self.total_tool_calls,
            "cost_by_model": {k: round(v, 6) for k, v in self.cost_by_model.items()},
            "last_updated": self.last_updated,
            "config": self.config.to_dict(),
        }


# ---------------------------------------------------------------------------
# FleetDashboard
# ---------------------------------------------------------------------------


class FleetDashboard:
    """Agent View-style desktop dashboard for monitoring all active sessions.

    Renders session cards with status, model, cost, and token counts.
    Supports peek, reply, cost breakdown, and real-time WebSocket push.

    Integrates with:
    - ``MetricsDashboard`` for per-session observability metrics.
    - ``SessionManager`` for persisted session records.
    """

    def __init__(
        self,
        metrics_dashboard: MetricsDashboard | None = None,
        session_manager: SessionManager | None = None,
        config: DashboardConfig | None = None,
    ) -> None:
        """Initialize the fleet dashboard.

        Args:
            metrics_dashboard: Shared metrics dashboard (or creates a new one).
            session_manager: Shared session manager (or creates a new one).
            config: Dashboard configuration.
        """
        self._metrics = metrics_dashboard or MetricsDashboard()
        self._session_manager = session_manager or SessionManager()
        self._config = config or DashboardConfig()
        self._ws_clients: set[Callable[[dict[str, Any]], None]] = set()
        self._model_map: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def config(self) -> DashboardConfig:
        """Current dashboard configuration."""
        return self._config

    def update_config(self, overrides: dict[str, Any]) -> DashboardConfig:
        """Update dashboard configuration via merge.

        Args:
            overrides: Configuration fields to override.

        Returns:
            The new (immutable) DashboardConfig instance.
        """
        self._config = self._config.merge(overrides)
        return self._config

    # ------------------------------------------------------------------
    # Fleet view
    # ------------------------------------------------------------------

    def render_fleet_view(self, sort_by: SortBy | None = None) -> DashboardState:
        """Render the full fleet view with all session cards.

        Args:
            sort_by: Optional override sort order. Uses config default if omitted.

        Returns:
            A DashboardState with all rendered cards and aggregate totals.
        """
        sort_key = sort_by or self._config.sort_by
        sessions = self._session_manager.list_sessions(
            status=None,
            limit=self._config.max_cards * 2,  # Fetch more than we display
        )

        # Build cards from persisted session records
        cards: list[SessionCard] = []
        for record in sessions:
            metrics = self._metrics.get_session(record.session_id)
            last_msg = ""
            if record.steps:
                last_step = record.steps[-1]
                last_msg = json.dumps(last_step) if isinstance(last_step, dict) else str(last_step)

            model = self._model_map.get(record.session_id, "")

            card = SessionCard(
                session_id=record.session_id,
                status=record.status,
                agent_id=record.agent_id,
                model=model,
                total_cost=metrics.total_cost if metrics else 0.0,
                total_tokens=metrics.total_tokens if metrics else 0,
                tool_calls=metrics.tool_calls if metrics else 0,
                errors=metrics.errors if metrics else 0,
                latency=metrics.total_latency if metrics else 0.0,
                last_message=last_msg[:120],
                started_at=record.created_at.isoformat() if record.created_at else "",
                updated_at=record.updated_at.isoformat() if record.updated_at else "",
                expanded=False,
                metadata=record.metadata,
            )
            cards.append(card)

        # Sort
        cards = self._sort_cards(cards, sort_key)

        # Apply max_cards limit
        cards = cards[: self._config.max_cards]

        # Aggregate totals
        total_cost = sum(c.total_cost for c in cards)
        total_tokens = sum(c.total_tokens for c in cards)
        total_errors = sum(c.errors for c in cards)
        total_tool_calls = sum(c.tool_calls for c in cards)

        # Per-model breakdown
        cost_by_model: dict[str, float] = {}
        for c in cards:
            model_key = c.model or "unknown"
            cost_by_model.setdefault(model_key, 0.0)
            cost_by_model[model_key] += c.total_cost

        return DashboardState(
            cards=cards,
            total_sessions=len(sessions),
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_errors=total_errors,
            total_tool_calls=total_tool_calls,
            cost_by_model=cost_by_model,
            last_updated=datetime.now(timezone.utc).isoformat(),
            config=self._config,
        )

    def session_card(self, session_id: str) -> SessionCard | None:
        """Get a single session card by ID.

        Args:
            session_id: The session identifier.

        Returns:
            SessionCard if found, None otherwise.
        """
        state = self.render_fleet_view()
        for card in state.cards:
            if card.session_id == session_id:
                return card
        return None

    # ------------------------------------------------------------------
    # Peek & reply
    # ------------------------------------------------------------------

    def peek_session(self, session_id: str, n: int | None = None) -> str:
        """Read the last N messages from a session without joining.

        Args:
            session_id: The session identifier.
            n: Number of recent messages to show. Uses config default if omitted.

        Returns:
            Formatted string of recent messages.
        """
        count = n if n is not None else self._config.peek_message_count
        steps = self._session_manager.get_steps(session_id)

        if not steps:
            return f"No messages found for session {session_id}."

        recent = steps[-count:]
        parts: list[str] = []
        for i, step in enumerate(recent):
            if isinstance(step, dict):
                content = step.get("content", step.get("message", json.dumps(step)))
            else:
                content = str(step)
            parts.append(f"[{i + 1}] {content[:500]}")

        return "\n---\n".join(parts)

    def reply_session(self, session_id: str, message: str) -> bool:
        """Inject a message into a session's step log.

        Args:
            session_id: The session identifier.
            message: The message content to inject.

        Returns:
            True if the message was appended, False if session not found.
        """
        step_data: dict[str, Any] = {
            "type": "user_reply",
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return self._session_manager.append_step(session_id, step_data)

    # ------------------------------------------------------------------
    # Cost summary
    # ------------------------------------------------------------------

    def cost_summary(self) -> dict[str, Any]:
        """Compute total cost across all sessions with per-model breakdown.

        Returns:
            Dict with ``total_cost``, ``per_model`` breakdown,
            ``total_tokens``, ``average_cost_per_token``, and
            ``session_count``.
        """
        state = self.render_fleet_view()

        per_model: dict[str, dict[str, float]] = {}
        for card in state.cards:
            model_key = card.model or "unknown"
            if model_key not in per_model:
                per_model[model_key] = {"cost": 0.0, "tokens": 0, "session_count": 0}
            per_model[model_key]["cost"] += card.total_cost
            per_model[model_key]["tokens"] += card.total_tokens
            per_model[model_key]["session_count"] += 1

        total_tokens = state.total_tokens
        avg_cost_per_token = (
            round(state.total_cost / total_tokens, 8) if total_tokens > 0 else 0.0
        )

        return {
            "total_cost": round(state.total_cost, 6),
            "total_tokens": total_tokens,
            "average_cost_per_token": avg_cost_per_token,
            "session_count": state.total_sessions,
            "per_model": {
                model: {
                    "cost": round(v["cost"], 6),
                    "tokens": int(v["tokens"]),
                    "session_count": int(v["session_count"]),
                }
                for model, v in sorted(per_model.items())
            },
        }

    # ------------------------------------------------------------------
    # Model tracking
    # ------------------------------------------------------------------

    def set_session_model(self, session_id: str, model: str) -> None:
        """Record the model identifier for a session.

        Args:
            session_id: The session identifier.
            model: Model identifier (e.g. "sonnet-4.6", "haiku-4.5").
        """
        self._model_map[session_id] = model

    # ------------------------------------------------------------------
    # WebSocket push
    # ------------------------------------------------------------------

    def register_ws_client(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a WebSocket callback for real-time push updates.

        The callback will be invoked with a serialized DashboardState dict
        each time ``push_update`` is called.

        Args:
            callback: A callable accepting a dict payload.
        """
        self._ws_clients.add(callback)

    def unregister_ws_client(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Remove a previously registered WebSocket callback.

        Args:
            callback: The callable to remove.
        """
        self._ws_clients.discard(callback)

    def push_update(self) -> None:
        """Push the current fleet state to all registered WebSocket clients.

        Called periodically or on significant state changes.
        """
        if not self._config.enable_websocket or not self._ws_clients:
            return

        state = self.render_fleet_view()
        payload = state.to_dict()

        stale_clients: list[Callable[[dict[str, Any]], None]] = []
        for callback in self._ws_clients:
            try:
                callback(payload)
            except Exception:
                logger.exception("WebSocket callback failed; removing client")
                stale_clients.append(callback)

        for cb in stale_clients:
            self._ws_clients.discard(cb)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sort_cards(cards: list[SessionCard], sort_by: SortBy) -> list[SessionCard]:
        """Sort cards according to the given criterion.

        Args:
            cards: List of session cards.
            sort_by: Sort criterion.

        Returns:
            New sorted list.
        """
        if sort_by == SortBy.STATUS:
            def _status_key(c: SessionCard) -> str:
                return c.status.value if isinstance(c.status, Enum) else str(c.status)
            return sorted(cards, key=lambda c: (_status_key(c), c.updated_at), reverse=True)
        elif sort_by == SortBy.COST:
            return sorted(cards, key=lambda c: c.total_cost, reverse=True)
        elif sort_by == SortBy.TOKENS:
            return sorted(cards, key=lambda c: c.total_tokens, reverse=True)
        elif sort_by == SortBy.MODEL:
            return sorted(cards, key=lambda c: (c.model or "", c.session_id))
        else:
            # SortBy.RECENT — most recently updated first
            return sorted(cards, key=lambda c: c.updated_at, reverse=True)
