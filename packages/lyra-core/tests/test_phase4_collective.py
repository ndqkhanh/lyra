"""Comprehensive tests for Phase 4: Collective Intelligence System."""

from __future__ import annotations

from lyra_core.collective import (
    CollectiveState,
    ConsensusLevel,
    DeadEndEntry,
    DeadEndRegistry,
    DiscussionForum,
    DiscussionThread,
    ForumPost,
    Hypothesis,
    HypothesisTeam,
    MetaImprovementLoop,
    NoiseGate,
    PostKind,
    ReorganizationPlan,
    ReorganizationTrigger,
    SelfReorganization,
    TeamFormationReason,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ForumPost
# ═══════════════════════════════════════════════════════════════════════════════


class TestForumPost:
    def test_create(self):
        post = ForumPost(id="p1", author_id="a1", kind=PostKind.PROPOSAL,
                        content="Test hypothesis")
        assert post.id == "p1"
        assert post.author_id == "a1"
        assert post.kind == PostKind.PROPOSAL

    def test_defaults(self):
        post = ForumPost(id="p1", author_id="a1", kind=PostKind.QUESTION,
                        content="Why?")
        assert post.thread_id is None
        assert post.references == []
        assert post.votes == {}

    def test_votes(self):
        post = ForumPost(id="p1", author_id="a1", kind=PostKind.PROPOSAL,
                        content="Test", votes={"a2": 1, "a3": -1})
        assert post.votes["a2"] == 1
        assert post.votes["a3"] == -1

    def test_all_post_kinds(self):
        for kind in PostKind:
            post = ForumPost(id="p1", author_id="a1", kind=kind, content="test")
            assert post.kind == kind


# ═══════════════════════════════════════════════════════════════════════════════
# DiscussionThread
# ═══════════════════════════════════════════════════════════════════════════════


class TestDiscussionThread:
    def test_create(self):
        thread = DiscussionThread(id="t1", topic="Test topic",
                                 hypothesis="H: testable claim")
        assert thread.id == "t1"
        assert thread.topic == "Test topic"
        assert thread.hypothesis == "H: testable claim"
        assert thread.status == "open"
        assert thread.post_count == 0

    def test_add_post(self):
        thread = DiscussionThread(id="t1", topic="Test")
        post = ForumPost(id="p1", author_id="a1", kind=PostKind.PROPOSAL,
                        content="proposal")
        thread.add_post(post)
        assert thread.post_count == 1
        assert post.thread_id == "t1"
        assert "a1" in thread.participants

    def test_vote(self):
        thread = DiscussionThread(id="t1", topic="Test")
        post = ForumPost(id="p1", author_id="a1", kind=PostKind.PROPOSAL,
                        content="proposal")
        thread.add_post(post)
        assert thread.vote("p1", "a2", 1) is True
        assert post.votes["a2"] == 1

    def test_vote_clamped(self):
        thread = DiscussionThread(id="t1", topic="Test")
        post = ForumPost(id="p1", author_id="a1", kind=PostKind.PROPOSAL,
                        content="proposal")
        thread.add_post(post)
        thread.vote("p1", "a2", 5)  # clamped to 1
        assert post.votes["a2"] == 1
        thread.vote("p1", "a3", -5)  # clamped to -1
        assert post.votes["a3"] == -1

    def test_vote_nonexistent_post(self):
        thread = DiscussionThread(id="t1", topic="Test")
        assert thread.vote("nonexistent", "a1", 1) is False

    def test_consensus_none_empty(self):
        thread = DiscussionThread(id="t1", topic="Test")
        assert thread.consensus == ConsensusLevel.NONE

    def test_consensus_unanimous(self):
        thread = DiscussionThread(id="t1", topic="Test")
        p1 = ForumPost(id="p1", author_id="a1", kind=PostKind.PROPOSAL,
                      content="yes")
        thread.add_post(p1)
        thread.vote("p1", "a1", 1)
        thread.vote("p1", "a2", 1)
        assert thread.consensus == ConsensusLevel.UNANIMOUS

    def test_consensus_with_mixed_votes(self):
        thread = DiscussionThread(id="t1", topic="Test")
        for i in range(4):
            post = ForumPost(id=f"p{i}", author_id=f"a{i}",
                           kind=PostKind.SUPPORT, content="y")
            thread.add_post(post)
        thread.vote("p0", "a0", 1)
        thread.vote("p0", "a1", -1)
        thread.vote("p1", "a2", 1)
        thread.vote("p1", "a3", 1)
        # Some agreement
        assert thread.consensus != ConsensusLevel.NONE


# ═══════════════════════════════════════════════════════════════════════════════
# DiscussionForum
# ═══════════════════════════════════════════════════════════════════════════════


class TestDiscussionForum:
    def test_create(self):
        forum = DiscussionForum()
        assert forum.thread_count == 0

    def test_create_thread(self):
        forum = DiscussionForum()
        thread = forum.create_thread("t1", "Test topic")
        assert forum.thread_count == 1
        assert forum.get_thread("t1") is thread

    def test_post_to_thread(self):
        forum = DiscussionForum()
        forum.create_thread("t1", "Test")
        post = ForumPost(id="p1", author_id="a1", kind=PostKind.PROPOSAL,
                        content="test")
        assert forum.post("t1", post) is True

    def test_post_to_nonexistent_thread(self):
        forum = DiscussionForum()
        post = ForumPost(id="p1", author_id="a1", kind=PostKind.PROPOSAL,
                        content="test")
        assert forum.post("nonexistent", post) is False

    def test_resolve_thread(self):
        forum = DiscussionForum()
        forum.create_thread("t1", "Test")
        assert forum.resolve_thread("t1", "Decision made") is True
        thread = forum.get_thread("t1")
        assert thread.status == "resolved"
        assert thread.resolution == "Decision made"

    def test_mark_dead_end(self):
        forum = DiscussionForum()
        forum.create_thread("t1", "Test")
        forum.mark_dead_end("t1", "Approach failed")
        thread = forum.get_thread("t1")
        assert thread.status == "dead_end"

    def test_open_threads(self):
        forum = DiscussionForum()
        forum.create_thread("t1", "Open")
        forum.create_thread("t2", "Closed")
        forum.mark_dead_end("t2", "done")
        assert len(forum.open_threads) == 1

    def test_get_nonexistent_thread(self):
        forum = DiscussionForum()
        assert forum.get_thread("nonexistent") is None


# ═══════════════════════════════════════════════════════════════════════════════
# DeadEndEntry
# ═══════════════════════════════════════════════════════════════════════════════


class TestDeadEndEntry:
    def test_create(self):
        entry = DeadEndEntry(
            id="de1", hypothesis="H: X causes Y",
            approach="Test X on Y", failure_reason="No correlation",
            discovered_by="agent_a",
        )
        assert entry.id == "de1"
        assert entry.hypothesis == "H: X causes Y"
        assert entry.failure_reason == "No correlation"
        assert entry.severity == "moderate"

    def test_tags(self):
        entry = DeadEndEntry(
            id="de1", hypothesis="H", approach="A",
            failure_reason="F", discovered_by="a1",
            tags=["nlp", "sentiment"],
        )
        assert "nlp" in entry.tags
        assert "sentiment" in entry.tags


# ═══════════════════════════════════════════════════════════════════════════════
# DeadEndRegistry
# ═══════════════════════════════════════════════════════════════════════════════


class TestDeadEndRegistry:
    def test_create_empty(self):
        reg = DeadEndRegistry()
        assert reg.entry_count == 0

    def test_register_entry(self):
        reg = DeadEndRegistry()
        entry = DeadEndEntry(id="de1", hypothesis="H", approach="A",
                            failure_reason="F", discovered_by="a1")
        reg.register(entry)
        assert reg.entry_count == 1

    def test_is_known_dead_end_exact_match(self):
        reg = DeadEndRegistry(similarity_threshold=0.5)
        entry = DeadEndEntry(
            id="de1",
            hypothesis="transformer model fails on long sequences",
            approach="Use sliding window attention",
            failure_reason="Context fragmentation",
            discovered_by="a1",
        )
        reg.register(entry)

        is_dead, matched = reg.is_known_dead_end(
            "transformer model fails on long sequences"
        )
        assert is_dead is True
        assert matched is not None
        assert matched.id == "de1"

    def test_not_dead_end_different_topic(self):
        reg = DeadEndRegistry(similarity_threshold=0.5)
        entry = DeadEndEntry(id="de1", hypothesis="nlp sentiment analysis",
                            approach="BERT fine-tuning",
                            failure_reason="overfitting", discovered_by="a1")
        reg.register(entry)

        is_dead, _ = reg.is_known_dead_end("computer vision object detection")
        assert is_dead is False

    def test_query_similar(self):
        reg = DeadEndRegistry()
        e1 = DeadEndEntry(id="de1", hypothesis="nlp transformer attention",
                         approach="self-attention", failure_reason="f1",
                         discovered_by="a1")
        e2 = DeadEndEntry(id="de2", hypothesis="nlp rnn sequential",
                         approach="lstm", failure_reason="f2",
                         discovered_by="a2")
        reg.register(e1)
        reg.register(e2)

        results = reg.query_similar("nlp transformer model")
        assert len(results) >= 1
        assert results[0].id == "de1"  # e1 matches better

    def test_query_similar_empty(self):
        reg = DeadEndRegistry()
        results = reg.query_similar("something")
        assert results == []

    def test_custom_threshold(self):
        reg = DeadEndRegistry(similarity_threshold=0.9)
        entry = DeadEndEntry(id="de1", hypothesis="foo bar", approach="baz",
                            failure_reason="f", discovered_by="a1")
        reg.register(entry)

        # One word out of 4 matches = 0.25 < 0.9 threshold
        is_dead, _ = reg.is_known_dead_end("foo qux quux corge")
        assert is_dead is False

        # Override with lower threshold
        is_dead, _ = reg.is_known_dead_end("foo qux quux corge", threshold=0.2)
        assert is_dead is True


# ═══════════════════════════════════════════════════════════════════════════════
# Hypothesis & HypothesisTeam
# ═══════════════════════════════════════════════════════════════════════════════


class TestHypothesis:
    def test_create(self):
        h = Hypothesis(id="h1", statement="X improves Y",
                      proposed_by="a1", test_criteria="Measure Y with/without X")
        assert h.id == "h1"
        assert h.status == "proposed"
        assert h.confidence == 0.0

    def test_defaults(self):
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        assert h.priority == 0
        assert h.result is None


class TestHypothesisTeam:
    def test_create(self):
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        team = HypothesisTeam(id="t1", hypothesis=h, champion_id="a1")
        assert team.id == "t1"
        assert team.champion_id == "a1"
        assert team.size == 1
        assert team.status == "forming"

    def test_add_member(self):
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        team = HypothesisTeam(id="t1", hypothesis=h, champion_id="a1")
        team.add_member("a2")
        assert team.size == 2
        assert "a2" in team.member_ids

    def test_add_duplicate_member(self):
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        team = HypothesisTeam(id="t1", hypothesis=h, champion_id="a1")
        team.add_member("a2")
        team.add_member("a2")
        assert team.member_ids.count("a2") == 1

    def test_cannot_add_champion_as_member(self):
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        team = HypothesisTeam(id="t1", hypothesis=h, champion_id="a1")
        team.add_member("a1")
        assert "a1" not in team.member_ids

    def test_remove_member(self):
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        team = HypothesisTeam(id="t1", hypothesis=h, champion_id="a1")
        team.add_member("a2")
        team.remove_member("a2")
        assert team.size == 1

    def test_can_reform_initially_false(self):
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        team = HypothesisTeam(id="t1", hypothesis=h, champion_id="a1")
        assert not team.can_reform

    def test_can_reform_after_min_cycles(self):
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        team = HypothesisTeam(id="t1", hypothesis=h, champion_id="a1",
                             min_lifetime_cycles=2)
        team.complete_cycle()
        team.complete_cycle()
        assert team.can_reform

    def test_complete_cycle(self):
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        team = HypothesisTeam(id="t1", hypothesis=h, champion_id="a1")
        team.complete_cycle()
        assert team.cycles_completed == 1

    def test_formation_reasons(self):
        for reason in TeamFormationReason:
            h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                          test_criteria="check")
            team = HypothesisTeam(id="t1", hypothesis=h, champion_id="a1",
                                 formation_reason=reason)
            assert team.formation_reason == reason


