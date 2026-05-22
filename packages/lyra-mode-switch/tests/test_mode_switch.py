
from lyra_mode_switch import ModeSwitchEngine, ComputeMode
class TestModeSwitchEngine:
    def test_non_thinking(self):
        m = ModeSwitchEngine(); mode = m.select_mode(0.1)
        assert mode == ComputeMode.NON_THINKING
    def test_deep_thinking(self):
        m = ModeSwitchEngine(); mode = m.select_mode(0.7)
        assert mode == ComputeMode.DEEP_THINKING
