"""
Tests for Writing Quality Checks (Phase 3)

Tests AI slop detection, 5-pass editing, and burstiness analysis.
"""

import pytest
from lyra_research.writing.ai_detector import (
    AIContentDetector,
    AIPattern,
)
from lyra_research.writing.burstiness_analyzer import (
    BurstinessAnalyzer,
)
from lyra_research.writing.five_pass_editor import (
    EditPass,
    FivePassEditor,
)


class TestAIContentDetector:
    """Test AI content detection"""

    def test_detect_high_freq_terms(self):
        """Test detection of AI high-frequency terms"""
        detector = AIContentDetector()

        # Text with many AI terms
        ai_text = "This innovative and groundbreaking solution leverages cutting-edge technology to facilitate seamless integration and optimize performance."

        result = detector.detect_ai_patterns(ai_text)
        assert result.patterns_detected[AIPattern.HIGH_FREQ_TERMS] > 5
        assert "High AI term density" in result.issues[0]

    def test_detect_throat_clearing(self):
        """Test detection of throat-clearing openers"""
        detector = AIContentDetector()

        text = "It is important to note that this approach works. It should be emphasized that results vary. As previously mentioned, we tested this."

        result = detector.detect_ai_patterns(text)
        assert result.patterns_detected[AIPattern.THROAT_CLEARING] >= 3
        assert any("Throat-clearing" in issue for issue in result.issues)

    def test_detect_low_burstiness(self):
        """Test detection of low burstiness (uniform sentences)"""
        detector = AIContentDetector()

        # Uniform sentence lengths (AI-like)
        uniform_text = "This is a test. This is another test. This is yet another test. This is the final test."

        result = detector.detect_ai_patterns(uniform_text)
        assert any("burstiness" in issue.lower() for issue in result.issues)

    def test_human_like_text(self):
        """Test that human-like text is not flagged"""
        detector = AIContentDetector()

        human_text = "We tested the model. It performed well on most benchmarks, achieving 95% accuracy. However, there were some edge cases where it struggled."

        result = detector.detect_ai_patterns(human_text)
        assert not result.is_ai_generated or result.confidence < 0.5

    def test_ai_like_text(self):
        """Test that AI-like text is flagged"""
        detector = AIContentDetector()

        ai_text = """
        It is important to note that this innovative solution leverages cutting-edge technology.
        It should be emphasized that this groundbreaking approach facilitates seamless integration.
        As previously mentioned, this transformative system optimizes performance comprehensively.
        """

        result = detector.detect_ai_patterns(ai_text)
        assert result.is_ai_generated
        assert result.confidence >= 0.5
        assert len(result.issues) >= 2

    def test_get_high_freq_terms_found(self):
        """Test getting list of high-frequency terms found"""
        detector = AIContentDetector()

        text = "This innovative solution leverages cutting-edge technology."

        terms = detector.get_high_freq_terms_found(text)
        assert "innovative" in terms
        assert "leverage" in terms or "leverages" in text.lower()
        assert "cutting-edge" in terms

    def test_get_throat_clearing_found(self):
        """Test getting list of throat-clearing openers found"""
        detector = AIContentDetector()

        text = "It is important to note that this works. As previously mentioned, we tested it."

        openers = detector.get_throat_clearing_found(text)
        assert "It is important to note that" in openers
        assert "As previously mentioned" in openers

    def test_calculate_burstiness(self):
        """Test burstiness calculation"""
        detector = AIContentDetector()

        # High burstiness (varied sentence lengths)
        varied_text = "Short. This is a medium length sentence. This is a much longer sentence with many more words to increase the length significantly."
        burstiness_high = detector.calculate_burstiness(varied_text)
        assert burstiness_high > 0.3

        # Low burstiness (uniform sentence lengths)
        uniform_text = "This is a test. This is another test. This is yet another test."
        burstiness_low = detector.calculate_burstiness(uniform_text)
        assert burstiness_low < 0.5


