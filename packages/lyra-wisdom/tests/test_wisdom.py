"""Tests for lyra-wisdom."""
from lyra_wisdom import WisdomEngine


class TestWisdomEngine:
    def test_distill(self):
        e = WisdomEngine()
        wisdoms = e.distill([
            {"action": "ran tests before commit", "outcome": "success", "id": "exp_1"},
            {"action": "deployed without testing", "outcome": "failure", "id": "exp_2"},
        ])
        assert len(wisdoms) == 2
        assert e.stats["total_wisdoms"] == 2

    def test_apply(self):
        e = WisdomEngine()
        e.distill([{"action": "test code thoroughly", "outcome": "success"},
                   {"action": "review pull request", "outcome": "success"}])
        results = e.apply("test the code")
        assert len(results) >= 1

    def test_record_application(self):
        e = WisdomEngine()
        e.distill([{"action": "test first", "outcome": "success"}])
        wid = list(e.wisdoms.keys())[0]
        old_conf = e.wisdoms[wid].confidence
        e.record_application(wid, success=True)
        assert e.wisdoms[wid].confidence > old_conf

    def test_record_failure(self):
        e = WisdomEngine()
        e.distill([{"action": "test first", "outcome": "success"}])
        wid = list(e.wisdoms.keys())[0]
        e.record_application(wid, success=False)
        assert e.wisdoms[wid].applications == 1
