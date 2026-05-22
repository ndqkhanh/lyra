"""Tests for lyra-experiment."""
from lyra_experiment import ExperimentRegistry, ExperimentStatus, AgentConfig, AgentExperiment


class TestExperimentRegistry:
    def test_create_experiment(self):
        r = ExperimentRegistry()
        exp = r.create_experiment(
            "test_exp",
            AgentConfig(id="c1", name="Control"),
            AgentConfig(id="v1", name="Variant"),
        )
        assert exp.id == "exp_1"
        assert exp.status == ExperimentStatus.DRAFT

    def test_start_and_pause(self):
        r = ExperimentRegistry()
        exp = r.create_experiment("test", AgentConfig("c", "C"), AgentConfig("v", "V"))
        assert r.start(exp.id)
        assert r.experiments[exp.id].status == ExperimentStatus.RUNNING
        assert r.pause(exp.id)
        assert r.experiments[exp.id].status == ExperimentStatus.PAUSED

    def test_record_and_results(self):
        r = ExperimentRegistry()
        exp = r.create_experiment("test", AgentConfig("c", "C"), AgentConfig("v", "V"))
        r.start(exp.id)
        for _ in range(10):
            r.record_result(exp.id, 0.8, is_variant=False)
            r.record_result(exp.id, 0.9, is_variant=True)
        results = r.get_results(exp.id)
        assert results is not None
        assert results["control"]["count"] == 10
        assert results["variant"]["count"] == 10

    def test_promote_variant(self):
        r = ExperimentRegistry()
        exp = r.create_experiment("test", AgentConfig("c", "C"), AgentConfig("v", "V"))
        r.start(exp.id)
        for _ in range(10):
            r.record_result(exp.id, 0.7, is_variant=False)
            r.record_result(exp.id, 0.9, is_variant=True)
        promoted = r.promote_variant(exp.id)
        assert promoted.id == "v"

    def test_summary(self):
        r = ExperimentRegistry()
        assert r.summary["total"] == 0
        r.create_experiment("e1", AgentConfig("c", "C"), AgentConfig("v", "V"))
        assert r.summary["total"] == 1
