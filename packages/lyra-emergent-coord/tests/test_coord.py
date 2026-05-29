"""Comprehensive tests for lyra-emergent-coord package."""

from __future__ import annotations

import asyncio
import time

import pytest
from lyra_emergent_coord import (
    AntColonyOptimizer,
    BeeAlgorithm,
    Bid,
    Coalition,
    CoalitionError,
    CoalitionFormationEngine,
    ConflictResolutionStrategy,
    ConflictResolver,
    Contract,
    ContractNetProtocol,
    ElectionAlgorithm,
    ElectionResult,
    EmergenceDetector,
    EmergentBehavior,
    FlockingSystem,
    InteractionPattern,
    LeaderHealthMonitor,
    LeaderManager,
    LeaderRecord,
    LeaderState,
    MultiRoundNegotiator,
    NegotiationState,
    NoValidCoalitionError,
    ParticleSwarmOptimizer,
    StigmergySystem,
    TaskAdvertisement,
)

# ============================================================================
# Coalition tests
# ============================================================================


class TestCoalitionFormation:
    @pytest.fixture
    def engine(self) -> CoalitionFormationEngine:
        eng = CoalitionFormationEngine()
        eng.register_agent("a1", capabilities=["nlp", "search"])
        eng.register_agent("a2", capabilities=["vision", "code"])
        eng.register_agent("a3", capabilities=["nlp", "code", "debug"])
        eng.register_agent("a4", capabilities=["search", "analyze"])
        eng.register_agent("a5", capabilities=["nlp", "search", "code"])
        return eng

    def test_register_and_form_coalition(self, engine: CoalitionFormationEngine) -> None:
        async def _run() -> Coalition:
            await engine.advertise_task(
                TaskAdvertisement(
                    task_id="task_1",
                    required_capabilities=("search", "analyze"),
                    complexity=0.5,
                )
            )
            return await engine.form_coalition("task_1")

        coalition = asyncio.run(_run())
        assert isinstance(coalition, Coalition)

    async def test_collect_bids(self, engine: CoalitionFormationEngine) -> None:
        ad = TaskAdvertisement(task_id="t1", required_capabilities=("nlp",))
        await engine.advertise_task(ad)
        bids = await engine.collect_bids("t1")
        assert len(bids) >= 3

    async def test_form_coalition_requirements(self, engine: CoalitionFormationEngine) -> None:
        ad = TaskAdvertisement(
            task_id="t1",
            task_type="research",
            complexity=0.5,
            required_capabilities=("nlp", "code"),
            min_coalition_size=2,
            max_coalition_size=3,
        )
        await engine.advertise_task(ad)
        coalition = await engine.form_coalition("t1")
        assert coalition.size >= 2
        assert coalition.leader_id
        assert coalition.capability_coverage > 0

    async def test_no_valid_coalition(self, engine: CoalitionFormationEngine) -> None:
        ad = TaskAdvertisement(task_id="t2", required_capabilities=("quantum", "telepathy"))
        await engine.advertise_task(ad)
        with pytest.raises(NoValidCoalitionError):
            await engine.form_coalition("t2")

    async def test_shapley_values(self, engine: CoalitionFormationEngine) -> None:
        ad = TaskAdvertisement(task_id="t3", required_capabilities=("nlp",), max_coalition_size=3)
        await engine.advertise_task(ad)
        coalition = await engine.form_coalition("t3")
        assert coalition.shapley_values
        assert len(coalition.shapley_values) == coalition.size
        total = sum(coalition.shapley_values.values())
        assert total > 0

    def test_bid_total_score(self) -> None:
        bid = Bid(
            agent_id="a1", task_id="t1", capability_score=0.8, current_load=0.2, bid_value=0.7
        )
        assert bid.total_score == pytest.approx(0.78)

    def test_coalition_properties(self) -> None:
        c = Coalition(
            task_id="t1",
            leader_id="a1",
            member_ids=("a1", "a2", "a3"),
            shapley_values={"a1": 0.5, "a2": 0.3, "a3": 0.2},
        )
        assert c.size == 3
        assert c.avg_shapley == pytest.approx(1.0 / 3.0)

    def test_task_advertisement_validation(self) -> None:
        with pytest.raises(CoalitionError):
            TaskAdvertisement(complexity=1.5)

    def test_register_and_unregister(self, engine: CoalitionFormationEngine) -> None:
        engine.register_agent("test-reg", ["research"])
        assert "test-reg" in engine._agent_capabilities
        engine.unregister_agent("test-reg")
        assert "test-reg" not in engine._agent_capabilities

    def test_record_contribution(self, engine: CoalitionFormationEngine) -> None:
        engine.record_contribution("a1", 0.9)
        engine.record_contribution("a1", 0.8)
        assert engine.get_agent_performance("a1") == pytest.approx(0.85)

    def test_dissolve_coalition(self, engine: CoalitionFormationEngine) -> None:
        assert not engine.dissolve_coalition("nonexistent")

    def test_snapshot(self, engine: CoalitionFormationEngine) -> None:
        s = engine.snapshot()
        assert s["registered_agents"] >= 5


