"""Tests for lyra-introspection."""
from lyra_introspection import IntrospectionEngine

class TestIntrospectionEngine:
    def test_begin_complete(self):
        e = IntrospectionEngine()
        e.begin_task("code review")
        assert e.get_state().is_processing
        e.complete_task(success=True)
        assert not e.get_state().is_processing

    def test_overload(self):
        e = IntrospectionEngine()
        for _ in range(15):
            e.begin_task("work")
        assert e.check_overload()
