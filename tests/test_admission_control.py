"""Tests for A-MAC 5-factor memory admission control."""

from lyra.memory.admission_control import (
    AdmissionController,
    ContentType,
    _TYPE_PRIORS,
)


class TestContentTypeClassifier:
    """Content type classification tests."""

    def test_classify_code(self):
        ctrl = AdmissionController()
        assert ctrl.classify_content_type("def foo(): return 42") == ContentType.CODE
        assert ctrl.classify_content_type("import os\n\nclass Foo:") == ContentType.CODE
        assert ctrl.classify_content_type("const x = 1; let y = 2;") == ContentType.CODE
        assert ctrl.classify_content_type("```python\nprint('hello')\n```") == ContentType.CODE

    def test_classify_decision(self):
        ctrl = AdmissionController()
        assert ctrl.classify_content_type("I decided to use SQLite") == ContentType.DECISION
        assert ctrl.classify_content_type("The PR was merged") == ContentType.DECISION
        assert ctrl.classify_content_type("deployed to production") == ContentType.DECISION

    def test_classify_preference(self):
        ctrl = AdmissionController()
        assert ctrl.classify_content_type("I prefer dark mode") == ContentType.PREFERENCE
        assert ctrl.classify_content_type("always use pnpm over npm") == ContentType.PREFERENCE
        assert ctrl.classify_content_type("my favorite editor is neovim") == ContentType.PREFERENCE

    def test_classify_error(self):
        ctrl = AdmissionController()
        assert ctrl.classify_content_type("error: connection refused") == ContentType.ERROR_LOG
        assert ctrl.classify_content_type("the build failed with exit code 1") == ContentType.ERROR_LOG
        assert ctrl.classify_content_type("Traceback (most recent call last):") == ContentType.ERROR_LOG

    def test_classify_plan(self):
        ctrl = AdmissionController()
        assert ctrl.classify_content_type("plan to refactor the router module") == ContentType.PLAN
        assert ctrl.classify_content_type("TODO: add error handling") == ContentType.PLAN
        assert ctrl.classify_content_type("next milestone: fleet view") == ContentType.PLAN

    def test_classify_fact(self):
        ctrl = AdmissionController()
        assert ctrl.classify_content_type("Python is a programming language") == ContentType.FACT
        assert ctrl.classify_content_type("it has built-in support for async I/O") == ContentType.FACT
        assert ctrl.classify_content_type("there are 280 PDFs in the corpus") == ContentType.FACT

    def test_classify_conversation(self):
        ctrl = AdmissionController()
        assert ctrl.classify_content_type("thanks, got it") == ContentType.CONVERSATION
        assert ctrl.classify_content_type("what do you think?") == ContentType.CONVERSATION


class TestAdmissionController:
    """5-factor admission scoring tests."""

    def test_preference_admitted(self):
        """User preferences should be admitted liberally."""
        ctrl = AdmissionController(threshold=0.45)
        score = ctrl.evaluate(
            content="I prefer dark mode for all interfaces",
            content_type=ContentType.PREFERENCE,
            confidence=0.95,
        )
        assert score.admit
        assert score.type_prior == _TYPE_PRIORS[ContentType.PREFERENCE]
        assert score.combined >= 0.45

    def test_code_conservative(self):
        """Code content should be admitted conservatively."""
        ctrl = AdmissionController(threshold=0.45)
        score = ctrl.evaluate(
            content="def old_helper(): return None  # unused",
            content_type=ContentType.CODE,
            confidence=0.90,
        )
        # Code has low type prior — may or may not admit
        assert score.type_prior == _TYPE_PRIORS[ContentType.CODE]
        assert 0.0 <= score.combined <= 1.0

    def test_duplicate_rejected(self):
        """Duplicate content should have low novelty."""
        ctrl = AdmissionController(threshold=0.45)
        existing = ["Python is a programming language used for web development"]
        score = ctrl.evaluate(
            content="Python is a programming language",
            content_type=ContentType.FACT,
            confidence=0.90,
            existing_memories=existing,
        )
        assert score.novelty < 1.0

    def test_novel_content_admitted(self):
        """Completely novel content should have high novelty."""
        ctrl = AdmissionController(threshold=0.45)
        score = ctrl.evaluate(
            content="The user's API key for Stripe is sk_live_xxx",
            content_type=ContentType.FACT,
            confidence=0.95,
            existing_memories=[],
        )
        assert score.novelty == 1.0

    def test_old_memory_penalized(self):
        """Old memories should have low recency."""
        ctrl = AdmissionController(threshold=0.45)
        score = ctrl.evaluate(
            content="old fact",
            content_type=ContentType.FACT,
            confidence=0.90,
            age_seconds=7 * 86400,  # 7 days old
        )
        assert score.recency < 0.1  # Should be very low after 7 days

    def test_recent_memory_favored(self):
        """Recent memories should have high recency."""
        ctrl = AdmissionController(threshold=0.45)
        score = ctrl.evaluate(
            content="new fact",
            content_type=ContentType.FACT,
            confidence=0.90,
            age_seconds=0,
        )
        assert score.recency == 1.0

    def test_weights_sum_to_one(self):
        """Default weights should be a valid distribution."""
        ctrl = AdmissionController()
        total = sum(ctrl.weights.values())
        assert abs(total - 1.0) < 0.01

    def test_dynamic_threshold(self):
        """Threshold should be adjustable at runtime."""
        ctrl = AdmissionController(threshold=0.90)
        score = ctrl.evaluate(
            content="test",
            content_type=ContentType.UNKNOWN,
            confidence=0.50,
        )
        assert not score.admit  # High threshold

        ctrl.set_threshold(0.10)
        score = ctrl.evaluate(
            content="test",
            content_type=ContentType.UNKNOWN,
            confidence=0.50,
        )
        assert score.admit  # Low threshold

    def test_score_serialization(self):
        """AdmissionScore should serialize to dict."""
        ctrl = AdmissionController()
        score = ctrl.evaluate(
            content="test fact",
            content_type=ContentType.FACT,
            confidence=0.95,
        )
        d = score.to_dict()
        assert isinstance(d, dict)
        assert "admit" in d
        assert all(k in d for k in ("utility", "confidence", "novelty", "recency", "type_prior", "combined"))
