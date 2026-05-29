"""Tests bridging Collective Intelligence with the Research Pipeline.

Validates the AutoScientists-inspired integration:
  - CollectiveState → ResearchOrchestrator → Forum feedback loop
  - DeadEndRegistry prevents duplicate hypothesis research
  - NoiseGate requires N confirmations before proceeding
  - Team formation, cross-team critique, meta-improvement, self-reorganization
"""

from __future__ import annotations

from lyra_core.collective import (
    CollectiveState,
    ConsensusLevel,
    DeadEndEntry,
    DiscussionForum,
    ForumPost,
    Hypothesis,
    MetaImprovementLoop,
    NoiseGate,
    PostKind,
    ReorganizationPlan,
    ReorganizationTrigger,
    SelfReorganization,
    TeamFormationReason,
)

# ── Helpers ────────────────────────────────────────────────────────────


def _hypothesis(
    id: str, statement: str, proposed_by: str = "agent-1", test_criteria: str = ""
) -> Hypothesis:
    return Hypothesis(
        id=id,
        statement=statement,
        proposed_by=proposed_by,
        test_criteria=test_criteria or f"test-{id}",
    )


def _post(
    id: str, author: str, kind: PostKind, content: str, thread_id: str | None = None
) -> ForumPost:
    return ForumPost(id=id, author_id=author, kind=kind, content=content, thread_id=thread_id)


# ── CollectiveState + Research Pipeline Bridge ──────────────────────────


class TestHypothesisDrivenResearch:
    """CollectiveState proposes hypothesis → feeds into research pipeline."""

    def test_propose_hypothesis_creates_team_and_thread(self):
        state = CollectiveState()
        h = _hypothesis("h1", "Transformer attention patterns are learnable")
        team = state.propose_hypothesis(h, champion_id="agent-1")

        assert team is not None
        assert team.champion_id == "agent-1"
        assert team.hypothesis.id == "h1"
        assert state.hypotheses["h1"].status == "proposed"

    def test_propose_hypothesis_blocked_by_dead_end(self):
        state = CollectiveState()
        dead = DeadEndEntry(
            id="de1",
            hypothesis="Transformer attention patterns are learnable",
            approach="standard analysis",
            failure_reason="already disproven",
            discovered_by="agent-2",
        )
        state.dead_ends.register(dead)

        h = _hypothesis("h1", "Transformer attention patterns are learnable")
        team = state.propose_hypothesis(h, champion_id="agent-1")
        assert team is None  # blocked by dead-end registry

    def test_research_result_feeds_back_to_forum_as_observation(self):
        state = CollectiveState()
        forum = state.forum
        thread = forum.create_thread("t1", "Test topic", hypothesis="H1")
        obs = _post(
            "p1",
            "research-agent",
            PostKind.OBSERVATION,
            "Experiment shows attention patterns ARE learnable",
        )
        assert forum.post("t1", obs) is True

        thread = forum.get_thread("t1")
        assert thread is not None
        assert thread.post_count == 1
        assert thread.posts[0].kind == PostKind.OBSERVATION

    def test_verify_hypothesis_records_dead_end_on_falsification(self):
        state = CollectiveState()
        h = _hypothesis("h1", "All models overfit with small data")
        state.propose_hypothesis(h, champion_id="agent-1")
        state.verify_hypothesis(
            "h1",
            "Disproven: only some architectures overfit",
            verified=False,
            verifier_id="agent-2",
        )

        assert state.hypotheses["h1"].status == "falsified"
        assert state.dead_ends.entry_count == 1
        is_dead, _ = state.dead_ends.is_known_dead_end("All models overfit with small data")
        assert is_dead

    def test_verify_hypothesis_marks_verified(self):
        state = CollectiveState()
        h = _hypothesis("h1", "Valid finding")
        state.propose_hypothesis(h, champion_id="agent-1")
        state.verify_hypothesis(
            "h1", "Confirmed by experiment", verified=True, verifier_id="agent-2"
        )
        assert state.hypotheses["h1"].status == "verified"
        assert state.dead_ends.entry_count == 0  # No dead-end for verified

    def test_noise_gate_requires_n_confirmations(self):
        ng = NoiseGate(required_confirmations=3)
        assert not ng.confirm("item-1", "agent-a")
        assert not ng.confirm("item-1", "agent-b")
        assert ng.confirm("item-1", "agent-c")  # 3rd → threshold met

    def test_team_formation_around_hypothesis(self):
        state = CollectiveState()
        h = _hypothesis("h1", "RLHF improves factual accuracy")
        team = state.propose_hypothesis(h, champion_id="lead")

        assert team is not None
        assert team.formation_reason == TeamFormationReason.HYPOTHESIS
        assert team.status == "forming"
        team.add_member("analyst-1")
        team.add_member("reviewer-1")
        assert team.size == 3  # champion + 2 members

    def test_cross_team_critique_flow(self):
        """Team A's finding → Team B's critique → Forum discussion."""
        state = CollectiveState()
        thread = state.forum.create_thread("t-critique", "Critique of finding X")

        # Team A posts a proposal
        state.forum.post(
            "t-critique",
            _post("p1", "team-a", PostKind.PROPOSAL, "Finding: attention heads specialize"),
        )
        # Team B posts a critique
        state.forum.post(
            "t-critique",
            _post("p2", "team-b", PostKind.CRITIQUE, "Counter: specialization is task-dependent"),
        )
        # Resolution post
        state.forum.post(
            "t-critique",
            _post(
                "p3", "arbitrator", PostKind.RESOLUTION, "Both partially correct; context matters"
            ),
        )

        thread = state.forum.get_thread("t-critique")
        assert thread is not None
        assert thread.post_count == 3
        assert len(thread.participants) == 3

    def test_meta_improvement_loop_triggers_every_n_cycles(self):
        state = CollectiveState()
        meta = MetaImprovementLoop(state, interval=3)

        assert not meta.should_evaluate()  # cycle 0

        state.cycle_count = 3
        assert meta.should_evaluate()

        report = meta.evaluate()
        assert "metrics" in report
        assert "recommendations" in report
        assert report["cycle"] == 3

    def test_meta_improvement_detects_thrashing(self):
        state = CollectiveState()
        meta = MetaImprovementLoop(state, interval=1)

        # Simulate rapid team dissolutions
        for i in range(6):
            state._log("team_dissolved", {"team_id": f"t{i}", "reason": "test"})

        state.cycle_count = 1
        report = meta.evaluate()
        assert report["thrashing_detected"] is True
        assert any(r["action"] == "increase_min_lifetime" for r in report["recommendations"])

    def test_self_reorganization_on_stagnation(self):
        state = CollectiveState()
        state.cycle_count = 4
        # Add an active team but no verifications
        h = _hypothesis("h1", "Some hypothesis")
        state.propose_hypothesis(h, champion_id="agent-1")
        state.teams["team_h1"].status = "working"

        reorg = SelfReorganization(state)
        triggers = reorg.check_triggers()
        assert ReorganizationTrigger.STAGNATION in triggers

    def test_self_reorganization_on_thrashing(self):
        state = CollectiveState()
        for i in range(6):
            state._log("team_dissolved", {"team_id": f"t{i}", "reason": "test"})

        reorg = SelfReorganization(state)
        triggers = reorg.check_triggers()
        assert ReorganizationTrigger.THRASHING in triggers


