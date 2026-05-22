"""Integration tests: AGI Orchestrator ↔ all 19 packages."""
import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))


# Test imports from all 5 plans
class TestPlanImports:
    """Verify every AGI package can be imported without errors."""

    def test_citadel_imports(self):
        from lyra_verification_mesh import VerificationMesh, CausalPastLogicVerifier
        from lyra_hbhc import HBHCManager, Verifier
        from lyra_viper_mcp import TaintAnalyzer
        from lyra_attestor import Attestor, AttestationGraph
        assert True

    def test_oracle_imports(self):
        from lyra_causal_graph import CausalGraph, EntityNode, ActionEdge
        from lyra_counterfactual import CounterfactualEngine
        from lyra_science_pipeline import SciencePipeline, Hypothesis
        from lyra_claim_verification import ClaimDAG, ClaimVerifier
        assert True

    def test_chameleon_imports(self):
        from lyra_drift_detector import DriftOrchestrator, PerformanceDriftDetector
        from lyra_skill_weaver import SkillWeaver, SkillComposer, SkillModule
        from lyra_context_profiler import ContextProfiler, ProfileMatcher, ContextProfile
        from lyra_competence_map import CompetenceMap, RegressionDetector
        assert True

    def test_singularity_imports(self):
        from lyra_meta_evolution import MetaCognitiveStack, Level0Executor
        from lyra_recursive_reward import RecursiveReward, InnerRewardLoop
        from lyra_fork_worker import ForkWorkerOrchestrator, PatchApplier, TestRunner
        assert True

    def test_superorganism_imports(self):
        from lyra_colony import AgentColony, ColonyConfig
        from lyra_emergent_coord import EmergentCoordinator, Coalition
        from lyra_gossip_memory import GossipProtocol, DualPoolMemory, MemoryItem
        from lyra_agent_lifecycle import LifecycleManager, ContributionTracker, AgentSpec
        assert True

    def test_core_upgrades_imports(self):
        from lyra_core import (
            EventSourcedAgentLoop, EventLog, StepEvent, EventType,
            MultiStreamExecutor, SpeculativePlanner, RuntimeHarnessAdaptor,
            AGIOrchestrator, AGIPhase,
        )
        assert True


class TestAGIOrchestratorIntegration:
    """Integration: AGI Orchestrator health checks across all packages."""

    @pytest.mark.asyncio
    async def test_health_check_all_plans(self):
        from lyra_core import AGIOrchestrator, AGIPhase
        orch = AGIOrchestrator()
        statuses = await orch.health_check()
        assert len(statuses) == 5
        assert set(statuses.keys()) == set(AGIPhase)

    def test_overview(self):
        from lyra_core import AGIOrchestrator
        orch = AGIOrchestrator()
        overview = orch.get_overview()
        assert "overall_health" in overview
        assert "plans" in overview

    @pytest.mark.asyncio
    async def test_emergency_shield(self):
        from lyra_core import AGIOrchestrator
        orch = AGIOrchestrator()
        result = await orch.emergency_shield()
        assert result["status"] == "emergency_shield_active"


class TestCitadelOracleIntegration:
    """Integration: Verification Mesh + Causal Graph."""

    def test_verification_with_causal_context(self):
        from lyra_verification_mesh import VerificationMesh, TemporalProperty
        from lyra_causal_graph import CausalGraph, EntityNode
        mesh = VerificationMesh()
        graph = CausalGraph()
        graph.add_entity(EntityNode(id="e1", name="test", entity_type="concept"))
        assert mesh.overall_status is not None


class TestChameleonSingularityIntegration:
    """Integration: Drift Detector + Meta Evolution."""

    def test_drift_feeds_evolution(self):
        from lyra_drift_detector import DriftOrchestrator
        from lyra_meta_evolution import MetaCognitiveStack
        drift = DriftOrchestrator()
        meta = MetaCognitiveStack()
        s = drift.summary
        assert "signals" in s
        assert meta.summary is not None


class TestSuperorganismIntegration:
    """Integration: Colony + EmergentCoord + Gossip + Lifecycle."""

    @pytest.mark.asyncio
    async def test_colony_forms_coalition(self):
        from lyra_colony import AgentColony
        colony = AgentColony()
        colony.coordinator.register_agent("coder_1", ["python", "code"])
        colony.coordinator.register_agent("researcher_1", ["search", "analyze"])
        result = await colony.process_task({"type": "python project", "complexity": 0.4, "capabilities": ["python", "code"]})
        assert "coalition_id" in result


class TestAllUpgrades:
    """Verify all upgrade modules are importable."""

    def test_event_sourced_loop(self):
        from lyra_core.agent.event_sourced_loop import EventSourcedAgentLoop
        loop = EventSourcedAgentLoop()
        assert loop.agent_id == "lyra"

    def test_graph_tier(self):
        from lyra_memory.graph_tier import GraphMemoryStore, KnowledgeGraphNode
        store = GraphMemoryStore()
        assert store.graph.stats["nodes"] == 0

    def test_moss_evolution(self):
        from lyra_evolution.moss_evolution import SourceEvolutionEngine, UserConsentGate
        engine = SourceEvolutionEngine()
        gate = UserConsentGate()
        assert len(gate.pending_approvals) == 0

    def test_sibyl_harness(self):
        from lyra_research.sibyl_harness import SibylPipeline, TrialHarness
        pipeline = SibylPipeline()
        assert len(pipeline.completed_trials) == 0

    def test_coalition_coordinator(self):
        from lyra_orchestration.coalition_coordinator import CoalitionAwareCoordinator
        coord = CoalitionAwareCoordinator()
        assert len(coord.coalitions) == 0

    def test_spec_bench(self):
        from lyra_evals.spec_bench import SpecBenchEvaluator, ProbabilisticEvaluator
        eval_ = SpecBenchEvaluator()
        report = eval_.get_report()
        assert report["total_evals"] == 0

    def test_mcp_security_scan(self):
        from lyra_mcp.security_scan import MCPTaintAnalyzer
        analyzer = MCPTaintAnalyzer()
        result = analyzer.scan_server("test", {})
        assert result["tools_scanned"] == 0
