"""Tests for src/mcp/anx_decoupler.py and streamable_http.py."""
from __future__ import annotations

import json
import pytest

from lyra.mcp.anx_decoupler import (
    ANXDecoupler,
    ToolSpec,
    ExecutePayload,
    ExplainPayload,
    ExaminePayload,
    DecoupledMessage,
    ANXStats,
    ANX_PROTOCOL_VERSION,
)
from lyra.mcp.streamable_http import (
    StreamableHTTPTransport,
    SSEEvent,
    SSEEventType,
    Connection,
    ConnectionPool,
    PoolConfig,
    compute_backoff_delay,
    ReconnectPolicy,
)


# =========================================================================
# ANX Decoupler tests
# =========================================================================


class TestToolSpec:
    def test_minimal_spec(self):
        spec = ToolSpec(tool_id="search", name="Search", description="Web search")
        assert spec.tool_id == "search"
        assert spec.version == "1.0.0"

    def test_full_spec(self):
        spec = ToolSpec(
            tool_id="code",
            name="Code Exec",
            description="Run code",
            parameters={"language": {"type": "string"}},
            examples=[{"input": "print(1)", "output": "1"}],
            return_schema={"type": "string"},
            version="2.0.0",
        )
        assert spec.parameters["language"]["type"] == "string"
        assert len(spec.examples) == 1


class TestANXStats:
    def test_default_stats(self):
        stats = ANXStats()
        assert stats.execute_count == 0
        assert stats.explain_count == 0
        assert stats.examine_count == 0
        assert stats.tokens_saved_estimate == 0
        assert stats.total_messages == 0


class TestANXDecoupler:
    def test_register_tool(self):
        decoupler = ANXDecoupler()
        spec = ToolSpec(tool_id="search", name="Web Search", description="Search tool")
        decoupler.register_tool(spec)
        assert "search" in decoupler.get_tool_ids()

    def test_unregister_tool(self):
        decoupler = ANXDecoupler()
        spec = ToolSpec(tool_id="temp", name="Temp", description="Temporary tool")
        decoupler.register_tool(spec)
        assert decoupler.unregister_tool("temp") is True
        assert decoupler.unregister_tool("nonexistent") is False

    def test_create_execute(self):
        decoupler = ANXDecoupler()
        decoupler.register_tool(ToolSpec(tool_id="search", name="Search", description=""))
        payload = decoupler.create_execute("search", {"query": "hello"})
        assert isinstance(payload, ExecutePayload)
        assert payload.tool_id == "search"
        assert payload.params["query"] == "hello"
        assert len(payload.correlation_id) == 16

    def test_create_execute_unregistered_raises(self):
        decoupler = ANXDecoupler()
        with pytest.raises(ValueError, match="not registered"):
            decoupler.create_execute("unknown_tool")

    def test_explain_tool(self):
        decoupler = ANXDecoupler()
        spec = ToolSpec(
            tool_id="search",
            name="Web Search",
            description="Performs web searches",
            parameters={"q": {"type": "string"}},
        )
        decoupler.register_tool(spec)
        payload = decoupler.explain_tool("search", reason="first use")
        assert isinstance(payload, ExplainPayload)
        assert payload.tool_id == "search"
        assert payload.spec is not None
        assert payload.spec.name == "Web Search"
        assert payload.reason == "first use"

    def test_explain_tool_unregistered_raises(self):
        decoupler = ANXDecoupler()
        with pytest.raises(ValueError, match="not registered"):
            decoupler.explain_tool("unknown")

    def test_examine_response_json(self):
        decoupler = ANXDecoupler()
        decoupler.register_tool(ToolSpec(tool_id="search", name="S", description=""))
        payload = decoupler.examine_response(
            "search", '{"results": ["a", "b"], "count": 2}',
        )
        assert isinstance(payload, ExaminePayload)
        assert payload.parsed_result["results"] == ["a", "b"]
        assert payload.parse_error == ""

    def test_examine_response_invalid_json(self):
        decoupler = ANXDecoupler()
        decoupler.register_tool(ToolSpec(tool_id="search", name="S", description=""))
        payload = decoupler.examine_response("search", "not-json-at-all")
        assert payload.parse_error != ""
        assert "raw" in payload.parsed_result

    def test_examine_response_custom_parser(self):
        decoupler = ANXDecoupler()
        decoupler.register_tool(ToolSpec(tool_id="custom", name="C", description=""))

        def my_parser(raw: str) -> dict:
            return {"parsed": raw.upper()}

        decoupler.register_parser("custom", my_parser)
        payload = decoupler.examine_response("custom", "hello")
        assert payload.parsed_result["parsed"] == "HELLO"
        assert payload.parse_error == ""

    def test_register_parser_error(self):
        decoupler = ANXDecoupler()
        decoupler.register_tool(ToolSpec(tool_id="broken", name="B", description=""))

        def broken_parser(raw: str) -> dict:
            raise ValueError("parse failed")

        decoupler.register_parser("broken", broken_parser)
        payload = decoupler.examine_response("broken", "data")
        assert payload.parse_error != ""

    def test_decouple_request_with_explain(self):
        decoupler = ANXDecoupler()
        decoupler.register_tool(ToolSpec(tool_id="calc", name="Calc", description="Calculator"))
        msg = decoupler.decouple_request({
            "tool_id": "calc",
            "params": {"expr": "1+1"},
            "explain": True,
        })
        assert isinstance(msg, DecoupledMessage)
        assert msg.execute is not None
        assert msg.execute.params["expr"] == "1+1"
        assert msg.explain is not None
        assert msg.explain.spec.name == "Calc"

    def test_decouple_request_with_examine(self):
        decoupler = ANXDecoupler()
        decoupler.register_tool(ToolSpec(tool_id="calc", name="Calc", description=""))
        msg = decoupler.decouple_request({
            "tool_id": "calc",
            "params": {"expr": "1+1"},
            "raw_response": '{"result": 2}',
        })
        assert msg.examine is not None
        assert msg.examine.parsed_result["result"] == 2

    def test_decouple_request_minimal(self):
        decoupler = ANXDecoupler()
        decoupler.register_tool(ToolSpec(tool_id="ping", name="Ping", description=""))
        msg = decoupler.decouple_request({"tool_id": "ping"})
        assert msg.execute is not None
        assert msg.execute.tool_id == "ping"
        assert msg.explain is None
        assert msg.examine is None

    def test_protocol_version(self):
        assert ANX_PROTOCOL_VERSION == "1.0.0"

    def test_stats_tracking(self):
        decoupler = ANXDecoupler()
        decoupler.register_tool(ToolSpec(tool_id="st", name="StatsTest", description=""))
        decoupler.create_execute("st")
        decoupler.create_execute("st")
        decoupler.explain_tool("st")
        decoupler.examine_response("st", "{}")
        stats = decoupler.stats
        assert stats.execute_count == 2
        assert stats.explain_count == 1
        assert stats.examine_count == 1
        assert stats.tokens_saved_estimate > 0
        assert stats.tools_registered == 1

    def test_reset_stats(self):
        decoupler = ANXDecoupler()
        decoupler.register_tool(ToolSpec(tool_id="rs", name="Reset", description=""))
        decoupler.create_execute("rs")
        decoupler.reset_stats()
        assert decoupler.stats.execute_count == 0


