"""
Review Agent - specialist for code review and quality assurance.
"""

import asyncio
from typing import Any

from src.agents.base import Agent, AgentCapability, AgentStatus
from src.core.task import Result, Task, TaskType


class ReviewAgent(Agent):
    """
    Specialist agent for code review and quality assurance.

    Capabilities:
    - Code review
    - Security scanning
    - Quality assessment
    """

    def __init__(self, agent_id: str = "review_agent"):
        """Initialize the review agent."""
        capabilities = [
            AgentCapability(
                name="code_review",
                description="Review code for quality and best practices",
                task_types=[TaskType.CODE_REVIEW],
                required_tools=["read_file", "lsp", "rg"],
                estimated_cost=0.06,
                estimated_time=15.0,
                confidence=0.9,
            ),
            AgentCapability(
                name="security_scan",
                description="Scan code for security vulnerabilities",
                task_types=[TaskType.SECURITY_SCAN],
                required_tools=["read_file", "bash"],
                estimated_cost=0.08,
                estimated_time=20.0,
                confidence=0.85,
            ),
        ]
        super().__init__(agent_id, capabilities)

    async def execute(self, task: Task) -> Result:
        """
        Execute a review task.

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
            if task.type == TaskType.CODE_REVIEW:
                result_data = await self.review_code(task)
            elif task.type == TaskType.SECURITY_SCAN:
                result_data = await self.security_scan(task)
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

    async def review_code(self, task: Task) -> dict[str, Any]:
        """
        Review code for quality and best practices.

        Args:
            task: Code review task

        Returns:
            Review results
        """
        file_path = task.params.get("file_path", "unknown")

        await self.report_progress(0.2, "Reading code...")
        await asyncio.sleep(0.4)

        await self.report_progress(0.4, "Checking style and conventions...")
        await asyncio.sleep(0.5)

        await self.report_progress(0.6, "Analyzing logic and structure...")
        await asyncio.sleep(0.6)

        await self.report_progress(0.8, "Checking for common issues...")
        await asyncio.sleep(0.4)

        # Simulated review
        issues = [
            {
                "severity": "warning",
                "category": "style",
                "message": "Function name should be snake_case",
                "line": 15,
                "suggestion": "Rename 'myFunction' to 'my_function'",
            },
            {
                "severity": "info",
                "category": "documentation",
                "message": "Missing docstring",
                "line": 20,
                "suggestion": "Add docstring describing function purpose",
            },
            {
                "severity": "warning",
                "category": "complexity",
                "message": "Function complexity too high (12)",
                "line": 42,
                "suggestion": "Consider breaking into smaller functions",
            },
        ]

        return {
            "file": file_path,
            "overall_quality": "good",
            "score": 7.5,
            "issues_found": len(issues),
            "issues": issues,
            "strengths": [
                "Good error handling",
                "Clear variable names",
                "Proper type hints",
            ],
            "recommendations": [
                "Add more inline comments",
                "Reduce function complexity",
                "Improve test coverage",
            ],
        }

    async def security_scan(self, task: Task) -> dict[str, Any]:
        """
        Scan code for security vulnerabilities.

        Args:
            task: Security scan task

        Returns:
            Security scan results
        """
        target = task.params.get("target", ".")

        await self.report_progress(0.2, "Scanning for vulnerabilities...")
        await asyncio.sleep(0.6)

        await self.report_progress(0.5, "Checking dependencies...")
        await asyncio.sleep(0.5)

        await self.report_progress(0.8, "Analyzing security patterns...")
        await asyncio.sleep(0.5)

        # Simulated security scan
        vulnerabilities = [
            {
                "severity": "medium",
                "type": "SQL Injection",
                "file": "database.py",
                "line": 78,
                "description": "Potential SQL injection vulnerability",
                "recommendation": "Use parameterized queries",
            },
            {
                "severity": "low",
                "type": "Hardcoded Secret",
                "file": "config.py",
                "line": 12,
                "description": "Hardcoded API key detected",
                "recommendation": "Move to environment variables",
            },
        ]

        return {
            "target": target,
            "scan_date": "2026-05-22",
            "vulnerabilities_found": len(vulnerabilities),
            "critical": 0,
            "high": 0,
            "medium": 1,
            "low": 1,
            "vulnerabilities": vulnerabilities,
            "security_score": 8.0,
            "recommendations": [
                "Update dependencies with known vulnerabilities",
                "Implement input validation",
                "Use environment variables for secrets",
            ],
        }

    async def assess_quality(self, task: Task) -> dict[str, Any]:
        """
        Assess overall code quality.

        Args:
            task: Quality assessment task

        Returns:
            Quality assessment results
        """
        await self.report_progress(0.5, "Assessing quality metrics...")
        await asyncio.sleep(0.7)

        return {
            "overall_score": 7.8,
            "metrics": {
                "maintainability": 8.0,
                "reliability": 7.5,
                "security": 8.0,
                "testability": 7.0,
                "documentation": 7.5,
            },
            "strengths": [
                "Well-structured code",
                "Good test coverage",
                "Clear documentation",
            ],
            "areas_for_improvement": [
                "Reduce code duplication",
                "Improve error handling",
                "Add more integration tests",
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
