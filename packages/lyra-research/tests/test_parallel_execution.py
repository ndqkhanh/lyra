"""
Integration tests for parallel research execution.

Tests parallel execution patterns:
- Concurrent workflow execution
- Result aggregation from parallel workflows
- Load balancing across workflows
- Deadlock prevention
- Resource contention handling
"""

import pytest
from unittest.mock import Mock, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from threading import Lock


class ParallelWorkflowExecutor:
    """Execute workflows in parallel."""

    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.results = []
        self.lock = Lock()

    def execute_parallel(self, workflows: list, topic: str):
        """Execute workflows in parallel."""
        futures = []

        for workflow in workflows:
            future = self.executor.submit(workflow.execute, topic)
            futures.append(future)

        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                with self.lock:
                    results.append(result)
            except Exception as e:
                with self.lock:
                    results.append({"error": str(e)})

        return results

    def shutdown(self):
        """Shutdown executor."""
        self.executor.shutdown(wait=True)


class MockWorkflow:
    """Mock workflow for testing."""

    def __init__(self, name: str, execution_time: float = 0.1):
        self.name = name
        self.execution_time = execution_time
        self.executed = False

    def execute(self, topic: str):
        """Execute workflow."""
        time.sleep(self.execution_time)
        self.executed = True
        return {
            "workflow": self.name,
            "topic": topic,
            "execution_time": self.execution_time,
            "quality_score": 0.85,
        }