# ============================================================================
# Leadership tests
# ============================================================================


class TestLeaderElection:
    @pytest.fixture
    def manager(self) -> LeaderManager:
        m = LeaderManager(default_algorithm=ElectionAlgorithm.BULLY)
        m.register_agent("agent-1", priority=1.0)
        m.register_agent("agent-2", priority=2.0)
        m.register_agent("agent-3", priority=0.5)
        return m

    def test_bully_election(self, manager: LeaderManager) -> None:
        result = manager.elect_leader(algorithm=ElectionAlgorithm.BULLY)
        assert result.winner_id == "agent-2"
        assert result.quorum_achieved

    def test_ring_election(self, manager: LeaderManager) -> None:
        result = manager.elect_leader(algorithm=ElectionAlgorithm.RING)
        assert result.winner_id == "agent-2"

    def test_random_election(self, manager: LeaderManager) -> None:
        result = manager.elect_leader(algorithm=ElectionAlgorithm.RANDOM)
        assert result.winner_id in ("agent-1", "agent-2", "agent-3")

    def test_raft_inspired_election(self, manager: LeaderManager) -> None:
        result = manager.elect_leader(algorithm=ElectionAlgorithm.RAFT_INSPIRED)
        assert result.term > 0
        assert result.winner_id

    def test_no_candidates_raises(self) -> None:
        m = LeaderManager()
        with pytest.raises(Exception):
            m.elect_leader([])

    def test_leader_health_monitor(self) -> None:
        monitor = LeaderHealthMonitor(heartbeat_timeout=0.1, max_missed_heartbeats=1)
        monitor.register_leader("leader-1")
        assert monitor.is_healthy("leader-1")
        time.sleep(0.15)
        failed = monitor.check_health()
        assert "leader-1" in failed

    def test_leader_heartbeat_keeps_alive(self) -> None:
        monitor = LeaderHealthMonitor(heartbeat_timeout=0.3, max_missed_heartbeats=2)
        monitor.register_leader("l1")
        monitor.record_heartbeat("l1")
        failed = monitor.check_health()
        assert "l1" not in failed

    def test_consensus_building(self, manager: LeaderManager) -> None:
        leaders = ["agent-1", "agent-2", "agent-3"]
        reached, positions = manager.build_consensus(leaders, "test proposal")
        assert isinstance(reached, bool)
        assert len(positions) == 3

    def test_delegation(self, manager: LeaderManager) -> None:
        manager.elect_leader()
        assert manager.delegate("agent-2", "agent-1", "monitoring")
        assert "monitoring" in manager.get_delegations("agent-2")
        assert manager.revoke_delegation("agent-2", "monitoring")

    def test_list_leaders(self, manager: LeaderManager) -> None:
        manager.elect_leader()
        leaders = manager.list_leaders()
        assert len(leaders) >= 1

    def test_leader_history(self, manager: LeaderManager) -> None:
        manager.elect_leader()
        history = manager.get_leader_history()
        assert len(history) >= 1

    def test_election_result_properties(self) -> None:
        result = ElectionResult(
            winner_id="agent-1", votes_received=3, total_voters=4, quorum_achieved=True
        )
        assert result.vote_share == 0.75
        assert result.is_valid

    def test_leader_record(self) -> None:
        record = LeaderRecord(leader_id="l1", domain="test", term=1)
        assert record.is_healthy
        record.state = LeaderState.DEPOSED
        assert not record.is_healthy

    async def test_start_stop_monitoring(self, manager: LeaderManager) -> None:
        manager.elect_leader()
        await manager.start_monitoring(interval=0.1)
        await asyncio.sleep(0.15)
        await manager.stop_monitoring()


