"""Cross-component messaging system.

Phase 4, Week 1: System Integration - Cross-Component Communication

Provides event bus and message routing for component coordination.
"""
from lyra_core.messaging.eventbus import EventBus
from lyra_core.messaging.message import Message, MessageHandler
from lyra_core.messaging.router import MessageRouter
from lyra_core.messaging.types import MessageType

__all__ = [
    "EventBus",
    "Message",
    "MessageHandler",
    "MessageRouter",
    "MessageType",
]
