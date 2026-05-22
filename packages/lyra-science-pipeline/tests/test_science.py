"""Tests for Science Pipeline package."""

import pytest
from lyra_science_pipeline import SciencePipeline


class TestSciencePipeline:
    def test_propose_hypothesis(self):
        p = SciencePipeline()
        h = p.propose_hypothesis("X causes Y", "X", "Y", "positive")
        assert h.id == "H1"
        assert h.status == "proposed"

    def test_create_harness(self):
        p = SciencePipeline()
        h = p.create_harness("code", {"language": "python"})
        assert h.id == "TH1"
        assert h.sandbox_type == "code"

    def test_run_experiment_sync(self):
        p = SciencePipeline()
        h = p.propose_hypothesis("Testing hypothesis", "IV", "DV", "increase")
        harness = p.create_harness("sandbox", {})
        import asyncio
        result = asyncio.run(p.run_experiment(h.id, harness.id))
        assert result.hypothesis_id == h.id
        assert result.significance > 0

    def test_analyze_results(self):
        p = SciencePipeline()
        p.propose_hypothesis("H test", "a", "b", "up")
        analysis = p.analyze_results()
        assert len(analysis) == 1
