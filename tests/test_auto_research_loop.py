"""Tests for Karpathy auto-research loop."""

from pathlib import Path
from lyra.research.auto_research_loop import (
    AutoResearchLoop,
    ExperimentLedger,
    ExperimentRecord,
    ExperimentStatus,
)


class TestExperimentLedger:
    """Experiment ledger tests."""

    def test_empty_ledger(self):
        ledger = ExperimentLedger()
        assert len(ledger.records) == 0
        assert ledger.best_record() is None
        assert ledger.best_metric() == float("-inf")
        assert ledger.total_kept() == 0
        assert ledger.total_discarded() == 0

    def test_append_and_query(self):
        ledger = ExperimentLedger()
        ledger.append(ExperimentRecord(
            iteration=1,
            hypothesis="Add caching layer",
            change_description="Added LRU cache to query path",
            metric_before=0.85,
            metric_after=0.92,
            delta=0.07,
            status=ExperimentStatus.KEPT,
            duration_seconds=45.2,
        ))
        assert len(ledger.records) == 1
        assert ledger.total_kept() == 1
        assert ledger.best_metric() == 0.92

    def test_multiple_records_best(self):
        ledger = ExperimentLedger()
        ledger.append(ExperimentRecord(1, "A", "desc", 0.5, 0.6, 0.1, ExperimentStatus.KEPT, 10.0))
        ledger.append(ExperimentRecord(2, "B", "desc", 0.6, 0.55, -0.05, ExperimentStatus.DISCARDED, 10.0))
        ledger.append(ExperimentRecord(3, "C", "desc", 0.55, 0.95, 0.4, ExperimentStatus.KEPT, 10.0))
        assert ledger.total_kept() == 2
        assert ledger.total_discarded() == 1
        assert ledger.best_metric() == 0.95

    def test_save_load_roundtrip(self, tmp_path):
        ledger = ExperimentLedger()
        ledger.append(ExperimentRecord(1, "Test", "desc", 0.5, 0.9, 0.4, ExperimentStatus.KEPT, 30.0))
        path = tmp_path / "results.jsonl"
        ledger.save(path)

        loaded = ExperimentLedger.load(path)
        assert len(loaded.records) == 1
        assert loaded.records[0].hypothesis == "Test"
        assert loaded.records[0].delta == 0.4


class TestAutoResearchLoop:
    """Auto-research loop tests."""

    def test_requires_proposer(self):
        loop = AutoResearchLoop(
            work_dir=Path("/tmp"),
            eval_command="echo 0.5",
        )
        try:
            loop.run()
            assert False, "Should have raised RuntimeError"
        except RuntimeError:
            pass

    def test_default_gate_higher_is_better(self):
        """Default gate: keep if metric_after > metric_before."""
        loop = AutoResearchLoop(
            work_dir=Path("/tmp"),
            eval_command="echo 0.5",
            max_iterations=1,
        )
        # Override _get_current_metric for deterministic testing
        loop._get_current_metric = lambda: 0.95  # type: ignore[method-assign]

        def mock_proposer(ledger, work_dir):
            _ = (ledger, work_dir)  # unused in mock
            return {
                "hypothesis": "Test hypothesis",
                "change_description": "Test change",
                "patch": "",
            }

        loop.set_proposer(mock_proposer)
        ledger = loop.run()
        assert len(ledger.records) == 1

    def test_ledger_persistence(self, tmp_path):
        """Ledger should persist to disk."""
        ledger = ExperimentLedger()
        path = tmp_path / "experiments.jsonl"
        ledger.save(path)
        assert path.is_file()

    def test_no_proposer_raises(self):
        loop = AutoResearchLoop(
            work_dir=Path("/tmp"),
            eval_command="echo 0.5",
        )
        try:
            loop.run()
            assert False
        except RuntimeError as e:
            assert "proposer" in str(e).lower()

    def test_max_consecutive_failures_stops_loop(self):
        loop = AutoResearchLoop(
            work_dir=Path("/tmp"),
            eval_command="echo 0.5",
            max_iterations=100,
            max_consecutive_failures=2,
        )
        loop._consecutive_failures = 2  # Simulate reaching limit
        loop.set_proposer(lambda l, w: {"hypothesis": "x", "change_description": "x"})
        loop._get_current_metric = lambda: 0.5  # type: ignore[method-assign]
        ledger = loop.run()
        assert len(ledger.records) == 0  # Stopped before first iteration
