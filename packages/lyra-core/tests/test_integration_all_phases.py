"""Integration tests: all 6 phases working together end-to-end."""

from __future__ import annotations

import time

import pytest
from lyra_core.adversarial import (
    AdversarialReview,
    ConvergenceCheck,
    ReviewFinding,
    ReviewRole,
    ReviewVerdict,
    Severity,
)
from lyra_core.backpressure import BackpressureRegulator
from lyra_core.collective import (
    CollectiveState,
    Hypothesis,
    MetaImprovementLoop,
)
from lyra_core.command_queue import Command, CommandQueue, CommandStatus
from lyra_core.containment import Project, ProjectRegistry, Team, TopologyTree
from lyra_core.events import EventBus
from lyra_core.protocol import AgentState, Task
from lyra_core.watchdog import AgentWatchdog

# ═══════════════════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════════════════


class _TestAgent:
    def __init__(self, agent_id: str, project_id: str = "p1") -> None:
        from lyra_core.protocol import AgentHealth, AgentIdentity, AgentLifecycle, AgentMode

        self._identity = AgentIdentity(
            agent_id=agent_id, project_id=project_id, agent_type="test",
            capabilities=frozenset({"test"}),
        )
        self._state = AgentState(
            lifecycle=AgentLifecycle.READY, health=AgentHealth.HEALTHY,
            since=time.time(),
        )
        self._modes: list[AgentMode] = []

    @property
    def identity(self):
        return self._identity

    @property
    def state(self):
        return self._state

    @property
    def mode_stack(self) -> tuple:
        return tuple(self._modes)

    def push_mode(self, mode):
        self._modes.append(mode)

    def pop_mode(self):
        if not self._modes:
            raise IndexError("empty")
        return self._modes.pop()

    def supports(self, capability: str) -> bool:
        return capability in self._identity.capabilities

    async def initialize(self) -> None:
        pass

    async def run(self, task: Task):
        yield f"result:{task.instruction}"

    async def shutdown(self) -> None:
        pass

    async def snapshot(self) -> dict:
        return {"agent_id": self._identity.agent_id}


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-end: Agent lifecycle with watchdog monitoring
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentLifecycleWithWatchdog:
    """Phase 1: Protocol + Events + Watchdog working together."""

    def test_agent_registration_and_monitoring(self):
        bus = EventBus.get()
        wd = AgentWatchdog("a1", "p1", bus=bus)

        assert wd.state.lifecycle.value == "registered"

        wd.transition(
            __import__('lyra_core.protocol', fromlist=['AgentLifecycle']).AgentLifecycle.READY,
            __import__('lyra_core.protocol', fromlist=['AgentHealth']).AgentHealth.HEALTHY,
        )
        assert wd.watchdog_status.value == "running/healthy"

    @pytest.mark.asyncio
    async def test_agent_runs_task(self):
        agent = _TestAgent("a1")
        task = Task(task_id="t1", instruction="analyze file")
        output = ""
        async for chunk in agent.run(task):
            output += chunk
        assert "analyze file" in output


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-end: Project → Team → Agent with topology execution
# ═══════════════════════════════════════════════════════════════════════════════


class TestProjectWithTopologyExecution:
    """Phase 1 + 2: Containment hierarchy with topology-based execution."""

    @pytest.mark.asyncio
    async def test_parallel_topology_execution(self):
        project = Project(id="p1", name="research-project")
        team = Team(id="t1", name="analysis-team")
        team.topology = TopologyTree.parallel(["a1", "a2"])

        team.add_agent(_TestAgent("a1"))
        team.add_agent(_TestAgent("a2"))
        project.add_team(team)

        task = Task(task_id="t1", instruction="evaluate")
        results = await team.run_all(task)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_sequential_topology_execution(self):
        team = Team(id="t1", name="pipeline")
        team.topology = TopologyTree.sequential(["a1", "a2"])
        team.add_agent(_TestAgent("a1"))
        team.add_agent(_TestAgent("a2"))

        task = Task(task_id="t1", instruction="process")
        results = await team.run_all(task)
        assert len(results) == 2

    def test_registry_links_team_to_project(self):
        reg = ProjectRegistry()
        reg.create_project("proj", project_id="p1")
        reg.create_team("team", team_id="t1")
        membership = reg.link_team("p1", "t1")
        assert membership is not None
        assert membership.project_id == "p1"


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-end: Command queue with reference resolution
# ═══════════════════════════════════════════════════════════════════════════════


