"""Tests for lyra-climate."""
from lyra_climate import ClimateAgent
class TestClimateAgent:
    def test_record_emission(self):
        c = ClimateAgent(); r = c.record_emission("factory", 500.0, 2026)
        assert r.co2_tons == 500.0
    def test_suggestions(self):
        c = ClimateAgent(); s = c.suggest_reduction(1000)
        assert len(s) > 0
