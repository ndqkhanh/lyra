"""Network tool implementations — net_http, net_dns, net_ping.

Each tool uses only stdlib where possible, with optional enhanced backends.
"""
from __future__ import annotations

import socket
import subprocess
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


def net_http(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: str | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """Make an HTTP request and return response data."""
    req = Request(url, method=method.upper())
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if body is not None and method.upper() in ("POST", "PUT", "PATCH"):
        req.data = body.encode("utf-8")

    try:
        resp = urlopen(req, timeout=timeout)
        status = resp.status
        resp_headers = dict(resp.headers)
        content = resp.read().decode("utf-8", errors="replace")
    except URLError as e:
        return {
            "url": url,
            "method": method.upper(),
            "status": 0,
            "error": str(e.reason),
            "headers": {},
            "body": "",
        }

    return {
        "url": url,
        "method": method.upper(),
        "status": status,
        "headers": dict(list(resp_headers.items())[:30]),
        "body": content[:5000],
        "body_size": len(content),
    }


def net_dns(
    hostname: str,
    *,
    record_type: str = "A",
    timeout: int = 10,
) -> dict[str, Any]:
    """DNS lookup and resolution."""
    records: list[str] = []
    try:
        socket.setdefaulttimeout(timeout)
        result = socket.getaddrinfo(hostname, None)
        seen: set[str] = set()
        for _family, _socktype, _proto, _canonname, sockaddr in result:
            addr = sockaddr[0]
            if addr not in seen:
                seen.add(addr)
                records.append(addr)
    except socket.gaierror as e:
        return {
            "hostname": hostname,
            "record_type": record_type,
            "records": [],
            "error": str(e),
        }

    return {
        "hostname": hostname,
        "record_type": record_type,
        "records": records,
        "count": len(records),
    }


def net_ping(
    host: str,
    *,
    count: int = 4,
    timeout: int = 5,
) -> dict[str, Any]:
    """Check host reachability via system ping."""
    # Platform-aware ping
    is_darwin = __import__("sys").platform == "darwin"
    cmd = [
        "ping",
        "-c" if not is_darwin else "-c", str(count),
        "-W" if is_darwin else "-W", str(timeout),
        host,
    ]
    # Simplify: use common flags
    cmd = ["ping", "-c", str(count), "-t", str(timeout), host]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + count * 2,
        )
        reachable = result.returncode == 0

        # Parse stats from output
        times: list[float] = []
        for line in result.stdout.split("\n") + result.stderr.split("\n"):
            if "time=" in line:
                try:
                    t = float(line.split("time=")[1].split(" ")[0].rstrip("ms"))
                    times.append(t)
                except (ValueError, IndexError):
                    pass

        stats: dict[str, Any] = {"sent": count, "received": len(times)}
        if times:
            stats["min_ms"] = round(min(times), 2)
            stats["avg_ms"] = round(sum(times) / len(times), 2)
            stats["max_ms"] = round(max(times), 2)
        if result.returncode != 0 and not times:
            stats["received"] = 0

        return {
            "host": host,
            "reachable": reachable,
            "stats": stats,
        }
    except subprocess.TimeoutExpired:
        return {
            "host": host,
            "reachable": False,
            "stats": {"sent": count, "received": 0, "error": "timeout"},
        }
    except FileNotFoundError:
        return {
            "host": host,
            "reachable": False,
            "stats": {"sent": count, "received": 0, "error": "ping not available"},
        }


__all__ = ["net_http", "net_dns", "net_ping"]
