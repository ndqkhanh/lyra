"""Tests for QA Engineer Agent."""

from __future__ import annotations

import pytest
import pytest_asyncio
from lyra_core.orchestration.agent_base import AgentMetadata, AgentRole, AgentStatus
from lyra_core.orchestration.agents.qa_agent import QAEngineerAgent
from lyra_core.orchestration.message_bus import InMemoryMessageBus
from lyra_core.orchestration.models.requirements import Priority, Requirements
from lyra_core.orchestration.models.testing import Test, TestType


@pytest_asyncio.fixture
async def message_bus() -> InMemoryMessageBus:
    """Create message bus fixture."""
    bus = InMemoryMessageBus()
    yield bus
    await bus.clear()


@pytest_asyncio.fixture
async def qa_agent(message_bus: InMemoryMessageBus) -> QAEngineerAgent:
    """Create QA Engineer agent fixture."""
    metadata = AgentMetadata.create(
        agent_id="qa-1",
        role=AgentRole.QA,
        team_id="team-1",
        capabilities=["testing", "quality_assurance", "test_strategy"],
    )
    agent = QAEngineerAgent(metadata, message_bus)
    await agent.start()
    yield agent
    await agent.stop()


@pytest.fixture
def sample_requirements() -> Requirements:
    """Create sample requirements."""
    return Requirements.create(
        id="req-1",
        description="Build user authentication",
        goals=["Secure authentication", "User management"],
        priority=Priority.HIGH,
    )


@pytest.mark.asyncio
async def test_qa_agent_initialization(qa_agent: QAEngineerAgent) -> None:
    """Test QA Engineer agent initialization."""
    assert qa_agent.agent_id == "qa-1"
    assert qa_agent.role == AgentRole.QA
    assert qa_agent.status == AgentStatus.IDLE


@pytest.mark.asyncio
async def test_create_test_strategy(
    qa_agent: QAEngineerAgent, sample_requirements: Requirements
) -> None:
    """Test test strategy creation."""
    strategy = await qa_agent.create_test_strategy(sample_requirements)

    assert strategy.requirements_id == sample_requirements.id
    assert strategy.coverage_target >= 80
    assert len(strategy.test_types) > 0
    assert len(strategy.frameworks) > 0


@pytest.mark.asyncio
async def test_write_tests(qa_agent: QAEngineerAgent) -> None:
    """Test test writing."""
    code = {"module": "auth", "functions": ["login", "logout"]}

    tests = await qa_agent.write_tests(code)

    assert len(tests) > 0
    for test in tests:
        assert test.type in TestType
        assert test.file_path
        assert test.function_name


@pytest.mark.asyncio
async def test_run_tests(qa_agent: QAEngineerAgent) -> None:
    """Test test execution."""
    tests = [
        Test.create(
            id="test-1",
            name="test_login",
            type=TestType.UNIT,
            description="Test login function",
            file_path="tests/test_auth.py",
            function_name="test_login",
        ),
        Test.create(
            id="test-2",
            name="test_logout",
            type=TestType.UNIT,
            description="Test logout function",
            file_path="tests/test_auth.py",
            function_name="test_logout",
        ),
    ]

    results = await qa_agent.run_tests(tests)

    assert results.total == len(tests)
    assert results.passed + results.failed + results.skipped == results.total
    assert results.coverage_percentage >= 0


@pytest.mark.asyncio
async def test_verify_quality_gates(qa_agent: QAEngineerAgent) -> None:
    """Test quality gate verification."""
    tests = [
        Test.create(
            id="test-1",
            name="test_function",
            type=TestType.UNIT,
            description="Test function",
            file_path="tests/test_module.py",
            function_name="test_function",
        )
    ]

    results = await qa_agent.run_tests(tests)
    quality_report = await qa_agent.verify_quality_gates(results)

    assert quality_report.test_results == results
    assert isinstance(quality_report.quality_gates_passed, bool)
    assert isinstance(quality_report.approved, bool)


@pytest.mark.asyncio
async def test_handle_create_test_strategy_message(
    qa_agent: QAEngineerAgent,
    message_bus: InMemoryMessageBus,
    sample_requirements: Requirements,
) -> None:
    """Test handling create test strategy message."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="qa-1",
        payload={
            "action": "create_test_strategy",
            "requirements": {
                "id": sample_requirements.id,
                "description": sample_requirements.description,
                "goals": list(sample_requirements.goals),
                "constraints": list(sample_requirements.constraints),
                "stakeholders": list(sample_requirements.stakeholders),
                "priority": sample_requirements.priority.value,
                "created_at": sample_requirements.created_at,
            },
        },
        timeout=5.0,
    )

    assert response.payload["status"] == "success"
    assert "test_strategy" in response.payload
    assert response.payload["test_strategy"]["coverage_target"] >= 80


@pytest.mark.asyncio
async def test_quality_gates_fail_on_low_coverage(qa_agent: QAEngineerAgent) -> None:
    """Test quality gates fail when coverage is low."""
    tests = [
        Test.create(
            id="test-1",
            name="test_function",
            type=TestType.UNIT,
            description="Test function",
            file_path="tests/test_module.py",
            function_name="test_function",
        )
    ]

    # Manually create results with low coverage
    from lyra_core.orchestration.models.testing import TestResult, TestResults, TestStatus

    results = TestResults.create(
        id="results-1",
        results=[
            TestResult(
                test_id="test-1",
                status=TestStatus.PASSED,
                duration_ms=100,
            )
        ],
        coverage_percentage=50.0,  # Below 80% threshold
    )

    quality_report = await qa_agent.verify_quality_gates(results)

    assert not quality_report.quality_gates_passed
    assert not quality_report.approved
    assert len(quality_report.issues) > 0
