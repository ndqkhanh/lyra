"""Tests for MCP Transport Pool."""
from __future__ import annotations

import pytest

from lyra_core.mcp.transport_pool import (
    ConnectionInfo,
    ConnectionState,
    PoolStats,
    PoolStatus,
    TransportConfig,
    TransportPool,
    TransportType,
)


class TestTransportPool:
    def test_add_server(self):
        pool = TransportPool()
        pool.add_server("github", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        assert "github" in pool.list_servers()

    def test_add_server_config_retrievable(self):
        pool = TransportPool()
        config = TransportConfig(
            transport_type=TransportType.STDIO,
            command="node",
            args=("server.js",),
        )
        pool.add_server("node-srv", config)
        retrieved = pool.get_server_config("node-srv")
        assert retrieved is not None
        assert retrieved.command == "node"
        assert retrieved.args == ("server.js",)

    def test_remove_server(self):
        pool = TransportPool()
        pool.add_server("temp", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        pool.acquire("temp")
        closed = pool.remove_server("temp")
        assert closed >= 0

    def test_remove_server_not_found(self):
        pool = TransportPool()
        closed = pool.remove_server("nonexistent")
        assert closed == 0

    def test_list_servers(self):
        pool = TransportPool()
        pool.add_server("a", TransportConfig(transport_type=TransportType.HTTP, url="http://a"))
        pool.add_server("b", TransportConfig(transport_type=TransportType.HTTP, url="http://b"))
        servers = pool.list_servers()
        assert len(servers) == 2

    def test_acquire_connection(self):
        pool = TransportPool()
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        conn = pool.acquire("srv")
        assert conn is not None
        assert conn.server_name == "srv"
        assert conn.state == ConnectionState.CONNECTING

    def test_acquire_connection_unknown_server(self):
        pool = TransportPool()
        conn = pool.acquire("ghost")
        assert conn is None

    def test_release_connection(self):
        pool = TransportPool()
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        conn = pool.acquire("srv")
        assert conn is not None
        released = pool.release(conn.connection_id)
        assert released is True

        info = pool.get_connection(conn.connection_id)
        assert info is not None
        assert info.state == ConnectionState.IDLE

    def test_release_nonexistent_connection(self):
        pool = TransportPool()
        released = pool.release("conn-fake")
        assert released is False

    def test_mark_error(self):
        pool = TransportPool()
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        conn = pool.acquire("srv")
        assert conn is not None

        pool.mark_error(conn.connection_id, "timeout")
        info = pool.get_connection(conn.connection_id)
        assert info is not None
        assert info.state == ConnectionState.ERROR
        assert info.error_message == "timeout"

    def test_close_connection(self):
        pool = TransportPool()
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        conn = pool.acquire("srv")
        assert conn is not None

        closed = pool.close_connection(conn.connection_id)
        assert closed is True

        info = pool.get_connection(conn.connection_id)
        assert info is not None
        assert info.state == ConnectionState.CLOSED

    def test_max_connections_per_server(self):
        pool = TransportPool(max_connections_per_server=2)
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        c1 = pool.acquire("srv")
        c2 = pool.acquire("srv")
        c3 = pool.acquire("srv")
        assert c1 is not None
        assert c2 is not None
        assert c3 is None

    def test_max_total_connections(self):
        pool = TransportPool(max_connections_per_server=2, max_total=3)
        pool.add_server("a", TransportConfig(transport_type=TransportType.HTTP, url="http://a"))
        pool.add_server("b", TransportConfig(transport_type=TransportType.HTTP, url="http://b"))

        pool.acquire("a")
        pool.acquire("a")
        pool.acquire("b")
        c4 = pool.acquire("b")
        assert c4 is None  # Total exhausted

    def test_get_stats(self):
        pool = TransportPool()
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        pool.acquire("srv")
        stats = pool.get_stats()
        assert stats.total_connections >= 1
        assert stats.active_connections + stats.idle_connections >= 1

    def test_get_stats_initial(self):
        pool = TransportPool()
        stats = pool.get_stats()
        assert stats.total_connections == 0
        assert stats.status == PoolStatus.SHUTDOWN

    def test_get_server_connections(self):
        pool = TransportPool()
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        pool.acquire("srv")
        conns = pool.get_server_connections("srv")
        assert len(conns) >= 1

    def test_get_server_connections_empty(self):
        pool = TransportPool()
        conns = pool.get_server_connections("ghost")
        assert len(conns) == 0

    def test_should_retry(self):
        pool = TransportPool()
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
            max_retries=3,
        ))
        conn = pool.acquire("srv")
        assert conn is not None
        pool.mark_error(conn.connection_id, "fail")
        assert pool.should_retry(conn.connection_id) is True

    def test_retry_delay_increases(self):
        pool = TransportPool(retry_base_delay=1.0, retry_backoff=2.0)
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
            max_retries=3,
        ))
        conn = pool.acquire("srv")
        assert conn is not None
        pool.mark_error(conn.connection_id)
        delay1 = pool.retry_delay(conn.connection_id)
        assert delay1 > 0.0
        assert delay1 < pool.retry_max_delay

    def test_retry_connection(self):
        pool = TransportPool()
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
            max_retries=3,
        ))
        conn = pool.acquire("srv")
        assert conn is not None
        pool.mark_error(conn.connection_id, "fail")
        retried = pool.retry_connection(conn.connection_id)
        assert retried is not None
        assert retried.state == ConnectionState.CONNECTING

    def test_shutdown(self):
        pool = TransportPool()
        pool.add_server("a", TransportConfig(transport_type=TransportType.HTTP, url="http://a"))
        pool.add_server("b", TransportConfig(transport_type=TransportType.HTTP, url="http://b"))
        pool.acquire("a")
        pool.acquire("b")
        count = pool.shutdown()
        assert count >= 2
        stats = pool.get_stats()
        assert stats.status == PoolStatus.SHUTDOWN

    def test_clear(self):
        pool = TransportPool()
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        pool.acquire("srv")
        pool.clear()
        assert len(pool.list_servers()) == 0
        assert pool.get_stats().total_connections == 0

    def test_connection_id_unique(self):
        pool = TransportPool()
        pool.add_server("a", TransportConfig(transport_type=TransportType.HTTP, url="http://a"))
        pool.add_server("b", TransportConfig(transport_type=TransportType.HTTP, url="http://b"))
        c1 = pool.acquire("a")
        c2 = pool.acquire("b")
        assert c1 is not None
        assert c2 is not None
        assert c1.connection_id != c2.connection_id

    def test_release_then_reacquire(self):
        pool = TransportPool()
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        conn = pool.acquire("srv")
        assert conn is not None
        pool.release(conn.connection_id)

        # Re-acquire should get the same idle connection
        conn2 = pool.acquire("srv")
        assert conn2 is not None
        assert conn2.connection_id == conn.connection_id

    def test_reap_idle_connections(self):
        pool = TransportPool(connection_ttl=0.0)
        pool.add_server("srv", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        conn = pool.acquire("srv")
        assert conn is not None
        pool.release(conn.connection_id)
        reaped = pool.reap_idle_connections()
        assert reaped >= 1

    def test_get_server_config_missing(self):
        pool = TransportPool()
        assert pool.get_server_config("ghost") is None

    def test_transport_config_defaults(self):
        config = TransportConfig(transport_type=TransportType.HTTP, url="http://example.com")
        assert config.command == ""
        assert config.args == ()
        assert config.headers == ()
        assert config.connect_timeout == 10.0
        assert config.idle_timeout == 300.0
        assert config.max_retries == 3


class TestTransportConfig:
    def test_http_config(self):
        config = TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
            headers=(("Authorization", "Bearer token"),),
            connect_timeout=5.0,
        )
        assert config.transport_type == TransportType.HTTP
        assert config.url == "http://localhost:8080"
        assert len(config.headers) == 1
        assert config.connect_timeout == 5.0

    def test_stdio_config(self):
        config = TransportConfig(
            transport_type=TransportType.STDIO,
            command="python",
            args=("-m", "my_mcp_server"),
        )
        assert config.transport_type == TransportType.STDIO
        assert config.command == "python"
        assert len(config.args) == 2

    def test_frozen_dataclass(self):
        config = TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        )
        with pytest.raises(Exception):
            config.url = "http://other"  # type: ignore[misc]


