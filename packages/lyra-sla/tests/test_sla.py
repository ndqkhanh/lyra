"""Tests for lyra-sla."""
from lyra_sla import SLAManager, AgentSLA


class TestSLAManager:
    def test_set_and_check_compliance(self):
        sla = SLAManager()
        sla.set_sla("agent_1", AgentSLA(response_time_p99_ms=5000))
        sla.record_metric("agent_1", "latency_ms", 100)
        result = sla.check_compliance("agent_1")
        assert "compliant" in result

    def test_no_sla_no_violation(self):
        sla = SLAManager()
        result = sla.check_compliance("unknown")
        assert result["compliant"]

    def test_summary(self):
        sla = SLAManager()
        assert sla.summary["total_violations"] == 0