# ============================================================================
# Negotiation tests
# ============================================================================


class TestNegotiation:
    def test_contract_net_protocol(self) -> None:
        cnp = ContractNetProtocol(bid_timeout=5.0)
        session = asyncio.run(
            cnp.announce_task("task-1", {"type": "build"}, eligible_agents=["a", "b"])
        )
        assert session.state == NegotiationState.OPEN
        offer = cnp.submit_bid(session.session_id, "a", {"price": 10}, value=0.8)
        assert offer.proposer_id == "a"
        contract = cnp.evaluate_and_award(session.session_id)
        assert contract is not None
        assert contract.parties[0] == "a"

    def test_cnp_invalid_bidder(self) -> None:
        cnp = ContractNetProtocol()
        session = asyncio.run(cnp.announce_task("t1", {}, eligible_agents=["a"]))
        with pytest.raises(Exception):
            cnp.submit_bid(session.session_id, "z", {})

    def test_multi_round_negotiator(self) -> None:
        neg = MultiRoundNegotiator(default_max_rounds=5)
        session = asyncio.run(neg.start_negotiation(participants=["a", "b"], topic="price"))
        offer = neg.make_offer(session.session_id, "a", {"price": 100}, initial_value=0.8)
        assert offer.round_number == 0
        counter = neg.counter_offer(
            session.session_id, offer.offer_id, "b", {"price": 80}, value=0.6
        )
        assert counter.round_number == 1
        contract = neg.accept_offer(session.session_id, counter.offer_id, "a")
        assert contract.parties == ("b", "a")

    def test_multi_round_max_rounds(self) -> None:
        neg = MultiRoundNegotiator(default_max_rounds=2)
        session = asyncio.run(neg.start_negotiation(participants=["a", "b"], topic="test"))
        o1 = neg.make_offer(session.session_id, "a", {}, initial_value=0.8)
        neg.counter_offer(session.session_id, o1.offer_id, "b", {}, value=0.7)
        # Third offer after 2 counter-offers triggers max rounds
        o3 = neg.make_offer(session.session_id, "a", {}, initial_value=0.6)
        # Counter-offer increments round to 2, now make_offer should raise
        neg.counter_offer(session.session_id, o3.offer_id, "b", {}, value=0.65)
        with pytest.raises(Exception):
            neg.make_offer(session.session_id, "a", {}, initial_value=0.5)

    def test_agent_strategies(self) -> None:
        neg = MultiRoundNegotiator()
        neg.set_strategy("a", "aggressive")
        neg.set_strategy("b", "cooperative")
        neg.set_strategy("c", "tit_for_tat")
        session = asyncio.run(neg.start_negotiation(participants=["a", "b", "c"], topic="test"))
        for agent_id in ["a", "b", "c"]:
            offer = neg.make_offer(session.session_id, agent_id, {}, initial_value=0.8)
            assert 0.1 <= offer.value <= 1.0

    def test_conflict_resolver_majority(self) -> None:
        resolver = ConflictResolver(default_strategy=ConflictResolutionStrategy.MAJORITY_VOTE)
        resolver.register_conflict(
            "c1", "test", parties=["a", "b", "c"], positions={"a": "opt1", "b": "opt1", "c": "opt2"}
        )
        result = resolver.resolve("c1")
        assert result["winner"] == "opt1"
        assert resolver.is_resolved("c1")

    def test_conflict_resolver_authority(self) -> None:
        resolver = ConflictResolver()
        resolver.register_conflict(
            "c2",
            "auth test",
            parties=["a", "b"],
            positions={"a": "opt1", "b": "opt2"},
            authority="a",
        )
        result = resolver.resolve("c2", strategy=ConflictResolutionStrategy.AUTHORITY_OVERRIDE)
        assert result["winner"] == "opt1"

    def test_formalized_contract(self) -> None:
        contract = Contract(parties=("a", "b", "c"), terms={"scope": "dev"})
        assert contract.party_count == 3
        assert not contract.is_expired()

    def test_negotiation_snapshot(self) -> None:
        neg = MultiRoundNegotiator()
        asyncio.run(neg.start_negotiation(participants=["a"], topic="test"))
        snap = neg.snapshot()
        assert snap["active_sessions"] >= 1


