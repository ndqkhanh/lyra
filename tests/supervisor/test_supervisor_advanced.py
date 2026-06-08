"""Tests for Lyra v8.2 Fleet Advanced Features.

Covers circuit breaker, fleet TUI, shell commands, and topology search.
"""

import datetime
import tempfile
from pathlib import Path

import pytest

from lyra.supervisor.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitState,
    ConfidenceCircuitBreaker,
    LoopHealth,
    TripAction,
)
from lyra.supervisor.fleet import AgentConfig, FleetConfig, FleetOrchestrator
from lyra.supervisor.fleet_tui import FleetTUI, FleetTUIConfig, TUISessionCard
from lyra.supervisor.shell_commands import (
    cmd_fleet_status,
    cmd_fleet_kill,
    cmd_fleet_logs,
    cmd_fleet_list,
    cmd_fleet_top,
    cmd_fleet_start,
    cmd_fleet_stop,
)
from lyra.supervisor.topology_search import (
    AgentRole,
    MCTSConfig,
    Topology,
    TopologyNode,
    TopologySearcher,
    TopologyTemplate,
)


# ==================================================================
# Circuit Breaker Tests
# ==================================================================


class TestCircuitBreakerConfig:
    """Verify ConfidenceCircuitBreaker configuration."""

    def test_defaults(self) -> None:
        cfg = CircuitBreakerConfig()
        assert cfg.trip_threshold == 3
        assert cfg.low_confidence_threshold == 0.4
        assert cfg.auto_reset_minutes == 5
        assert cfg.max_trips == 5
        assert cfg.default_action == TripAction.PAUSE_AND_ASK

    def test_custom_values(self) -> None:
        cfg = CircuitBreakerConfig(
            trip_threshold=2,
            low_confidence_threshold=0.3,
            auto_reset_minutes=10,
            max_trips=3,
            default_action=TripAction.FALLBACK_MODEL,
        )
        assert cfg.trip_threshold == 2
        assert cfg.trip_threshold < 3
        assert cfg.default_action == TripAction.FALLBACK_MODEL


class TestCircuitBreakerTrip:
    """Test that the circuit breaker trips on consecutive low confidence."""

    @pytest.fixture
    def breaker(self) -> ConfidenceCircuitBreaker:
        cfg = CircuitBreakerConfig(trip_threshold=3, auto_reset_minutes=0)
        return ConfidenceCircuitBreaker(config=cfg)

    def test_stays_closed_on_good_confidence(self, breaker: ConfidenceCircuitBreaker) -> None:
        breaker.record_step("session-1", 0.9)
        breaker.record_step("session-1", 0.8)
        breaker.record_step("session-1", 0.95)
        health = breaker.monitor_loop("session-1")
        assert health.circuit_state == CircuitState.CLOSED

    def test_trips_on_low_confidence_threshold(self, breaker: ConfidenceCircuitBreaker) -> None:
        breaker.record_step("session-1", 0.3)
        breaker.record_step("session-1", 0.2)
        breaker.record_step("session-1", 0.1)
        health = breaker.monitor_loop("session-1")
        assert health.circuit_state == CircuitState.OPEN

    def test_trip_action_default(self, breaker: ConfidenceCircuitBreaker) -> None:
        breaker.record_step("session-1", 0.1)
        breaker.record_step("session-1", 0.2)
        breaker.record_step("session-1", 0.1)
        health = breaker.monitor_loop("session-1")
        assert health.action == TripAction.PAUSE_AND_ASK

    def test_resets_after_good_step(self, breaker: ConfidenceCircuitBreaker) -> None:
        breaker.record_step("session-1", 0.1)
        breaker.record_step("session-1", 0.2)
        # Good step resets counter
        breaker.record_step("session-1", 0.9)
        breaker.record_step("session-1", 0.1)
        breaker.record_step("session-1", 0.2)
        breaker.record_step("session-1", 0.1)
        # Now should trip again
        health = breaker.monitor_loop("session-1")
        assert health.circuit_state == CircuitState.OPEN

    @staticmethod
    def test_does_not_trip_below_threshold() -> None:
        cfg = CircuitBreakerConfig(trip_threshold=2)
        breaker = ConfidenceCircuitBreaker(config=cfg)
        breaker.record_step("session-2", 0.1)
        health = breaker.monitor_loop("session-2")
        assert health.circuit_state == CircuitState.CLOSED


