"""
Tests for EvalHarness with tau-bench and SWE-bench integration.
"""

import pytest

from lyra.verification.eval_harness import (
    BenchmarkScoreboard,
    EvalHarness,
    EvalResults,
    EvalTask,
    SWEBenchRunner,
    TauBenchRunner,
    Tau2BenchRunner,
)


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, success_rate: float = 1.0):
        self.success_rate = success_rate
        self.call_count = 0

    async def run(self, prompt: str) -> dict:
        """Run agent on prompt."""
        self.call_count += 1
        passed = (self.call_count % int(1 / self.success_rate)) != 0

        return {
            "output": "Success" if passed else "Failure",
            "tokens": 100,
            "cost": 0.01,
        }


class TestTauBenchRunner:
    """Test Tau-Bench runner."""

    def test_get_tasks(self):
        """Test task retrieval."""
        runner = TauBenchRunner(domain="airline")
        tasks = runner.get_tasks(10)

        assert len(tasks) == 10
        assert all(isinstance(task, EvalTask) for task in tasks)
        assert all(task.domain == "airline" for task in tasks)

    @pytest.mark.asyncio
    async def test_check(self):
        """Test output checking."""
        runner = TauBenchRunner(domain="retail")
        task = EvalTask(
            task_id="test-001",
            prompt="Test task",
            expected_output="expected result",
        )

        # Should pass
        assert await runner.check(task, "This is the expected result")

        # Should fail
        assert not await runner.check(task, "Wrong output")

    def test_get_name(self):
        """Test runner name."""
        runner = TauBenchRunner(domain="telecom")
        assert runner.get_name() == "tau-bench-telecom"


class TestTau2BenchRunner:
    """Test Tau2-Bench runner."""

    def test_get_tasks(self):
        """Test task retrieval for multi-agent coordination."""
        runner = Tau2BenchRunner(domain="telecom")
        tasks = runner.get_tasks(5)

        assert len(tasks) == 5
        assert all("compositional" in task.prompt.lower() or task.task_id.startswith("tau2-") for task in tasks)


class TestSWEBenchRunner:
    """Test SWE-bench Verified runner."""

    def test_get_tasks(self):
        """Test SWE task retrieval."""
        runner = SWEBenchRunner()
        tasks = runner.get_tasks(10)

        assert len(tasks) == 10
        assert all(task.domain == "software_engineering" for task in tasks)

    @pytest.mark.asyncio
    async def test_check(self):
        """Test code verification."""
        runner = SWEBenchRunner()
        task = EvalTask(task_id="swe-001", prompt="Fix bug", domain="software_engineering")

        # Valid code
        assert await runner.check(task, "def fix():\n    return True")

        # Invalid code
        assert not await runner.check(task, "Not code at all")


class TestEvalHarness:
    """Test evaluation harness."""

    @pytest.mark.asyncio
    async def test_evaluate_perfect_agent(self):
        """Test evaluation with perfect agent."""
        harness = EvalHarness(backend="tau-bench", config={"domain": "airline"})
        agent = MockAgent(success_rate=1.0)

        results = await harness.evaluate(agent, tasks=5, k=3)

        assert isinstance(results, EvalResults)
        assert results.pass_at_1 == 1.0
        assert results.pass_at_k == 1.0
        assert results.n_tasks == 5
        assert results.k == 3
        assert len(results.task_results) == 5

    @pytest.mark.asyncio
    async def test_evaluate_inconsistent_agent(self):
        """Test evaluation with inconsistent agent."""
        harness = EvalHarness(backend="tau-bench", config={"domain": "retail"})
        agent = MockAgent(success_rate=0.5)

        results = await harness.evaluate(agent, tasks=10, k=5)

        # Inconsistent agent: pass@1 > pass@5
        assert results.pass_at_1 >= results.pass_at_k
        assert results.pass_at_k < 1.0

    @pytest.mark.asyncio
    async def test_evaluate_single_task(self):
        """Test single task evaluation."""
        harness = EvalHarness(backend="swe-bench")
        agent = MockAgent(success_rate=1.0)
        task = EvalTask(task_id="test-001", prompt="Test task", domain="software_engineering")

        result = await harness.evaluate_single(agent, task, k=3)

        assert result.task_id == "test-001"
        assert len(result.trials) == 3
        assert result.pass_at_1 in [True, False]

    def test_unknown_backend(self):
        """Test that unknown backend raises error."""
        with pytest.raises(ValueError, match="Unknown backend"):
            EvalHarness(backend="unknown-backend")

    @pytest.mark.asyncio
    async def test_tau2_bench_backend(self):
        """Test Tau2-Bench backend."""
        harness = EvalHarness(backend="tau2-bench", config={"domain": "telecom"})
        agent = MockAgent(success_rate=1.0)

        results = await harness.evaluate(agent, tasks=3, k=2)

        assert results.backend == "tau2-bench-telecom"
        assert results.n_tasks == 3


class TestBenchmarkScoreboard:
    """Test benchmark scoreboard."""

    def test_scoreboard_initialization(self):
        """Test scoreboard loads default entries."""
        scoreboard = BenchmarkScoreboard()

        assert len(scoreboard.entries) > 0
        assert any("tau-bench" in e.name for e in scoreboard.entries)
        assert any("SWE-bench" in e.name for e in scoreboard.entries)

    def test_update_score(self):
        """Test score updating."""
        scoreboard = BenchmarkScoreboard()
        initial_best = scoreboard.entries[0].lyra_best

        # Update with better score
        scoreboard.update(scoreboard.entries[0].name, initial_best + 0.1)

        assert scoreboard.entries[0].lyra_best == initial_best + 0.1

        # Update with worse score (should not change)
        scoreboard.update(scoreboard.entries[0].name, initial_best)

        assert scoreboard.entries[0].lyra_best == initial_best + 0.1

    def test_report_generation(self):
        """Test markdown report generation."""
        scoreboard = BenchmarkScoreboard()
        report = scoreboard.report()

        assert "| Benchmark | Metric | SOTA | Lyra Best | Target | Gap |" in report
        assert "tau-bench" in report
        assert "%" in report

    def test_get_entry(self):
        """Test getting specific entry."""
        scoreboard = BenchmarkScoreboard()
        entry = scoreboard.get_entry("tau-bench airline")

        assert entry is not None
        assert entry.name == "tau-bench airline"
        assert entry.metric == "pass@1"

        # Non-existent entry
        assert scoreboard.get_entry("nonexistent") is None