# =========================================================================
# Streamable HTTP tests
# =========================================================================


class TestSSEEvent:
    def test_create_event(self):
        event = SSEEvent(
            event_type=SSEEventType.TOOL_START,
            data={"tool": "search"},
            server_id="srv1",
        )
        assert event.event_type == SSEEventType.TOOL_START
        assert event.server_id == "srv1"
        assert event.event_id.startswith("tool_start_")

    def test_serialize(self):
        event = SSEEvent(
            event_type=SSEEventType.TOOL_PROGRESS,
            data={"progress": 0.5},
            event_id="evt_001",
        )
        text = event.serialize()
        assert "event: tool_progress" in text
        assert 'data: {"progress": 0.5}' in text
        assert "id: evt_001" in text

    def test_auto_id(self):
        event = SSEEvent(event_type=SSEEventType.HEARTBEAT)
        assert len(event.event_id) > 0


class TestConnectionPool:
    def test_acquire_creates_connection(self):
        pool = ConnectionPool()
        conn = pool.acquire("srv1", "http://localhost:8000/mcp")
        assert isinstance(conn, Connection)
        assert conn.server_id == "srv1"
        assert pool.total_count == 1

    def test_max_per_server(self):
        pool = ConnectionPool(PoolConfig(max_connections=2))
        pool.acquire("srv1", "http://localhost:1")
        pool.acquire("srv1", "http://localhost:1")
        with pytest.raises(RuntimeError, match="Max connections"):
            pool.acquire("srv1", "http://localhost:1")

    def test_release_and_remove(self):
        pool = ConnectionPool()
        conn = pool.acquire("srv1", "http://localhost:1")
        pool.release(conn)
        assert pool.total_count == 1
        pool.remove(conn)
        assert pool.total_count == 0

    def test_mark_unhealthy(self):
        pool = ConnectionPool()
        conn = pool.acquire("srv1", "http://localhost:1")
        assert conn.is_healthy is True
        pool.mark_unhealthy(conn)
        assert conn.is_healthy is False
        assert conn.error_count == 1

    def test_health_check_removes_unhealthy(self):
        pool = ConnectionPool()
        conn = pool.acquire("srv1", "http://localhost:1")
        pool.mark_unhealthy(conn)
        pool.mark_unhealthy(conn)
        pool.mark_unhealthy(conn)
        removed = pool.health_check()
        assert removed >= 1
        pool2 = ConnectionPool()
        removed2 = pool2.health_check()
        assert removed2 == 0

    def test_get_stats(self):
        pool = ConnectionPool()
        pool.acquire("srv1", "http://localhost:1")
        pool.acquire("srv2", "http://localhost:2")
        stats = pool.get_stats()
        assert stats["total_connections"] == 2
        assert "srv1" in stats["servers"]
        assert stats["servers"]["srv1"]["active"] == 1


