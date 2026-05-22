"""
ECC agent definitions and importer.

This module provides infrastructure for importing ECC's 60 specialized
agents into Lyra's unified agent registry.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

from src.agents.base import Agent, AgentCapability, AgentStatus
from src.agents.unified_registry import AgentSource, UnifiedAgentRegistry
from src.core.task import Task, TaskType, Result


@dataclass
class ECCAgentDefinition:
    """Definition of an ECC agent from YAML."""

    name: str
    description: str
    model: str  # sonnet, opus, haiku
    capabilities: List[str]
    task_types: List[str]
    languages: List[str]
    frameworks: List[str]
    tools: List[str]
    instructions: str
    priority: int = 0


class ECCAgent(Agent):
    """
    ECC agent implementation.

    Wraps ECC agent definitions in Lyra's Agent interface.
    """

    def __init__(
        self,
        agent_id: str,
        definition: ECCAgentDefinition,
    ):
        """
        Initialize ECC agent.

        Args:
            agent_id: Agent identifier
            definition: ECC agent definition
        """
        super().__init__(agent_id)
        self.definition = definition
        self.description = definition.description
        self.model = definition.model

    def can_handle(self, task: Task) -> float:
        """
        Determine if this agent can handle a task.

        Args:
            task: Task to evaluate

        Returns:
            Confidence score (0-1) based on task type and capability matching
        """
        # Extract task type string
        task_type_str = task.type.value if hasattr(task.type, 'value') else str(task.type)

        # Exact task type match = high confidence
        if task_type_str in self.definition.task_types:
            return 0.9

        # Capability keyword match in task description = medium confidence
        task_desc_lower = task.description.lower()
        for capability in self.definition.capabilities:
            if capability.lower() in task_desc_lower:
                return 0.7

        # No match = cannot handle
        return 0.0

    async def execute(self, task: Task) -> Result:
        """
        Execute a task.

        Args:
            task: Task to execute

        Returns:
            Task result
        """
        self.status = AgentStatus.BUSY

        try:
            # Simulated execution based on ECC agent definition
            # In production, this would call the actual LLM with the agent's instructions
            result = Result(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                data={
                    "message": f"Task executed by {self.agent_id} ({self.definition.model})",
                    "agent_type": "ecc",
                    "model": self.model,
                },
            )

            self.status = AgentStatus.IDLE
            return result

        except Exception as e:
            self.status = AgentStatus.ERROR
            return Result(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error=str(e),
            )


class ECCAgentParser:
    """Parser for ECC agent definition files."""

    def parse_file(self, path: Path) -> Optional[ECCAgentDefinition]:
        """
        Parse an ECC agent definition file.

        Args:
            path: Path to agent definition file

        Returns:
            Parsed agent definition or None if parsing fails
        """
        try:
            with open(path, "r") as f:
                content = f.read()

            # Split frontmatter and instructions
            parts = content.split("---", 2)
            if len(parts) < 3:
                return None

            frontmatter = yaml.safe_load(parts[1])
            instructions = parts[2].strip()

            return ECCAgentDefinition(
                name=frontmatter.get("name", ""),
                description=frontmatter.get("description", ""),
                model=frontmatter.get("model", "sonnet"),
                capabilities=frontmatter.get("capabilities", []),
                task_types=frontmatter.get("task_types", []),
                languages=frontmatter.get("languages", []),
                frameworks=frontmatter.get("frameworks", []),
                tools=frontmatter.get("tools", []),
                instructions=instructions,
                priority=frontmatter.get("priority", 0),
            )

        except Exception as e:
            print(f"Error parsing {path}: {e}")
            return None

    def parse_directory(self, directory: Path) -> Dict[str, ECCAgentDefinition]:
        """
        Parse all agent definitions in a directory.

        Args:
            directory: Directory containing agent definitions

        Returns:
            Dictionary mapping agent names to definitions
        """
        definitions = {}

        for path in directory.glob("**/*.md"):
            definition = self.parse_file(path)
            if definition and definition.name:
                definitions[definition.name] = definition

        return definitions


@dataclass
class ImportResult:
    """Result of agent import operation."""

    total_files: int
    parsed_successfully: int
    registered_successfully: int
    failed: List[str]
    agents: Dict[str, ECCAgent]

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_files == 0:
            return 0.0
        return self.registered_successfully / self.total_files


class ECCAgentImporter:
    """
    Import ECC agents into Lyra's unified registry.

    Handles parsing ECC agent definitions and registering them
    in the unified agent registry.
    """

    def __init__(self, registry: UnifiedAgentRegistry):
        """
        Initialize importer.

        Args:
            registry: Unified agent registry
        """
        self.registry = registry
        self.parser = ECCAgentParser()

    def import_agent(
        self,
        definition: ECCAgentDefinition,
    ) -> Optional[str]:
        """
        Import a single agent.

        Args:
            definition: Agent definition

        Returns:
            Qualified agent name if successful, None otherwise
        """
        try:
            # Create ECC agent
            agent = ECCAgent(
                agent_id=definition.name,
                definition=definition,
            )

            # Convert task types
            task_types = []
            for task_type_str in definition.task_types:
                try:
                    task_types.append(TaskType(task_type_str))
                except ValueError:
                    pass

            # Create capabilities
            capabilities = [
                AgentCapability(
                    name=cap,
                    description=f"{cap} capability",
                    task_types=task_types,
                )
                for cap in definition.capabilities
            ]

            # Register in unified registry
            qualified_name = self.registry.register(
                agent=agent,
                source=AgentSource.ECC,
                capabilities=capabilities,
                languages=set(definition.languages),
                frameworks=set(definition.frameworks),
                priority=definition.priority,
            )

            return qualified_name

        except Exception as e:
            print(f"Error importing agent {definition.name}: {e}")
            return None

    def import_directory(
        self,
        directory: Path,
    ) -> ImportResult:
        """
        Import all agents from a directory.

        Args:
            directory: Directory containing agent definitions

        Returns:
            Import result with statistics
        """
        # Get all markdown files
        all_files = list(directory.glob("**/*.md"))
        total_files = len(all_files)

        # Parse all definitions
        definitions = self.parser.parse_directory(directory)
        parsed_successfully = len(definitions)

        # Calculate parse failures: total files - successfully parsed
        parse_failure_count = total_files - parsed_successfully

        registered_successfully = 0
        failed = []
        agents = {}

        # Import each agent
        for name, definition in definitions.items():
            qualified_name = self.import_agent(definition)
            if qualified_name:
                agent = self.registry.get(qualified_name)
                if agent and isinstance(agent, ECCAgent):
                    agents[name] = agent
                    registered_successfully += 1
            else:
                failed.append(name)

        # Add placeholder entries for parse failures
        for i in range(parse_failure_count):
            failed.append(f"parse_error_{i}")

        return ImportResult(
            total_files=total_files,
            parsed_successfully=parsed_successfully,
            registered_successfully=registered_successfully,
            failed=failed,
            agents=agents,
        )

    def import_all(self, ecc_agents_path: Path) -> ImportResult:
        """
        Import all ECC agents from the standard directory structure.

        Args:
            ecc_agents_path: Root path to ECC agents

        Returns:
            Import result with statistics
        """
        return self.import_directory(ecc_agents_path)


def create_sample_ecc_agents() -> Dict[str, ECCAgentDefinition]:
    """
    Create sample ECC agent definitions.

    This represents a subset of the 60 ECC agents for testing.
    In production, these would be loaded from actual ECC agent files.
    """
    return {
        "planner": ECCAgentDefinition(
            name="planner",
            description="Implementation planning and task breakdown",
            model="opus",
            capabilities=["planning", "task_breakdown", "architecture"],
            task_types=["planning", "analysis"],
            languages=[],
            frameworks=[],
            tools=["read", "write"],
            instructions="Create detailed implementation plans with step-by-step breakdown.",
            priority=10,
        ),
        "architect": ECCAgentDefinition(
            name="architect",
            description="System design and architecture decisions",
            model="opus",
            capabilities=["architecture", "design", "system_design"],
            task_types=["design", "architecture"],
            languages=[],
            frameworks=[],
            tools=["read", "write"],
            instructions="Design system architecture and make technical decisions.",
            priority=10,
        ),
        "executor": ECCAgentDefinition(
            name="executor",
            description="Task implementation and code execution",
            model="sonnet",
            capabilities=["implementation", "coding", "execution"],
            task_types=["code_generation", "implementation"],
            languages=["python", "typescript", "javascript"],
            frameworks=[],
            tools=["read", "write", "edit", "bash"],
            instructions="Implement tasks according to specifications.",
            priority=5,
        ),
        "code-reviewer": ECCAgentDefinition(
            name="code-reviewer",
            description="Code review and quality assessment",
            model="sonnet",
            capabilities=["code_review", "quality", "best_practices"],
            task_types=["code_review", "analysis"],
            languages=["python", "typescript", "javascript", "go", "rust"],
            frameworks=[],
            tools=["read"],
            instructions="Review code for quality, security, and best practices.",
            priority=8,
        ),
        "security-reviewer": ECCAgentDefinition(
            name="security-reviewer",
            description="Security analysis and vulnerability detection",
            model="sonnet",
            capabilities=["security", "vulnerability_detection", "owasp"],
            task_types=["security_review", "analysis"],
            languages=["python", "typescript", "javascript", "go", "rust"],
            frameworks=[],
            tools=["read"],
            instructions="Analyze code for security vulnerabilities and risks.",
            priority=9,
        ),
        "tdd-guide": ECCAgentDefinition(
            name="tdd-guide",
            description="Test-driven development guidance",
            model="sonnet",
            capabilities=["testing", "tdd", "test_generation"],
            task_types=["test_generation", "testing"],
            languages=["python", "typescript", "javascript"],
            frameworks=["pytest", "jest", "mocha"],
            tools=["read", "write", "bash"],
            instructions="Guide test-driven development with comprehensive test coverage.",
            priority=7,
        ),
        "debugger": ECCAgentDefinition(
            name="debugger",
            description="Root-cause analysis and debugging",
            model="sonnet",
            capabilities=["debugging", "root_cause_analysis", "troubleshooting"],
            task_types=["debugging", "analysis"],
            languages=["python", "typescript", "javascript", "go", "rust"],
            frameworks=[],
            tools=["read", "bash"],
            instructions="Analyze errors and find root causes of bugs.",
            priority=8,
        ),
        "python-reviewer": ECCAgentDefinition(
            name="python-reviewer",
            description="Python-specific code review",
            model="sonnet",
            capabilities=["code_review", "python", "pep8"],
            task_types=["code_review"],
            languages=["python"],
            frameworks=["django", "fastapi", "flask"],
            tools=["read"],
            instructions="Review Python code for language-specific best practices.",
            priority=7,
        ),
        "typescript-reviewer": ECCAgentDefinition(
            name="typescript-reviewer",
            description="TypeScript-specific code review",
            model="sonnet",
            capabilities=["code_review", "typescript", "type_safety"],
            task_types=["code_review"],
            languages=["typescript"],
            frameworks=["react", "nextjs", "nestjs"],
            tools=["read"],
            instructions="Review TypeScript code for type safety and best practices.",
            priority=7,
        ),
        "designer": ECCAgentDefinition(
            name="designer",
            description="UI/UX design and frontend architecture",
            model="sonnet",
            capabilities=["ui_design", "ux", "frontend"],
            task_types=["design", "ui_generation"],
            languages=["typescript", "javascript"],
            frameworks=["react", "vue", "svelte"],
            tools=["read", "write"],
            instructions="Design user interfaces and frontend architecture.",
            priority=6,
        ),
    }
