"""
MASAI-style Specialist Agents for Advanced Orchestration.

Implements role-specific agents: Planner, Editor, Debugger, Tester.
Each agent has specialized prompts and capabilities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class AgentRole(Enum):
    """Specialist agent roles."""

    PLANNER = "planner"
    EDITOR = "editor"
    DEBUGGER = "debugger"
    TESTER = "tester"


@dataclass
class AgentCapability:
    """A capability that an agent possesses."""

    capability_id: str
    name: str
    description: str
    tools: List[str] = field(default_factory=list)


@dataclass
class AgentTask:
    """A task assigned to a specialist agent."""

    task_id: str
    role: AgentRole
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class SpecialistAgent:
    """A specialist agent with role-specific capabilities."""

    agent_id: str
    role: AgentRole
    name: str
    description: str
    system_prompt: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    tasks_completed: int = 0
    tasks_failed: int = 0

    def get_success_rate(self) -> float:
        """Calculate agent success rate."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return self.tasks_completed / total


class AgentOrchestrator:
    """
    Orchestrates specialist agents for complex tasks.

    Features:
    - MASAI-style role specialization
    - Task routing to appropriate agents
    - Agent coordination and handoffs
    - Performance tracking per agent
    """

    def __init__(self):
        self.agents: Dict[AgentRole, SpecialistAgent] = {}
        self.tasks: List[AgentTask] = []

        # Statistics
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "agent_handoffs": 0,
        }

        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize specialist agents with their capabilities."""

        # Planner Agent
        planner = SpecialistAgent(
            agent_id="planner_001",
            role=AgentRole.PLANNER,
            name="Planner",
            description="Plans implementation strategy and breaks down tasks",
            system_prompt="""You are a Planner agent specialized in:
- Breaking down complex tasks into subtasks
- Identifying dependencies and ordering
- Estimating effort and complexity
- Creating implementation roadmaps
- Risk assessment and mitigation planning

Your output should be structured, actionable plans.""",
            capabilities=[
                AgentCapability(
                    capability_id="plan_001",
                    name="Task Decomposition",
                    description="Break complex tasks into subtasks",
                    tools=["analyze", "decompose", "prioritize"],
                ),
                AgentCapability(
                    capability_id="plan_002",
                    name="Dependency Analysis",
                    description="Identify task dependencies",
                    tools=["graph_analysis", "critical_path"],
                ),
            ],
        )

        # Editor Agent
        editor = SpecialistAgent(
            agent_id="editor_001",
            role=AgentRole.EDITOR,
            name="Editor",
            description="Writes and modifies code based on plans",
            system_prompt="""You are an Editor agent specialized in:
- Writing clean, maintainable code
- Following coding standards and patterns
- Implementing features from specifications
- Refactoring existing code
- Code documentation

Your output should be production-ready code.""",
            capabilities=[
                AgentCapability(
                    capability_id="edit_001",
                    name="Code Generation",
                    description="Generate code from specifications",
                    tools=["write", "edit", "format"],
                ),
                AgentCapability(
                    capability_id="edit_002",
                    name="Refactoring",
                    description="Improve code structure",
                    tools=["analyze", "refactor", "optimize"],
                ),
            ],
        )

        # Debugger Agent
        debugger = SpecialistAgent(
            agent_id="debugger_001",
            role=AgentRole.DEBUGGER,
            name="Debugger",
            description="Diagnoses and fixes bugs",
            system_prompt="""You are a Debugger agent specialized in:
- Root cause analysis of failures
- Reproducing bugs systematically
- Proposing and implementing fixes
- Regression testing
- Error pattern recognition

Your output should identify root causes and provide fixes.""",
            capabilities=[
                AgentCapability(
                    capability_id="debug_001",
                    name="Error Analysis",
                    description="Analyze error messages and stack traces",
                    tools=["trace", "analyze", "reproduce"],
                ),
                AgentCapability(
                    capability_id="debug_002",
                    name="Fix Implementation",
                    description="Implement bug fixes",
                    tools=["edit", "test", "verify"],
                ),
            ],
        )

        # Tester Agent
        tester = SpecialistAgent(
            agent_id="tester_001",
            role=AgentRole.TESTER,
            name="Tester",
            description="Writes and runs tests",
            system_prompt="""You are a Tester agent specialized in:
- Writing comprehensive test suites
- Test-driven development (TDD)
- Coverage analysis
- Edge case identification
- Test automation

Your output should be thorough test coverage.""",
            capabilities=[
                AgentCapability(
                    capability_id="test_001",
                    name="Test Generation",
                    description="Generate test cases",
                    tools=["analyze", "generate_tests", "coverage"],
                ),
                AgentCapability(
                    capability_id="test_002",
                    name="Test Execution",
                    description="Run tests and analyze results",
                    tools=["run_tests", "analyze_failures", "report"],
                ),
            ],
        )

        # Register agents
        self.agents[AgentRole.PLANNER] = planner
        self.agents[AgentRole.EDITOR] = editor
        self.agents[AgentRole.DEBUGGER] = debugger
        self.agents[AgentRole.TESTER] = tester

    def assign_task(
        self,
        role: AgentRole,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Assign a task to a specialist agent.

        Args:
            role: Agent role to assign to
            description: Task description
            context: Optional context information

        Returns:
            Task ID
        """
        task = AgentTask(
            task_id=f"task_{len(self.tasks):06d}",
            role=role,
            description=description,
            context=context or {},
        )

        self.tasks.append(task)
        self.stats["total_tasks"] += 1

        return task.task_id

    def execute_task(self, task_id: str) -> tuple[bool, Any, Optional[str]]:
        """
        Execute a task (placeholder for actual execution).

        Args:
            task_id: Task to execute

        Returns:
            (success, result, error)
        """
        # Find task
        task = None
        for t in self.tasks:
            if t.task_id == task_id:
                task = t
                break

        if not task:
            return False, None, f"Task {task_id} not found"

        # Update task status
        task.status = "in_progress"

        # Get agent
        agent = self.agents.get(task.role)
        if not agent:
            task.status = "failed"
            task.error = f"No agent for role {task.role}"
            self.stats["failed_tasks"] += 1
            return False, None, task.error

        # Execute task (placeholder - actual execution would happen here)
        # For now, simulate successful execution
        success = True
        result = f"Executed by {agent.name}: {task.description}"
        error = None

        # Update task and agent
        if success:
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now().isoformat()
            agent.tasks_completed += 1
            self.stats["completed_tasks"] += 1
        else:
            task.status = "failed"
            task.error = error
            agent.tasks_failed += 1
            self.stats["failed_tasks"] += 1

        return success, result, error

    def handoff_task(
        self,
        task_id: str,
        from_role: AgentRole,
        to_role: AgentRole,
        reason: str
    ) -> str:
        """
        Hand off a task from one agent to another.

        Args:
            task_id: Task to hand off
            from_role: Source agent role
            to_role: Target agent role
            reason: Reason for handoff

        Returns:
            New task ID
        """
        # Find original task
        original_task = None
        for t in self.tasks:
            if t.task_id == task_id:
                original_task = t
                break

        if not original_task:
            raise ValueError(f"Task {task_id} not found")

        # Create new task for target agent
        new_task = AgentTask(
            task_id=f"task_{len(self.tasks):06d}",
            role=to_role,
            description=f"Handoff from {from_role.value}: {original_task.description}",
            context={
                **original_task.context,
                "handoff_reason": reason,
                "original_task_id": task_id,
                "from_role": from_role.value,
            },
        )

        self.tasks.append(new_task)
        self.stats["agent_handoffs"] += 1

        return new_task.task_id

    def get_agent_stats(self, role: AgentRole) -> Dict[str, Any]:
        """Get statistics for a specific agent."""
        agent = self.agents.get(role)
        if not agent:
            return {}

        return {
            "agent_id": agent.agent_id,
            "role": agent.role.value,
            "name": agent.name,
            "tasks_completed": agent.tasks_completed,
            "tasks_failed": agent.tasks_failed,
            "success_rate": agent.get_success_rate(),
            "capabilities": len(agent.capabilities),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            **self.stats,
            "num_agents": len(self.agents),
            "agent_stats": {
                role.value: self.get_agent_stats(role)
                for role in AgentRole
            },
        }