# ═══════════════════════════════════════════════════════════════════════════════
# NoiseGate
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoiseGate:
    def test_create_with_default(self):
        gate = NoiseGate()
        assert gate.required == 2

    def test_create_custom_threshold(self):
        gate = NoiseGate(required_confirmations=3)
        assert gate.required == 3

    def test_single_confirmation_not_enough(self):
        gate = NoiseGate(required_confirmations=2)
        assert not gate.confirm("item1", "a1")

    def test_confirm_reaches_threshold(self):
        gate = NoiseGate(required_confirmations=2)
        gate.confirm("item1", "a1")
        result = gate.confirm("item1", "a2")
        assert result is True

    def test_is_confirmed(self):
        gate = NoiseGate(required_confirmations=1)
        gate.confirm("item1", "a1")
        assert gate.is_confirmed("item1")

    def test_duplicate_confirmations_dont_double_count(self):
        gate = NoiseGate(required_confirmations=2)
        gate.confirm("item1", "a1")
        gate.confirm("item1", "a1")  # duplicate
        gate.confirm("item1", "a1")  # duplicate
        assert not gate.is_confirmed("item1")  # still only 1 unique confirmer

    def test_get_confirmers(self):
        gate = NoiseGate()
        gate.confirm("item1", "a1")
        gate.confirm("item1", "a2")
        assert gate.get_confirmers("item1") == frozenset({"a1", "a2"})

    def test_reset(self):
        gate = NoiseGate()
        gate.confirm("item1", "a1")
        gate.reset("item1")
        assert not gate.is_confirmed("item1")

    def test_pending_items(self):
        gate = NoiseGate(required_confirmations=3)
        gate.confirm("item1", "a1")
        gate.confirm("item2", "a1")
        gate.confirm("item2", "a2")
        gate.confirm("item2", "a3")
        pending = gate.pending_items
        assert "item1" in pending
        assert "item2" not in pending

    def test_multiple_independent_items(self):
        gate = NoiseGate(required_confirmations=2)
        gate.confirm("hyp1", "a1")
        gate.confirm("hyp1", "a2")
        gate.confirm("hyp2", "a1")
        assert gate.is_confirmed("hyp1")
        assert not gate.is_confirmed("hyp2")


