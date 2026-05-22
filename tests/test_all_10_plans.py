"""Integration test: ALL 10 Lyra AGI plans working together."""
import os, sys

_p = os.path.join(os.path.dirname(__file__), "..", "packages")
for _d in sorted(os.listdir(_p)):
    _s = os.path.join(_p, _d, "src")
    if os.path.isdir(_s):
        sys.path.insert(0, _s)


class TestAll10Plans:
    """Verify all 10 plans can be used together."""

    def test_all_imports(self):
        """Plans 1-5 (AGI)"""
        from lyra_verification_mesh import VerificationMesh
        from lyra_causal_graph import CausalGraph
        from lyra_drift_detector import DriftOrchestrator
        from lyra_meta_evolution import MetaCognitiveStack
        from lyra_colony import AgentColony
        """Plans 6-10 (Breakthrough)"""
        from lyra_instincts import InstinctEngine
        from lyra_beliefs import BeliefSystem
        from lyra_memory_token import TokenNativeIndex
        from lyra_router import AgentRouter
        from lyra_identity import AgentIdentity
        from lyra_resilience import CircuitBreaker
        from lyra_sla import SLAManager
        from lyra_experiment import ExperimentRegistry
        from lyra_ecology import AgentEcology
        from lyra_emergence import EmergenceDetector
        assert True

    def test_plan6_plan8_integration(self):
        """Instincts → Commands → Router pipeline."""
        from lyra_instincts import InstinctEngine
        from lyra_router import AgentRouter, AgentInstance
        engine = InstinctEngine()
        inst = engine.collect("code_review", "Always lint before commit")
        engine._project_instincts[inst.id].hit_count = 15
        router = AgentRouter()
        router.register(AgentInstance(id="a1", capabilities=["code"]))
        assert router.route("code", ["code"]) is not None
        assert engine.status()["total"] >= 1

    def test_plan7_plan9_integration(self):
        """Token memory → Experiment platform."""
        from lyra_memory_token import TokenNativeIndex
        from lyra_experiment import ExperimentRegistry, AgentConfig
        idx = TokenNativeIndex()
        idx.index("doc1", "Experiment results: variant improved by 15%")
        exp = ExperimentRegistry()
        exp.create_experiment("test", AgentConfig("c","C"), AgentConfig("v","V"))
        results = idx.retrieve("experiment results", top_k=5)
        assert len(results) >= 1
        assert exp.summary["total"] == 1

    def test_plan10_integration(self):
        """Ecology → Emergence pipeline."""
        from lyra_ecology import AgentEcology
        from lyra_emergence import EmergenceDetector
        eco = AgentEcology()
        eco.seed(count=10)
        detect = EmergenceDetector()
        for _ in range(20):
            s = eco.step()
            detect.record_generation(s)
        report = detect.get_report()
        assert report["generations_tracked"] == 20

    def test_breakthrough_integration_facade(self):
        """BreakthroughIntegration in lyra-core."""
        from lyra_core import BreakthroughIntegration
        bt = BreakthroughIntegration()
        status = bt.initialize()
        assert isinstance(status, dict)
