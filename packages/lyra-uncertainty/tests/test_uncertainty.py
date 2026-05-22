from lyra_uncertainty import UncertaintyEngine
class TestUncertaintyEngine:
    def test_predict(self):
        e = UncertaintyEngine()
        est = e.predict(0.85, evidence_count=100)
        assert est.uncertainty < 0.2
    def test_calibration(self):
        e = UncertaintyEngine()
        e.update_calibration(0.9, True)
        assert e.stats["calibration_samples"] == 1