# ═══════════════════════════════════════════════════════════════════════════════
# CollectiveState
# ═══════════════════════════════════════════════════════════════════════════════


class TestCollectiveState:
    def test_create(self):
        state = CollectiveState()
        assert state.cycle_count == 0
        assert state.forum is not None
        assert state.dead_ends is not None
        assert state.noise_gate is not None

    def test_propose_hypothesis_creates_team(self):
        state = CollectiveState()
        h = Hypothesis(id="h1", statement="X causes Y", proposed_by="a1",
                      test_criteria="Measure Y")
        team = state.propose_hypothesis(h, champion_id="a1")
        assert team is not None
        assert team.champion_id == "a1"
        assert "h1" in state.hypotheses
        assert team.id in state.teams

    def test_propose_hypothesis_blocked_by_dead_end(self):
        state = CollectiveState()
        # Register a dead end
        entry = DeadEndEntry(
            id="de1",
            hypothesis="X causes Y is a dead end",
            approach="testing X on Y",
            failure_reason="No correlation found",
            discovered_by="a0",
        )
        state.dead_ends.register(entry)

        h = Hypothesis(id="h1", statement="X causes Y is a dead end",
                      proposed_by="a1", test_criteria="check")
        team = state.propose_hypothesis(h, champion_id="a1")
        assert team is None  # Blocked by dead-end registry

    def test_verify_hypothesis_verified(self):
        state = CollectiveState()
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        state.propose_hypothesis(h, champion_id="a1")
        state.verify_hypothesis("h1", "Confirmed: X works", True, "a2")
        assert state.hypotheses["h1"].status == "verified"
        assert len(state.verified_hypotheses) == 1

    def test_verify_hypothesis_falsified_registers_dead_end(self):
        state = CollectiveState()
        h = Hypothesis(id="h1", statement="X bad idea", proposed_by="a1",
                      test_criteria="check")
        state.propose_hypothesis(h, champion_id="a1")
        state.verify_hypothesis("h1", "X does not work", False, "a2")
        assert state.hypotheses["h1"].status == "falsified"
        assert state.dead_ends.entry_count == 1

    def test_dissolve_team(self):
        state = CollectiveState()
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        team = state.propose_hypothesis(h, champion_id="a1")
        state.dissolve_team(team.id, "completed")
        assert team.status == "dissolved"

    def test_advance_cycle(self):
        state = CollectiveState()
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        team = state.propose_hypothesis(h, champion_id="a1")
        team.status = "working"
        state.advance_cycle()
        assert state.cycle_count == 1
        assert team.cycles_completed == 1

    def test_active_teams(self):
        state = CollectiveState()
        h1 = Hypothesis(id="h1", statement="X", proposed_by="a1",
                       test_criteria="check")
        h2 = Hypothesis(id="h2", statement="Y", proposed_by="a2",
                       test_criteria="check")
        t1 = state.propose_hypothesis(h1, champion_id="a1")
        t2 = state.propose_hypothesis(h2, champion_id="a2")
        state.dissolve_team(t2.id)
        assert len(state.active_teams) == 1
        assert t1 in state.active_teams

    def test_work_log(self):
        state = CollectiveState()
        h = Hypothesis(id="h1", statement="X", proposed_by="a1",
                      test_criteria="check")
        state.propose_hypothesis(h, champion_id="a1")
        assert len(state.work_log) == 1
        assert state.work_log[0]["event"] == "hypothesis_proposed"

    def test_verified_and_falsified_hypotheses(self):
        state = CollectiveState()
        h1 = Hypothesis(id="h1", statement="good", proposed_by="a1",
                       test_criteria="check")
        h2 = Hypothesis(id="h2", statement="bad", proposed_by="a1",
                       test_criteria="check")
        state.propose_hypothesis(h1, champion_id="a1")
        state.propose_hypothesis(h2, champion_id="a1")
        state.verify_hypothesis("h1", "works", True, "v1")
        state.verify_hypothesis("h2", "fails", False, "v1")
        assert len(state.verified_hypotheses) == 1
        assert len(state.falsified_hypotheses) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# MetaImprovementLoop