class TestCommandQueueRefResolution:
    """Phase 3: Command queue CMD_RETURN_WAIT reference pattern."""

    @pytest.mark.asyncio
    async def test_producer_consumer_ref_pattern(self):
        q = CommandQueue()
        q.declare_ref("data_ready")

        producer = Command(
            id="producer", type="generate_data",
            produces_refs=["data_ready"],
        )
        consumer = Command(
            id="consumer", type="process_data",
            waits_on_refs=["data_ready"],
        )

        await q.enqueue(producer)
        await q.enqueue(consumer)

        # Consumer should be blocked
        consumer_cmd = await q.get_command("consumer")
        assert consumer_cmd is not None

        # Resolve producer → unblocks consumer
        producer.status = CommandStatus.RUNNING
        producer.started_at = time.time()
        await q.resolve("producer", result="data_generated")

        assert "data_ready" in q._resolved_refs
        assert q._are_refs_satisfied(consumer)


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-end: Hypothesis → discussion → dead-end check → verification
# ═══════════════════════════════════════════════════════════════════════════════


class TestCollectiveHypothesisFlow:
    """Phase 4: Collective intelligence hypothesis lifecycle."""

    def test_hypothesis_to_verification_flow(self):
        state = CollectiveState()

        # Propose
        h = Hypothesis(id="h1", statement="X improves Y",
                      proposed_by="scientist_1", test_criteria="measure Y")
        team = state.propose_hypothesis(h, champion_id="scientist_1")
        assert team is not None
        assert len(state.hypotheses) == 1

        # Discuss in forum
        thread = state.forum.get_thread("thread_h1")
        assert thread is not None

        # Verify
        state.verify_hypothesis("h1", "Confirmed: X improves Y by 30%",
                               True, "validator_1")
        assert state.hypotheses["h1"].status == "verified"
        assert len(state.verified_hypotheses) == 1

    def test_dead_end_blocks_repeated_failure(self):
        state = CollectiveState()

        # First attempt → falsified → dead end registered
        h1 = Hypothesis(id="h1", statement="sentiment via rule-based approach",
                       proposed_by="a1", test_criteria="accuracy > 0.8")
        state.propose_hypothesis(h1, champion_id="a1")
        state.verify_hypothesis("h1", "Accuracy 0.45 — insufficient",
                               False, "validator_1")
        assert state.dead_ends.entry_count == 1

        # Second attempt with similar approach → blocked
        h2 = Hypothesis(id="h2", statement="sentiment via rule-based approach v2",
                       proposed_by="a2", test_criteria="accuracy > 0.8")
        team2 = state.propose_hypothesis(h2, champion_id="a2")
        assert team2 is None  # Blocked by dead-end registry

    def test_meta_improvement_loop(self):
        state = CollectiveState()
        h = Hypothesis(id="h1", statement="X works", proposed_by="a1",
                      test_criteria="test")
        state.propose_hypothesis(h, champion_id="a1")
        state.verify_hypothesis("h1", "yes", True, "v1")
        state.advance_cycle()

        loop = MetaImprovementLoop(state, interval=1)
        report = loop.evaluate()
        assert "metrics" in report
        assert report["metrics"]["hypotheses"]["total"] == 1
        assert report["metrics"]["hypotheses"]["success_rate"] == 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-end: Adversarial review → convergence → arbitration
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdversarialReviewFlow:
    """Phase 5: Review → convergence → arbitration pipeline."""

    def test_review_convergence_pipeline(self):
        cc = ConvergenceCheck(required_reviewers=3, agreement_threshold=0.6)

        # 3 reviewers: 2 approve, 1 revise
        r1 = AdversarialReview(
            id="r1", reviewer_id="alice", role=ReviewRole.REVIEWER,
            subject_id="task_1", verdict=ReviewVerdict.APPROVED,
        )
        r2 = AdversarialReview(
            id="r2", reviewer_id="bob", role=ReviewRole.REVIEWER,
            subject_id="task_1", verdict=ReviewVerdict.APPROVED,
        )
        r3 = AdversarialReview(
            id="r3", reviewer_id="carol", role=ReviewRole.REVIEWER,
            subject_id="task_1", verdict=ReviewVerdict.REVISE,
        )
        # Carol found a minor issue
        r3.add_finding(ReviewFinding(
            id="f1", reviewer_id="carol", severity=Severity.MEDIUM,
            category="maintainability", description="Extract helper function",
        ))

        cc.submit_review(r1)
        cc.submit_review(r2)
        result = cc.submit_review(r3)

        # 2/3 ≥ 0.6 → converged
        assert result.status.value == "converged"
        assert result.consensus_verdict == ReviewVerdict.APPROVED
        assert "carol" in result.dissenting_reviewers

    def test_review_with_critical_finding(self):
        review = AdversarialReview(
            id="r1", reviewer_id="security_bot", role=ReviewRole.REVIEWER,
            subject_id="code_pr_42",
        )
        review.add_finding(ReviewFinding(
            id="f1", reviewer_id="security_bot", severity=Severity.CRITICAL,
            category="security", description="Hardcoded API key in source",
            location="src/config.py:15",
            suggestion="Use environment variable instead",
        ))
        verdict = review.update_verdict()
        assert verdict == ReviewVerdict.REJECTED
        assert review.has_critical


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-end: Backpressure with streaming data
# ═══════════════════════════════════════════════════════════════════════════════