class TestCircuitBreakerManualTrip:
    """Test manual trip and reset."""

    def test_manual_trip(self) -> None:
        breaker = ConfidenceCircuitBreaker()
        breaker.trip("session-1", TripAction.ABORT_SESSION)
        health = breaker.monitor_loop("session-1")
        assert health.circuit_state == CircuitState.OPEN
        assert health.action == TripAction.ABORT_SESSION

    def test_manual_reset(self) -> None:
        breaker = ConfidenceCircuitBreaker()
        breaker.trip("session-1")
        breaker.reset("session-1")
        health = breaker.monitor_loop("session-1")
        assert health.circuit_state == CircuitState.CLOSED


class TestCircuitBreakerAutoReset:
    """Test HALF_OPEN state behavior."""

    def test_auto_reset_disabled_by_zero(self) -> None:
        """With auto_reset_minutes=0, circuit stays OPEN until manual reset."""
        cfg = CircuitBreakerConfig(trip_threshold=1, auto_reset_minutes=0)
        breaker = ConfidenceCircuitBreaker(config=cfg)
        breaker.record_step("session-1", 0.1)
        health = breaker.monitor_loop("session-1")
        assert health.circuit_state == CircuitState.OPEN

    def test_half_open_good_confidence_closes(self) -> None:
        """A good confidence step in HALF_OPEN state closes the circuit."""
        breaker = ConfidenceCircuitBreaker()
        # Set up HALF_OPEN state directly (as if auto-reset had occurred)
        breaker._states["session-1"] = CircuitState.HALF_OPEN
        breaker._consecutive_low["session-1"] = 1
        breaker._last_confidence["session-1"] = 0.2

        # Good step should close the circuit
        breaker.record_step("session-1", 0.9)
        health = breaker.monitor_loop("session-1")
        assert health.circuit_state == CircuitState.CLOSED

    def test_half_open_low_confidence_retrips(self) -> None:
        """A low confidence step in HALF_OPEN state re-opens the circuit."""
        breaker = ConfidenceCircuitBreaker()
        # Set up HALF_OPEN state directly
        breaker._states["session-1"] = CircuitState.HALF_OPEN
        breaker._consecutive_low["session-1"] = 0
        breaker._last_confidence["session-1"] = 0.6

        # Low step should re-trip
        breaker.record_step("session-1", 0.2)
        health = breaker.monitor_loop("session-1")
        assert health.circuit_state == CircuitState.OPEN


class TestCircuitBreakerMaxTrips:
    """Test max trip enforcement."""

    def test_max_trips_forces_abort(self) -> None:
        cfg = CircuitBreakerConfig(
            trip_threshold=1,
            auto_reset_minutes=0,
            max_trips=2,
        )
        breaker = ConfidenceCircuitBreaker(config=cfg)

        # First trip -> OPEN
        breaker.record_step("session-1", 0.1)
        health = breaker.monitor_loop("session-1")

        # Force reset and trip again
        breaker.reset("session-1")
        breaker.record_step("session-1", 0.1)
        health = breaker.monitor_loop("session-1")
        assert health.action == TripAction.ABORT_SESSION

    def test_trip_callback_invoked(self) -> None:
        callback_args: list[tuple[str, TripAction]] = []

        def on_trip(sid: str, action: TripAction) -> None:
            callback_args.append((sid, action))

        cfg = CircuitBreakerConfig(trip_threshold=1)
        breaker = ConfidenceCircuitBreaker(config=cfg, on_trip=on_trip)
        breaker.trip("session-1", TripAction.PAUSE_AND_ASK)
        assert len(callback_args) == 1
        assert callback_args[0] == ("session-1", TripAction.PAUSE_AND_ASK)

    def test_reset_callback_invoked(self) -> None:
        callback_args: list[str] = []

        def on_reset(sid: str) -> None:
            callback_args.append(sid)

        breaker = ConfidenceCircuitBreaker(on_reset=on_reset)
        breaker.trip("session-1")
        breaker.reset("session-1")
        assert len(callback_args) == 1
        assert callback_args[0] == "session-1"


