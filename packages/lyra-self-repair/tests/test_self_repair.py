from lyra_self_repair import SelfRepairSystem
class TestSelfRepair:
    def test_detect_diagnose_repair(self):
        s = SelfRepairSystem()
        a = s.detect("auth_service", "timeout error", 0.8)
        d = s.diagnose(a)
        r = s.repair(d)
        assert r.success
        assert s.verify(r)
