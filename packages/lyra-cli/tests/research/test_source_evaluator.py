"""Tests for SourceCredibility."""

import pytest

from lyra_cli.research.source_evaluator import (
    SourceCredibility,
    SourceProfile,
    SourceType,
    BASE_CREDIBILITY,
)


class TestSourceCredibility:
    """Test suite for SourceCredibility."""

    def test_evaluate_source_default_credibility(self):
        """Academic papers get the highest base credibility."""
        ev = SourceCredibility()
        profile = ev.evaluate_source(
            source_id="src_001",
            url="https://arxiv.org/abs/1234",
            source_type=SourceType.ACADEMIC_PAPER,
            title="A Great Paper",
        )
        assert profile.source_id == "src_001"
        assert profile.credibility_score >= 0.8
        assert profile.source_type == SourceType.ACADEMIC_PAPER

    def test_evaluate_source_social_media_low(self):
        """Social media sources get low credibility."""
        ev = SourceCredibility()
        profile = ev.evaluate_source(
            source_id="src_tweet",
            url="https://twitter.com/user/status/1",
            source_type=SourceType.SOCIAL_MEDIA,
            title="Hot take",
        )
        assert profile.credibility_score < 0.5

    def test_evaluate_source_bias_penalty(self):
        """Sources with detected biases get penalised."""
        ev = SourceCredibility()
        profile = ev.evaluate_source(
            source_id="src_biased",
            url="https://example.com/biased",
            source_type=SourceType.NEWS_ARTICLE,
            title="Biased article",
            detected_biases=["political_slant", "sensationalism"],
        )
        assert profile.credibility_score < BASE_CREDIBILITY[SourceType.NEWS_ARTICLE]

    def test_evaluate_source_citation_bonus(self):
        """Sources with many citations get a credibility bonus."""
        ev = SourceCredibility()
        low = ev.evaluate_source(
            source_id="src_low", url="https://a.com",
            source_type=SourceType.ACADEMIC_PAPER, title="A",
            citation_count=0,
        )
        high = ev.evaluate_source(
            source_id="src_high", url="https://b.com",
            source_type=SourceType.ACADEMIC_PAPER, title="B",
            citation_count=100,
        )
        assert high.credibility_score > low.credibility_score

    def test_get_source_returns_none_for_missing(self):
        """get_source returns None for unknown source IDs."""
        ev = SourceCredibility()
        assert ev.get_source("nonexistent") is None

    def test_get_all_sources(self):
        """get_all_sources returns all evaluated sources."""
        ev = SourceCredibility()
        ev.evaluate_source("s1", "https://a.com", SourceType.ACADEMIC_PAPER, "A")
        ev.evaluate_source("s2", "https://b.com", SourceType.OFFICIAL_DOCS, "B")

        all_s = ev.get_all_sources()
        assert len(all_s) == 2
        assert {s.source_id for s in all_s} == {"s1", "s2"}

    def test_citation_chain(self):
        """get_citation_chain walks the citation graph backwards."""
        ev = SourceCredibility()
        ev.evaluate_source(
            "src_root", "https://root.com", SourceType.ACADEMIC_PAPER,
            "Root paper",
        )
        ev.evaluate_source(
            "src_mid", "https://mid.com", SourceType.ACADEMIC_PAPER,
            "Middle paper", cited_by=["src_root"],
        )
        ev.evaluate_source(
            "src_leaf", "https://leaf.com", SourceType.ACADEMIC_PAPER,
            "Leaf paper", cited_by=["src_mid"],
        )

        chain = ev.get_citation_chain("src_leaf")
        assert len(chain) == 3
        assert chain[0].source_id == "src_root"
        assert chain[1].source_id == "src_mid"
        assert chain[2].source_id == "src_leaf"

    def test_contradiction_detection(self):
        """Detected contradictions are stored and retrievable."""
        ev = SourceCredibility()
        ev.evaluate_source("s1", "https://a.com", SourceType.ACADEMIC_PAPER, "A")
        ev.evaluate_source("s2", "https://b.com", SourceType.ACADEMIC_PAPER, "B")

        report = ev.detect_contradictions(
            "s1", "s2",
            "RLHF is safe",
            "RLHF is dangerous",
            severity=0.9,
        )
        assert report.source_a_id == "s1"
        assert report.severity == 0.9

        all_c = ev.get_contradictions()
        assert len(all_c) == 1

        filtered = ev.get_contradictions(source_id="s1")
        assert len(filtered) == 1

    def test_consensus_score(self):
        """Consensus score is higher with more credible sources."""
        ev = SourceCredibility()
        ev.evaluate_source("s_good", "https://good.com", SourceType.ACADEMIC_PAPER, "G")
        ev.evaluate_source("s_bad", "https://bad.com", SourceType.SOCIAL_MEDIA, "B")

        score = ev.get_consensus_score(["s_good", "s_bad"])
        assert 0.0 < score < 1.0

    def test_consensus_score_empty(self):
        """Consensus score for empty list is 0."""
        ev = SourceCredibility()
        assert ev.get_consensus_score([]) == 0.0

    def test_consensus_score_contradiction_penalty(self):
        """Contradictions reduce the consensus score."""
        ev = SourceCredibility()
        ev.evaluate_source("s1", "https://a.com", SourceType.ACADEMIC_PAPER, "A")
        ev.evaluate_source("s2", "https://b.com", SourceType.ACADEMIC_PAPER, "B")
        ev.detect_contradictions("s1", "s2", "claim a", "claim b", severity=1.0)

        noisy_score = ev.get_consensus_score(["s1", "s2"])
        clean_score = ev.get_consensus_score(["s1"])

        assert noisy_score < clean_score

    def test_base_credibility_ordering(self):
        """Source type credibility ordering is as expected."""
        assert (
            BASE_CREDIBILITY[SourceType.ACADEMIC_PAPER]
            > BASE_CREDIBILITY[SourceType.OFFICIAL_DOCS]
            > BASE_CREDIBILITY[SourceType.EXPERT_BLOG]
            > BASE_CREDIBILITY[SourceType.SOCIAL_MEDIA]
        )