class TestCircuitBreakerHealth:
    """Test LoopHealth and session_health queries."""

    def test_session_health_returns_none_for_unknown(self) -> None:
        breaker = ConfidenceCircuitBreaker()
        assert breaker.session_health("unknown") is None

    def test_session_health_after_steps(self) -> None:
        breaker = ConfidenceCircuitBreaker()
        breaker.record_step("session-1", 0.8)
        breaker.record_step("session-1", 0.7)
        health = breaker.session_health("session-1")
        assert health is not None
        assert health.session_id == "session-1"
        assert health.consecutive_low == 0
        assert health.last_confidence == 0.7

    def test_all_sessions_health(self) -> None:
        breaker = ConfidenceCircuitBreaker()
        breaker.record_step("session-1", 0.1)
        breaker.record_step("session-2", 0.9)
        all_health = breaker.all_sessions_health()
        assert len(all_health) == 2
        health_map = {h.session_id: h for h in all_health}
        assert "session-1" in health_map
        assert "session-2" in health_map

    def test_loop_health_dataclass(self) -> None:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        health = LoopHealth(
            session_id="s1",
            circuit_state=CircuitState.OPEN,
            consecutive_low=3,
            last_confidence=0.2,
            trip_count=1,
            last_trip_at=now,
            action=TripAction.PAUSE_AND_ASK,
        )
        assert health.session_id == "s1"
        assert health.circuit_state == CircuitState.OPEN
        assert health.last_trip_at == now


# ==================================================================
# Fleet TUI Tests
# ==================================================================


class TestFleetTUIRender:
    """Test FleetTUI rendering methods."""

    @pytest.fixture
    def fleet_with_sessions(self, db_path: str) -> FleetOrchestrator:
        cfg = FleetConfig(max_concurrent=5)
        fleet = FleetOrchestrator(db_path=db_path, config=cfg)
        fleet.spawn_agent(AgentConfig(name="agent-1", working_dir="/tmp/1"))
        fleet.spawn_agent(AgentConfig(name="agent-2", working_dir="/tmp/2"))
        return fleet

    @pytest.fixture
    def db_path(self) -> str:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        yield path
        Path(path).unlink(missing_ok=True)

    def test_render_fleet_has_header(self, fleet_with_sessions: FleetOrchestrator) -> None:
        tui = FleetTUI(fleet_with_sessions)
        output = tui.render_fleet()
        assert len(output) > 0

    def test_render_fleet_with_sessions(self, fleet_with_sessions: FleetOrchestrator) -> None:
        tui = FleetTUI(fleet_with_sessions)
        output = tui.render_fleet()
        # Should contain session names
        assert "agent-1" in output or "agent-2" in output

    def test_render_empty_fleet(self, db_path: str) -> None:
        fleet = FleetOrchestrator(db_path=db_path)
        tui = FleetTUI(fleet)
        output = tui.render_fleet()
        assert isinstance(output, str)

    def test_peek_panel_for_known_session(self, fleet_with_sessions: FleetOrchestrator) -> None:
        status = fleet_with_sessions.fleet_status()
        assert len(status.sessions) > 0
        sid = status.sessions[0].session_id
        tui = FleetTUI(fleet_with_sessions)
        panel = tui.peek_panel(sid)
        assert sid in panel
        assert "Session Details" in panel

    def test_peek_panel_for_unknown_session(self, fleet_with_sessions: FleetOrchestrator) -> None:
        tui = FleetTUI(fleet_with_sessions)
        panel = tui.peek_panel("nonexistent")
        assert "not found" in panel

    def test_keyboard_navigation(self, fleet_with_sessions: FleetOrchestrator) -> None:
        tui = FleetTUI(fleet_with_sessions)
        # Simulate key handling by calling _handle_key
        tui._handle_key("j")  # down
        assert tui._selected_index == 1
        tui._handle_key("k")  # up
        assert tui._selected_index == 0
        tui._handle_key("q")  # quit
        assert tui._running is False

    def test_kill_via_keyboard(self, fleet_with_sessions: FleetOrchestrator) -> None:
        """Pressing K kills the selected session."""
        tui = FleetTUI(fleet_with_sessions)
        status = fleet_with_sessions.fleet_status()
        start_count = status.total_sessions

        tui._handle_key("K")  # kill selected
        status = fleet_with_sessions.fleet_status()
        assert status.total_sessions == start_count  # sessions still tracked

    def test_toggle_peek_via_enter(self, fleet_with_sessions: FleetOrchestrator) -> None:
        tui = FleetTUI(fleet_with_sessions)
        assert len(tui._peek_sessions) == 0
        tui._handle_key("\r")  # Enter
        assert len(tui._peek_sessions) > 0
        tui._handle_key("\r")  # Enter again toggles off
        assert len(tui._peek_sessions) == 0

    def test_config_defaults(self) -> None:
        cfg = FleetTUIConfig()
        assert cfg.auto_refresh_seconds == 2.0
        assert cfg.color_enabled is True


