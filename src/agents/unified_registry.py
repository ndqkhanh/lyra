"""
Unified agent registry for Lyra RSI + ECC agents.

This module provides a unified registry that combines Lyra's native
agents with imported ECC agents, enabling intelligent dispatch based
on task requirements.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from src.agents.base import Agent, AgentCapability
from src.core.task import Task, TaskType


class AgentSource(str, Enum):
    """Source of agent."""

    LYRA = "lyra"
    ECC = "ecc"


@dataclass
class AgentMetadata:
    """Metadata about a registered agent."""

    agent: Agent
    source: AgentSource
    namespace: str  # e.g., "lyra:code" or "ecc:planner"
    capabilities: List[AgentCapability]
    languages: Set[str] = field(default_factory=set)
    frameworks: Set[str] = field(default_factory=set)
    priority: int = 0  # Higher priority agents selected first
    usage_count: int = 0
    success_count: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count

    @property
    def qualified_name(self) -> str:
        """Get fully qualified agent name."""
        return f"{self.source.value}:{self.agent.agent_id}"


class UnifiedAgentRegistry:
    """
    Unified registry for Lyra RSI + ECC agents.

    Manages both Lyra's native agents and imported ECC agents,
    providing intelligent dispatch based on task requirements.
    """

    def __init__(self):
        """Initialize unified registry."""
        self.agents: Dict[str, AgentMetadata] = {}
        self._capability_index: Dict[TaskType, Set[str]] = {}
        self._language_index: Dict[str, Set[str]] = {}
        self._framework_index: Dict[str, Set[str]] = {}

    def register(
        self,
        agent: Agent,
        source: AgentSource,
        capabilities: List[AgentCapability],
        languages: Optional[Set[str]] = None,
        frameworks: Optional[Set[str]] = None,
        priority: int = 0,
    ) -> str:
        """
        Register an agent.

        Args:
            agent: Agent to register
            source: Source of agent (lyra or ecc)
            capabilities: Agent capabilities
            languages: Programming languages supported
            frameworks: Frameworks supported
            priority: Priority for selection (higher = preferred)

        Returns:
            Qualified agent name
        """
        namespace = f"{source.value}:{agent.agent_id}"

        metadata = AgentMetadata(
            agent=agent,
            source=source,
            namespace=namespace,
            capabilities=capabilities,
            languages=languages or set(),
            frameworks=frameworks or set(),
            priority=priority,
        )

        self.agents[namespace] = metadata

        # Update capability index
        for capability in capabilities:
            for task_type in capability.task_types:
                if task_type not in self._capability_index:
                    self._capability_index[task_type] = set()
                self._capability_index[task_type].add(namespace)

        # Update language index
        for language in metadata.languages:
            if language not in self._language_index:
                self._language_index[language] = set()
            self._language_index[language].add(namespace)

        # Update framework index
        for framework in metadata.frameworks:
            if framework not in self._framework_index:
                self._framework_index[framework] = set()
            self._framework_index[framework].add(namespace)

        return namespace

    def unregister(self, qualified_name: str) -> bool:
        """
        Unregister an agent.

        Args:
            qualified_name: Qualified agent name (e.g., "lyra:code")

        Returns:
            True if unregistered, False if not found
        """
        if qualified_name not in self.agents:
            return False

        metadata = self.agents[qualified_name]

        # Remove from capability index
        for capability in metadata.capabilities:
            for task_type in capability.task_types:
                if task_type in self._capability_index:
                    self._capability_index[task_type].discard(qualified_name)

        # Remove from language index
        for language in metadata.languages:
            if language in self._language_index:
                self._language_index[language].discard(qualified_name)

        # Remove from framework index
        for framework in metadata.frameworks:
            if framework in self._framework_index:
                self._framework_index[framework].discard(qualified_name)

        del self.agents[qualified_name]
        return True

    def get(self, qualified_name: str) -> Optional[Agent]:
        """
        Get an agent by qualified name.

        Args:
            qualified_name: Qualified agent name

        Returns:
            Agent if found, None otherwise
        """
        metadata = self.agents.get(qualified_name)
        return metadata.agent if metadata else None

    def find_candidates(
        self,
        task: Task,
        language: Optional[str] = None,
        framework: Optional[str] = None,
    ) -> List[AgentMetadata]:
        """
        Find candidate agents for a task.

        Args:
            task: Task to find agents for
            language: Optional language filter
            framework: Optional framework filter

        Returns:
            List of candidate agent metadata
        """
        # Find agents by capability
        candidate_names = self._capability_index.get(task.type, set()).copy()

        # Filter by language if specified
        if language and language in self._language_index:
            candidate_names &= self._language_index[language]

        # Filter by framework if specified
        if framework and framework in self._framework_index:
            candidate_names &= self._framework_index[framework]

        # Get metadata for candidates
        candidates = [
            self.agents[name]
            for name in candidate_names
            if name in self.agents
        ]

        return candidates

    def dispatch(
        self,
        task: Task,
        language: Optional[str] = None,
        framework: Optional[str] = None,
        prefer_source: Optional[AgentSource] = None,
    ) -> Optional[Agent]:
        """
        Dispatch a task to the best agent.

        Args:
            task: Task to dispatch
            language: Optional language hint
            framework: Optional framework hint
            prefer_source: Prefer agents from this source

        Returns:
            Selected agent or None if no suitable agent found
        """
        candidates = self.find_candidates(task, language, framework)

        if not candidates:
            return None

        # Score candidates
        scored = []
        for metadata in candidates:
            score = self._score_agent(metadata, task, prefer_source)
            scored.append((score, metadata))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Select best agent
        best_metadata = scored[0][1]
        best_metadata.usage_count += 1

        return best_metadata.agent

    def _score_agent(
        self,
        metadata: AgentMetadata,
        task: Task,
        prefer_source: Optional[AgentSource],
    ) -> float:
        """
        Score an agent for a task.

        Args:
            metadata: Agent metadata
            task: Task to score for
            prefer_source: Preferred source

        Returns:
            Score (higher is better)
        """
        score = 0.0

        # Base score from priority
        score += metadata.priority * 10

        # Bonus for success rate
        score += metadata.success_rate * 5

        # Bonus for preferred source
        if prefer_source and metadata.source == prefer_source:
            score += 20

        # Penalty for high usage (load balancing)
        if metadata.usage_count > 10:
            score -= min(metadata.usage_count / 10, 5)

        return score

    def record_success(self, qualified_name: str) -> None:
        """
        Record successful task completion.

        Args:
            qualified_name: Qualified agent name
        """
        if qualified_name in self.agents:
            self.agents[qualified_name].success_count += 1

    def record_failure(self, qualified_name: str) -> None:
        """
        Record failed task completion.

        Args:
            qualified_name: Qualified agent name
        """
        # Usage count already incremented in dispatch
        pass

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_agents": len(self.agents),
            "by_source": {
                "lyra": sum(1 for m in self.agents.values() if m.source == AgentSource.LYRA),
                "ecc": sum(1 for m in self.agents.values() if m.source == AgentSource.ECC),
            },
            "by_capability": {
                task_type.value: len(names)
                for task_type, names in self._capability_index.items()
            },
            "by_language": {
                lang: len(names)
                for lang, names in self._language_index.items()
            },
            "total_usage": sum(m.usage_count for m in self.agents.values()),
            "average_success_rate": (
                sum(m.success_rate for m in self.agents.values()) / len(self.agents)
                if self.agents else 0.0
            ),
        }

    def list_agents(
        self,
        source: Optional[AgentSource] = None,
        language: Optional[str] = None,
    ) -> List[AgentMetadata]:
        """
        List registered agents.

        Args:
            source: Filter by source
            language: Filter by language

        Returns:
            List of agent metadata
        """
        agents = list(self.agents.values())

        if source:
            agents = [a for a in agents if a.source == source]

        if language:
            agents = [a for a in agents if language in a.languages]

        return agents

    def clear(self) -> None:
        """Clear all agents from registry."""
        self.agents.clear()
        self._capability_index.clear()
        self._language_index.clear()
        self._framework_index.clear()
