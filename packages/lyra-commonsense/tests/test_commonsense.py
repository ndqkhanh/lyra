"""Tests for lyra-commonsense."""
from lyra_commonsense import CommonSenseKB
class TestCommonSenseKB:
    def test_query_known(self):
        kb = CommonSenseKB(); f = kb.query("What happens when it rains?")
        assert f is not None
    def test_add_fact(self):
        kb = CommonSenseKB(); kb.add_fact("custom", "Cats purr when happy", "biology")
        assert kb.stats["facts"] >= 11
