from lyra_trace_inspector import TraceInspector
class TestTraceInspector:
    def test_trace_lifecycle(self):
        t = TraceInspector(); tid = t.start_trace("agent_1")
        t.record_event(tid, "search", 500, True); t.record_event(tid, "analyze", 1200, True)
        assert len(t.replay(tid)) == 2
    def test_failure_rate(self):
        t = TraceInspector(); tid = t.start_trace("agent_2")
        t.record_event(tid, "step1", 100, True); t.record_event(tid, "step2", 200, False)
        assert t.get_failure_rate(tid) == 0.5
