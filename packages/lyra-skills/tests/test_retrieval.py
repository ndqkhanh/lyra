"""Tests for Phase J — BM25, DCI, and Hybrid retrieval."""
import pytest

from lyra_skills.retrieval import (
    BM25Retriever,
    DCIRetriever,
    HybridRetriever,
    RetrievalResult,
)


SKILL_A = "deploy docker image to kubernetes cluster using kubectl apply"
SKILL_B = "backup postgresql database to s3 bucket with pg_dump"
SKILL_C = "send slack notification when deployment succeeds"


class TestRetrievalResult:
    def test_lt_comparison(self):
        r1 = RetrievalResult("s1", score=0.3)
        r2 = RetrievalResult("s2", score=0.7)
        assert r1 < r2

    def test_defaults(self):
        r = RetrievalResult("s", score=0.5)
        assert r.bm25_score == 0.0
        assert r.dci_score == 0.0
        assert r.semantic_score == 0.0
        assert r.matched_lines == []


class TestBM25Retriever:
    def setup_method(self):
        self.bm25 = BM25Retriever()
        self.bm25.index("skill-a", SKILL_A)
        self.bm25.index("skill-b", SKILL_B)
        self.bm25.index("skill-c", SKILL_C)

    def test_search_returns_results(self):
        results = self.bm25.search("docker kubernetes")
        assert len(results) > 0

    def test_search_top_k_respected(self):
        results = self.bm25.search("deploy", top_k=2)
        assert len(results) <= 2

    def test_relevant_skill_ranked_first(self):
        results = self.bm25.search("postgresql backup pg_dump")
        assert results[0].skill_id == "skill-b"

    def test_scores_are_positive(self):
        results = self.bm25.search("deploy docker")
        for r in results:
            assert r.score > 0

    def test_unknown_query_returns_empty(self):
        results = self.bm25.search("xyzzy_not_in_corpus_at_all")
        assert results == []

    def test_empty_corpus_returns_empty(self):
        bm25 = BM25Retriever()
        assert bm25.search("anything") == []


class TestDCIRetriever:
    def setup_method(self):
        self.dci = DCIRetriever()
        self.dci.load_text("skill-a", SKILL_A)
        self.dci.load_text("skill-b", SKILL_B)
        self.dci.load_text("skill-c", SKILL_C)

    def test_grep_finds_match(self):
        results = self.dci.grep("kubectl")
        assert any(r.skill_id == "skill-a" for r in results)

    def test_grep_returns_matched_lines(self):
        results = self.dci.grep("kubectl")
        match = next(r for r in results if r.skill_id == "skill-a")
        assert len(match.matched_lines) > 0

    def test_grep_no_match_returns_empty(self):
        results = self.dci.grep("xyzzy_impossible_term")
        assert results == []

    def test_grep_case_insensitive(self):
        results = self.dci.grep("KUBECTL")
        assert any(r.skill_id == "skill-a" for r in results)

    def test_multi_grep_conjunction(self):
        results = self.dci.multi_grep(["docker", "kubectl"])
        # Both terms in skill-a only
        assert len(results) >= 1
        assert all("skill-a" == r.skill_id for r in results)

    def test_multi_grep_empty_patterns(self):
        assert self.dci.multi_grep([]) == []

    def test_multi_grep_no_conjunction_match(self):
        results = self.dci.multi_grep(["kubectl", "pg_dump"])
        assert results == []


class TestHybridRetriever:
    def setup_method(self):
        self.hybrid = HybridRetriever()
        self.hybrid.index("skill-a", SKILL_A)
        self.hybrid.index("skill-b", SKILL_B)
        self.hybrid.index("skill-c", SKILL_C)

    def test_search_returns_results(self):
        results = self.hybrid.search("docker kubernetes deploy")
        assert len(results) > 0

    def test_top_k_respected(self):
        results = self.hybrid.search("deploy", top_k=2)
        assert len(results) <= 2

    def test_semantic_score_incorporated(self):
        self.hybrid.set_semantic_score("skill-a", 0.99)
        results = self.hybrid.search("deploy kubernetes", top_k=3)
        top = results[0]
        assert top.semantic_score == pytest.approx(0.99)

    def test_scores_are_combined(self):
        results = self.hybrid.search("docker")
        for r in results:
            assert r.score >= 0

    def test_result_has_score_breakdown(self):
        results = self.hybrid.search("kubectl")
        r = results[0]
        assert hasattr(r, "bm25_score")
        assert hasattr(r, "dci_score")
        assert hasattr(r, "semantic_score")

    def test_dci_matched_lines_propagated(self):
        results = self.hybrid.search("kubectl")
        match = next((r for r in results if r.skill_id == "skill-a"), None)
        assert match is not None
        assert len(match.matched_lines) > 0
