"""Tests for lyra-novelty."""
from lyra_novelty import NoveltyEngine

class TestNoveltyEngine:
    def test_assess_novelty_new(self):
        n = NoveltyEngine()
        score = n.assess_novelty("new topic")
        assert score > 0

    def test_explore(self):
        n = NoveltyEngine()
        r = n.explore("learn python")
        assert r["explorations"] == 1
