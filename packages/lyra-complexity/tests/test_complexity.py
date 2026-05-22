
from lyra_complexity import ComplexityEstimator
class TestComplexityEstimator:
    def test_estimate_simple(self):
        e = ComplexityEstimator(); s = e.estimate("What time is it?")
        assert s.overall < 0.5
    def test_estimate_complex(self):
        e = ComplexityEstimator(); s = e.estimate("Design, implement, test, and deploy the new authentication system")
        assert s.overall > 0.3
