"""
Integration tests for self-healing execution (US-028).

Tests self-healing execution with Pivot/Refine loops and error recovery.
"""

import pytest
from lyra_core.context.layered_context import LayeredContextManager
from lyra_research.coordination.parallel_executor import ParallelExecutor
from lyra_research.roles.role_base import Role, RoleResult, RoleStatus


class MockRole(Role):
    """Mock role for testing."""

    def __init__(self, name: str, should_fail: bool = False, fail_count: int = 0):
        # Create mock context manager
        mock_context = LayeredContextManager(max_tokens=100000)
        super().__init__(name, model="test-model", context_manager=mock_context)
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.attempt_count = 0

    def validate_input(self, input_data) -> bool:
        """Validate input data."""
        return input_data is not None

    def validate_output(self, output) -> bool:
        """Validate output data."""
        # Always return True to avoid VALIDATION_ERROR status
        return True

    async def execute(self, input_data):
        """Execute role logic."""
        self.attempt_count += 1

        # Fail for first N attempts by raising exception
        if self.attempt_count <= self.fail_count:
            raise RuntimeError(f"Transient error (attempt {self.attempt_count})")

        # Succeed after fail_count attempts
        if not self.should_fail:
            result = RoleResult(
                role_name=self.name,
                status=RoleStatus.SUCCESS,
                data={"result": f"Success from {self.name}", "attempts": self.attempt_count},
                error=None,
            )
            return result

        # Permanent failure by raising exception
        raise RuntimeError("Permanent failure")


class TestSelfHealingExecution:
    """Test self-healing execution with retry logic."""

    @pytest.mark.asyncio
    async def test_execute_success_no_healing(self):
        """Test successful execution without healing."""
        executor = ParallelExecutor()
        role = MockRole("test_role", should_fail=False)

        result = await executor.execute_with_retries(role, {"input": "test"}, max_retries=0)

        assert result.status == RoleStatus.SUCCESS
        assert result.data["result"] == "Success from test_role"
        assert result.data["attempts"] == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self):
        """Test execution with transient failure and retry."""
        executor = ParallelExecutor()
        # Fail first 2 attempts, succeed on 3rd
        role = MockRole("flaky_role", should_fail=False, fail_count=2)

        result = await executor.execute_with_retries(
            role, {"input": "test"}, max_retries=3, retry_delay_seconds=0.1
        )

        assert result.status == RoleStatus.SUCCESS
        assert result.data["attempts"] == 3
        assert role.attempt_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_max_retries_exhausted(self):
        """Test execution with max retries exhausted."""
        executor = ParallelExecutor()
        # Always fail
        role = MockRole("failing_role", should_fail=True)

        result = await executor.execute_with_retries(
            role, {"input": "test"}, max_retries=2, retry_delay_seconds=0.1
        )

        assert result.status == RoleStatus.FAILED
        assert "after 2 retries" in result.error
        assert role.attempt_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """Test execution with timeout."""
        executor = ParallelExecutor()

        # Create role that takes too long
        class SlowRole(Role):
            def __init__(self):
                mock_context = LayeredContextManager(max_tokens=100000)
                super().__init__("slow_role", model="test-model", context_manager=mock_context)

            def validate_input(self, input_data) -> bool:
                return True

            def validate_output(self, output) -> bool:
                return True

            async def execute(self, input_data):
                import asyncio

                await asyncio.sleep(10)  # Sleep longer than timeout
                return RoleResult(
                    role_name=self.name,
                    status=RoleStatus.SUCCESS,
                    data={"result": "Should not reach here"},
                    error=None,
                )

        role = SlowRole()
        result = await executor.execute_with_timeout(role, {"input": "test"}, timeout_seconds=1)

        assert result.status == RoleStatus.FAILED
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_parallel_execution_with_mixed_results(self):
        """Test parallel execution with some successes and failures."""
        executor = ParallelExecutor()

        roles = [
            MockRole("success_role", should_fail=False),
            MockRole("fail_role", should_fail=True),
            MockRole("retry_role", should_fail=False, fail_count=1),
        ]

        results = await executor.execute_parallel_roles(roles, {"input": "test"})

        assert len(results) == 3
        assert results[0].status == RoleStatus.SUCCESS
        assert results[1].status == RoleStatus.FAILED
        assert results[2].status == RoleStatus.SUCCESS


