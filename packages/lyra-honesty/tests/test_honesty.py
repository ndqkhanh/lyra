"""Tests for lyra-honesty."""
from lyra_honesty import DeceptionDetector


class TestDeceptionDetector:
    def test_honest_statement(self):
        d = DeceptionDetector()
        result = d.analyze("agent_1", "I verified the output. It matches the expected result.")
        assert result.verdict == "honest"
        assert result.score < 0.2

    def test_evasion_detected(self):
        d = DeceptionDetector()
        result = d.analyze("agent_1", "I can't tell you about that. It's unclear.")
        assert result.score > 0

    def test_inconsistency_detected(self):
        d = DeceptionDetector()
        result = d.analyze("agent_1", "The file is complete and ready to deploy.", {
            "previous_statements": ["The file is not ready and needs more work"]
        })
        assert result.score > 0

    def test_fabrication_detected(self):
        d = DeceptionDetector()
        result = d.analyze("agent_1", "According to unpublished internal studies, this is proven.")
        assert len(result.signals) > 0
        assert any(s.signal_type == "fabrication" for s in result.signals)

    def test_omission_detected(self):
        d = DeceptionDetector()
        result = d.analyze("agent_1", "The code compiles.", {
            "expected_topics": ["testing", "deployment", "security"]
        })
        assert len(result.signals) > 0
        assert any(s.signal_type == "omission" for s in result.signals)

    def test_misdirection_detected(self):
        d = DeceptionDetector()
        result = d.analyze("agent_1", "That's not relevant. You should focus on the real issue.")
        assert any(s.signal_type == "misdirection" for s in result.signals)
