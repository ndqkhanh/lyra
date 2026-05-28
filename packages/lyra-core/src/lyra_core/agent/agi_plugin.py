"""AGI-aware plugin for the Hermes-style AgentLoop.

Connects the existing AgentLoop to the EventSourcedAgentLoop for
event-sourced logging, multi-stream execution, and speculative planning.
Acts as a duck-typed plugin (on_session_start, pre_llm_call, etc.).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from lyra_core.agent.event_sourced_loop import (
    EventLog,
    EventSourcedAgentLoop,
    EventType,
    StepEvent,
)

logger = logging.getLogger(__name__)


@dataclass
class SessionCtx:
    session_id: str
    user_text: str = ""


class AGILoopPlugin:
    """Plugin that bridges AgentLoop → EventSourcedAgentLoop for AGI-level logging."""

    def __init__(self, agent_id: str = "lyra"):
        self.agent_id = agent_id
        self._es_loop = EventSourcedAgentLoop(agent_id)
        self._active = True

    @property
    def event_log(self) -> EventLog:
        return self._es_loop.log

    # --- Duck-typed plugin hooks ---

    def on_session_start(self, ctx: SessionCtx) -> None:
        if not self._active:
            return
        self._es_loop.log.emit(StepEvent(
            EventType.AGENT_STARTED, self.agent_id,
            self._now(), {"session_id": ctx.session_id, "user_text": ctx.user_text[:80]}
        ))
        logger.info(f"AGI: session {ctx.session_id} started")

    def pre_llm_call(self, ctx: Any) -> None:
        if not self._active:
            return
        self._es_loop.log.emit(StepEvent(
            EventType.THOUGHT_GENERATED, self.agent_id,
            self._now(), {"prompt_length": len(str(ctx))}
        ))

    def pre_tool_call(self, ctx: Any) -> None:
        if not self._active:
            return
        tool_name = getattr(ctx, "tool_name", "unknown")
        self._es_loop.log.emit(StepEvent(
            EventType.TOOL_CALLED, self.agent_id,
            self._now(), {"tool": tool_name}
        ))

    def post_tool_call(self, ctx: Any) -> None:
        if not self._active:
            return
        self._es_loop.log.emit(StepEvent(
            EventType.TOOL_RESULT, self.agent_id,
            self._now(), {}
        ))

    def on_session_end(self, ctx: SessionCtx) -> None:
        if not self._active:
            return
        self._es_loop.log.emit(StepEvent(
            EventType.AGENT_FINISHED, self.agent_id,
            self._now(), {"session_id": ctx.session_id}
        ))
        state = self._es_loop.log.project(self.agent_id)
        logger.info(f"AGI: session {ctx.session_id} ended — {state['step']} steps, {len(state['tools_called'])} tools")

    def get_event_log_summary(self) -> dict[str, Any]:
        """Return AGI event log summary for the orchestrator."""
        return {
            "agent_id": self.agent_id,
            "total_events": self._es_loop.log.size,
            "state": self._es_loop.log.project(self.agent_id),
        }

    def _now(self) -> float:
        import time
        return time.time()