class TestBackpressureIntegration:
    """Phase 6: Backpressure regulation for streaming data."""

    @pytest.mark.asyncio
    async def test_stream_produce_consume_flow(self):
        reg = BackpressureRegulator()

        # Produce a batch
        for i in range(10):
            result = await reg.produce(f"chunk_{i}")
            assert result is True

        assert reg.buffer_size == 10

        # Consume all
        items = await reg.drain_all()
        assert len(items) == 10
        assert items[0] == "chunk_0"
        assert items[9] == "chunk_9"

    @pytest.mark.asyncio
    async def test_backpressure_pause_resume_cycle(self):
        from lyra_core.backpressure import BackpressureConfig, Watermark

        config = BackpressureConfig(
            watermark=Watermark(low=3, high=5),
            token_bucket_rate=10000.0,
            token_bucket_capacity=10000.0,
        )
        reg = BackpressureRegulator(config=config)

        # Fill above high watermark
        for i in range(7):
            await reg.produce(f"item_{i}")
        assert reg.is_paused

        # Drain below low watermark
        for _ in range(5):
            await reg.consume()
        assert not reg.is_paused


# ═══════════════════════════════════════════════════════════════════════════════
# Full pipeline: All phases integrated
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullPipeline:
    """A complete workflow exercising all 6 phases."""

    @pytest.mark.asyncio
    async def test_full_research_pipeline(self):
        """Simulate: research project → form team → queue work → review → converge."""
        # Phase 1: Event bus + protocol
        bus = EventBus.get()
        wd = AgentWatchdog("lead_agent", "proj_research", bus=bus)
        wd.transition(
            __import__('lyra_core.protocol', fromlist=['AgentLifecycle']).AgentLifecycle.READY,
            __import__('lyra_core.protocol', fromlist=['AgentHealth']).AgentHealth.HEALTHY,
        )

        # Phase 2: Project + Team
        reg = ProjectRegistry()
        reg.create_project("AI Research", project_id="proj_research")
        reg.create_team("Analysis Squad", team_id="team_analysis")
        reg.link_team("proj_research", "team_analysis")

        team = reg.get_team("team_analysis")
        team.topology = TopologyTree.parallel(["agent_1", "agent_2"])
        team.add_agent(_TestAgent("agent_1"))
        team.add_agent(_TestAgent("agent_2"))

        # Phase 3: Queue work
        q = CommandQueue(bus=bus)
        cmd = Command(id="cmd_1", type="run_experiment",
                     payload={"hypothesis": "X improves Y"})
        await q.enqueue(cmd)
        assert q.size == 1

        # Phase 4: Collective intelligence
        state = CollectiveState()
        h = Hypothesis(id="hyp_1", statement="X improves Y",
                      proposed_by="agent_1", test_criteria="A/B test")
        hypothesis_team = state.propose_hypothesis(h, champion_id="agent_1")
        assert hypothesis_team is not None

        # Phase 5: Adversarial review
        cc = ConvergenceCheck(required_reviewers=2)
        r1 = AdversarialReview(
            id="rev_1", reviewer_id="agent_2", role=ReviewRole.REVIEWER,
            subject_id="hyp_1", verdict=ReviewVerdict.APPROVED,
        )
        r2 = AdversarialReview(
            id="rev_2", reviewer_id="agent_3", role=ReviewRole.VALIDATOR,
            subject_id="hyp_1", verdict=ReviewVerdict.APPROVED,
        )
        cc.submit_review(r1)
        result = cc.submit_review(r2)
        assert result.status.value == "converged"

        # Phase 6: Record progress
        state.verify_hypothesis("hyp_1", "Confirmed with p<0.01", True, "agent_2")
        assert len(state.verified_hypotheses) == 1

        # Verify watchdog is healthy
        assert wd.watchdog_status.value == "running/healthy"
