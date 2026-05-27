"""Tests for observability health check tool."""
from __future__ import annotations

from lyra_tools.obs_health import obs_health


class TestObsHealth:
    def test_returns_status(self) -> None:
        result = obs_health()
        assert "status" in result
        assert result["status"] in ("healthy", "degraded", "unhealthy")

    def test_has_runtime_info(self) -> None:
        result = obs_health()
        assert "runtime" in result
        runtime = result["runtime"]
        assert "python_version" in runtime
        assert "hostname" in runtime

    def test_has_disk_info(self) -> None:
        result = obs_health()
        assert "disk" in result
        assert "path" in result["disk"]

    def test_has_git_context(self) -> None:
        result = obs_health()
        assert "git" in result
        assert "repository" in result["git"]

    def test_has_timestamp(self) -> None:
        result = obs_health()
        assert "timestamp" in result
        assert isinstance(result["timestamp"], float)

    def test_issues_is_list(self) -> None:
        result = obs_health()
        assert isinstance(result["issues"], list)

    def test_uptime_field_present(self) -> None:
        result = obs_health()
        assert "uptime_seconds" in result
