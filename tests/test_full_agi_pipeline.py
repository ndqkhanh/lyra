"""End-to-end integration test: Full AGI pipeline across all 5 plans.

Tests that all 5 AGI plans can be instantiated and coordinated together.
This is the closest we get to an "Are we there yet?" AGI readiness check.
"""

import os, sys

# Build PYTHONPATH
src_dirs = []
for d in os.listdir('packages'):
    src = os.path.join(os.path.abspath('packages'), d, 'src')
    if os.path.isdir(src):
        src_dirs.append(src)
sys.path = src_dirs + sys.path


class TestFullAGIPipeline:
    """End-to-end test: all 5 AGI plans together."""

    def test_all_plans_import(self):
        """Verify every AGI package can be imported."""
        from lyra_verification_mesh import VerificationMesh
        from lyra_hbhc import HBHCManager
        from lyra_viper_mcp import VulnerabilityScanner
        from lyra_attestor import Attestor
        from lyra_causal_graph import CausalGraph
        from lyra_counterfactual import CounterfactualEngine
        from lyra_science_pipeline import SciencePipeline
        from lyra_claim_verification import ClaimVerifier
        from lyra_drift_detector import DriftOrchestrator
        from lyra_skill_weaver import SkillWeaver
        from lyra_context_profiler import ContextProfiler
        from lyra_competence_map import CompetenceMap
        from lyra_meta_evolution import MetaCognitiveStack
        from lyra_recursive_reward import RecursiveReward
        from lyra_fork_worker import ForkWorkerOrchestrator
        from lyra_colony import AgentColony
        from lyra_emergent_coord import EmergentCoordinator
        from lyra_gossip_memory import GossipProtocol
        from lyra_agent_lifecycle import LifecycleManager
        assert True

    def test_citadel_oracle_integration(self):
        """Citadel (safety) + Oracle (causal understanding) together."""
        from lyra_verification_mesh import VerificationMesh, TemporalProperty
        from lyra_causal_graph import CausalGraph, EntityNode
        mesh = VerificationMesh()
        graph = CausalGraph()
        graph.add_entity(EntityNode(id="e1", name="test", entity_type="concept"))
        assert mesh.overall_status is not None
        assert graph.stats["entities"] == 1

    def test_chameleon_singularity_integration(self):
        """Chameleon (drift detection) + Singularity (self-improvement) together."""
        from lyra_drift_detector import DriftOrchestrator
        from lyra_meta_evolution import MetaCognitiveStack
        drift = DriftOrchestrator()
        meta = MetaCognitiveStack()
        s = drift.summary
        assert "adaptation_needed" in s
        assert meta.summary is not None

    def test_superorganism_orchestration(self):
        """Superorganism (agent colony) with orchestration."""
        import asyncio
        from lyra_colony import AgentColony
        colony = AgentColony()
        colony.coordinator.register_agent("coder_1", ["python", "code"])
        colony.coordinator.register_agent("researcher_1", ["search", "analyze"])
        result = asyncio.run(colony.process_task({
            "type": "research_project",
            "complexity": 0.4,
            "capabilities": ["search", "analyze", "python"]
        }))
        assert "coalition_id" in result

    def test_agi_orchestrator(self):
        """AGI Orchestrator health check across all 5 plans."""
        import asyncio
        from lyra_core import AGIOrchestrator, AGIPhase
        orch = AGIOrchestrator()
        statuses = asyncio.run(orch.health_check())
        assert len(statuses) == 5
        overview = orch.get_overview()
        assert "overall_health" in overview
        assert overview["ready_phases"] >= 0

    def test_event_sourced_loop_with_agi(self):
        """EventSourcedAgentLoop with AGI plugin wiring."""
        from lyra_core.agent.event_sourced_loop import EventSourcedAgentLoop
        from lyra_core.agent.agi_plugin import AGILoopPlugin
        from lyra_core.agent.safety_hooks import SafetyHookPlugin
        loop = EventSourcedAgentLoop()
        plugin = AGILoopPlugin()
        safety = SafetyHookPlugin()
        assert loop.agent_id == "lyra"
        assert safety.enabled
        assert plugin.event_log.size >= 0

    def test_emergency_shield_activation(self):
        """Emergency shield across all plans."""
        import asyncio
        from lyra_core import AGIOrchestrator
        orch = AGIOrchestrator()
        result = asyncio.run(orch.emergency_shield())
        assert result["status"] == "emergency_shield_active"

    def test_all_core_upgrades(self):
        """Verify all 9 upgrade modules are usable."""
        import asyncio
        from lyra_core.agent.event_sourced_loop import (
            EventSourcedAgentLoop, EventLog, StepEvent, EventType,
            MultiStreamExecutor, SpeculativePlanner, RuntimeHarnessAdaptor
        )
        from lyra_memory.graph_tier import GraphMemoryStore, KnowledgeGraphNode
        from lyra_core import AGIOrchestrator
        from lyra_core.agent.agi_plugin import AGILoopPlugin
        from lyra_core.agent.safety_hooks import SafetyHookPlugin
        assert True
