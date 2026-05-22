"""Tests for lyra-devops."""
from lyra_devops import DevOpsAgent, IncidentSeverity


class TestDevOpsAgent:
    def test_record_metric(self):
        d = DevOpsAgent()
        d.record_metric("cpu_usage", 85.0)
        assert "cpu_usage" in d.metrics

    def test_detect_anomaly(self):
        d = DevOpsAgent()
        for _ in range(10):
            d.record_metric("error_rate", 250.0)
        incident = d.detect_anomaly("error_rate", threshold=80.0)
        assert incident is not None
        assert incident.severity == IncidentSeverity.CRITICAL

    def test_diagnose(self):
        d = DevOpsAgent()
        for _ in range(10):
            d.record_metric("latency", 5000.0)
        inci = d.detect_anomaly("latency", threshold=1000.0)
        diag = d.diagnose(inci.id)
        assert diag is not None
        assert "Root cause" in diag

    def test_remediate(self):
        d = DevOpsAgent()
        for _ in range(10):
            d.record_metric("memory", 95.0)
        inci = d.detect_anomaly("memory", threshold=80.0)
        action = d.remediate(inci.id, strategy="scale")
        assert action is not None
        assert "scaling" in action.lower()

    def test_health_check(self):
        d = DevOpsAgent()
        result = d.health_check()
        assert "active_incidents" in result
        assert result["monitored_metrics"] == 0
