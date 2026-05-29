"""Tests for lyra-ecology."""
from lyra_ecology import AgentEcology, EmergenceDetector


class TestAgentEcology:
    def test_seed_and_step(self):
        eco = AgentEcology()
        eco.seed(count=10)
        assert len(eco.agents) == 10
        snapshot = eco.step()
        assert snapshot["generation"] == 1
        assert snapshot["population"] >= 0

    def test_run_generations(self):
        eco = AgentEcology()
        eco.seed(count=10)
        history = eco.run(generations=20)
        assert len(history) == 20

    def test_specialization_emerges(self):
        eco = AgentEcology()
        eco.seed(count=10)
        for _ in range(50):
            eco.step()
        specializations = {a.specialization for a in eco.agents}
        assert len(specializations) >= 1


class TestEmergenceDetector:
    def test_scan_early(self):
        eco = AgentEcology()
        eco.seed(count=5)
        detector = EmergenceDetector()
        result = detector.scan(eco)
        assert "emergence_detected" in result

    def test_scan_late(self):
        eco = AgentEcology()
        eco.seed(count=10)
        for _ in range(20):
            eco.step()
        detector = EmergenceDetector()
        result = detector.scan(eco)
        assert "emergence_detected" in result