class TestConnectionInfo:
    def test_connection_info_fields(self):
        import time
        now = time.monotonic()
        info = ConnectionInfo(
            connection_id="conn-001",
            server_name="test",
            transport_type=TransportType.HTTP,
            state=ConnectionState.IDLE,
            created_at=now,
            last_used_at=now,
        )
        assert info.connection_id == "conn-001"
        assert info.server_name == "test"
        assert info.state == ConnectionState.IDLE

    def test_connection_info_frozen(self):
        import time
        info = ConnectionInfo(
            connection_id="c1",
            server_name="s",
            transport_type=TransportType.HTTP,
            state=ConnectionState.IDLE,
            created_at=time.monotonic(),
            last_used_at=time.monotonic(),
        )
        with pytest.raises(Exception):
            info.state = ConnectionState.ACTIVE  # type: ignore[misc]


class TestPoolStats:
    def test_pool_stats_defaults(self):
        stats = PoolStats()
        assert stats.total_connections == 0
        assert stats.active_connections == 0
        assert stats.status == PoolStatus.HEALTHY
        assert stats.uptime_seconds == 0.0

    def test_pool_stats_exhausted(self):
        stats = PoolStats(
            total_connections=50,
            active_connections=50,
            status=PoolStatus.EXHAUSTED,
        )
        assert stats.status == PoolStatus.EXHAUSTED
