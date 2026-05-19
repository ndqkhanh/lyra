"""
Lyra Testing - Testing and hardening suite.

This package provides:
- Performance benchmarks
- Security auditing
- Integration tests
"""

from lyra_testing.integration_tests import IntegrationTester, IntegrationTestResult
from lyra_testing.performance_benchmark import BenchmarkResult, PerformanceBenchmark
from lyra_testing.security_audit import (
    SecurityAuditor,
    SecurityAuditResult,
    SecurityIssue,
    SecuritySeverity,
)

__version__ = "0.1.0"

__all__ = [
    # Performance
    "PerformanceBenchmark",
    "BenchmarkResult",
    # Security
    "SecurityAuditor",
    "SecurityAuditResult",
    "SecurityIssue",
    "SecuritySeverity",
    # Integration
    "IntegrationTester",
    "IntegrationTestResult",
]
