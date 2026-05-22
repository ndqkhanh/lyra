"""Event-Sourced Agent Loop — Agent Loop 2.0 with Multi-Stream execution and speculative planning."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    AGENT_STARTED = auto()
    THOUGHT_GENERATED = auto()
    TOOL_CALLED = auto()
    TOOL_RESULT = auto()
    ERROR_CAUGHT = auto()
    STEP_COMPLETED = auto()
    AGENT_FINISHED = auto()


@dataclass
class StepEvent:
    event_type: EventType
    agent_id: str
    timestamp: float
    data: dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None


class EventLog:
    """Append-only event log — the source of truth for agent execution."""

    def __init__(self):
        self.events: list[StepEvent] = []
        self._index: dict[str, list[int]] = {}

    def emit(self, event: StepEvent) -> int:
        idx = len(self.events)
        self.events.append(event)
        if event.agent_id not in self._index:
            self._index[event.agent_id] = []
        self._index[event.agent_id].append(idx)
        return idx

    def replay(self, start: int = 0) -> list[StepEvent]:
        return self.events[start:]

    def get_agent_events(self, agent_id: str) -> list[StepEvent]:
        indices = self._index.get(agent_id, [])
        return [self.events[i] for i in indices]

    def project(self, agent_id: str) -> dict[str, Any]:
        """Project event log to current working state for an agent."""
        state = {"step": 0, "tools_called": [], "errors": [], "completed": False}
        for event in self.get_agent_events(agent_id):
            state["step"] += 1
            if event.event_type == EventType.TOOL_CALLED:
                state["tools_called"].append(event.data.get("tool", "unknown"))
            elif event.event_type == EventType.ERROR_CAUGHT:
                state["errors"].append(event.data.get("error", "unknown"))
            elif event.event_type == EventType.AGENT_FINISHED:
                state["completed"] = True
        return state

    @property
    def size(self) -> int:
        return len(self.events)


class MultiStreamExecutor:
    """Separates prompts, thinking, and I/O into parallel streams."""

    def __init__(self):
        self.thinking_stream: asyncio.Queue = asyncio.Queue()
        self.io_stream: asyncio.Queue = asyncio.Queue()
        self.output_stream: asyncio.Queue = asyncio.Queue()

    async def execute_parallel(self, prompt: str, tools: list[str]) -> dict[str, Any]:
        async def thinking():
            await asyncio.sleep(0.1)  # simulated thinking
            await self.thinking_stream.put({"type": "thought", "content": f"Analyzing {prompt[:20]}..."})

        async def io():
            await asyncio.sleep(0.05)  # simulated I/O
            await self.io_stream.put({"type": "io", "tools": tools})

        await asyncio.gather(thinking(), io())
        thoughts = []
        while not self.thinking_stream.empty():
            thoughts.append(await self.thinking_stream.get())

        return {"thoughts": thoughts, "status": "parallel_executed"}


class SpeculativePlanner:
    """Uses idle time (waiting for tool results) to plan multiple future paths."""

    def __init__(self, max_speculations: int = 3):
        self.max_speculations = max_speculations
        self.plans: list[dict[str, Any]] = []

    async def speculate(self, current_state: dict[str, Any], idle_time: float) -> list[dict[str, Any]]:
        """Generate speculative plans during idle time."""
        if idle_time < 0.1:
            return []
        plans = []
        for i in range(min(self.max_speculations, int(idle_time / 0.1))):
            plans.append({
                "plan_id": f"spec_{i}",
                "strategy": f"alternative_{i}",
                "expected_utility": 1.0 - (i * 0.2),
            })
        self.plans.extend(plans)
        return plans


class RuntimeHarnessAdaptor:
    """Adapts tools and permissions dynamically based on context."""

    def __init__(self):
        self.tool_registry: dict[str, dict[str, Any]] = {}
        self.permission_mode: str = "standard"

    def register_tool(self, tool_name: str, metadata: dict[str, Any]) -> None:
        self.tool_registry[tool_name] = metadata

    def adapt_tools(self, context: dict[str, Any]) -> list[str]:
        """Select optimal tools based on current context."""
        available = list(self.tool_registry.keys())
        task_type = context.get("task_type", "general")
        if task_type == "code":
            return [t for t in available if any(kw in t for kw in ["code", "file", "git"])]
        elif task_type == "research":
            return [t for t in available if any(kw in t for kw in ["search", "read", "web"])]
        return available

    def set_permission_mode(self, mode: str) -> None:
        self.permission_mode = mode


class EventSourcedAgentLoop:
    """Agent Loop 2.0: Event-sourced, multi-stream, speculative, adaptable."""

    def __init__(self, agent_id: str = "lyra"):
        self.agent_id = agent_id
        self.log = EventLog()
        self.executor = MultiStreamExecutor()
        self.planner = SpeculativePlanner()
        self.adaptor = RuntimeHarnessAdaptor()

    async def step(self, prompt: str, tools: list[str]) -> dict[str, Any]:
        self.log.emit(StepEvent(EventType.AGENT_STARTED, self.agent_id, self._now(), {"prompt": prompt}))

        adapted_tools = self.adaptor.adapt_tools({"task_type": prompt.split()[0] if prompt else "general"})
        self.log.emit(StepEvent(EventType.THOUGHT_GENERATED, self.agent_id, self._now(), {"prompt_length": len(prompt)}))

        exec_result = await self.executor.execute_parallel(prompt, adapted_tools)
        self.log.emit(StepEvent(EventType.TOOL_CALLED, self.agent_id, self._now(), exec_result))

        spec_plans = await self.planner.speculate({}, idle_time=0.5)
        self.log.emit(StepEvent(EventType.STEP_COMPLETED, self.agent_id, self._now(), {"spec_plans": len(spec_plans)}))

        return {
            "agent_id": self.agent_id,
            "execution": exec_result,
            "speculative_plans": len(spec_plans),
            "state": self.log.project(self.agent_id),
        }

    def _now(self) -> float:
        return __import__("time").time()
