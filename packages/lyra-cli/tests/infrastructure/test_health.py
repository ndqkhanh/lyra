"""Tests for infrastructure health check system."""

from __future__ import annotations

from lyra_cli.infrastructure.health import (
    HealthCheck,
    HealthCheckRegistry,
    HealthCheckResult,
    HealthStatus,
    create_default_health_checks,
)


class TestHealthCheckResult:
    """Tests for HealthCheckResult."""

    def test_health_check_result_creation(self):
        """Test creating a health check result."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="All systems operational",
        )

        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All systems operational"
        assert result.is_healthy()

    def test_health_check_result_to_dict(self):
        """Test converting result to dictionary."""
        result = HealthCheckResult(
            status=HealthStatus.DEGRADED,
            message="Service degraded",
            details={"reason": "high latency"},
        )

        result_dict = result.to_dict()
        assert result_dict["status"] == "degraded"
        assert result_dict["message"] == "Service degraded"
        assert result_dict["details"]["reason"] == "high latency"


class TestHealthCheck:
    """Tests for HealthCheck."""

    def test_health_check_execution(self):
        """Test executing a health check."""
        def check_func():
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="OK",
            )

        check = HealthCheck("test_check", check_func)
        result = check.execute()

        assert result.status == HealthStatus.HEALTHY
        assert result.message == "OK"

    def test_health_check_error_handling(self):
        """Test health check handles errors."""
        def failing_check():
            raise ValueError("Check failed")

        check = HealthCheck("test_check", failing_check)
        result = check.execute()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Check failed" in result.message

    def test_health_check_last_result(self):
        """Test getting last check result."""
        def check_func():
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="OK",
            )

        check = HealthCheck("test_check", check_func)
        check.execute()

        last_result = check.get_last_result()
        assert last_result is not None
        assert last_result.status == HealthStatus.HEALTHY

    def test_health_check_critical_flag(self):
        """Test critical flag."""
        def check_func():
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="OK",
            )

        critical_check = HealthCheck("critical", check_func, critical=True)
        non_critical_check = HealthCheck("non_critical", check_func, critical=False)

        assert critical_check.critical is True
        assert non_critical_check.critical is False


class TestHealthCheckRegistry:
    """Tests for HealthCheckRegistry."""

    def test_register_health_check(self):
        """Test registering a health check."""
        registry = HealthCheckRegistry()

        def check_func():
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="OK",
            )

        check = HealthCheck("test_check", check_func)
        registry.register(check)

        results = registry.check_all()
        assert "test_check" in results

    def test_register_simple_check(self):
        """Test registering a simple boolean check."""
        registry = HealthCheckRegistry()

        registry.register_simple(
            "simple_check",
            lambda: True,
        )

        results = registry.check_all()
        assert "simple_check" in results
        assert results["simple_check"].status == HealthStatus.HEALTHY

    def test_check_all(self):
        """Test checking all health checks."""
        registry = HealthCheckRegistry()

        registry.register_simple("check1", lambda: True)
        registry.register_simple("check2", lambda: True)
        registry.register_simple("check3", lambda: False)

        results = registry.check_all()
        assert len(results) == 3
        assert results["check1"].status == HealthStatus.HEALTHY
        assert results["check2"].status == HealthStatus.HEALTHY
        assert results["check3"].status == HealthStatus.UNHEALTHY

    def test_check_readiness(self):
        """Test readiness checks."""
        registry = HealthCheckRegistry()

        registry.register_simple(
            "readiness_check",
            lambda: True,
            readiness=True,
            liveness=False,
        )

        registry.register_simple(
            "liveness_check",
            lambda: True,
            readiness=False,
            liveness=True,
        )

        readiness_results = registry.check_readiness()
        assert "readiness_check" in readiness_results
        assert "liveness_check" not in readiness_results

    def test_check_liveness(self):
        """Test liveness checks."""
        registry = HealthCheckRegistry()

        registry.register_simple(
            "readiness_check",
            lambda: True,
            readiness=True,
            liveness=False,
        )

        registry.register_simple(
            "liveness_check",
            lambda: True,
            readiness=False,
            liveness=True,
        )

        liveness_results = registry.check_liveness()
        assert "liveness_check" in liveness_results
        assert "readiness_check" not in liveness_results

    def test_get_overall_status_healthy(self):
        """Test overall status when all checks are healthy."""
        registry = HealthCheckRegistry()

        registry.register_simple("check1", lambda: True)
        registry.register_simple("check2", lambda: True)

        status = registry.get_overall_status()
        assert status == HealthStatus.HEALTHY

    def test_get_overall_status_unhealthy(self):
        """Test overall status when critical check fails."""
        registry = HealthCheckRegistry()

        registry.register_simple("critical_check", lambda: False, critical=True)
        registry.register_simple("other_check", lambda: True)

        status = registry.get_overall_status()
        assert status == HealthStatus.UNHEALTHY

    def test_get_overall_status_degraded(self):
        """Test overall status when non-critical check fails."""
        registry = HealthCheckRegistry()

        registry.register_simple("critical_check", lambda: True, critical=True)
        registry.register_simple("non_critical_check", lambda: False, critical=False)

        status = registry.get_overall_status()
        assert status == HealthStatus.DEGRADED

    def test_get_health_report(self):
        """Test getting comprehensive health report."""
        registry = HealthCheckRegistry()

        registry.register_simple("check1", lambda: True)
        registry.register_simple("check2", lambda: False)

        report = registry.get_health_report()

        assert "status" in report
        assert "timestamp" in report
        assert "checks" in report
        assert "summary" in report
        assert report["summary"]["total"] == 2
        assert report["summary"]["healthy"] == 1
        assert report["summary"]["unhealthy"] == 1

    def test_get_readiness_report(self):
        """Test getting readiness report."""
        registry = HealthCheckRegistry()

        registry.register_simple("check1", lambda: True, readiness=True)

        report = registry.get_readiness_report()

        assert "ready" in report
        assert "status" in report
        assert "checks" in report
        assert report["ready"] is True

    def test_get_liveness_report(self):
        """Test getting liveness report."""
        registry = HealthCheckRegistry()

        registry.register_simple("check1", lambda: True, liveness=True)

        report = registry.get_liveness_report()

        assert "alive" in report
        assert "status" in report
        assert "checks" in report
        assert report["alive"] is True


class TestDefaultHealthChecks:
    """Tests for default health checks."""

    def test_create_default_health_checks(self):
        """Test creating default health checks."""
        registry = create_default_health_checks()

        # Should have system and disk checks
        results = registry.check_all()
        assert "system" in results
        assert "disk" in results

    def test_system_health_check(self):
        """Test system health check."""
        registry = create_default_health_checks()

        results = registry.check_all()
        system_result = results["system"]

        # Should have CPU and memory details
        assert "cpu_percent" in system_result.details
        assert "memory_percent" in system_result.details

    def test_disk_health_check(self):
        """Test disk health check."""
        registry = create_default_health_checks()

        results = registry.check_all()
        disk_result = results["disk"]

        # Should have disk usage details
        assert "percent_used" in disk_result.details
        assert "free_gb" in disk_result.details
