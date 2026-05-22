"""Testing phase executor for QA and validation."""

from __future__ import annotations

import time
from typing import Any

from lyra_core.orchestration.agent_base import AgentRole
from lyra_core.orchestration.agents.qa_agent import QAEngineerAgent
from lyra_core.orchestration.workflow.models import Artifact, PhaseResult, SDLCPhase
from lyra_core.orchestration.workflow.phase_executors.base_executor import (
    BasePhaseExecutor,
)


class TestingExecutor(BasePhaseExecutor):
    """Executor for the Testing phase.

    Responsibilities:
    - Spawn QA Engineer agent
    - Create test strategy
    - Write and run tests
    - Verify quality gates
    - Request user review and approval
    """

    @property
    def phase(self) -> SDLCPhase:
        """Get the phase this executor handles."""
        return SDLCPhase.TESTING

    @property
    def required_roles(self) -> list[AgentRole]:
        """Get list of required agent roles for this phase."""
        return [AgentRole.QA]

    @property
    def requires_user_review(self) -> bool:
        """Whether this phase requires user review."""
        return True

    async def execute(
        self,
        workflow_id: str,
        team_id: str,
        input_data: dict[str, Any],
    ) -> PhaseResult:
        """Execute the Testing phase.

        Args:
            workflow_id: Workflow ID
            team_id: Team ID
            input_data: Input data containing code artifacts

        Returns:
            Phase execution result with test artifacts
        """
        start_time = time.time()
        artifacts: list[Artifact] = []
        errors: list[str] = []

        try:
            # Spawn QA Engineer agent
            agent_ids = await self._spawn_agents(
                team_id=team_id,
                roles=[
                    (
                        AgentRole.QA,
                        QAEngineerAgent,
                        [
                            "test_strategy",
                            "test_creation",
                            "test_execution",
                            "quality_reporting",
                        ],
                    )
                ],
            )

            qa_agent_id = agent_ids[AgentRole.QA]

            # Extract code artifacts from input
            code_artifacts = input_data.get("code_artifacts", [])
            if not code_artifacts:
                raise ValueError("No code artifacts provided in input_data")

            # Create test strategy (simulated)
            test_strategy = self._create_test_strategy(code_artifacts)
            strategy_artifact = Artifact.create(
                type="test_strategy",
                name="Test Strategy",
                content=test_strategy,
                phase=self.phase,
            )
            artifacts.append(strategy_artifact)

            # Write tests (simulated)
            test_files = self._write_tests(code_artifacts, test_strategy)
            for test_file in test_files:
                artifacts.append(test_file)

            # Run tests (simulated)
            test_results = self._run_tests(test_files)
            results_artifact = Artifact.create(
                type="test_results",
                name="Test Results",
                content=test_results,
                phase=self.phase,
            )
            artifacts.append(results_artifact)

            # Generate quality report (simulated)
            quality_report = self._generate_quality_report(test_results)
            report_artifact = Artifact.create(
                type="quality_report",
                name="Quality Report",
                content=quality_report,
                phase=self.phase,
            )
            artifacts.append(report_artifact)

            # Request user review
            review_id = await self._request_user_review(
                workflow_id=workflow_id,
                artifacts=artifacts,
                questions=[
                    "Do the test results meet your quality expectations?",
                    "Is the test coverage sufficient?",
                    "Are there any additional test scenarios needed?",
                ],
            )

            duration = time.time() - start_time

            return PhaseResult.create(
                phase=self.phase,
                success=True,
                artifacts=artifacts,
                duration=duration,
                metadata={
                    "qa_agent_id": qa_agent_id,
                    "review_request_id": review_id,
                    "test_count": test_results.get("total_tests"),
                    "coverage": test_results.get("coverage"),
                },
            )

        except Exception as e:
            duration = time.time() - start_time
            errors.append(str(e))

            return PhaseResult.create(
                phase=self.phase,
                success=False,
                artifacts=artifacts,
                duration=duration,
                errors=errors,
            )

    def _create_test_strategy(self, code_artifacts: list[Any]) -> dict[str, Any]:
        """Create test strategy based on code artifacts.

        Args:
            code_artifacts: Code artifacts to test

        Returns:
            Test strategy dictionary
        """
        # Simplified implementation - real version would use QA agent
        return {
            "approach": "Test-Driven Development",
            "test_types": ["unit", "integration", "e2e"],
            "coverage_target": 80,
            "tools": ["pytest", "coverage", "pytest-asyncio"],
            "test_environments": ["local", "ci"],
        }

    def _write_tests(
        self,
        code_artifacts: list[Any],
        test_strategy: dict[str, Any],
    ) -> list[Artifact]:
        """Write tests based on code and strategy.

        Args:
            code_artifacts: Code artifacts
            test_strategy: Test strategy

        Returns:
            List of test file artifacts
        """
        # Simplified implementation - real version would use QA agent
        test_files = [
            {
                "path": "tests/test_main.py",
                "content": "# Unit tests for main module\n",
                "type": "unit",
            },
            {
                "path": "tests/test_api.py",
                "content": "# Integration tests for API\n",
                "type": "integration",
            },
        ]

        return [
            Artifact.create(
                type="test",
                name=f"Test: {file['path']}",
                content=file,
                phase=self.phase,
            )
            for file in test_files
        ]

    def _run_tests(self, test_files: list[Artifact]) -> dict[str, Any]:
        """Run tests and collect results.

        Args:
            test_files: Test file artifacts

        Returns:
            Test results dictionary
        """
        # Simplified implementation - real version would use QA agent
        return {
            "total_tests": 25,
            "passed": 24,
            "failed": 1,
            "skipped": 0,
            "coverage": 85.5,
            "duration": 12.3,
            "failures": [
                {
                    "test": "test_api.py::test_authentication",
                    "error": "AssertionError: Expected 200, got 401",
                }
            ],
        }

    def _generate_quality_report(self, test_results: dict[str, Any]) -> dict[str, Any]:
        """Generate quality report from test results.

        Args:
            test_results: Test results

        Returns:
            Quality report dictionary
        """
        # Simplified implementation - real version would use QA agent
        passed = test_results.get("passed", 0)
        total = test_results.get("total_tests", 1)
        pass_rate = (passed / total) * 100 if total > 0 else 0

        return {
            "overall_status": "pass" if pass_rate >= 95 else "warning",
            "pass_rate": pass_rate,
            "coverage": test_results.get("coverage"),
            "quality_gates": {
                "coverage_80": test_results.get("coverage", 0) >= 80,
                "pass_rate_95": pass_rate >= 95,
                "no_critical_failures": test_results.get("failed", 0) == 0,
            },
            "recommendations": [
                "Fix failing authentication test",
                "Increase coverage to 90%",
            ],
        }


__all__ = ["TestingExecutor"]
