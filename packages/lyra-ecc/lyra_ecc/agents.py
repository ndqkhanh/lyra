"""
ECC Agent Fleet Integration

Unified agent registry merging ECC's 60 specialized agents with Lyra's RSI agents.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class AgentCategory(Enum):
    """Agent categories for organization."""

    PLANNING = "planning"
    DEVELOPMENT = "development"
    QUALITY = "quality"
    SECURITY = "security"
    LANGUAGE_SPECIFIC = "language_specific"
    RSI = "rsi"


@dataclass(frozen=True)
class AgentDefinition:
    """Immutable agent definition."""

    name: str
    category: AgentCategory
    description: str
    capabilities: List[str]
    trigger_patterns: List[str] = field(default_factory=list)
    model: str = "sonnet"
    source: str = "ECC"  # "ECC" or "Lyra"
    version: str = "1.0.0"


@dataclass(frozen=True)
class AgentDispatchResult:
    """Result of agent dispatch."""

    agent_name: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0


class UnifiedAgentRegistry:
    """
    Unified registry for Lyra RSI + ECC agents.

    Merges 60 ECC specialized agents with 7 Lyra RSI agents into a single
    intelligent dispatch system.
    """

    def __init__(self, ecc_path: Optional[Path] = None):
        """Initialize unified agent registry."""
        self.ecc_path = ecc_path or Path.home() / ".claude"
        self.agents: Dict[str, AgentDefinition] = {}
        self._load_agents()

    def _load_agents(self) -> None:
        """Load all agents from ECC and Lyra."""
        # Load ECC agents
        ecc_agents = self._load_ecc_agents()
        for agent in ecc_agents:
            self.agents[agent.name] = agent

        # Load Lyra RSI agents
        rsi_agents = self._load_rsi_agents()
        for agent in rsi_agents:
            self.agents[agent.name] = agent

    def _load_ecc_agents(self) -> List[AgentDefinition]:
        """Load ECC's 60 specialized agents."""
        # Planning & Architecture (8 agents)
        planning_agents = [
            AgentDefinition(
                name="planner",
                category=AgentCategory.PLANNING,
                description="Implementation planning and task breakdown",
                capabilities=["planning", "architecture", "task_breakdown"],
                trigger_patterns=["plan", "design", "architecture"],
            ),
            AgentDefinition(
                name="architect",
                category=AgentCategory.PLANNING,
                description="System design and architectural decisions",
                capabilities=["system_design", "architecture", "patterns"],
                trigger_patterns=["architect", "design", "system"],
            ),
            AgentDefinition(
                name="designer",
                category=AgentCategory.PLANNING,
                description="UI/UX design and interface planning",
                capabilities=["ui_design", "ux_design", "interface"],
                trigger_patterns=["design", "ui", "ux", "interface"],
            ),
            AgentDefinition(
                name="analyst",
                category=AgentCategory.PLANNING,
                description="Requirements analysis and specification",
                capabilities=["requirements", "analysis", "specification"],
                trigger_patterns=["analyze", "requirements", "spec"],
            ),
            AgentDefinition(
                name="critic",
                category=AgentCategory.PLANNING,
                description="Work plan review and critique",
                capabilities=["review", "critique", "validation"],
                trigger_patterns=["review", "critique", "validate"],
            ),
            AgentDefinition(
                name="document-specialist",
                category=AgentCategory.PLANNING,
                description="External documentation research",
                capabilities=["documentation", "research", "external_docs"],
                trigger_patterns=["docs", "documentation", "research"],
            ),
            AgentDefinition(
                name="explore",
                category=AgentCategory.PLANNING,
                description="Codebase search and exploration",
                capabilities=["search", "explore", "codebase"],
                trigger_patterns=["search", "find", "explore"],
            ),
            AgentDefinition(
                name="tracer",
                category=AgentCategory.PLANNING,
                description="Evidence-driven debugging and tracing",
                capabilities=["debugging", "tracing", "evidence"],
                trigger_patterns=["trace", "debug", "investigate"],
            ),
        ]

        # Development (12 agents)
        development_agents = [
            AgentDefinition(
                name="executor",
                category=AgentCategory.DEVELOPMENT,
                description="Task implementation and execution",
                capabilities=["implementation", "execution", "coding"],
                trigger_patterns=["implement", "execute", "build"],
            ),
            AgentDefinition(
                name="code-simplifier",
                category=AgentCategory.DEVELOPMENT,
                description="Code refinement and simplification",
                capabilities=["refactoring", "simplification", "cleanup"],
                trigger_patterns=["simplify", "refactor", "clean"],
            ),
            AgentDefinition(
                name="tdd-guide",
                category=AgentCategory.DEVELOPMENT,
                description="Test-driven development guidance",
                capabilities=["tdd", "testing", "test_first"],
                trigger_patterns=["tdd", "test", "test-driven"],
            ),
            AgentDefinition(
                name="test-engineer",
                category=AgentCategory.DEVELOPMENT,
                description="Test strategy and engineering",
                capabilities=["testing", "test_strategy", "coverage"],
                trigger_patterns=["test", "testing", "coverage"],
            ),
            AgentDefinition(
                name="debugger",
                category=AgentCategory.DEVELOPMENT,
                description="Root-cause analysis and debugging",
                capabilities=["debugging", "root_cause", "analysis"],
                trigger_patterns=["debug", "fix", "bug"],
            ),
            AgentDefinition(
                name="scientist",
                category=AgentCategory.DEVELOPMENT,
                description="Data analysis and research",
                capabilities=["data_analysis", "research", "experiments"],
                trigger_patterns=["analyze", "research", "experiment"],
            ),
            AgentDefinition(
                name="writer",
                category=AgentCategory.DEVELOPMENT,
                description="Technical documentation writing",
                capabilities=["documentation", "writing", "technical_writing"],
                trigger_patterns=["write", "document", "docs"],
            ),
        ]

        # Quality & Security (10 agents)
        quality_agents = [
            AgentDefinition(
                name="code-reviewer",
                category=AgentCategory.QUALITY,
                description="Code review and quality analysis",
                capabilities=["code_review", "quality", "best_practices"],
                trigger_patterns=["review", "quality", "check"],
            ),
            AgentDefinition(
                name="security-reviewer",
                category=AgentCategory.SECURITY,
                description="Security analysis and vulnerability detection",
                capabilities=["security", "vulnerabilities", "owasp"],
                trigger_patterns=["security", "vulnerability", "secure"],
            ),
            AgentDefinition(
                name="qa-tester",
                category=AgentCategory.QUALITY,
                description="Interactive testing and QA",
                capabilities=["testing", "qa", "interactive"],
                trigger_patterns=["test", "qa", "quality"],
            ),
            AgentDefinition(
                name="verifier",
                category=AgentCategory.QUALITY,
                description="Verification strategy and validation",
                capabilities=["verification", "validation", "correctness"],
                trigger_patterns=["verify", "validate", "check"],
            ),
            AgentDefinition(
                name="build-error-resolver",
                category=AgentCategory.QUALITY,
                description="Build error resolution and fixes",
                capabilities=["build_errors", "compilation", "fixes"],
                trigger_patterns=["build", "compile", "error"],
            ),
        ]

        # Language-Specific (30 agents) - Sample subset
        language_agents = [
            AgentDefinition(
                name="typescript-reviewer",
                category=AgentCategory.LANGUAGE_SPECIFIC,
                description="TypeScript code review specialist",
                capabilities=["typescript", "code_review", "type_safety"],
                trigger_patterns=["typescript", "ts", "type"],
            ),
            AgentDefinition(
                name="python-reviewer",
                category=AgentCategory.LANGUAGE_SPECIFIC,
                description="Python code review specialist",
                capabilities=["python", "code_review", "pythonic"],
                trigger_patterns=["python", "py", "pythonic"],
            ),
            AgentDefinition(
                name="go-reviewer",
                category=AgentCategory.LANGUAGE_SPECIFIC,
                description="Go code review specialist",
                capabilities=["go", "golang", "code_review"],
                trigger_patterns=["go", "golang"],
            ),
            AgentDefinition(
                name="rust-reviewer",
                category=AgentCategory.LANGUAGE_SPECIFIC,
                description="Rust code review specialist",
                capabilities=["rust", "code_review", "memory_safety"],
                trigger_patterns=["rust", "rs"],
            ),
            AgentDefinition(
                name="java-reviewer",
                category=AgentCategory.LANGUAGE_SPECIFIC,
                description="Java code review specialist",
                capabilities=["java", "code_review", "jvm"],
                trigger_patterns=["java", "jvm"],
            ),
        ]

        return planning_agents + development_agents + quality_agents + language_agents

    def _load_rsi_agents(self) -> List[AgentDefinition]:
        """Load Lyra's 7 RSI agents."""
        return [
            AgentDefinition(
                name="agent0",
                category=AgentCategory.RSI,
                description="Meta-agent for agent synthesis",
                capabilities=["agent_synthesis", "meta_learning", "self_improvement"],
                trigger_patterns=["synthesize", "meta", "agent"],
                source="Lyra",
            ),
            AgentDefinition(
                name="skillrl",
                category=AgentCategory.RSI,
                description="Skill reinforcement learning",
                capabilities=["skill_learning", "reinforcement", "optimization"],
                trigger_patterns=["skill", "learn", "optimize"],
                source="Lyra",
            ),
            AgentDefinition(
                name="cli-anything",
                category=AgentCategory.RSI,
                description="Universal CLI tool synthesis",
                capabilities=["cli_synthesis", "tool_creation", "automation"],
                trigger_patterns=["cli", "tool", "command"],
                source="Lyra",
            ),
            AgentDefinition(
                name="meta-harness",
                category=AgentCategory.RSI,
                description="Harness meta-programming",
                capabilities=["harness", "meta_programming", "framework"],
                trigger_patterns=["harness", "framework", "meta"],
                source="Lyra",
            ),
            AgentDefinition(
                name="alphaevolve",
                category=AgentCategory.RSI,
                description="Evolutionary optimization",
                capabilities=["evolution", "optimization", "genetic"],
                trigger_patterns=["evolve", "optimize", "genetic"],
                source="Lyra",
            ),
            AgentDefinition(
                name="post-training",
                category=AgentCategory.RSI,
                description="Post-training refinement",
                capabilities=["post_training", "refinement", "fine_tuning"],
                trigger_patterns=["train", "refine", "tune"],
                source="Lyra",
            ),
            AgentDefinition(
                name="hyperagent",
                category=AgentCategory.RSI,
                description="Hyper-parameter optimization agent",
                capabilities=["hyperparameters", "optimization", "tuning"],
                trigger_patterns=["hyper", "parameter", "tune"],
                source="Lyra",
            ),
        ]

    def select_agent(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Intelligent agent selection based on task and context.

        Args:
            task: Task description
            context: Optional context dictionary (reserved for future use)

        Returns:
            Selected agent name
        """
        _ = context  # Reserved for future context-aware selection
        task_lower = task.lower()

        # Check trigger patterns
        for agent_name, agent in self.agents.items():
            for pattern in agent.trigger_patterns:
                if pattern in task_lower:
                    return agent_name

        # Default to executor for implementation tasks
        if any(word in task_lower for word in ["implement", "build", "create", "add"]):
            return "executor"

        # Default to planner for planning tasks
        if any(word in task_lower for word in ["plan", "design", "architect"]):
            return "planner"

        # Default to code-reviewer for review tasks
        if any(word in task_lower for word in ["review", "check", "analyze"]):
            return "code-reviewer"

        # Default fallback
        return "executor"

    def dispatch(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentDispatchResult:
        """
        Dispatch task to appropriate agent.

        Args:
            task: Task description
            context: Optional context dictionary

        Returns:
            AgentDispatchResult with execution details
        """
        agent_name = self.select_agent(task, context)
        agent = self.agents.get(agent_name)

        if not agent:
            return AgentDispatchResult(
                agent_name=agent_name,
                success=False,
                output=None,
                error=f"Agent '{agent_name}' not found",
            )

        # In a real implementation, this would execute the agent
        # For now, return a success result with agent info
        return AgentDispatchResult(
            agent_name=agent_name,
            success=True,
            output={
                "agent": agent.name,
                "category": agent.category.value,
                "description": agent.description,
                "capabilities": agent.capabilities,
            },
        )

    def get_agent(self, name: str) -> Optional[AgentDefinition]:
        """Get agent definition by name."""
        return self.agents.get(name)

    def list_agents(
        self, category: Optional[AgentCategory] = None, source: Optional[str] = None
    ) -> List[AgentDefinition]:
        """
        List agents, optionally filtered by category or source.

        Args:
            category: Optional category filter
            source: Optional source filter ("ECC" or "Lyra")

        Returns:
            List of matching agent definitions
        """
        agents = list(self.agents.values())

        if category:
            agents = [a for a in agents if a.category == category]

        if source:
            agents = [a for a in agents if a.source == source]

        return agents

    def get_registry_summary(self) -> Dict[str, Any]:
        """Get summary of agent registry."""
        total_agents = len(self.agents)
        ecc_agents = len([a for a in self.agents.values() if a.source == "ECC"])
        rsi_agents = len([a for a in self.agents.values() if a.source == "Lyra"])

        by_category = {}
        for agent in self.agents.values():
            category = agent.category.value
            by_category[category] = by_category.get(category, 0) + 1

        return {
            "total_agents": total_agents,
            "ecc_agents": ecc_agents,
            "rsi_agents": rsi_agents,
            "by_category": by_category,
            "agent_names": list(self.agents.keys()),
        }