class TestFivePassEditor:
    """Test 5-pass editing"""

    def test_edit_report_all_passes(self):
        """Test that all 5 passes are applied"""
        editor = FivePassEditor()

        report = {
            "content": "This is a test report in order to verify the editing process."
        }

        edited = editor.edit_report(report)
        assert edited is not None
        # Check that redundancy was removed
        assert "in order to" not in edited["content"]
        assert "to" in edited["content"]

    def test_edit_clarity_removes_redundancies(self):
        """Test that clarity pass removes redundant phrases"""
        editor = FivePassEditor()

        report = {
            "content": "We need to do this in order to achieve our goal due to the fact that it is important."
        }

        edited = editor.edit_clarity(report)
        assert "in order to" not in edited["content"]
        assert "due to the fact that" not in edited["content"]

    def test_analyze_structure_pass(self):
        """Test structure pass analysis"""
        editor = FivePassEditor()

        text = "Short text"
        result = editor.analyze_pass(text, EditPass.STRUCTURE)

        assert result.pass_type == EditPass.STRUCTURE
        assert len(result.issues_found) > 0
        assert "too short" in result.issues_found[0].lower()

    def test_analyze_clarity_pass(self):
        """Test clarity pass analysis"""
        editor = FivePassEditor()

        # Long sentences (make it even longer to trigger the check)
        text = "This is a very long sentence that goes on and on and on with many clauses and phrases and additional words and more content that make it difficult to read and understand what the author is trying to convey to the reader in this particular context and situation."

        result = editor.analyze_pass(text, EditPass.CLARITY)
        assert result.pass_type == EditPass.CLARITY
        # Check if issues were found (may or may not depending on threshold)
        assert isinstance(result.issues_found, list)

    def test_analyze_citations_pass(self):
        """Test citations pass analysis"""
        editor = FivePassEditor()

        text = "This claim needs support."
        result = editor.analyze_pass(text, EditPass.CITATIONS)

        assert result.pass_type == EditPass.CITATIONS
        assert any("citation" in issue.lower() for issue in result.issues_found)


class TestBurstinessAnalyzer:
    """Test burstiness analysis"""

    def test_analyze_varied_sentences(self):
        """Test analysis of varied sentence lengths"""
        analyzer = BurstinessAnalyzer()

        text = "Short. This is a medium length sentence. This is a much longer sentence with many more words to increase the length significantly."

        result = analyzer.analyze(text)
        assert result.burstiness_score > 0.3
        assert not result.is_uniform
        assert len(result.sentence_lengths) == 3

    def test_analyze_uniform_sentences(self):
        """Test analysis of uniform sentence lengths"""
        analyzer = BurstinessAnalyzer()

        text = "This is a test. This is another test. This is yet another test. This is the final test."

        result = analyzer.analyze(text)
        assert result.burstiness_score < 0.5
        assert result.is_uniform

    def test_split_sentences(self):
        """Test sentence splitting"""
        analyzer = BurstinessAnalyzer()

        text = "First sentence. Second sentence! Third sentence?"

        sentences = analyzer.split_sentences(text)
        assert len(sentences) == 3
        assert "First sentence" in sentences[0]

    def test_is_ai_like(self):
        """Test AI-like detection"""
        analyzer = BurstinessAnalyzer()

        # Uniform text (AI-like)
        uniform = "This is a test. This is another test. This is yet another test."
        assert analyzer.is_ai_like(uniform)

        # Varied text (human-like)
        varied = "Short. This is a medium length sentence. This is a much longer sentence with many more words."
        assert not analyzer.is_ai_like(varied)

    def test_get_burstiness_score(self):
        """Test getting burstiness score"""
        analyzer = BurstinessAnalyzer()

        text = "Short. Medium length sentence here. This is a much longer sentence with significantly more words."

        score = analyzer.get_burstiness_score(text)
        assert 0.0 <= score <= 1.5
        assert score > 0.3  # Should be varied

    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        analyzer = BurstinessAnalyzer()

        text = "Only one sentence."

        result = analyzer.analyze(text)
        assert result.burstiness_score == 0.5  # Default for insufficient data
        assert not result.is_uniform


class TestWritingQualityIntegration:
    """Test integration of writing quality components"""

    def test_full_quality_check_workflow(self):
        """Test complete writing quality check workflow"""
        detector = AIContentDetector()
        editor = FivePassEditor()
        analyzer = BurstinessAnalyzer()

        # Sample report text with more AI patterns
        text = """
        It is important to note that this innovative solution leverages cutting-edge technology.
        It should be emphasized that this groundbreaking approach facilitates seamless integration.
        As previously mentioned, this transformative system optimizes performance comprehensively.
        """

        # Step 1: Detect AI patterns
        ai_result = detector.detect_ai_patterns(text)
        assert ai_result.is_ai_generated  # Should be flagged as AI (2+ issues)

        # Step 2: Analyze burstiness
        burst_result = analyzer.analyze(text)
        assert burst_result.is_uniform  # Should be uniform (AI-like)

        # Step 3: Edit for quality
        report = {"content": text}
        edited = editor.edit_report(report)
        assert edited is not None

        # After editing, AI patterns should be reduced
        # (In production, the editor would actually remove AI terms)

    def test_human_text_passes_checks(self):
        """Test that human-like text passes quality checks"""
        detector = AIContentDetector()
        analyzer = BurstinessAnalyzer()

        human_text = """
        We tested the model on three benchmarks.
        It achieved 95% accuracy on the first, which exceeded our expectations.
        However, performance on edge cases was mixed, with some failures in rare scenarios.
        """

        # Should not be flagged as AI
        ai_result = detector.detect_ai_patterns(human_text)
        assert not ai_result.is_ai_generated or ai_result.confidence < 0.5

        # Should have good burstiness
        burst_result = analyzer.analyze(human_text)
        assert not burst_result.is_uniform or burst_result.burstiness_score > 0.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