# ============================================================================
# Emergence tests
# ============================================================================


class TestEmergenceDetection:
    @pytest.fixture
    def detector(self) -> EmergenceDetector:
        return EmergenceDetector(pattern_min_frequency=2, novelty_threshold=0.5)

    def test_record_interaction(self, detector: EmergenceDetector) -> None:
        detector.record_interaction("a", "b", "cooperation", {"score": 0.8})
        detector.record_interaction("a", "b", "cooperation", {"score": 0.9})
        detector.record_interaction("b", "a", "cooperation", {"score": 0.7})
        patterns = detector.detect_patterns()
        assert len(patterns) >= 1

    def test_specialization_detection(self, detector: EmergenceDetector) -> None:
        for _ in range(5):
            detector.record_interaction("specialist-a", "any", "nlp_task", {})
        patterns = detector.detect_patterns()
        spec = [p for p in patterns if p.pattern_type == "specialization"]
        assert len(spec) >= 1

    def test_novelty_detection(self, detector: EmergenceDetector) -> None:
        detector.record_behavior("agent-1", "normal-behavior")
        s2 = detector.record_behavior("agent-1", "normal-behavior")
        s3 = detector.record_behavior("agent-1", "radically-different")
        assert s3.novelty > s2.novelty

    def test_strategy_amplification(self, detector: EmergenceDetector) -> None:
        for _ in range(10):
            detector.record_strategy_outcome("good-strategy", 0.9)
            detector.record_strategy_outcome("bad-strategy", 0.2)
        amplified = detector.amplify_strategies()
        assert "good-strategy" in amplified
        assert "bad-strategy" not in amplified

    def test_emergence_metrics(self, detector: EmergenceDetector) -> None:
        for _ in range(5):
            detector.record_interaction("a", "b", "cooperation", {})
        metrics = detector.compute_emergence_metrics()
        assert "emergence_score" in metrics
        assert 0.0 <= metrics["emergence_score"] <= 1.0

    def test_signature_similarity(self) -> None:
        assert EmergenceDetector._signature_similarity("abc", "abc") > 0.8
        assert EmergenceDetector._signature_similarity("abc", "xyz") < 0.5
        assert EmergenceDetector._signature_similarity("", "") == 0.0

    def test_pattern_significance(self) -> None:
        p = InteractionPattern(
            agents_involved=["a", "b"], pattern_type="cooperation", frequency=5, confidence=0.5
        )
        assert p.is_significant
        p2 = InteractionPattern(
            agents_involved=["c"], pattern_type="unknown", frequency=1, confidence=0.1
        )
        assert not p2.is_significant

    def test_emergent_behavior_model(self) -> None:
        behavior = EmergentBehavior(
            name="test",
            description="desc",
            source_patterns=["p1"],
            complexity=5,
            utility=0.7,
            stability=0.8,
        )
        assert behavior.complexity == 5


# ============================================================================
# Swarm Intelligence tests
# ============================================================================


