"""
Event Bus - Typed pub/sub for cross-module communication.

Inspired by OpenHuman's event bus architecture:
- Typed events with Pydantic
- Native request/response (zero serialization)
- Domain events for agent coordination
- Subscription handles with RAII cleanup
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel


class EventPriority(Enum):
    """Event priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class Event(BaseModel):
    """Base event class."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    metadata: dict[str, Any] = field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


# Domain Events for Agent Coordination

class AgentStarted(Event):
    """Agent started event."""

    event_type: str = "agent.started"
    agent_id: str
    agent_type: str


class AgentCompleted(Event):
    """Agent completed event."""

    event_type: str = "agent.completed"
    agent_id: str
    agent_type: str
    result: dict[str, Any] | None = None


class AgentFailed(Event):
    """Agent failed event."""

    event_type: str = "agent.failed"
    agent_id: str
    agent_type: str
    error: str


class ScanCompleted(Event):
    """Scan completed event."""

    event_type: str = "scan.completed"
    target: str
    findings: list[dict[str, Any]]
    scan_type: str


class VulnerabilityDiscovered(Event):
    """Vulnerability discovered event."""

    event_type: str = "vulnerability.discovered"
    cve: str
    severity: str
    exploitable: bool
    affected_asset: str
    affected_service: str


class ExploitAttempted(Event):
    """Exploit attempted event."""

    event_type: str = "exploit.attempted"
    target: str
    exploit_name: str
    success: bool
    evidence: str | None = None


class MemoryIngested(Event):
    """Memory ingested event."""

    event_type: str = "memory.ingested"
    namespace: str
    doc_count: int


class IntegrationSynced(Event):
    """Integration synced event."""

    event_type: str = "integration.synced"
    provider: str
    items_fetched: int


@dataclass
class Subscription:
    """Event subscription handle."""

    subscription_id: str
    event_type: str
    handler: Callable
    priority: EventPriority = EventPriority.NORMAL

    def __hash__(self):
        return hash(self.subscription_id)


class EventBus:
    """
    Event bus for cross-module communication.

    Features:
    - Typed pub/sub
    - Priority-based delivery
    - Async handlers
    - Subscription management
    """

    def __init__(self):
        """Initialize event bus."""
        self._subscriptions: dict[str, set[Subscription]] = {}
        self._event_history: list[Event] = []
        self._max_history = 1000

    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> Subscription:
        """
        Subscribe to events.

        Args:
            event_type: Event type to subscribe to
            handler: Async handler function
            priority: Subscription priority

        Returns:
            Subscription handle
        """
        subscription = Subscription(
            subscription_id=str(uuid4()),
            event_type=event_type,
            handler=handler,
            priority=priority,
        )

        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = set()

        self._subscriptions[event_type].add(subscription)

        return subscription

    def unsubscribe(self, subscription: Subscription):
        """
        Unsubscribe from events.

        Args:
            subscription: Subscription handle
        """
        if subscription.event_type in self._subscriptions:
            self._subscriptions[subscription.event_type].discard(subscription)

    async def publish(self, event: Event):
        """
        Publish event to subscribers.

        Args:
            event: Event to publish
        """
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Get subscribers
        subscribers = self._subscriptions.get(event.event_type, set())

        if not subscribers:
            return

        # Sort by priority
        sorted_subscribers = sorted(
            subscribers,
            key=lambda s: s.priority.value,
            reverse=True,
        )

        # Call handlers
        tasks = []
        for subscription in sorted_subscribers:
            task = asyncio.create_task(self._call_handler(subscription.handler, event))
            tasks.append(task)

        # Wait for all handlers
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _call_handler(self, handler: Callable, event: Event):
        """
        Call event handler.

        Args:
            handler: Handler function
            event: Event
        """
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            # Log error but don't propagate
            print(f"Error in event handler: {e}")

    def get_history(
        self,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """
        Get event history.

        Args:
            event_type: Filter by event type
            limit: Maximum events to return

        Returns:
            List of events
        """
        events = self._event_history

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()

    def get_stats(self) -> dict[str, Any]:
        """
        Get event bus statistics.

        Returns:
            Statistics dictionary
        """
        event_counts = {}
        for event in self._event_history:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1

        return {
            "total_events": len(self._event_history),
            "total_subscriptions": sum(len(subs) for subs in self._subscriptions.values()),
            "event_types": len(self._subscriptions),
            "event_counts": event_counts,
        }
