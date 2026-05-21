"""QA Engineer Agent implementation."""

from __future__ import annotations

import uuid
from typing import Any

from lyra_core.orchestration.agent_base import AgentStatus, BaseAgent
from lyra_core.orchestration.models.requirements import Priority, Requirements
from lyra_core.orchestration.models.testing import (
    QualityReport,
    Test,
    TestResult,
    TestResults,
    TestStatus,
    TestStrategy,
    TestType,
)
from lyra_core.orchestration.protocol import Message, MessageType


class QAEngineerAgent(BaseAgent):
    """QA Engineer agent responsible for quality assurance.

    Responsibilities:
    - Create test strategy
    - Write and run tests
    - Verify quality gates
    - Report bugs and issues
    - Approve releases
    """

    async def on_start(self) -> None:
        """Initialize QA Engineer agent."""
        self._set_status(AgentStatus.IDLE)

    async def on_stop(self) -> None:
        """Cleanup QA Engineer agent."""
        pass

    async def on_message(self, message: Message) -> None:
        """Handle incoming messages.

        Args:
            message: Received message
        """
        action = message.payload.get("action")

        if action == "create_test_strategy":
            await self._handle_create_test_strategy(message)
        elif action == "write_tests":
            await self._handle_write_tests(message)
        elif action == "run_tests":
            await self._handle_run_tests(message)
        elif action == "verify_quality_gates":
            await self._handle_verify_quality_gates(message)
        else:
            await self.send_response(
                message,
                {
                    "status": "error",
                    "error": f"Unknown action: {action}",
                },
            )

    async def _handle_create_test_strategy(self, message: Message) -> None:
        """Handle test strategy creation request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            requirements_data = message.payload.get("requirements", {})

            requirements = Requirements(
                id=requirements_data["id"],
                description=requirements_data["description"],
                goals=tuple(requirements_data["goals"]),
                constraints=tuple(requirements_data.get("constraints", [])),
                stakeholders=tuple(requirements_data.get("stakeholders", [])),
                priority=Priority(requirements_data["priority"]),
                created_at=requirements_data["created_at"],
            )

            strategy = await self.create_test_strategy(requirements)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "test_strategy": {
                        "id": strategy.id,
                        "requirements_id": strategy.requirements_id,
                        "coverage_target": strategy.coverage_target,
                        "test_types": [t.value for t in strategy.test_types],
                        "frameworks": list(strategy.frameworks),
                        "ci_integration": strategy.ci_integration,
                        "created_at": strategy.created_at,
                    },
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_write_tests(self, message: Message) -> None:
        """Handle test writing request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            code_data = message.payload.get("code", {})

            tests = await self.write_tests(code_data)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "tests": [
                        {
                            "id": test.id,
                            "name": test.name,
                            "type": test.type.value,
                            "description": test.description,
                            "file_path": test.file_path,
                            "function_name": test.function_name,
                            "created_at": test.created_at,
                        }
                        for test in tests
                    ],
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_run_tests(self, message: Message) -> None:
        """Handle test execution request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            tests_data = message.payload.get("tests", [])

            # Reconstruct tests
            tests = [
                Test(
                    id=t["id"],
                    name=t["name"],
                    type=TestType(t["type"]),
                    description=t["description"],
                    file_path=t["file_path"],
                    function_name=t["function_name"],
                    created_at=t["created_at"],
                )
                for t in tests_data
            ]

            results = await self.run_tests(tests)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "test_results": {
                        "id": results.id,
                        "total": results.total,
                        "passed": results.passed,
                        "failed": results.failed,
                        "skipped": results.skipped,
                        "coverage_percentage": results.coverage_percentage,
                        "results": [
                            {
                                "test_id": r.test_id,
                                "status": r.status.value,
                                "duration_ms": r.duration_ms,
                                "error_message": r.error_message,
                                "stack_trace": r.stack_trace,
                            }
                            for r in results.results
                        ],
                        "created_at": results.created_at,
                    },
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_verify_quality_gates(self, message: Message) -> None:
        """Handle quality gate verification request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            results_data = message.payload.get("test_results", {})

            # Reconstruct test results
            test_results = TestResults(
                id=results_data["id"],
                total=results_data["total"],
                passed=results_data["passed"],
                failed=results_data["failed"],
                skipped=results_data["skipped"],
                coverage_percentage=results_data["coverage_percentage"],
                results=tuple(
                    TestResult(
                        test_id=r["test_id"],
                        status=TestStatus(r["status"]),
                        duration_ms=r["duration_ms"],
                        error_message=r.get("error_message"),
                        stack_trace=r.get("stack_trace"),
                    )
                    for r in results_data["results"]
                ),
                created_at=results_data["created_at"],
            )

            quality_report = await self.verify_quality_gates(test_results)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "quality_report": {
                        "id": quality_report.id,
                        "quality_gates_passed": quality_report.quality_gates_passed,
                        "issues": list(quality_report.issues),
                        "recommendations": list(quality_report.recommendations),
                        "approved": quality_report.approved,
                        "created_at": quality_report.created_at,
                    },
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def create_test_strategy(self, requirements: Requirements) -> TestStrategy:
        """Create test strategy based on requirements.

        Args:
            requirements: Requirements object

        Returns:
            TestStrategy object
        """
        # Determine test types based on requirements
        test_types = [TestType.UNIT, TestType.INTEGRATION]

        # Add E2E tests for high priority requirements
        if requirements.priority in [Priority.CRITICAL, Priority.HIGH]:
            test_types.append(TestType.E2E)

        strategy = TestStrategy.create(
            id=str(uuid.uuid4()),
            requirements_id=requirements.id,
            coverage_target=80,
            test_types=test_types,
            frameworks=["pytest", "pytest-cov", "pytest-asyncio"],
            ci_integration="Run tests on every PR, block merge if coverage < 80%",
        )

        return strategy

    async def write_tests(self, code: dict[str, Any]) -> list[Test]:
        """Write tests for code.

        Args:
            code: Code to test

        Returns:
            List of Test objects
        """
        # Generate tests based on code
        # In production, this would analyze code and generate appropriate tests
        tests = []

        # Create unit tests
        for i in range(3):
            test = Test.create(
                id=str(uuid.uuid4()),
                name=f"test_function_{i + 1}",
                type=TestType.UNIT,
                description=f"Unit test for function {i + 1}",
                file_path=f"tests/test_module_{i + 1}.py",
                function_name=f"test_function_{i + 1}",
            )
            tests.append(test)

        # Create integration test
        test = Test.create(
            id=str(uuid.uuid4()),
            name="test_integration",
            type=TestType.INTEGRATION,
            description="Integration test for module",
            file_path="tests/test_integration.py",
            function_name="test_integration",
        )
        tests.append(test)

        return tests

    async def run_tests(self, tests: list[Test]) -> TestResults:
        """Run tests and collect results.

        Args:
            tests: List of tests to run

        Returns:
            TestResults object
        """
        # Execute tests and collect results
        # In production, this would actually run the tests
        results = []

        for test in tests:
            # Simulate test execution
            result = TestResult(
                test_id=test.id,
                status=TestStatus.PASSED,
                duration_ms=100,
            )
            results.append(result)

        # Calculate coverage (simulated)
        coverage = 85.0

        test_results = TestResults.create(
            id=str(uuid.uuid4()),
            results=results,
            coverage_percentage=coverage,
        )

        return test_results

    async def verify_quality_gates(self, results: TestResults) -> QualityReport:
        """Verify quality gates and generate report.

        Args:
            results: Test results

        Returns:
            QualityReport object
        """
        issues = []
        recommendations = []

        # Check quality gates
        if results.failed > 0:
            issues.append(f"{results.failed} tests failed")

        if results.coverage_percentage < 80:
            issues.append(
                f"Coverage {results.coverage_percentage}% is below target 80%"
            )

        # Provide recommendations
        if results.skipped > 0:
            recommendations.append(f"Review {results.skipped} skipped tests")

        if results.coverage_percentage < 90:
            recommendations.append("Consider increasing test coverage to 90%")

        # Determine if quality gates passed
        quality_gates_passed = len(issues) == 0

        # Approve if quality gates passed
        approved = quality_gates_passed

        report = QualityReport.create(
            id=str(uuid.uuid4()),
            test_results=results,
            quality_gates_passed=quality_gates_passed,
            approved=approved,
            issues=issues,
            recommendations=recommendations,
        )

        return report


__all__ = ["QAEngineerAgent"]
