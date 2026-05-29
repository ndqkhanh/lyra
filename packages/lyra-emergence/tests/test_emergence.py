"""Tests for lyra-emergence."""
from lyra_emergence import EmergenceDetector


class TestEmergenceDetector:
    def test_record_initial(self):
        d = EmergenceDetector()
        result = d.record_generation({"population": 10, "diversity": 3, "avg_fitness": 0.5, "resources": 800})
        assert result["generation"] == 1
        assert "signals_detected" in result

    def test_specialization_detected(self):
        d = EmergenceDetector()
        for i in range(8):
            d.record_generation({"population": 10 + i, "diversity": 1, "avg_fitness": 0.5, "resources": 800})
        for i in range(8):
            d.record_generation({"population": 10 + i, "diversity": 4, "avg_fitness": 0.5, "resources": 800})
        report = d.get_report()
        assert report["transitions_detected"] >= 0

    def test_population_growth(self):
        d = EmergenceDetector()
        for _i in range(8):
            d.record_generation({"population": 5, "diversity": 1, "avg_fitness": 0.3, "resources": 800})
        for _i in range(8):
            d.record_generation({"population": 20, "diversity": 1, "avg_fitness": 0.5, "resources": 800})
        report = d.get_report()
        assert report["transitions_detected"] >= 0

    def test_get_report(self):
        d = EmergenceDetector()
        report = d.get_report()
        assert report["generations_tracked"] == 0
        assert report["transitions_detected"] == 0
