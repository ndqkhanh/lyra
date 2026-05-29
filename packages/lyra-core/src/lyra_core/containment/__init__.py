"""Containment hierarchy — tmux-inspired Project/Team/Agent model.

Inspired by tmux's session/window/pane hierarchy:
  - Projects are hard isolation boundaries (like tmux sessions)
  - Teams are reusable agent groups (like tmux windows with winlink indirection)
  - Agents are individual agents (like tmux panes)
  - TopologyTree defines coordination structure (like tmux layout cells)
  - ConfigTree enforces configuration inheritance (like tmux options cascade)
  - ModeStack provides pluggable interaction layers (like tmux window modes)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence

from lyra_core.events import EventBus, EventCategory, ProjectEventBus
from lyra_core.protocol import AgentMode, AgentProtocol, Task

# ── Project ─────────────────────────────────────────────────────────────────


class ProjectStatus(str, Enum):
    CREATING = "creating"
    ACTIVE = "active"
    IDLE = "idle"
    ARCHIVING = "archiving"
    ARCHIVED = "archived"


@dataclass
class Project:
    """Hard isolation boundary. Like a tmux session.

    Each project has its own:
      - Key namespace (API keys, secrets)
      - Data store (project-scoped)
      - Event bus (project-scoped)
      - Configuration (project-level overrides)
    """

    id: str
    name: str
    status: ProjectStatus = ProjectStatus.CREATING
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    _team_memberships: dict[str, TeamMembership] = field(default_factory=dict, repr=False)
    _bus: ProjectEventBus | None = field(default=None, repr=False)

    @property
    def bus(self) -> ProjectEventBus:
        if self._bus is None:
            self._bus = ProjectEventBus(EventBus.get(), self.id)
        return self._bus

    @property
    def team_count(self) -> int:
        return len(self._team_memberships)

    @property
    def active_teams(self) -> list[str]:
        return [tid for tid, tm in self._team_memberships.items()
                if tm.active]

    def add_team(self, team: Team, index: int | None = None) -> TeamMembership:
        """Link a team into this project via a membership (winlink)."""
        if index is None:
            index = len(self._team_memberships)
        membership = TeamMembership(
            team_id=team.id,
            project_id=self.id,
            index=index,
        )
        self._team_memberships[team.id] = membership
        self.bus.emit(EventCategory.LIFECYCLE, "project.team_added",
                      payload={"team_id": team.id})
        return membership

    def remove_team(self, team_id: str) -> None:
        if team_id in self._team_memberships:
            del self._team_memberships[team_id]
            self.bus.emit(EventCategory.LIFECYCLE, "project.team_removed",
                          payload={"team_id": team_id})

    def list_teams(self) -> list[TeamMembership]:
        return sorted(self._team_memberships.values(), key=lambda m: m.index)


# ── Team & Membership ───────────────────────────────────────────────────────


@dataclass
class Team:
    """A reusable group of agents. Like a tmux window.

    Teams can be shared across projects via TeamMembership (winlink indirection).
    Each membership records project-specific positioning without modifying the
    team's actual agent composition.
    """

    id: str
    name: str
    topology: TopologyTree | None = None
    config: dict[str, Any] = field(default_factory=dict)
    _agents: dict[str, AgentProtocol] = field(default_factory=dict, repr=False)
    _active_agent_id: str = ""

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def active_agent(self) -> AgentProtocol | None:
        return self._agents.get(self._active_agent_id)

    @property
    def agent_ids(self) -> list[str]:
        # MRU order: active first, then last-used stack
        return list(self._agents.keys())

    def add_agent(self, agent: AgentProtocol, make_active: bool = True) -> None:
        self._agents[agent.identity.agent_id] = agent
        if make_active or not self._active_agent_id:
            self._active_agent_id = agent.identity.agent_id

    def remove_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
        if self._active_agent_id == agent_id:
            self._active_agent_id = next(iter(self._agents), "")

    def set_active(self, agent_id: str) -> None:
        if agent_id in self._agents:
            self._active_agent_id = agent_id

    async def run_all(self, task: Task) -> dict[str, str]:
        """Run the task on all agents, respecting topology."""
        if self.topology:
            return await self.topology.execute(self._agents, task)
        # Default: run on active agent only
        agent = self.active_agent
        if agent is None:
            return {}
        output = ""
        async for chunk in agent.run(task):
            output += chunk
        return {agent.identity.agent_id: output}


@dataclass
class TeamMembership:
    """Lightweight link between a Team and a Project. Like tmux's winlink.

    Each membership records the team's position (index) within the project's
    team list. The actual team composition is independent — shared teams
    can appear in multiple projects with different indices.
    """

    team_id: str
    project_id: str
    index: int = 0
    active: bool = True
    project_config_overrides: dict[str, Any] = field(default_factory=dict)


# ── Topology Tree ───────────────────────────────────────────────────────────


class TopologyKind(str, Enum):
    """Coordination patterns for agent teams. Like tmux layout cells."""

    PARALLEL = "parallel"         # Run all agents concurrently
    SEQUENTIAL = "sequential"      # Run agents one after another
    FAN_OUT = "fan_out"           # Distribute work items across agents
    FAN_IN = "fan_in"             # Collect results from multiple agents
    DEBATE = "debate"             # Agents argue, then converge
    DAG = "dag"                   # Dependency-ordered execution
    ROUND_ROBIN = "round_robin"   # Rotate through agents
    CONSENSUS = "consensus"       # Majority vote among agents


@dataclass
class TopologyTree:
    """Recursive coordination structure. Like tmux's layout_cell tree.

    Interior nodes define coordination patterns. Leaf nodes hold agent IDs.
    """

    kind: TopologyKind
    children: Sequence[TopologyTree | str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def agent_ids(self) -> list[str]:
        """Collect all agent IDs from leaf nodes."""
        result: list[str] = []
        for child in self.children:
            if isinstance(child, str):
                result.append(child)
            else:
                result.extend(child.agent_ids)
        return result

    async def execute(
        self, agents: dict[str, AgentProtocol], task: Task,
    ) -> dict[str, str]:
        """Execute the task through this topology tree."""
        if self.kind == TopologyKind.PARALLEL:
            return await self._execute_parallel(agents, task)
        elif self.kind == TopologyKind.SEQUENTIAL:
            return await self._execute_sequential(agents, task)
        elif self.kind == TopologyKind.DEBATE:
            return await self._execute_debate(agents, task)
        else:
            # Default: run on all leaf agents in parallel
            return await self._execute_parallel(agents, task)

    async def _execute_parallel(
        self, agents: dict[str, AgentProtocol], task: Task,
    ) -> dict[str, str]:
        leaf_ids = self.agent_ids
        results = {}
        async def _run_one(aid: str) -> tuple[str, str]:
            agent = agents.get(aid)
            if agent is None:
                return (aid, "")
            output = ""
            async for chunk in agent.run(task):
                output += chunk
            return (aid, output)

        coros = [_run_one(aid) for aid in leaf_ids]
        for coro in asyncio.as_completed(coros):
            aid, out = await coro
            results[aid] = out
        return results

    async def _execute_sequential(
        self, agents: dict[str, AgentProtocol], task: Task,
    ) -> dict[str, str]:
        results = {}
        for child in self.children:
            if isinstance(child, str):
                agent = agents.get(child)
                if agent:
                    out = ""
                    async for chunk in agent.run(task):
                        out += chunk
                    results[child] = out
            else:
                sub = await child.execute(agents, task)
                results.update(sub)
        return results

    async def _execute_debate(
        self, agents: dict[str, AgentProtocol], task: Task,
    ) -> dict[str, str]:
        # Run all agents independently, then collect arguments
        leaf_ids = self.agent_ids
        arguments: dict[str, str] = {}
        for aid in leaf_ids:
            agent = agents.get(aid)
            if agent:
                out = ""
                async for chunk in agent.run(task):
                    out += chunk
                arguments[aid] = out

        # Simple majority: pick the most common output prefix
        return {"consensus": self._pick_consensus(arguments),
                "arguments": str(arguments)}

    @staticmethod
    def _pick_consensus(arguments: dict[str, str]) -> str:
        """Simple consensus: return the output shared by most agents."""
        if not arguments:
            return ""
        # Count first-sentence agreement
        from collections import Counter
        first_sentences = [
            v.split(".")[0].strip()[:80] for v in arguments.values()
        ]
        counts = Counter(first_sentences)
        most_common = counts.most_common(1)[0]
        if most_common[1] > len(arguments) / 2:
            return f"Consensus ({most_common[1]}/{len(arguments)}): {most_common[0]}"
        return f"No consensus ({len(arguments)} agents disagreed)"

    # ── Factory methods ──────────────────────────────────────────────────

    @classmethod
    def parallel(cls, agent_ids: list[str]) -> TopologyTree:
        return cls(kind=TopologyKind.PARALLEL, children=list(agent_ids))

    @classmethod
    def sequential(cls, agent_ids: list[str]) -> TopologyTree:
        return cls(kind=TopologyKind.SEQUENTIAL, children=list(agent_ids))

    @classmethod
    def debate(cls, agent_ids: list[str]) -> TopologyTree:
        return cls(kind=TopologyKind.DEBATE, children=list(agent_ids))

    @classmethod
    def pipeline(cls, stages: list[list[str]]) -> TopologyTree:
        """Create a pipeline: each stage is a parallel group, stages run sequentially."""
        children = [cls.parallel(stage) for stage in stages]
        return cls(kind=TopologyKind.SEQUENTIAL, children=children)


# ── Configuration Inheritance ───────────────────────────────────────────────


@dataclass
class ConfigNode:
    """A node in the configuration inheritance tree.

    Like tmux's options with parent-pointer inheritance.
    Copy-on-write: overriding at a lower level materializes a local copy.
    """

    key: str
    value: Any
    parent: ConfigNode | None = None
    children: dict[str, ConfigNode] = field(default_factory=dict)

    def get(self, path: str | None = None) -> Any:
        """Walk up the parent chain to find a value."""
        if path is None:
            return self.value
        parts = path.split(".")
        current = self.children.get(parts[0])
        if current is None and self.parent:
            return self.parent.get(path)
        if current is None:
            return None
        if len(parts) == 1:
            return current.value
        return current.get(".".join(parts[1:]))

    def set_local(self, path: str, value: Any) -> ConfigNode:
        """Set a value at this node level (copy-on-write)."""
        parts = path.split(".")
        key = parts[0]
        if key not in self.children:
            # Copy parent value if exists
            parent_val = self.get(key)
            self.children[key] = ConfigNode(key=key, value=parent_val,
                                            parent=self)
        child = self.children[key]
        if len(parts) == 1:
            child.value = value
        else:
            child.set_local(".".join(parts[1:]), value)
        return child


class ConfigTree:
    """Three-level configuration inheritance: Global → Project → Team → Agent.

    Like tmux's options cascade: server → session → window → pane.
    Each level can override any setting. Lookups walk up the parent chain.
    """

    def __init__(self) -> None:
        self._global = ConfigNode(key="global", value=None)

    def get(self, scope: str, scope_id: str, key: str) -> Any:
        """Get a configuration value, walking up the inheritance chain."""
        node = self._find_node(scope, scope_id)
        if node:
            val = node.get(key)
            if val is not None:
                return val
        return self._global.get(key)

    def set(self, scope: str, scope_id: str, key: str, value: Any) -> None:
        """Set a configuration value at a specific scope level."""
        node = self._ensure_node(scope, scope_id)
        node.set_local(key, value)

    def _find_node(self, scope: str, scope_id: str) -> ConfigNode | None:
        return self._global.children.get(f"{scope}:{scope_id}")

    def _ensure_node(self, scope: str, scope_id: str) -> ConfigNode:
        node_key = f"{scope}:{scope_id}"
        if node_key not in self._global.children:
            self._global.children[node_key] = ConfigNode(
                key=node_key, value=None, parent=self._global,
            )
        return self._global.children[node_key]


# ── Mode Stack ──────────────────────────────────────────────────────────────


class ModeStack:
    """Pluggable interaction layers for agents. Like tmux's window_mode stack.

    Modes stack on top of each other. The topmost mode intercepts input.
    When a mode exits, it's popped and the underlying mode is restored.

    Built-in modes:
      - base: default conversation mode
      - review: reviewing accumulated context
      - debug: step-through debugging
      - edit: intercepting tool calls for editing
    """

    def __init__(self) -> None:
        self._modes: list[AgentMode] = []

    @property
    def top(self) -> AgentMode | None:
        return self._modes[-1] if self._modes else None

    @property
    def depth(self) -> int:
        return len(self._modes)

    @property
    def all_modes(self) -> tuple[AgentMode, ...]:
        return tuple(self._modes)

    async def push(self, mode: AgentMode, agent: AgentProtocol) -> None:
        """Push a new mode onto the stack. The previous top is suspended."""
        self._modes.append(mode)
        await mode.on_enter(agent)

    async def pop(self, agent: AgentProtocol) -> AgentMode:
        """Pop the topmost mode. The previous mode is restored."""
        if not self._modes:
            raise IndexError("Mode stack is empty")
        mode = self._modes.pop()
        await mode.on_exit(agent)
        return mode

    async def handle_input(self, agent: AgentProtocol, text: str) -> str:
        """Route input through the mode stack. Topmost mode gets first chance."""
        if self._modes:
            top = self.top
            if top is not None:
                result = await top.handle_input(agent, text)
                if result is not None:
                    return result
        return text

    async def transform_output(self, agent: AgentProtocol, chunk: str) -> str:
        """Route output through the mode stack for transformation."""
        for mode in reversed(self._modes):
            chunk = await mode.transform_output(agent, chunk)
        return chunk


# ── Project Registry ────────────────────────────────────────────────────────


class ProjectRegistry:
    """Central registry of all projects. Like tmux's server-level session tree.

    Provides:
      - O(1) lookup by project ID
      - Project-scoped event buses
      - Cross-project team sharing
    """

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._teams: dict[str, Team] = {}
        self._config = ConfigTree()

    # ── Projects ─────────────────────────────────────────────────────────

    def create_project(self, name: str, project_id: str | None = None,
                       config: dict[str, Any] | None = None) -> Project:
        pid = project_id or f"proj_{len(self._projects):04x}"
        project = Project(id=pid, name=name, config=config or {})
        self._projects[pid] = project
        return project

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def remove_project(self, project_id: str) -> None:
        self._projects.pop(project_id, None)

    # ── Teams ────────────────────────────────────────────────────────────

    def create_team(self, name: str, team_id: str | None = None) -> Team:
        tid = team_id or f"team_{len(self._teams):04x}"
        team = Team(id=tid, name=name)
        self._teams[tid] = team
        return team

    def get_team(self, team_id: str) -> Team | None:
        return self._teams.get(team_id)

    def link_team(self, project_id: str, team_id: str,
                  index: int | None = None) -> TeamMembership | None:
        """Link a team into a project via a membership (winlink)."""
        project = self._projects.get(project_id)
        team = self._teams.get(team_id)
        if project is None or team is None:
            return None
        return project.add_team(team, index)

    # ── Config ───────────────────────────────────────────────────────────

    @property
    def config_tree(self) -> ConfigTree:
        return self._config

    def set_config(self, scope: str, scope_id: str, key: str, value: Any) -> None:
        self._config.set(scope, scope_id, key, value)

    def get_config(self, scope: str, scope_id: str, key: str, default: Any = None) -> Any:
        val = self._config.get(scope, scope_id, key)
        return val if val is not None else default


# ── Singleton ────────────────────────────────────────────────────────────────

_registry: ProjectRegistry | None = None


def get_project_registry() -> ProjectRegistry:
    global _registry
    if _registry is None:
        _registry = ProjectRegistry()
    return _registry
