"""Tests for testing and hardening suite."""

import pytest

from lyra_testing import (
    IntegrationTester,
    PerformanceBenchmark,
    SecurityAuditor,
    SecuritySeverity,
)


def test_performance_benchmark_init():
    """Test performance benchmark initialization."""
    benchmark = PerformanceBenchmark()
    assert len(benchmark.results) == 0


def test_performance_benchmark_token_compression():
    """Test token compression benchmark."""
    benchmark = PerformanceBenchmark()

    result = benchmark.benchmark_token_compression()

    assert result.benchmark_name == "token_compression"
    assert result.operations_per_second > 0


def test_performance_benchmark_model_routing():
    """Test model routing benchmark."""
    benchmark = PerformanceBenchmark()

    result = benchmark.benchmark_model_routing()

    assert result.benchmark_name == "model_routing"
    assert result.avg_latency_ms < 1.0


def test_performance_benchmark_all():
    """Test running all benchmarks."""
    benchmark = PerformanceBenchmark()

    summary = benchmark.run_all_benchmarks()

    assert summary["total_benchmarks"] == 4
    assert summary["total_ops_per_second"] > 0


def test_performance_score():
    """Test performance score calculation."""
    benchmark = PerformanceBenchmark()

    benchmark.run_all_benchmarks()
    score = benchmark.get_performance_score()

    assert 0 <= score <= 100


def test_security_auditor_init():
    """Test security auditor initialization."""
    auditor = SecurityAuditor()
    assert len(auditor.checklist) > 0


def test_security_audit_package():
    """Test package security audit."""
    auditor = SecurityAuditor()

    result = auditor.audit_package("lyra-memory")

    assert result.total_checks > 0
    assert result.security_score >= 0


def test_security_audit_all_packages():
    """Test auditing all packages."""
    auditor = SecurityAuditor()

    results = auditor.audit_all_packages()

    assert len(results) == 9  # 9 packages
    assert all(r.security_score >= 0 for r in results.values())


def test_security_audit_summary():
    """Test security audit summary."""
    auditor = SecurityAuditor()

    results = auditor.audit_all_packages()
    summary = auditor.get_summary(results)

    assert summary["total_packages"] == 9
    assert summary["avg_security_score"] >= 0


def test_integration_tester_init():
    """Test integration tester initialization."""
    tester = IntegrationTester()
    assert len(tester.results) == 0


def test_integration_memory_compression():
    """Test memory to compression integration."""
    tester = IntegrationTester()

    result = tester.test_memory_to_compression()

    assert result.passed is True
    assert result.duration_ms > 0


def test_integration_oauth_memory():
    """Test OAuth to memory integration."""
    tester = IntegrationTester()

    result = tester.test_oauth_to_memory()

    assert result.passed is True


def test_integration_all_tests():
    """Test running all integration tests."""
    tester = IntegrationTester()

    summary = tester.run_all_tests()

    assert summary["total_tests"] == 5
    assert summary["pass_rate"] == 100.0


def test_integration_failed_tests():
    """Test getting failed tests."""
    tester = IntegrationTester()

    tester.run_all_tests()
    failed = tester.get_failed_tests()

    assert len(failed) == 0  # All tests should pass