class ResourcePool:
    """Mock resource pool for testing."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.available = capacity
        self.lock = Lock()

    def acquire(self, amount: int = 1):
        """Acquire resources."""
        with self.lock:
            if self.available >= amount:
                self.available -= amount
                return True
            return False

    def release(self, amount: int = 1):
        """Release resources."""
        with self.lock:
            self.available = min(self.capacity, self.available + amount)


@pytest.mark.integration
class TestParallelExecution:
    """Test parallel workflow execution."""

    def test_concurrent_workflow_execution(self):
        """Test executing multiple workflows concurrently."""
        # Setup
        executor = ParallelWorkflowExecutor(max_workers=3)
        workflows = [
            MockWorkflow("deep", 0.1),
            MockWorkflow("auto", 0.1),
            MockWorkflow("scientist", 0.1),
        ]

        # Execute
        start_time = time.time()
        results = executor.execute_parallel(workflows, "LLM reasoning")
        elapsed = time.time() - start_time

        # Verify
        assert len(results) == 3
        assert all(r.get("topic") == "LLM reasoning" for r in results)
        # Parallel execution should be faster than sequential
        assert elapsed < 0.4  # Should be ~0.1s, not 0.3s
        executor.shutdown()

    def test_result_aggregation_from_parallel_workflows(self):
        """Test aggregating results from parallel workflows."""
        # Setup
        executor = ParallelWorkflowExecutor(max_workers=3)
        workflows = [
            MockWorkflow("deep", 0.05),
            MockWorkflow("auto", 0.05),
            MockWorkflow("scientist", 0.05),
        ]

        # Execute
        results = executor.execute_parallel(workflows, "LLM reasoning")

        # Aggregate
        aggregated = {
            "workflows_executed": len(results),
            "workflow_names": [r["workflow"] for r in results],
            "avg_quality": sum(r["quality_score"] for r in results) / len(results),
        }

        # Verify
        assert aggregated["workflows_executed"] == 3
        assert set(aggregated["workflow_names"]) == {"deep", "auto", "scientist"}
        assert aggregated["avg_quality"] == 0.85
        executor.shutdown()

    def test_parallel_execution_with_different_speeds(self):
        """Test parallel execution with workflows of different speeds."""
        # Setup
        executor = ParallelWorkflowExecutor(max_workers=3)
        workflows = [
            MockWorkflow("fast", 0.05),
            MockWorkflow("medium", 0.1),
            MockWorkflow("slow", 0.2),
        ]

        # Execute
        start_time = time.time()
        results = executor.execute_parallel(workflows, "LLM reasoning")
        elapsed = time.time() - start_time

        # Verify
        assert len(results) == 3
        # Should complete in time of slowest workflow
        assert 0.2 <= elapsed < 0.3
        executor.shutdown()

    def test_parallel_execution_error_handling(self):
        """Test error handling in parallel execution."""
        # Setup
        executor = ParallelWorkflowExecutor(max_workers=3)

        # Create failing workflow
        failing_workflow = Mock()
        failing_workflow.execute = Mock(side_effect=Exception("Workflow failed"))

        workflows = [
            MockWorkflow("success1", 0.05),
            failing_workflow,
            MockWorkflow("success2", 0.05),
        ]

        # Execute
        results = executor.execute_parallel(workflows, "LLM reasoning")

        # Verify
        assert len(results) == 3
        success_results = [r for r in results if "error" not in r]
        error_results = [r for r in results if "error" in r]
        assert len(success_results) == 2
        assert len(error_results) == 1
        executor.shutdown()

    def test_load_balancing_across_workflows(self):
        """Test load balancing across parallel workflows."""
        # Setup
        executor = ParallelWorkflowExecutor(max_workers=2)
        workflows = [
            MockWorkflow(f"workflow{i}", 0.05)
            for i in range(4)
        ]

        # Execute
        start_time = time.time()
        results = executor.execute_parallel(workflows, "LLM reasoning")
        elapsed = time.time() - start_time

        # Verify
        assert len(results) == 4
        # With 2 workers and 4 tasks, should take ~2 batches
        assert 0.1 <= elapsed < 0.2
        executor.shutdown()


@pytest.mark.integration
class TestResourceContention:
    """Test resource contention handling."""

    def test_resource_pool_acquisition(self):
        """Test acquiring resources from pool."""
        # Setup
        pool = ResourcePool(capacity=10)

        # Acquire resources
        assert pool.acquire(3) is True
        assert pool.available == 7

        assert pool.acquire(5) is True
        assert pool.available == 2

        # Try to acquire more than available
        assert pool.acquire(5) is False
        assert pool.available == 2

    def test_resource_pool_release(self):
        """Test releasing resources back to pool."""
        # Setup
        pool = ResourcePool(capacity=10)

        # Acquire and release
        pool.acquire(5)
        assert pool.available == 5

        pool.release(3)
        assert pool.available == 8

        pool.release(5)
        assert pool.available == 10  # Capped at capacity

    def test_concurrent_resource_access(self):
        """Test concurrent access to resource pool."""
        # Setup
        pool = ResourcePool(capacity=10)
        executor = ThreadPoolExecutor(max_workers=3)

        def acquire_and_release(amount: int):
            if pool.acquire(amount):
                time.sleep(0.05)
                pool.release(amount)
                return True
            return False

        # Execute concurrent acquisitions
        futures = [
            executor.submit(acquire_and_release, 3)
            for _ in range(5)
        ]

        results = [f.result() for f in futures]

        # Verify
        # Some should succeed, some may fail due to contention
        assert any(results)
        assert pool.available <= 10
        executor.shutdown()

    def test_workflow_resource_coordination(self):
        """Test coordinating resources across workflows."""
        # Setup
        pool = ResourcePool(capacity=10)

        class ResourceAwareWorkflow:
            def __init__(self, name: str, resource_need: int):
                self.name = name
                self.resource_need = resource_need

            def execute(self, topic: str):
                if pool.acquire(self.resource_need):
                    try:
                        time.sleep(0.05)
                        return {
                            "workflow": self.name,
                            "success": True,
                            "resources_used": self.resource_need,
                        }
                    finally:
                        pool.release(self.resource_need)
                else:
                    return {
                        "workflow": self.name,
                        "success": False,
                        "error": "Insufficient resources",
                    }

        # Execute workflows
        workflows = [
            ResourceAwareWorkflow("workflow1", 3),
            ResourceAwareWorkflow("workflow2", 4),
            ResourceAwareWorkflow("workflow3", 5),
        ]

        executor = ParallelWorkflowExecutor(max_workers=3)
        results = executor.execute_parallel(workflows, "LLM reasoning")

        # Verify
        assert len(results) == 3
        successful = [r for r in results if r.get("success")]
        assert len(successful) >= 1
        executor.shutdown()


@pytest.mark.integration
class TestDeadlockPrevention:
    """Test deadlock prevention in parallel execution."""

    def test_timeout_prevents_deadlock(self):
        """Test timeout mechanism prevents deadlock."""
        # Setup
        class TimeoutWorkflow:
            def __init__(self, name: str, timeout: float):
                self.name = name
                self.timeout = timeout

            def execute(self, topic: str):
                start = time.time()
                # Simulate long-running task
                time.sleep(0.2)
                elapsed = time.time() - start

                if elapsed > self.timeout:
                    raise TimeoutError(f"Workflow {self.name} timed out")

                return {"workflow": self.name, "success": True}

        workflows = [
            TimeoutWorkflow("workflow1", 0.1),
            TimeoutWorkflow("workflow2", 0.3),
        ]

        executor = ParallelWorkflowExecutor(max_workers=2)
        results = executor.execute_parallel(workflows, "LLM reasoning")

        # Verify
        assert len(results) == 2
        errors = [r for r in results if "error" in r]
        assert len(errors) == 1
        executor.shutdown()

    def test_resource_ordering_prevents_deadlock(self):
        """Test resource ordering prevents deadlock."""
        # Setup
        resource_a = Lock()
        resource_b = Lock()

        def workflow1():
            # Always acquire in same order
            with resource_a:
                time.sleep(0.01)
                with resource_b:
                    return {"workflow": "workflow1", "success": True}

        def workflow2():
            # Same order prevents deadlock
            with resource_a:
                time.sleep(0.01)
                with resource_b:
                    return {"workflow": "workflow2", "success": True}

        # Execute
        executor = ThreadPoolExecutor(max_workers=2)
        future1 = executor.submit(workflow1)
        future2 = executor.submit(workflow2)

        result1 = future1.result(timeout=1.0)
        result2 = future2.result(timeout=1.0)

        # Verify
        assert result1["success"]
        assert result2["success"]
        executor.shutdown()


@pytest.mark.integration
class TestParallelResultAggregation:
    """Test aggregating results from parallel workflows."""

    def test_aggregate_quality_scores(self):
        """Test aggregating quality scores from parallel workflows."""
        # Setup
        results = [
            {"workflow": "deep", "quality_score": 0.85},
            {"workflow": "auto", "quality_score": 0.88},
            {"workflow": "scientist", "quality_score": 0.82},
        ]

        # Aggregate
        avg_quality = sum(r["quality_score"] for r in results) / len(results)
        max_quality = max(r["quality_score"] for r in results)
        min_quality = min(r["quality_score"] for r in results)

        # Verify
        assert 0.84 < avg_quality < 0.86
        assert max_quality == 0.88
        assert min_quality == 0.82

    def test_aggregate_findings_from_parallel_workflows(self):
        """Test aggregating findings from parallel workflows."""
        # Setup
        results = [
            {
                "workflow": "deep",
                "findings": ["Finding 1", "Finding 2"],
            },
            {
                "workflow": "auto",
                "findings": ["Finding 3", "Finding 4"],
            },
            {
                "workflow": "scientist",
                "findings": ["Finding 5"],
            },
        ]

        # Aggregate
        all_findings = []
        for result in results:
            all_findings.extend(result["findings"])

        # Verify
        assert len(all_findings) == 5
        assert "Finding 1" in all_findings
        assert "Finding 5" in all_findings

    def test_aggregate_with_weighted_results(self):
        """Test weighted aggregation of parallel results."""
        # Setup
        results = [
            {"workflow": "deep", "quality_score": 0.85, "weight": 0.5},
            {"workflow": "auto", "quality_score": 0.88, "weight": 0.3},
            {"workflow": "scientist", "quality_score": 0.82, "weight": 0.2},
        ]

        # Weighted average
        weighted_quality = sum(
            r["quality_score"] * r["weight"] for r in results
        )

        # Verify
        expected = 0.85 * 0.5 + 0.88 * 0.3 + 0.82 * 0.2
        assert abs(weighted_quality - expected) < 0.001