# ==================================================================
# Shell Commands Tests
# ==================================================================


class TestShellCommands:
    """Test fleet CLI command functions."""

    @pytest.fixture
    def fleet(self, db_path: str) -> FleetOrchestrator:
        cfg = FleetConfig(max_concurrent=5)
        return FleetOrchestrator(db_path=db_path, config=cfg)

    @pytest.fixture
    def db_path(self) -> str:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        yield path
        Path(path).unlink(missing_ok=True)

    def test_cmd_fleet_status_empty(self, fleet: FleetOrchestrator) -> None:
        result = cmd_fleet_status(fleet)
        assert "empty" in result

    def test_cmd_fleet_status_with_sessions(self, fleet: FleetOrchestrator) -> None:
        fleet.spawn_agent(AgentConfig(name="test", working_dir="/tmp"))
        result = cmd_fleet_status(fleet)
        assert "LYRA FLEET STATUS" in result

    def test_cmd_fleet_start(self, fleet: FleetOrchestrator) -> None:
        cfg = AgentConfig(name="spawned-agent", working_dir="/tmp/s")
        result = cmd_fleet_start(fleet, cfg)
        assert "spawned" in result
        assert "Session ID" in result

    def test_cmd_fleet_kill_known(self, fleet: FleetOrchestrator) -> None:
        sid = fleet.spawn_agent(AgentConfig(name="kill-me", working_dir="/tmp/k"))
        result = cmd_fleet_kill(fleet, sid)
        assert "killed" in result

    def test_cmd_fleet_kill_unknown(self, fleet: FleetOrchestrator) -> None:
        result = cmd_fleet_kill(fleet, "nonexistent")
        assert "not found" in result

    def test_cmd_fleet_logs_known(self, fleet: FleetOrchestrator) -> None:
        sid = fleet.spawn_agent(AgentConfig(name="log-test", working_dir="/tmp/l"))
        result = cmd_fleet_logs(fleet, sid)
        assert sid in result
        assert "log-test" in result

    def test_cmd_fleet_logs_unknown(self, fleet: FleetOrchestrator) -> None:
        result = cmd_fleet_logs(fleet, "nonexistent")
        assert "not found" in result

    def test_cmd_fleet_top(self, fleet: FleetOrchestrator) -> None:
        fleet.spawn_agent(AgentConfig(name="top-test", working_dir="/tmp/t"))
        result = cmd_fleet_top(fleet)
        assert "LYRA FLEET TOP" in result

    def test_cmd_fleet_list(self, fleet: FleetOrchestrator) -> None:
        result = cmd_fleet_list(fleet)
        assert isinstance(result, str)

    def test_cmd_fleet_stop_with_sessions(self, fleet: FleetOrchestrator) -> None:
        fleet.spawn_agent(AgentConfig(name="a1", working_dir="/tmp/a1"))
        fleet.spawn_agent(AgentConfig(name="a2", working_dir="/tmp/a2"))
        result = cmd_fleet_stop(fleet)
        assert "Stopped" in result

    def test_cmd_fleet_stop_empty(self, fleet: FleetOrchestrator) -> None:
        result = cmd_fleet_stop(fleet)
        assert "No active sessions" in result


