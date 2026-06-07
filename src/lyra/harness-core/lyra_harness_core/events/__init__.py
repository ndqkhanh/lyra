"""Unified EventBus — P4-X BREAKTHROUGH primitive.

Bounded circular buffer with JSONL persistence, subscription filtering,
and boot-scoped event IDs. Single unified dispatch across the codebase.
"""
from __future__ import annotations

from lyra.harness_core.events.eventbus import (
    Event,
    EventBus,
    Subscription,
    get_event_bus,
    set_event_bus,
)

__all__ = [
    "Event",
    "EventBus",
    "get_event_bus",
    "set_event_bus",
    "Subscription",
]
