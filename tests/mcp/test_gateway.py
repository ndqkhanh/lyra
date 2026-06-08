"""Comprehensive tests for MCPEnterpriseGateway — enterprise-grade MCP gateway."""

from unittest.mock import patch

import pytest

from lyra.mcp.gateway import (
    AuthMethod,
    GatewayConfig,
    GatewayPolicy,
    GatewayStats,
    MCPEnterpriseGateway,
    RateLimitState,
    ServerRegistration,
    _match_glob,
    _now_ms,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def default_policy():
    return GatewayPolicy(
        allow=(),
        deny=(),
        requests_per_minute=60,
        max_concurrent=10,
        tool_timeout_ms=30000,
    )


@pytest.fixture
def gateway(default_policy):
    config = GatewayConfig(default_policy=default_policy)
    return MCPEnterpriseGateway(config=config)


@pytest.fixture
def sample_server():
    return ServerRegistration(
        server_id="svr-001",
        name="user-tools",
        url="http://localhost:8000/mcp",
    )


@pytest.fixture
def server_with_policy():
    return ServerRegistration(
        server_id="svr-002",
        name="admin-tools",
        url="http://localhost:9000/mcp",
        auth_method=AuthMethod.API_KEY,
        policy=GatewayPolicy(
            allow=("user-*",),
            deny=("admin-*", "delete-*"),
            requests_per_minute=30,
            max_concurrent=5,
            tool_timeout_ms=5000,
        ),
    )


# =============================================================================
# Tests: Module imports
# =============================================================================


def test_module_imports():
    from lyra import mcp
    assert mcp is not None


def test_gateway_module_exists():
    import lyra.mcp
    assert lyra.mcp is not None


# =============================================================================
# Tests: Enums
# =============================================================================


class TestAuthMethod:
    def test_values(self):
        assert AuthMethod.OAUTH21.name == "OAUTH21"
        assert AuthMethod.API_KEY.name == "API_KEY"
        assert AuthMethod.MTLS.name == "MTLS"
        assert AuthMethod.NONE.name == "NONE"

    def test_members(self):
        assert len(AuthMethod) == 4


# =============================================================================
# Tests: Data structures
# =============================================================================


class TestGatewayPolicy:
    def test_defaults(self):
        p = GatewayPolicy()
        assert p.allow == ()
        assert p.deny == ()
        assert p.requests_per_minute == 60
        assert p.max_concurrent == 10
        assert p.tool_timeout_ms == 30000

    def test_frozen(self):
        p = GatewayPolicy(allow=("read",))
        with pytest.raises(AttributeError):
            p.allow = ("write",)

    def test_custom_values(self):
        p = GatewayPolicy(
            allow=("read", "write"),
            deny=("admin",),
            requests_per_minute=10,
            max_concurrent=3,
            tool_timeout_ms=1000,
        )
        assert p.allow == ("read", "write")
        assert p.deny == ("admin",)
        assert p.requests_per_minute == 10
        assert p.max_concurrent == 3
        assert p.tool_timeout_ms == 1000


class TestServerRegistration:
    def test_minimal(self):
        s = ServerRegistration(server_id="s1", name="test", url="http://localhost")
        assert s.auth_method == AuthMethod.NONE
        assert s.policy is None
        assert s.health_check_url is None

    def test_full(self):
        policy = GatewayPolicy()
        s = ServerRegistration(
            server_id="s2",
            name="full",
            url="http://localhost:8080",
            auth_method=AuthMethod.MTLS,
            policy=policy,
            health_check_url="http://localhost:8080/healthz",
        )
        assert s.auth_method == AuthMethod.MTLS
        assert s.policy is policy
        assert s.health_check_url == "http://localhost:8080/healthz"

    def test_frozen(self):
        s = ServerRegistration(server_id="s3", name="frozen", url="http://localhost")
        with pytest.raises(AttributeError):
            s.server_id = "changed"


class TestGatewayConfig:
    def test_defaults(self):
        c = GatewayConfig()
        assert c.servers == ()
        assert c.auto_discovery is False
        assert c.default_policy.requests_per_minute == 60

    def test_full(self):
        policy = GatewayPolicy(requests_per_minute=100)
        servers = (
            ServerRegistration(server_id="s1", name="s1", url="http://localhost:1"),
            ServerRegistration(server_id="s2", name="s2", url="http://localhost:2"),
        )
        c = GatewayConfig(servers=servers, default_policy=policy, auto_discovery=True)
        assert len(c.servers) == 2
        assert c.auto_discovery is True
        assert c.default_policy.requests_per_minute == 100


class TestRateLimitState:
    def test_defaults(self):
        r = RateLimitState(server_id="s1")
        assert r.request_count == 0
        assert r.window_start_ms == 0

    def test_frozen(self):
        r = RateLimitState(server_id="s2", request_count=5, window_start_ms=1000)
        assert r.request_count == 5
        with pytest.raises(AttributeError):
            r.request_count = 10


class TestGatewayStats:
    def test_defaults(self):
        s = GatewayStats()
        assert s.total_requests == 0
        assert s.allowed == 0
        assert s.denied == 0
        assert s.active_servers == 0

    def test_values(self):
        s = GatewayStats(total_requests=100, allowed=80, denied=20, active_servers=3)
        assert s.total_requests == 100
        assert s.allowed == 80
        assert s.denied == 20
        assert s.active_servers == 3


# =============================================================================
# Tests: Utility functions
# =============================================================================


class TestNowMs:
    def test_returns_positive_int(self):
        ms = _now_ms()
        assert isinstance(ms, int)
        assert ms > 0


class TestMatchGlob:
    def test_exact_match(self):
        assert _match_glob(("user-list",), "user-list") is True

    def test_wildcard_match(self):
        assert _match_glob(("user-*",), "user-list") is True

    def test_no_match(self):
        assert _match_glob(("admin-*",), "user-list") is False

    def test_multiple_patterns(self):
        assert _match_glob(("read-*", "write-*"), "write-data") is True

    def test_empty_patterns(self):
        assert _match_glob((), "anything") is False

    def test_question_mark(self):
        assert _match_glob(("user-???",), "user-abc") is True


# =============================================================================
# Tests: MCPEnterpriseGateway — init
# =============================================================================


class TestInit:
    def test_default_init(self):
        gw = MCPEnterpriseGateway()
        assert gw._config is not None
        assert len(gw._registrations) == 0
        assert gw._total_requests == 0
        assert gw._allowed == 0
        assert gw._denied == 0

    def test_with_config_bootstraps_servers(self):
        server = ServerRegistration(
            server_id="init1",
            name="initial",
            url="http://localhost",
        )
        config = GatewayConfig(
            servers=(server,),
            default_policy=GatewayPolicy(),
        )
        gw = MCPEnterpriseGateway(config=config)
        assert "init1" in gw._registrations
        assert "init1" in gw._rate_states
        assert "init1" in gw._active_requests

    def test_with_auto_discovery(self):
        config = GatewayConfig(auto_discovery=True)
        gw = MCPEnterpriseGateway(config=config)
        assert len(gw._registrations) == 0

    def test_config_without_servers(self):
        config = GatewayConfig()
        gw = MCPEnterpriseGateway(config=config)
        assert len(gw._registrations) == 0


# =============================================================================
# Tests: Server lifecycle
# =============================================================================


class TestRegisterServer:
    def test_registers_new_server(self, gateway, sample_server):
        result = gateway.register_server(sample_server)
        assert result is sample_server
        assert "svr-001" in gateway._registrations
        assert "svr-001" in gateway._rate_states
        assert "svr-001" in gateway._active_requests

    def test_replaces_existing(self, gateway, sample_server):
        gateway.register_server(sample_server)
        replacement = ServerRegistration(
            server_id="svr-001",
            name="replacement",
            url="http://new-url",
        )
        gateway.register_server(replacement)
        assert gateway._registrations["svr-001"].name == "replacement"

    def test_with_existing_rate_state(self, gateway, sample_server):
        gateway.register_server(sample_server)
        gateway.register_server(sample_server)
        assert "svr-001" in gateway._rate_states


class TestUnregisterServer:
    def test_unregisters_existing(self, gateway, sample_server):
        gateway.register_server(sample_server)
        gateway.unregister_server("svr-001")
        assert "svr-001" not in gateway._registrations
        assert "svr-001" not in gateway._rate_states
        assert "svr-001" not in gateway._active_requests

    def test_unregister_unknown_silent(self, gateway):
        gateway.unregister_server("unknown")

    def test_unregister_then_register(self, gateway, sample_server):
        gateway.register_server(sample_server)
        gateway.unregister_server("svr-001")
        gateway.register_server(sample_server)
        assert "svr-001" in gateway._registrations


# =============================================================================
# Tests: Policy enforcement
# =============================================================================


class TestPolicyFor:
    def test_returns_server_policy(self, gateway, server_with_policy):
        gateway.register_server(server_with_policy)
        policy = gateway._policy_for("svr-002")
        assert policy.requests_per_minute == 30

    def test_falls_back_to_default(self, gateway, sample_server):
        gateway.register_server(sample_server)
        policy = gateway._policy_for("svr-001")
        assert policy.requests_per_minute == 60
        assert policy.max_concurrent == 10

    def test_unknown_server_returns_default(self, gateway):
        policy = gateway._policy_for("unknown")
        assert policy is gateway._default_policy


class TestCheckAccess:
    def test_unknown_server_denied(self, gateway):
        assert gateway.check_access("unknown", "tool") is False

    def test_allowed_by_default(self, gateway, sample_server):
        gateway.register_server(sample_server)
        assert gateway.check_access("svr-001", "any-tool") is True

    def test_denied_by_deny_list(self, gateway, server_with_policy):
        gateway.register_server(server_with_policy)
        assert gateway.check_access("svr-002", "admin-delete") is False

    def test_denied_not_in_allow_list(self, gateway, server_with_policy):
        gateway.register_server(server_with_policy)
        assert gateway.check_access("svr-002", "system-shutdown") is False

    def test_allowed_in_allow_list(self, gateway, server_with_policy):
        gateway.register_server(server_with_policy)
        assert gateway.check_access("svr-002", "user-list") is True

    def test_allowed_with_allow_and_not_denied(self, gateway, server_with_policy):
        gateway.register_server(server_with_policy)
        assert gateway.check_access("svr-002", "user-create") is True

    def test_deny_overrides_allow(self, gateway, server_with_policy):
        gateway.register_server(server_with_policy)
        assert gateway.check_access("svr-002", "admin-list") is False

    def test_tracks_denied_count(self, gateway):
        assert gateway._denied == 0
        gateway.check_access("unknown", "tool")
        assert gateway._denied == 1

    def test_tracks_allowed_count(self, gateway, sample_server):
        gateway.register_server(sample_server)
        gateway.check_access("svr-001", "tool")
        assert gateway._allowed == 1


class TestEnforcePolicy:
    def test_unknown_server(self, gateway):
        assert gateway.enforce_policy("unknown") is False

    def test_under_rate_limit(self, gateway, sample_server):
        gateway.register_server(sample_server)
        assert gateway.enforce_policy("svr-001") is True

    def test_rate_limit_exceeded(self, gateway):
        server = ServerRegistration(
            server_id="limited",
            name="limited",
            url="http://localhost",
            policy=GatewayPolicy(requests_per_minute=1, max_concurrent=10),
        )
        gateway.register_server(server)
        assert gateway.enforce_policy("limited") is True
        gateway.record_request("limited")
        assert gateway.enforce_policy("limited") is False

    def test_concurrency_exceeded(self, gateway):
        server = ServerRegistration(
            server_id="concurrent",
            name="concurrent",
            url="http://localhost",
            policy=GatewayPolicy(requests_per_minute=100, max_concurrent=1),
        )
        gateway.register_server(server)
        assert gateway.enforce_policy("concurrent") is True
        gateway._active_requests["concurrent"] = 1
        assert gateway.enforce_policy("concurrent") is False

    def test_window_reset_after_timeout(self, gateway, sample_server):
        gateway.register_server(sample_server)
        now = _now_ms()
        window_ms = 60_000
        gateway._rate_states["svr-001"] = RateLimitState(
            server_id="svr-001",
            request_count=999,
            window_start_ms=now - window_ms - 1000,
        )
        assert gateway.enforce_policy("svr-001") is True

    def test_rate_limit_zero(self, gateway):
        server = ServerRegistration(
            server_id="zero",
            name="zero",
            url="http://localhost",
            policy=GatewayPolicy(requests_per_minute=0, max_concurrent=10),
        )
        gateway.register_server(server)
        assert gateway.enforce_policy("zero") is False


class TestRecordRequest:
    def test_increments_count(self, gateway, sample_server):
        gateway.register_server(sample_server)
        state = gateway.record_request("svr-001")
        assert state.request_count == 1

    def test_starts_new_window_if_expired(self, gateway, sample_server):
        gateway.register_server(sample_server)
        now = _now_ms()
        gateway._rate_states["svr-001"] = RateLimitState(
            server_id="svr-001",
            request_count=100,
            window_start_ms=now - 120_000,
        )
        new_state = gateway.record_request("svr-001")
        assert new_state.request_count == 1

    def test_increments_active_requests(self, gateway, sample_server):
        gateway.register_server(sample_server)
        gateway.record_request("svr-001")
        assert gateway._active_requests["svr-001"] == 1

    def test_increments_total_requests(self, gateway, sample_server):
        gateway.register_server(sample_server)
        gateway.record_request("svr-001")
        assert gateway._total_requests == 1

    def test_unknown_server_raises(self, gateway):
        with pytest.raises(ValueError, match="is not registered"):
            gateway.record_request("unknown")


class TestReleaseRequest:
    def test_decrements_active_count(self, gateway, sample_server):
        gateway.register_server(sample_server)
        gateway._active_requests["svr-001"] = 5
        gateway.release_request("svr-001")
        assert gateway._active_requests["svr-001"] == 4

    def test_no_negative(self, gateway, sample_server):
        gateway.register_server(sample_server)
        gateway._active_requests["svr-001"] = 0
        gateway.release_request("svr-001")
        assert gateway._active_requests["svr-001"] == 0

    def test_unknown_server(self, gateway):
        gateway.release_request("unknown")


# =============================================================================
# Tests: Discovery
# =============================================================================


class TestDiscoverServers:
    def test_stub_returns_empty(self, gateway):
        result = gateway.discover_servers("https://discovery.example.com")
        assert result == []


class TestAutoDiscover:
    def test_called_on_init(self):
        config = GatewayConfig(auto_discovery=True)
        MCPEnterpriseGateway(config=config)


# =============================================================================
# Tests: Routing
# =============================================================================


class TestRouteRequest:
    def test_unknown_server(self, gateway):
        result = gateway.route_request("unknown", "tool", {})
        assert result["success"] is False
        assert "Unknown server" in result["error"]

    def test_successful_route(self, gateway, sample_server):
        gateway.register_server(sample_server)
        result = gateway.route_request("svr-001", "list-users", {})
        assert result["success"] is True
        assert result["server_id"] == "svr-001"
        assert result["tool"] == "list-users"

    def test_route_with_denied_tool(self, gateway, server_with_policy):
        gateway.register_server(server_with_policy)
        result = gateway.route_request("svr-002", "admin-delete", {})
        assert result["success"] is False
        assert "Access denied" in result["error"]

    def test_route_rate_limited(self, gateway):
        server = ServerRegistration(
            server_id="rate-limited-svr",
            name="rate-limited",
            url="http://localhost",
            policy=GatewayPolicy(requests_per_minute=1, max_concurrent=10),
        )
        gateway.register_server(server)
        gateway.route_request("rate-limited-svr", "tool1", {})
        result = gateway.route_request("rate-limited-svr", "tool2", {})
        assert result["success"] is False
        assert "Rate-limited" in result["error"]

    def test_route_includes_rate_state(self, gateway, sample_server):
        gateway.register_server(sample_server)
        result = gateway.route_request("svr-001", "tool", {})
        assert "rate_state" in result
        assert result["rate_state"]["request_count"] == 1

    def test_route_includes_timeout(self, gateway, sample_server):
        gateway.register_server(sample_server)
        result = gateway.route_request("svr-001", "tool", {})
        assert result["timeout_ms"] == 30000

    def test_route_increments_counters(self, gateway, sample_server):
        gateway.register_server(sample_server)
        gateway.route_request("svr-001", "tool", {})
        assert gateway._total_requests == 1
        assert gateway._allowed == 1

    def test_route_with_policy_timeout(self, gateway, server_with_policy):
        gateway.register_server(server_with_policy)
        result = gateway.route_request("svr-002", "user-list", {})
        assert result["timeout_ms"] == 5000


# =============================================================================
# Tests: Statistics
# =============================================================================


class TestGetStats:
    def test_initial_stats(self, gateway):
        stats = gateway.get_stats()
        assert stats.total_requests == 0
        assert stats.allowed == 0
        assert stats.denied == 0
        assert stats.active_servers == 0

    def test_after_operations(self, gateway, sample_server):
        gateway.register_server(sample_server)
        gateway.route_request("svr-001", "tool", {})
        stats = gateway.get_stats()
        assert stats.active_servers == 1
        assert stats.total_requests == 1
        assert stats.allowed == 1

    def test_after_denied(self, gateway):
        gateway.check_access("unknown", "tool")
        stats = gateway.get_stats()
        assert stats.denied == 1
        assert stats.total_requests == 0
