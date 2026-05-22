"""Tests for lyra-evals-evolved."""
import pytest
from lyra_evals_evolved import BenchmarkSuite, AGIBenchmarkRunner, OpenEndedEvaluator, BenchmarkResult


class TestBenchmarkSuite:
    @pytest.mark.asyncio
    async def test_run_all(self):
        suite = BenchmarkSuite("test")
        suite.add_benchmark("specbench", {})
        suite.add_benchmark("agentbench", {})
        results = await suite.run_all()
        assert len(results) == 2
        assert all(r.score > 0 for r in results)


class TestAGIBenchmarkRunner:
    @pytest.mark.asyncio
    async def test_register_and_run(self):
        runner = AGIBenchmarkRunner()
        suite = BenchmarkSuite("specbench")
        runner.register_suite(suite)
        results = await runner.run_suite("specbench")
        assert isinstance(results, list)

    def test_agi_score(self):
        runner = AGIBenchmarkRunner()
        score = runner.compute_agi_score({
            "spec": [BenchmarkResult("test", 85, 100) for _ in range(2)]
        })
        assert score == 85.0


class TestOpenEndedEvaluator:
    @pytest.mark.asyncio
    async def test_propose_and_evaluate(self):
        eval_ = OpenEndedEvaluator()
        task = await eval_.propose_task(["code", "math", "research"])
        assert task is not None
        result = await eval_.evaluate(task, "agent output")
        assert result.score > 0