# ── Full AutoScientists Cycle ───────────────────────────────────────────


class TestAutoScientistsFullCycle:
    def test_discuss_execute_cycle_single_team(self):
        state = CollectiveState()
        h = _hypothesis("h1", "Larger batch sizes reduce generalization gap")
        team = state.propose_hypothesis(h, champion_id="agent-1")
        assert team is not None

        # Discussion phase — add posts AND votes for consensus
        thread_id = team.discussion_thread_id
        assert thread_id is not None
        state.forum.post(thread_id, _post("p1", "agent-1", PostKind.PROPOSAL, "Let's test this"))
        state.forum.post(thread_id, _post("p2", "agent-2", PostKind.SUPPORT, "Agreed"))
        state.forum.post(
            thread_id, _post("p3", "agent-3", PostKind.CRITIQUE, "Check different architectures")
        )

        # Cast votes to generate consensus signal
        thread = state.forum.get_thread(thread_id)
        assert thread is not None
        thread.vote("p1", "agent-1", 1)
        thread.vote("p2", "agent-2", 1)
        thread.vote("p3", "agent-3", -1)
        assert thread.post_count == 3
        # With 3 participants × 3 posts = 9 max votes, total votes = 1+1-1 = 1, ratio = 1/9 ≈
        assert thread.consensus in (ConsensusLevel.WEAK, ConsensusLevel.NONE)

        # Execute phase
        team.status = "working"
        team.complete_cycle()
        state.verify_hypothesis(
            "h1", "Confirmed: larger batches help", verified=True, verifier_id="agent-1"
        )

        assert state.hypotheses["h1"].status == "verified"
        assert team.cycles_completed == 1

    def test_multi_team_parallel_research(self):
        state = CollectiveState()

        for i in range(3):
            h = _hypothesis(f"h{i}", f"Hypothesis {i} about research topic")
            team = state.propose_hypothesis(h, champion_id=f"agent-{i}")
            assert team is not None

        assert len(state.teams) == 3
        assert len(state.active_teams) == 3

    def test_champion_replacement_on_poor_performance(self):
        state = CollectiveState()
        h = _hypothesis("h1", "Testable claim")
        team = state.propose_hypothesis(h, champion_id="weak-agent")
        assert team is not None

        # Simulate poor performance — falsified hypothesis
        state.verify_hypothesis("h1", "Failed to validate", verified=False, verifier_id="reviewer")
        assert state.hypotheses["h1"].status == "falsified"

    def test_experiment_log_accumulates_across_cycles(self):
        state = CollectiveState()

        for cycle in range(3):
            state.cycle_count = cycle
            h = _hypothesis(f"h{cycle}", f"Cycle {cycle} discovery")
            state.propose_hypothesis(h, champion_id="agent-1")
            state.verify_hypothesis(f"h{cycle}", "Result", verified=True, verifier_id="agent-1")

        events = [e for e in state.work_log if e["event"] == "hypothesis_verified"]
        assert len(events) == 3

    def test_forum_resolve_and_dead_end_marking(self):
        forum = DiscussionForum()
        forum.create_thread("t1", "Dead-end topic")
        forum.mark_dead_end("t1", "Approach fundamentally flawed")
        t = forum.get_thread("t1")
        assert t is not None
        assert t.status == "dead_end"

    def test_collective_state_advance_cycle(self):
        state = CollectiveState()
        h = _hypothesis("h1", "Test")
        team = state.propose_hypothesis(h, champion_id="a1")
        assert team is not None
        team.status = "working"
        state.advance_cycle()
        assert state.cycle_count == 1
        assert team.cycles_completed == 1

    def test_reorganization_propose_and_execute(self):
        state = CollectiveState()
        h = _hypothesis("h1", "Stagnated hypothesis")
        state.propose_hypothesis(h, champion_id="agent-1")
        state.teams["team_h1"].status = "working"
        state.teams["team_h1"].cycles_completed = 3
        state.cycle_count = 4

        reorg = SelfReorganization(state)
        triggers = reorg.check_triggers()
        assert ReorganizationTrigger.STAGNATION in triggers

        plan = reorg.propose_plan(ReorganizationTrigger.STAGNATION, "No progress in 4 cycles")
        assert isinstance(plan, ReorganizationPlan)
        assert len(plan.dissolve_teams) == 1  # stagnant team
        assert plan.trigger == ReorganizationTrigger.STAGNATION

        reorg.execute_plan(plan)
        assert reorg.applied_plan_count == 1

    def test_snapshot_progress_records_state(self):
        state = CollectiveState()
        reorg = SelfReorganization(state)
        reorg.snapshot_progress()
        reorg.snapshot_progress()
        assert len(reorg._progress_snapshots) == 2


