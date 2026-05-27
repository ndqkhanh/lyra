"""Tests for network tool implementations — net_http, net_dns, net_ping."""
from __future__ import annotations

from lyra_tools.network_ops import net_http, net_dns, net_ping


class TestNetHttp:
    def test_get_request_smoke(self) -> None:
        """Test HTTP GET to a known endpoint."""
        result = net_http("https://httpbin.org/get", timeout=10)
        assert "status" in result

    def test_post_request_with_body(self) -> None:
        result = net_http(
            "https://httpbin.org/post",
            method="POST",
            body='{"key": "value"}',
            timeout=10,
        )
        assert "status" in result

    def test_request_with_custom_headers(self) -> None:
        result = net_http(
            "https://httpbin.org/headers",
            headers={"X-Custom": "test-value"},
            timeout=10,
        )
        assert "status" in result

    def test_request_invalid_url(self) -> None:
        result = net_http("https://invalid.example.invalid/", timeout=5)
        assert "error" in result


class TestNetDns:
    def test_dns_lookup_localhost(self) -> None:
        result = net_dns("localhost")
        assert "127.0.0.1" in result["records"] or "::1" in result["records"]

    def test_dns_invalid_hostname(self) -> None:
        result = net_dns("this-host-does-not-exist-xyz.invalid")
        assert "error" in result or result["count"] == 0

    def test_dns_has_count(self) -> None:
        result = net_dns("localhost")
        assert result["count"] >= 1


class TestNetPing:
    def test_ping_localhost(self) -> None:
        result = net_ping("127.0.0.1", count=2, timeout=3)
        assert "reachable" in result
        assert result["reachable"] is True
        assert result["stats"]["received"] >= 1

    def test_ping_unreachable(self) -> None:
        result = net_ping("192.0.2.1", count=1, timeout=2)
        # 192.0.2.0/24 is reserved for TEST-NET, should be unreachable
        assert "reachable" in result