# ═══════════════════════════════════════════════════════════════════════════════


class TestMetaImprovementLoop:
    def test_create(self):
        state = CollectiveState()
        loop = MetaImprovementLoop(state, interval=3)
        assert loop.interval == 3
        assert not loop.should_evaluate()

    def test_should_evaluate_after_interval(self):
        state = CollectiveState()
        loop = MetaImprovementLoop(state, interval=2)
        state.advance_cycle()
        state.advance_cycle()
        assert loop.should_evaluate()

    def test_evaluate_produces_report(self):
        state = CollectiveState()
        h1 = Hypothesis(id="h1", statement="good", proposed_by="a1",
                       test_criteria="check")
        h2 = Hypothesis(id="h2", statement="bad", proposed_by="a2",
                       test_criteria="check")
        state.propose_hypothesis(h1, champion_id="a1")
        state.propose_hypothesis(h2, champion_id="a2")
        state.verify_hypothesis("h1", "works", True, "v1")
        state.verify_hypothesis("h2", "fails", False, "v1")
        state.advance_cycle()
        state.advance_cycle()

        loop = MetaImprovementLoop(state, interval=1)
        report = loop.evaluate()
        assert "metrics" in report
        assert "recommendations" in report
        assert report["metrics"]["hypotheses"]["total"] == 2

    def test_last_report(self):
        state = CollectiveState()
        state.advance_cycle()
        loop = MetaImprovementLoop(state, interval=1)
        loop.evaluate()
        assert loop.last_report is not None
        assert loop.last_report["cycle"] == 1

    def test_detect_thrashing(self):
        state = CollectiveState()
        # Simulate many team dissolutions
        for i in range(6):
            state._log("team_dissolved", {"team_id": f"t{i}"})
        state.advance_cycle()
        loop = MetaImprovementLoop(state, interval=1)
        report = loop.evaluate()
        assert report["thrashing_detected"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# SelfReorganization
# ═══════════════════════════════════════════════════════════════════════════════


class TestSelfReorganization:
    def test_create(self):
        state = CollectiveState()
        reorg = SelfReorganization(state)
        assert reorg.applied_plan_count == 0

    def test_no_triggers_initial_state(self):
        state = CollectiveState()
        reorg = SelfReorganization(state)
        triggers = reorg.check_triggers()
        assert triggers == []

    def test_stagnation_trigger(self):
        state = CollectiveState()
        h = Hypothesis(id="h1", statement="stuck", proposed_by="a1",
                      test_criteria="check")
        state.propose_hypothesis(h, champion_id="a1")
        # Advance 3 cycles without verification
        for _ in range(3):
            state.advance_cycle()
        reorg = SelfReorganization(state)
        triggers = reorg.check_triggers()
        assert ReorganizationTrigger.STAGNATION in triggers

    def test_thrashing_trigger(self):
        state = CollectiveState()
        # Simulate many dissolutions
        for i in range(6):
            state._log("team_dissolved", {"team_id": f"t{i}"})
        reorg = SelfReorganization(state)
        triggers = reorg.check_triggers()
        assert ReorganizationTrigger.THRASHING in triggers

    def test_propose_stagnation_plan(self):
        state = CollectiveState()
        # Create stagnant team
        h = Hypothesis(id="h1", statement="stuck", proposed_by="a1",
                      test_criteria="check")
        team = state.propose_hypothesis(h, champion_id="a1")
        for _ in range(3):
            team.complete_cycle()
        state.advance_cycle()

        reorg = SelfReorganization(state)
        plan = reorg.propose_plan(
            ReorganizationTrigger.STAGNATION,
            "No progress in 3 cycles",
        )
        assert plan.trigger == ReorganizationTrigger.STAGNATION
        # Stagnant team should be dissolved
        assert team.id in plan.dissolve_teams

    def test_execute_plan_dissolves_teams(self):
        state = CollectiveState()
        h = Hypothesis(id="h1", statement="test", proposed_by="a1",
                      test_criteria="check")
        team = state.propose_hypothesis(h, champion_id="a1")

        reorg = SelfReorganization(state)
        plan = ReorganizationPlan(
            id="rp1", trigger=ReorganizationTrigger.STAGNATION,
            dissolve_teams=[team.id], rationale="Testing",
        )
        reorg.execute_plan(plan)
        assert team.status == "dissolved"
        assert reorg.applied_plan_count == 1

    def test_execute_plan_forms_teams(self):
        state = CollectiveState()
        reorg = SelfReorganization(state)

        h = Hypothesis(id="h_new", statement="fresh", proposed_by="a1",
                      test_criteria="check")
        new_team = HypothesisTeam(id="t_new", hypothesis=h, champion_id="a1")

        plan = ReorganizationPlan(
            id="rp1", trigger=ReorganizationTrigger.STAGNATION,
            form_teams=[new_team], rationale="Form fresh team",
        )
        reorg.execute_plan(plan)
        assert "t_new" in state.teams

    def test_snapshot_progress(self):
        state = CollectiveState()
        reorg = SelfReorganization(state)
        reorg.snapshot_progress()
        assert len(reorg._progress_snapshots) == 1

    def test_consensus_deadlock_trigger(self):
        state = CollectiveState()
        # Create several open forum threads
        state.forum.create_thread("t1", "topic1")
        state.forum.create_thread("t2", "topic2")
        state.forum.create_thread("t3", "topic3")
        # Advance enough cycles
        for _ in range(5):
            state.advance_cycle()
        reorg = SelfReorganization(state)
        triggers = reorg.check_triggers()
        assert ReorganizationTrigger.CONSENSUS_DEADLOCK in triggers


# ═══════════════════════════════════════════════════════════════════════════════
# ReorganizationTrigger
# ═══════════════════════════════════════════════════════════════════════════════


class TestReorganizationTrigger:
    def test_all_values(self):
        for trigger in ReorganizationTrigger:
            assert isinstance(trigger.value, str)


# ═══════════════════════════════════════════════════════════════════════════════
# ConsensusLevel
# ═══════════════════════════════════════════════════════════════════════════════


class TestConsensusLevel:
    def test_all_values(self):
        for level in ConsensusLevel:
            assert isinstance(level.value, str)