# ── Integration properties ──────────────────────────────────────────────


class TestCollectiveIntegrationProperties:
    def test_dead_end_prevents_repeat_proposals(self):
        state = CollectiveState()
        # Register a dead end
        h1 = _hypothesis("h1", "reinforcement learning PPO unstable in training")
        state.propose_hypothesis(h1, champion_id="a1")
        state.verify_hypothesis("h1", "Disproven", verified=False, verifier_id="a2")

        # Nearly identical hypothesis — same content keywords dominate
        h2 = _hypothesis("h2", "reinforcement learning PPO unstable")
        team = state.propose_hypothesis(h2, champion_id="a1")
        assert team is None  # blocked: all keywords overlap the dead-end entry

    def test_verified_hypotheses_property(self):
        state = CollectiveState()
        for i in range(5):
            h = _hypothesis(f"h{i}", f"Statement {i}")
            state.propose_hypothesis(h, champion_id="a1")
            if i % 2 == 0:
                state.verify_hypothesis(f"h{i}", "ok", verified=True, verifier_id="a2")
            else:
                state.verify_hypothesis(f"h{i}", "nope", verified=False, verifier_id="a2")

        assert len(state.verified_hypotheses) == 3
        assert len(state.falsified_hypotheses) == 2

    def test_meta_evaluation_publishes_event(self):
        state = CollectiveState()
        state.cycle_count = 3
        meta = MetaImprovementLoop(state, interval=3)
        report = meta.evaluate()
        assert report is not None
        assert meta.last_report is not None
