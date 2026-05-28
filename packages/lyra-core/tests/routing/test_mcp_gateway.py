"""Tests for the MCP Gateway."""
from __future__ import annotations

from lyra_cli.mcp.mcp_gateway import (
    CircuitState,
    GatewayConfig,
    McpGateway,
)


class TestMcpGateway:
    def test_initial_state(self):
        gw = McpGateway()
        assert gw.server_count == 0
        assert gw.healthy_count == 0
        assert gw.total_requests == 0

    def test_register_server(self):
        gw = McpGateway()
        gw.register("srv-1", "http://localhost:8080")
        assert gw.server_count == 1

    def test_register_duplicate_idempotent(self):
        gw = McpGateway()
        gw.register("srv-1", "http://a")
        gw.register("srv-1", "http://b")
        assert gw.server_count == 1

    def test_deregister(self):
        gw = McpGateway()
        gw.register("srv-1", "http://localhost")
        gw.deregister("srv-1")
        assert gw.server_count == 0

    def test_route_returns_none_with_no_servers(self):
        gw = McpGateway()
        assert gw.route() is None

    def test_route_returns_server_with_one_registered(self):
        gw = McpGateway()
        gw.register("srv-1", "http://localhost:8080")
        result = gw.route()
        assert result is not None
        assert result.server_id == "srv-1"

    def test_route_round_robin(self):
        gw = McpGateway()
        gw.register("a", "http://a")
        gw.register("b", "http://b")
        r1 = gw.route()
        r2 = gw.route()
        assert r1 is not None and r2 is not None
        assert r1.server_id != r2.server_id

    def test_report_success_resets_failures(self):
        gw = McpGateway()
        gw.register("srv-1", "http://a")
        gw.report_failure("srv-1")
        gw.report_failure("srv-1")
        gw.report_success("srv-1")
        assert gw._servers["srv-1"].failure_count == 0

    def test_report_failure_increments_counter(self):
        gw = McpGateway()
        gw.register("srv-1", "http://a")
        gw.report_failure("srv-1")
        assert gw._servers["srv-1"].failure_count == 1

    def test_circuit_breaker_opens(self):
        config = GatewayConfig(circuit_breaker_threshold=3)
        gw = McpGateway(config=config)
        gw.register("srv-1", "http://a")
        gw.report_failure("srv-1")
        gw.report_failure("srv-1")
        gw.report_failure("srv-1")
        assert gw._servers["srv-1"].circuit == CircuitState.OPEN

    def test_route_skips_open_circuits(self):
        config = GatewayConfig(circuit_breaker_threshold=2)
        gw = McpGateway(config=config)
        gw.register("srv-1", "http://a")
        gw.register("srv-2", "http://b")
        gw.report_failure("srv-1")
        gw.report_failure("srv-1")
        # srv-1 should be OPEN now
        r1 = gw.route()
        assert r1 is not None
        assert r1.server_id == "srv-2"

    def test_health_check_recovery(self):
        config = GatewayConfig(circuit_breaker_threshold=1, circuit_breaker_timeout_sec=0)
        gw = McpGateway(config=config)
        gw.register("srv-1", "http://a")
        gw.report_failure("srv-1")
        assert gw._servers["srv-1"].circuit == CircuitState.OPEN
        gw.health_check()
        assert gw._servers["srv-1"].circuit == CircuitState.HALF_OPEN

    def test_stats(self):
        gw = McpGateway()
        gw.register("srv-1", "http://a")
        stats = gw.stats()
        assert stats["total_servers"] == 1
        assert "error_rate" in stats
