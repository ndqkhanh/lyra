"""
Code Agent - specialist for code-related tasks.
"""

import asyncio
from typing import Any

from lyra.agents.base import Agent, AgentCapability, AgentStatus
from lyra.core.task import Result, Task, TaskType


class CodeAgent(Agent):
    """
    Specialist agent for code-related tasks.

    Capabilities:
    - Code analysis
    - Code generation
    - Code refactoring
    - Code review
    """

    def __init__(self, agent_id: str = "code_agent"):
        """Initialize the code agent."""
        capabilities = [
            AgentCapability(
                name="code_analysis",
                description="Analyze code structure and quality",
                task_types=[TaskType.CODE_ANALYSIS],
                required_tools=["lsp", "ast_grep", "rg"],
                estimated_cost=0.05,
                estimated_time=10.0,
                confidence=0.9,
            ),
            AgentCapability(
                name="code_generation",
                description="Generate new code from specifications",
                task_types=[TaskType.CODE_GENERATION],
                required_tools=["write_file", "lsp"],
                estimated_cost=0.10,
                estimated_time=30.0,
                confidence=0.85,
            ),
            AgentCapability(
                name="refactoring",
                description="Refactor existing code",
                task_types=[TaskType.CODE_REFACTORING],
                required_tools=["read_file", "edit_file", "lsp"],
                estimated_cost=0.08,
                estimated_time=20.0,
                confidence=0.9,
            ),
            AgentCapability(
                name="code_review",
                description="Review code for quality and issues",
                task_types=[TaskType.CODE_REVIEW],
                required_tools=["read_file", "lsp", "rg"],
                estimated_cost=0.06,
                estimated_time=15.0,
                confidence=0.85,
            ),
        ]
        super().__init__(agent_id, capabilities)

    async def execute(self, task: Task) -> Result:
        """
        Execute a code-related task.

        Args:
            task: Task to execute

        Returns:
            Execution result
        """
        self.status = AgentStatus.BUSY
        self.current_task = task

        try:
            print(f"[{self.agent_id}] Executing {task.type.value}: {task.description}")

            # Route to appropriate handler
            if task.type == TaskType.CODE_ANALYSIS:
                result_data = await self.analyze_code(task)
            elif task.type == TaskType.CODE_GENERATION:
                result_data = await self.generate_code(task)
            elif task.type == TaskType.CODE_REFACTORING:
                result_data = await self.refactor_code(task)
            elif task.type == TaskType.CODE_REVIEW:
                result_data = await self.review_code(task)
            else:
                raise ValueError(f"Unsupported task type: {task.type}")

            result = Result(
                task_id=task.task_id,
                success=True,
                data=result_data,
                agent_id=self.agent_id,
            )

        except Exception as e:
            result = Result(
                task_id=task.task_id,
                success=False,
                error=str(e),
                agent_id=self.agent_id,
            )

        finally:
            self.status = AgentStatus.IDLE
            self.current_task = None

        self.record_execution(result)
        return result

    async def analyze_code(self, task: Task) -> dict[str, Any]:
        """
        Analyze code quality and structure.

        Args:
            task: Analysis task

        Returns:
            Analysis results
        """
        await self.report_progress(0.2, "Reading code...")
        await asyncio.sleep(0.5)  # Simulate work

        await self.report_progress(0.5, "Analyzing structure...")
        await asyncio.sleep(0.5)

        await self.report_progress(0.8, "Generating report...")
        await asyncio.sleep(0.3)

        # Simulated analysis results
        return {
            "file": task.params.get("file_path", "unknown"),
            "lines_of_code": 150,
            "complexity": "medium",
            "issues": [
                {"type": "warning", "message": "Function too long", "line": 42},
                {"type": "info", "message": "Consider adding type hints", "line": 15},
            ],
            "suggestions": [
                "Break down large functions",
                "Add docstrings",
                "Improve error handling",
            ],
        }

    async def generate_code(self, task: Task) -> dict[str, Any]:
        """
        Generate new code from specifications.

        Args:
            task: Generation task

        Returns:
            Generated code and metadata
        """
        await self.report_progress(0.3, "Understanding requirements...")
        await asyncio.sleep(0.5)

        await self.report_progress(0.6, "Generating code...")
        await asyncio.sleep(1.0)

        await self.report_progress(0.9, "Validating output...")
        await asyncio.sleep(0.3)

        # Simulated code generation
        spec = task.params.get("specification", "")
        return {
            "code": f"# Generated code for: {spec}\n\ndef example():\n    pass\n",
            "language": "python",
            "files_created": 1,
            "lines_generated": 10,
        }

    async def refactor_code(self, task: Task) -> dict[str, Any]:
        """
        Refactor existing code.

        Args:
            task: Refactoring task

        Returns:
            Refactoring results
        """
        await self.report_progress(0.2, "Analyzing current code...")
        await asyncio.sleep(0.5)

        await self.report_progress(0.5, "Planning refactoring...")
        await asyncio.sleep(0.5)

        await self.report_progress(0.8, "Applying changes...")
        await asyncio.sleep(0.7)

        return {
            "file": task.params.get("file_path", "unknown"),
            "changes_made": [
                "Extracted helper function",
                "Simplified conditional logic",
                "Improved variable names",
            ],
            "lines_changed": 25,
            "complexity_improvement": "15%",
        }

    async def review_code(self, task: Task) -> dict[str, Any]:
        """
        Review code for quality and issues.

        Args:
            task: Review task

        Returns:
            Review results
        """
        await self.report_progress(0.3, "Reading code...")
        await asyncio.sleep(0.4)

        await self.report_progress(0.6, "Checking for issues...")
        await asyncio.sleep(0.6)

        await self.report_progress(0.9, "Generating review...")
        await asyncio.sleep(0.3)

        return {
            "file": task.params.get("file_path", "unknown"),
            "overall_quality": "good",
            "issues_found": 3,
            "critical_issues": 0,
            "warnings": 2,
            "suggestions": 1,
            "comments": [
                "Code is well-structured",
                "Consider adding more error handling",
                "Good use of type hints",
            ],
        }

    def can_handle(self, task: Task) -> float:
        """
        Determine if this agent can handle a task.

        Args:
            task: Task to evaluate

        Returns:
            Confidence score (0-1)
        """
        capability = self.get_capability(task.type)
        if capability:
            return capability.confidence
        return 0.0