class TestSwarmIntelligence:
    def test_stigmergy_deposit(self) -> None:
        system = StigmergySystem(default_decay_rate=0.5, evaporation_interval=0.0)
        system.deposit("loc1", "agent-a", intensity=2.0)
        assert system.get_trail_strength("loc1") > 0
        system.reinforce("loc1", bonus=1.0)
        assert system.get_trail_strength("loc1") >= 2.0

    def test_stigmergy_best_location(self) -> None:
        system = StigmergySystem()
        system.deposit("best", "a", intensity=5.0)
        system.deposit("ok", "b", intensity=1.0)
        assert system.get_best_location() == "best"

    def test_ant_colony_optimization(self) -> None:
        aco = AntColonyOptimizer(num_ants=10, iterations=30)
        aco.add_edge("A", "B", distance=1.0)
        aco.add_edge("B", "C", distance=1.0)
        aco.add_edge("A", "C", distance=3.0)
        aco.add_edge("C", "D", distance=1.0)
        path = aco.optimize("A", "D")
        assert len(path) >= 2
        assert path[0] == "A"
        assert path[-1] == "D"

    def test_particle_swarm_optimization(self) -> None:
        pso = ParticleSwarmOptimizer(num_particles=20, bounds=(-5.0, 5.0))
        pso.initialize(dimensions=2)

        def sphere_fn(pos: list[float]) -> float:
            return -(pos[0] ** 2 + pos[1] ** 2)

        pso.optimize(fitness_fn=sphere_fn, iterations=50)
        assert pso.best_score >= -1.0

    def test_bee_algorithm(self) -> None:
        bees = BeeAlgorithm(num_scouts=3, num_employed=5, num_onlookers=3)
        bees.register_source("task-a", quality=0.8)
        bees.register_source("task-b", quality=0.5)
        bees.register_source("task-c", quality=0.3)
        best = bees.get_best_source()
        assert best is not None
        assert best.location == "task-a"
        bees.scout("task-d", quality=0.95)
        best = bees.get_best_source()
        assert best is not None
        assert best.location == "task-d"
        allocation = bees.get_allocation()
        assert len(allocation) >= 4

    def test_bee_abandon(self) -> None:
        bees = BeeAlgorithm(abandonment_limit=1)
        bees.register_source("ephemeral", quality=0.5)
        bees.abandon_exhausted()
        assert bees.get_best_source() is None

    def test_flocking_system(self) -> None:
        flock = FlockingSystem(width=100.0, height=100.0)
        for _i in range(10):
            flock.add_boid()
        assert flock.population == 10
        for _ in range(50):
            flock.step(dt=0.1)
        positions = flock.get_positions()
        assert len(positions) == 10
        centroid = flock.get_centroid()
        assert 0.0 <= centroid[0] <= 100.0

    def test_flocking_add_remove(self) -> None:
        flock = FlockingSystem()
        bid = flock.add_boid(position=(10.0, 10.0))
        assert flock.population == 1
        assert flock.remove_boid(bid)
        assert flock.population == 0

    def test_flocking_empty_centroid(self) -> None:
        flock = FlockingSystem()
        assert flock.get_centroid() == (0.0, 0.0)


# ============================================================================
# Integration tests
# ============================================================================


class TestEmergentIntegration:
    async def test_coalition_and_negotiation_flow(self) -> None:
        engine = CoalitionFormationEngine()
        engine.register_agent("leader", capabilities=["manage", "code"])
        engine.register_agent("coder-1", capabilities=["code", "test"])
        engine.register_agent("coder-2", capabilities=["code", "deploy"])
        ad = TaskAdvertisement(
            task_id="build-api",
            required_capabilities=("code",),
            min_coalition_size=2,
            max_coalition_size=3,
        )
        await engine.advertise_task(ad)
        coalition = await engine.form_coalition("build-api")
        assert coalition.size >= 2
        assert coalition.leader_id

        cnp = ContractNetProtocol()
        session = await cnp.announce_task(
            "build-api", {"type": "api"}, eligible_agents=list(coalition.member_ids)
        )
        cnp.submit_bid(session.session_id, coalition.leader_id, {"approach": "rest"}, value=0.9)
        contract = cnp.evaluate_and_award(session.session_id)
        assert contract is not None

    async def test_leader_with_pso(self) -> None:
        manager = LeaderManager()
        manager.register_agent("alpha", priority=3.0)
        manager.register_agent("beta", priority=2.0)
        result = manager.elect_leader()
        assert result.winner_id == "alpha"

        pso = ParticleSwarmOptimizer(num_particles=10, bounds=(-5.0, 5.0))
        pso.initialize(dimensions=2)

        def cost(pos: list[float]) -> float:
            return -((pos[0] - 1.0) ** 2 + (pos[1] - 2.0) ** 2)

        pso.optimize(fitness_fn=cost, iterations=20)
        assert pso.best_score <= 0.0

    async def test_emergence_from_coordination(self) -> None:
        detector = EmergenceDetector(pattern_min_frequency=2)
        for _ in range(5):
            detector.record_interaction("a", "b", "cooperation", {"success": True})
            detector.record_interaction("b", "a", "acknowledgment", {"status": "ok"})
        patterns = detector.detect_patterns()
        assert len(patterns) > 0
        metrics = detector.compute_emergence_metrics()
        assert metrics["total_patterns"] > 0
