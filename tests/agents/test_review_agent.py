"""
Tests for ReviewAgent — code review, security scan, and quality assessment.
"""

import pytest

from lyra.agents.review_agent import ReviewAgent
from lyra.core.task import Task, TaskType


class TestReviewAgentInit:

    def test_default_id(self):
        agent = ReviewAgent()
        assert agent.agent_id == "review_agent"

    def test_two_capabilities(self):
        agent = ReviewAgent()
        assert len(agent.capabilities) == 2
        names = {c.name for c in agent.capabilities}
        assert names == {"code_review", "security_scan"}

    def test_custom_id(self):
        agent = ReviewAgent(agent_id="my-reviewer")
        assert agent.agent_id == "my-reviewer"


class TestReviewAgentCanHandle:

    def test_code_review(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.CODE_REVIEW, description="review")
        assert agent.can_handle(task) > 0.0

    def test_security_scan(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.SECURITY_SCAN, description="scan")
        assert agent.can_handle(task) > 0.0

    def test_unhandled_task(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        assert agent.can_handle(task) == 0.0


class TestReviewAgentExecute:

    @pytest.mark.asyncio
    async def test_execute_code_review(self):
        agent = ReviewAgent()
        task = Task(
            type=TaskType.CODE_REVIEW,
            description="Review auth module",
            params={"file_path": "src/auth.py"},
        )
        result = await agent.execute(task)
        assert result.success
        assert result.agent_id == "review_agent"
        data = result.data
        assert data["file"] == "src/auth.py"
        assert data["overall_quality"] == "good"
        assert data["score"] == 7.5
        assert len(data["issues"]) == 3
        assert len(data["strengths"]) == 3
        assert len(data["recommendations"]) == 3

    @pytest.mark.asyncio
    async def test_execute_security_scan(self):
        agent = ReviewAgent()
        task = Task(
            type=TaskType.SECURITY_SCAN,
            description="Security scan",
            params={"target": "src/"},
        )
        result = await agent.execute(task)
        assert result.success
        data = result.data
        assert data["target"] == "src/"
        assert data["vulnerabilities_found"] == 2
        assert data["critical"] == 0
        assert data["high"] == 0
        assert data["medium"] == 1
        assert data["low"] == 1
        assert data["security_score"] == 8.0

    @pytest.mark.asyncio
    async def test_execute_unsupported_type_returns_error(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        result = await agent.execute(task)
        assert not result.success
        assert "Unsupported task type" in result.error

    @pytest.mark.asyncio
    async def test_execute_sets_status_lifecycle(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.CODE_REVIEW, description="test")
        await agent.execute(task)
        assert agent.status.value == "idle"
        assert agent.current_task is None

    @pytest.mark.asyncio
    async def test_execute_records_history(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.CODE_REVIEW, description="test")
        await agent.execute(task)
        assert len(agent.execution_history) == 1

    @pytest.mark.asyncio
    async def test_code_review_default_file_path(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.CODE_REVIEW, description="review")
        result = await agent.execute(task)
        assert result.success
        assert result.data["file"] == "unknown"

    @pytest.mark.asyncio
    async def test_security_scan_default_target(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.SECURITY_SCAN, description="scan")
        result = await agent.execute(task)
        assert result.success
        assert result.data["target"] == "."


class TestReviewAgentReviewCode:

    @pytest.mark.asyncio
    async def test_review_code_issues_have_expected_structure(self):
        agent = ReviewAgent()
        task = Task(
            type=TaskType.CODE_REVIEW,
            description="review",
            params={"file_path": "src/app.py"},
        )
        result = await agent.execute(task)
        for issue in result.data["issues"]:
            assert "severity" in issue
            assert "category" in issue
            assert "message" in issue
            assert "line" in issue
            assert "suggestion" in issue

    @pytest.mark.asyncio
    async def test_review_code_includes_warnings(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.CODE_REVIEW, description="review")
        result = await agent.execute(task)
        severities = {i["severity"] for i in result.data["issues"]}
        assert "warning" in severities
        assert "info" in severities


class TestReviewAgentSecurityScan:

    @pytest.mark.asyncio
    async def test_security_vulnerabilities_have_structure(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.SECURITY_SCAN, description="scan")
        result = await agent.execute(task)
        for vuln in result.data["vulnerabilities"]:
            assert "severity" in vuln
            assert "type" in vuln
            assert "file" in vuln
            assert "line" in vuln
            assert "description" in vuln
            assert "recommendation" in vuln

    @pytest.mark.asyncio
    async def test_security_scan_includes_recommendations(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.SECURITY_SCAN, description="scan")
        result = await agent.execute(task)
        assert len(result.data["recommendations"]) == 3


class TestReviewAgentAssessQuality:

    @pytest.mark.asyncio
    async def test_assess_quality_returns_scores(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.CODE_REVIEW, description="quality")  # will route to review_code
        result = await agent.execute(task)
        assert result.success

    @pytest.mark.asyncio
    async def test_assess_quality_direct_call(self):
        agent = ReviewAgent()
        task = Task(type=TaskType.CODE_REVIEW, description="quality check")
        # Call assess_quality directly to exercise the method
        # (since execute routes CODE_REVIEW to review_code, we call it directly)
        quality = await agent.assess_quality(task)
        assert quality["overall_score"] == 7.8
        assert "metrics" in quality
        assert quality["metrics"]["maintainability"] == 8.0
        assert "strengths" in quality
        assert "areas_for_improvement" in quality
