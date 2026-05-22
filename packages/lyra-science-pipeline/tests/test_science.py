"""Tests for Science Pipeline package."""

import pytest
from lyra_science_pipeline import SciencePipeline, Hypothesis, TrialHarness


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

    @pytest.mark.asyncio
    async def test_run_experiment(self):
        p = SciencePipeline()
        h = p.propose_hypothesis("Testing hypothesis", "IV", "DV", "increase")
        harness = p.create_harness("sandbox", {})
        result = await p.run_experiment(h.id, harness.id)
        assert result.hypothesis_id == h.id
        assert result.significance > 0

    def test_analyze_results(self):
        p = SciencePipeline()
        p.propose_hypothesis("H test", "a", "b", "up")
        analysis = p.analyze_results()
        assert len(analysis) == 1
        assert analysis[0]["hypothesis"] == "H test"