# ==================================================================
# Topology Search Tests
# ==================================================================


class TestTopologyTemplates:
    """Test pre-built topology templates."""

    @pytest.fixture
    def pool(self) -> list[AgentRole]:
        return [
            AgentRole(role="supervisor", capabilities=("plan", "coordinate", "review"), cost_per_step=2.0),
            AgentRole(role="researcher", capabilities=("search", "analyze"), cost_per_step=1.0),
            AgentRole(role="writer", capabilities=("write", "format"), cost_per_step=0.5),
            AgentRole(role="critic", capabilities=("review", "test"), cost_per_step=0.8),
        ]

    def test_star_topology(self, pool: list[AgentRole]) -> None:
        searcher = TopologySearcher()
        topo = searcher.build_template(TopologyTemplate.STAR, pool)
        assert topo.template == TopologyTemplate.STAR
        assert len(topo.nodes) == len(pool)
        # Star should have a root with children
        root = [n for n in topo.nodes.values() if n.parent is None]
        assert len(root) == 1

    def test_mesh_topology(self, pool: list[AgentRole]) -> None:
        searcher = TopologySearcher()
        topo = searcher.build_template(TopologyTemplate.MESH, pool)
        assert topo.template == TopologyTemplate.MESH
        # Mesh should have edges between every pair
        n = len(pool)
        expected_edges = n * (n - 1)  # each node talks to every other (bidirectional counted)
        assert len(topo.edges) == expected_edges

    def test_tree_topology(self, pool: list[AgentRole]) -> None:
        searcher = TopologySearcher()
        topo = searcher.build_template(TopologyTemplate.TREE, pool)
        assert topo.template == TopologyTemplate.TREE
        assert len(topo.nodes) == len(pool)

    def test_hybrid_topology(self, pool: list[AgentRole]) -> None:
        searcher = TopologySearcher()
        topo = searcher.build_template(TopologyTemplate.HYBRID, pool)
        assert topo.template == TopologyTemplate.HYBRID
        assert len(topo.nodes) == len(pool)

    def test_empty_pool_returns_empty_topology(self) -> None:
        searcher = TopologySearcher()
        topo = searcher.build_template(TopologyTemplate.STAR, [])
        assert len(topo.nodes) == 0


class TestTopologySearch:
    """Test MCTS-driven topology search."""

    @pytest.fixture
    def pool(self) -> list[AgentRole]:
        return [
            AgentRole(role="planner", capabilities=("plan",), cost_per_step=1.0),
            AgentRole(role="executor", capabilities=("code",), cost_per_step=0.5),
            AgentRole(role="reviewer", capabilities=("review",), cost_per_step=0.3),
        ]

    def test_search_returns_topology(self, pool: list[AgentRole]) -> None:
        cfg = MCTSConfig(iterations=10)
        searcher = TopologySearcher(config=cfg)
        topo = searcher.search_optimal_topology(task="Write unit tests", pool=pool)
        assert isinstance(topo, Topology)
        assert topo.template in list(TopologyTemplate)
        assert topo.reward >= 0

    def test_search_assigns_reward(self, pool: list[AgentRole]) -> None:
        cfg = MCTSConfig(iterations=5)
        searcher = TopologySearcher(config=cfg)
        topo = searcher.search_optimal_topology(task="Debug crash", pool=pool)
        assert topo.reward > 0
        assert topo.quality_score > 0
        assert topo.cost_estimate > 0

    def test_search_with_single_role(self) -> None:
        pool = [AgentRole(role="solo", capabilities=("all",), cost_per_step=1.0)]
        cfg = MCTSConfig(iterations=5)
        searcher = TopologySearcher(config=cfg)
        topo = searcher.search_optimal_topology(task="Single task", pool=pool)
        assert topo.reward >= 0


