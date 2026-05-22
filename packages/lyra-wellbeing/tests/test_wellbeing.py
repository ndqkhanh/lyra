from lyra_wellbeing import WellbeingMonitor
class TestWellbeingMonitor:
    def test_record_tasks(self):
        w = WellbeingMonitor(); w.record_task(30, 0.8); assert w.stats["tasks_completed"] == 1
    def test_rest_recommendation(self):
        w = WellbeingMonitor()
        for _ in range(10): w.record_task(60, 0.9)
        rec = w.recommend_rest(); assert rec["rest_needed"]