class TestComputeBackoffDelay:
    def test_initial_delay(self):
        delay = compute_backoff_delay(0)
        assert delay >= 0.9  # base 1.0 with jitter
        assert delay <= 1.1

    def test_exponential_increase(self):
        d1 = compute_backoff_delay(0, ReconnectPolicy(jitter_factor=0.0))
        d2 = compute_backoff_delay(1, ReconnectPolicy(jitter_factor=0.0))
        d3 = compute_backoff_delay(2, ReconnectPolicy(jitter_factor=0.0))
        assert abs(d2 - d1 * 2) < 0.01
        assert abs(d3 - d1 * 4) < 0.01

    def test_max_delay_cap(self):
        delay = compute_backoff_delay(
            10,
            ReconnectPolicy(base_delay_s=1.0, max_delay_s=5.0, jitter_factor=0.0),
        )
        assert delay <= 5.0

    def test_jitter(self):
        delays = [
            compute_backoff_delay(0, ReconnectPolicy(jitter_factor=0.5))
            for _ in range(50)
        ]
        # With jitter, delays should vary
        assert max(delays) > min(delays)


class TestStreamableHTTPTransport:
    def test_register_server(self):
        transport = StreamableHTTPTransport()
        transport.register_server("search", "http://localhost:8000/mcp")
        assert "search" in transport.registered_servers

    def test_unregister_server(self):
        transport = StreamableHTTPTransport()
        transport.register_server("tmp", "http://localhost:1")
        transport.unregister_server("tmp")
        assert "tmp" not in transport.registered_servers

    def test_generate_event(self):
        transport = StreamableHTTPTransport()
        event = transport.generate_event(
            SSEEventType.TOOL_START,
            {"tool": "search"},
            server_id="srv1",
        )
        assert isinstance(event, SSEEvent)
        assert event.event_type == SSEEventType.TOOL_START

    def test_event_callbacks(self):
        transport = StreamableHTTPTransport()
        received = []
        transport.on_event(lambda e: received.append(e))
        transport.generate_event(SSEEventType.HEARTBEAT, {}, server_id="s")
        assert len(received) == 1
        assert received[0].event_type == SSEEventType.HEARTBEAT

    def test_remove_event_callback(self):
        transport = StreamableHTTPTransport()
        def cb(e): pass
        transport.on_event(cb)
        transport.remove_event_callback(cb)
        # Should not raise

    def test_stream_unregistered_server(self):
        transport = StreamableHTTPTransport()
        import asyncio
        events = asyncio.run(
            transport.stream_tool_execution("unknown", "tool", {}),
        )
        assert len(events) == 1
        assert events[0].event_type == SSEEventType.TOOL_ERROR
        assert "not registered" in events[0].data["error"]

    def test_stream_registered_server(self):
        transport = StreamableHTTPTransport()
        transport.register_server("test-srv", "http://localhost:9999/mcp")
        import asyncio
        events = asyncio.run(
            transport.stream_tool_execution(
                "test-srv", "my_tool", {"param": "value", "_simulated_steps": 2},
            ),
        )
        assert len(events) > 0
        # Should have start + progress + heartbeat + complete
        event_types = [e.event_type for e in events]
        assert SSEEventType.TOOL_START in event_types
        assert SSEEventType.TOOL_PROGRESS in event_types
        assert SSEEventType.TOOL_COMPLETE in event_types


class TestConnection:
    def test_is_idle(self):
        import time
        conn = Connection(server_id="s", url="http://localhost")
        conn.last_used_at = time.time() - 120  # 2 minutes ago
        assert conn.is_idle

    def test_not_idle(self):
        import time
        conn = Connection(server_id="s", url="http://localhost")
        conn.last_used_at = time.time()  # just used
        assert not conn.is_idle


class TestPoolConfig:
    def test_defaults(self):
        config = PoolConfig()
        assert config.max_connections == 5
        assert config.max_total_connections == 20
        assert config.connection_timeout_s == 10.0

    def test_custom(self):
        config = PoolConfig(max_connections=10, max_total_connections=50)
        assert config.max_connections == 10
        assert config.max_total_connections == 50