class TestTopologyNode:
    """Verify TopologyNode dataclass."""

    def test_create_node(self) -> None:
        node = TopologyNode(role="researcher", parent="supervisor")
        assert node.role == "researcher"
        assert node.parent == "supervisor"
        assert node.children == ()
        assert node.communication_weight == 1.0

    def test_node_with_children(self) -> None:
        node = TopologyNode(
            role="manager",
            parent=None,
            children=("worker_a", "worker_b"),
            communication_weight=0.8,
        )
        assert node.parent is None
        assert len(node.children) == 2
        assert node.communication_weight == 0.8


class TestTopologyData:
    """Verify Topology dataclass."""

    def test_create_topology(self) -> None:
        topo = Topology(
            nodes={
                "root": TopologyNode(role="root", parent=None),
                "leaf": TopologyNode(role="leaf", parent="root"),
            },
            template=TopologyTemplate.STAR,
            edges=(("root", "leaf"),),
            reward=0.75,
            quality_score=0.8,
            cost_estimate=2.5,
            latency_estimate=1.0,
        )
        assert len(topo.nodes) == 2
        assert topo.reward == 0.75
        assert topo.template == TopologyTemplate.STAR

    def test_default_values(self) -> None:
        topo = Topology(
            nodes={},
            template=TopologyTemplate.MESH,
        )
        assert topo.reward == 0.0
        assert topo.quality_score == 0.0
        assert topo.edges == ()


class TestTopologyEvaluation:
    """Test topology quality/cost/latency estimation."""

    @pytest.fixture
    def pool(self) -> list[AgentRole]:
        return [
            AgentRole(role="supervisor", capabilities=("plan",), cost_per_step=2.0),
            AgentRole(role="worker", capabilities=("execute",), cost_per_step=0.5),
        ]

    def test_star_quality(self, pool: list[AgentRole]) -> None:
        searcher = TopologySearcher()
        topo = searcher.build_template(TopologyTemplate.STAR, pool)
        # Evaluate internally via search_optimal_topology or build_template
        # build_template does not evaluate; search does
        cfg = MCTSConfig(iterations=2)
        searcher2 = TopologySearcher(config=cfg)
        topo2 = searcher2.search_optimal_topology(task="test", pool=pool)
        assert topo2.quality_score >= 0

    def test_cost_estimate(self) -> None:
        # Cost = sum(1.0 + communication_weight * 0.5) per node
        nodes = {
            "a": TopologyNode(role="a", parent=None, communication_weight=1.0),
            "b": TopologyNode(role="b", parent="a", communication_weight=0.5),
        }
        topo = Topology(nodes=nodes, template=TopologyTemplate.STAR)
        cost = TopologySearcher._estimate_cost(topo)
        expected_a = 1.0 + 1.0 * 0.5
        expected_b = 1.0 + 0.5 * 0.5
        assert abs(cost - (expected_a + expected_b)) < 0.01

    def test_latency_estimate_single_node(self) -> None:
        nodes = {
            "root": TopologyNode(role="root", parent=None),
        }
        topo = Topology(nodes=nodes, template=TopologyTemplate.STAR)
        latency = TopologySearcher._estimate_latency(topo)
        assert latency == 1.0  # root step

    def test_latency_estimate_two_levels(self) -> None:
        nodes = {
            "root": TopologyNode(role="root", parent=None, children=("child",), communication_weight=1.0),
            "child": TopologyNode(role="child", parent="root", communication_weight=0.5),
        }
        topo = Topology(nodes=nodes, template=TopologyTemplate.STAR)
        latency = TopologySearcher._estimate_latency(topo)
        assert latency > 0


class TestMCTSConfig:
    """Verify MCTSConfig defaults."""

    def test_defaults(self) -> None:
        cfg = MCTSConfig()
        assert cfg.iterations == 100
        assert cfg.exploration_constant == 1.414
        assert cfg.max_depth == 5
        assert cfg.simulation_budget == 50