class TestSelfHealingIntegration:
    """Integration tests for self-healing execution."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_stage_healing(self):
        """Test multi-stage healing: retry → pivot → refine."""
        executor = ParallelExecutor()

        # Simulate multi-stage healing with different roles
        stage1_role = MockRole("stage1", should_fail=False, fail_count=1)
        stage2_role = MockRole("stage2", should_fail=False, fail_count=0)

        # Stage 1: Retry until success
        result1 = await executor.execute_with_retries(
            stage1_role, {"input": "test"}, max_retries=2, retry_delay_seconds=0.1
        )

        assert result1.status == RoleStatus.SUCCESS
        assert stage1_role.attempt_count == 2

        # Stage 2: Use result from stage 1
        result2 = await executor.execute_with_retries(
            stage2_role, result1.data, max_retries=1, retry_delay_seconds=0.1
        )

        assert result2.status == RoleStatus.SUCCESS

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_sequential_execution_with_healing(self):
        """Test sequential execution with self-healing."""
        executor = ParallelExecutor()

        roles = [
            MockRole("step1", should_fail=False, fail_count=1),
            MockRole("step2", should_fail=False, fail_count=0),
            MockRole("step3", should_fail=False, fail_count=1),
        ]

        # Execute sequentially with retries
        results = []
        current_input = {"input": "initial"}

        for role in roles:
            result = await executor.execute_with_retries(
                role, current_input, max_retries=2, retry_delay_seconds=0.1
            )
            results.append(result)

            if result.status != RoleStatus.SUCCESS:
                break

            current_input = result.data

        assert len(results) == 3
        assert all(r.status == RoleStatus.SUCCESS for r in results)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_healing_with_dependency_graph(self):
        """Test healing in dependency graph execution."""
        executor = ParallelExecutor()

        # Create dependency graph
        role_graph = {
            "root": (MockRole("root", should_fail=False, fail_count=0), []),
            "child1": (MockRole("child1", should_fail=False, fail_count=1), ["root"]),
            "child2": (MockRole("child2", should_fail=False, fail_count=0), ["root"]),
            "grandchild": (
                MockRole("grandchild", should_fail=False, fail_count=1),
                ["child1", "child2"],
            ),
        }

        results = await executor.execute_with_dependencies(role_graph, {"input": "test"})

        assert len(results) == 4
        assert all(r.status == RoleStatus.SUCCESS for r in results.values())


class TestErrorRecovery:
    """Test error recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_recover_from_transient_error(self):
        """Test recovering from transient errors."""
        executor = ParallelExecutor()
        role = MockRole("transient", should_fail=False, fail_count=2)

        result = await executor.execute_with_retries(
            role, {"input": "test"}, max_retries=3, retry_delay_seconds=0.05
        )

        assert result.status == RoleStatus.SUCCESS
        assert role.attempt_count == 3

    @pytest.mark.asyncio
    async def test_fail_on_permanent_error(self):
        """Test failing on permanent errors."""
        executor = ParallelExecutor()
        role = MockRole("permanent_fail", should_fail=True)

        result = await executor.execute_with_retries(
            role, {"input": "test"}, max_retries=2, retry_delay_seconds=0.05
        )

        assert result.status == RoleStatus.FAILED
        assert "Permanent failure" in result.error

    @pytest.mark.asyncio
    async def test_error_propagation_in_sequential(self):
        """Test error propagation in sequential execution."""
        executor = ParallelExecutor()

        roles = [
            MockRole("step1", should_fail=False),
            MockRole("step2", should_fail=True),  # This will fail
            MockRole("step3", should_fail=False),  # Should not execute
        ]

        results = await executor.execute_sequential(roles, {"input": "test"})

        assert len(results) == 2  # Should stop after step2 fails
        assert results[0].status == RoleStatus.SUCCESS
        assert results[1].status == RoleStatus.FAILED

    @pytest.mark.asyncio
    async def test_partial_success_in_parallel(self):
        """Test partial success in parallel execution."""
        executor = ParallelExecutor()

        roles = [
            MockRole("success1", should_fail=False),
            MockRole("fail1", should_fail=True),
            MockRole("success2", should_fail=False),
            MockRole("fail2", should_fail=True),
        ]

        results = await executor.execute_parallel_roles(roles, {"input": "test"})

        assert len(results) == 4
        successes = [r for r in results if r.status == RoleStatus.SUCCESS]
        failures = [r for r in results if r.status == RoleStatus.FAILED]

        assert len(successes) == 2
        assert len(failures) == 2


class TestPerformanceTracking:
    """Test tracking self-healing performance."""

    @pytest.mark.asyncio
    async def test_track_retry_count(self):
        """Test tracking retry count."""
        executor = ParallelExecutor()
        role = MockRole("tracked", should_fail=False, fail_count=3)

        result = await executor.execute_with_retries(
            role, {"input": "test"}, max_retries=5, retry_delay_seconds=0.01
        )

        assert result.status == RoleStatus.SUCCESS
        assert role.attempt_count == 4  # Initial + 3 retries

    @pytest.mark.asyncio
    async def test_track_healing_time(self):
        """Test tracking healing time."""
        import time

        executor = ParallelExecutor()
        role = MockRole("timed", should_fail=False, fail_count=2)

        start_time = time.time()
        result = await executor.execute_with_retries(
            role, {"input": "test"}, max_retries=3, retry_delay_seconds=0.1
        )
        elapsed = time.time() - start_time

        assert result.status == RoleStatus.SUCCESS
        # Should take at least 0.2 seconds (2 retries * 0.1s delay)
        assert elapsed >= 0.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
