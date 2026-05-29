"""
3-Tier cascade implementations for the Lyra Model Router (V4).

Tier 1 — Rule Layer (0-1ms, $0): Keyword/regex pattern matching.
Tier 2 — Semantic Match (5-50ms, <$0.001): TF-IDF similarity + complexity estimation.
Tier 3 — Neural Router (20-100ms, ~$0.001): MLP classifier with online learning.

Each tier returns an optional routing result. The cascade stops at the first
tier that produces a result with sufficient confidence.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from .models import ModelTier, TaskComplexity

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Shared types
# ────────────────────────────────────────────────────────────────────


@dataclass
class TierResult:
    """Result from any tier in the routing cascade."""

    complexity: TaskComplexity
    model_tier: ModelTier
    confidence: float
    reasoning: str
    matched_rule: str = ""


# ────────────────────────────────────────────────────────────────────
# Tier 1 — Rule Layer
# ────────────────────────────────────────────────────────────────────

# Keyword sets for each task complexity level. Ordered from most
# specific (AGENTIC) to least specific (TRIVIAL) so the first match wins.

_AGENTIC_KEYWORDS: set[str] = {
    "build a",
    "create a complete",
    "full application",
    "entire codebase",
    "autonomous",
    "multi-agent",
    "multi-step research",
    "deep research",
    "from scratch",
    "self-correcting",
    "self-improving",
    "autonomously",
    "orchestrate",
    "deploy to production",
    "end-to-end",
    "refactor entire",
    "system design",
    "full pipeline",
    "integrated system",
}

_COMPLEX_KEYWORDS: set[str] = {
    "architecture",
    "architect",
    "system design",
    "scalability",
    "trade-off",
    "tradeoff",
    "database schema",
    "data model",
    "security audit",
    "performance optimization",
    "deep analysis",
    "evaluate",
    "compare frameworks",
    "design pattern",
    "best practice",
    "migration strategy",
    "cost optimization",
    "microservices",
    "distributed",
    "concurrency model",
    "review this codebase",
    "code review of the entire",
    "design a system",
    "design an api",
}

_MODERATE_KEYWORDS: set[str] = {
    "implement",
    "write a function",
    "debug",
    "fix this bug",
    "add feature",
    "refactor",
    "write tests for",
    "explain how",
    "how does",
    "what is the difference",
    "optimize this",
    "write a script",
    "configure",
    "integrate",
    "api endpoint",
    "database query",
    "middleware",
    "authentication",
    "authorization",
}

_SIMPLE_KEYWORDS: set[str] = {
    "what is",
    "define",
    "lookup",
    "find",
    "search for",
    "convert",
    "translate",
    "syntax for",
    "example of",
    "who is",
    "when was",
    "where is",
}

_TRIVIAL_PATTERNS: list[str] = [
    r"^(hi|hello|hey|yo|sup)\b",
    r"^(yes|no|yep|nope|yeah|nah)\b",
    r"^(ok|okay|thanks|thank you|thx)\b",
    r"^(good morning|good afternoon|good evening)\b",
    r"^(bye|goodbye|see you|cya)\b",
    r"^what('?s| is) up\b",
    r"^how are you",
]

# Domain-specific routing rules
_DOMAIN_RULES: dict[str, ModelTier] = {
    "security": ModelTier.PREMIUM,
    "authentication": ModelTier.PREMIUM,
    "cryptography": ModelTier.PREMIUM,
    "payment": ModelTier.PREMIUM,
    "compliance": ModelTier.PREMIUM,
    "medical": ModelTier.PREMIUM,
    "legal": ModelTier.PREMIUM,
    "production deployment": ModelTier.PREMIUM,
    "infrastructure": ModelTier.PREMIUM,
}


class RuleTier:
    """
    Tier 1 — Rule-based keyword/pattern matching.

    Characteristics:
    - Latency: 0-1ms
    - Cost: $0
    - Hit rate target: 50-60%
    """

    def __init__(self, custom_rules: dict[str, ModelTier] | None = None) -> None:
        self._domain_rules = dict(_DOMAIN_RULES)
        if custom_rules:
            self._domain_rules.update(custom_rules)

    def route(self, task: str, context: dict[str, Any] | None = None) -> TierResult | None:
        """
        Attempt to classify a task using rule-based pattern matching.

        Args:
            task: The user's task description.
            context: Optional context dictionary (e.g. conversation history).

        Returns:
            TierResult if a match is found, None otherwise.
        """
        task_lower = task.lower().strip()

        # 1. Check domain-specific rules (highest priority)
        for domain, tier in self._domain_rules.items():
            if domain in task_lower:
                if tier == ModelTier.PREMIUM:
                    return TierResult(
                        complexity=TaskComplexity.COMPLEX,
                        model_tier=tier,
                        confidence=0.85,
                        reasoning=f"Domain keyword '{domain}' matched — routing to {tier.value}",
                        matched_rule=f"domain:{domain}",
                    )

        # 2. Check trivial patterns
        for pattern in _TRIVIAL_PATTERNS:
            if re.search(pattern, task_lower):
                return TierResult(
                    complexity=TaskComplexity.TRIVIAL,
                    model_tier=ModelTier.LOCAL_SLM,
                    confidence=0.95,
                    reasoning="Trivial conversation pattern matched",
                    matched_rule="pattern:trivial",
                )

        # 3. Check keyword sets (most specific first)
        keyword_checks: list[tuple[set[str], TaskComplexity, ModelTier]] = [
            (_AGENTIC_KEYWORDS, TaskComplexity.AGENTIC, ModelTier.AGENTIC),
            (_COMPLEX_KEYWORDS, TaskComplexity.COMPLEX, ModelTier.PREMIUM),
            (_MODERATE_KEYWORDS, TaskComplexity.MODERATE, ModelTier.STANDARD),
            (_SIMPLE_KEYWORDS, TaskComplexity.SIMPLE, ModelTier.HAIKU),
        ]

        for keywords, complexity, tier in keyword_checks:
            for kw in keywords:
                if kw in task_lower:
                    return TierResult(
                        complexity=complexity,
                        model_tier=tier,
                        confidence=0.80,
                        reasoning=f"Keyword '{kw}' matched — classified as {complexity.value}",
                        matched_rule=f"keyword:{kw}",
                    )

        # 4. Quick length heuristic: very short tasks are likely simple
        word_count = len(task.split())
        if word_count <= 3:
            return TierResult(
                complexity=TaskComplexity.SIMPLE,
                model_tier=ModelTier.HAIKU,
                confidence=0.55,
                reasoning=f"Short task ({word_count} words) — defaulting to simple",
                matched_rule="heuristic:short",
            )

        # 5. Question detection: questions tend to be simple/moderate
        if task_lower.endswith("?") or task_lower.startswith(
            ("what", "how", "why", "when", "where", "who", "can", "is", "do", "does")
        ):
            return TierResult(
                complexity=TaskComplexity.SIMPLE,
                model_tier=ModelTier.HAIKU,
                confidence=0.55,
                reasoning="Detected question pattern — defaulting to simple",
                matched_rule="heuristic:question",
            )

        # No rule matched — delegate to Tier 2
        return None

    def add_rule(self, keyword: str, tier: ModelTier) -> None:
        """Add a custom domain routing rule."""
        self._domain_rules[keyword] = tier

    def remove_rule(self, keyword: str) -> None:
        """Remove a domain routing rule."""
        self._domain_rules.pop(keyword, None)


# ────────────────────────────────────────────────────────────────────
# Tier 2 — Semantic Match (TF-IDF fallback)
# ────────────────────────────────────────────────────────────────────


class SemanticTier:
    """
    Tier 2 — Embedding similarity with TF-IDF fallback.

    Characteristics:
    - Latency: 5-50ms
    - Cost: <$0.001
    - Hit rate target: 20-30%

    Attempts to use sentence-transformers for semantic similarity.
    Falls back to TF-IDF when the library is not available.
    """

    def __init__(self) -> None:
        self._encoder = None
        self._corpus_embeddings: list | None = None
        self._corpus_labels: list[str] = []
        self._tfidf_vocab: dict[str, int] = {}
        self._tfidf_idf: dict[str, float] = {}
        self._initialized = False
        self._init_encoder()
        self._init_corpus()

    def _init_encoder(self) -> None:
        """Try to load sentence-transformers; fall back to None."""
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

            self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SemanticTier: loaded sentence-transformers (all-MiniLM-L6-v2)")
        except Exception:
            logger.info("SemanticTier: sentence-transformers unavailable, using TF-IDF fallback")

    def _init_corpus(self) -> None:
        """Build a reference corpus of example tasks with known classifications."""
        examples: list[tuple[str, TaskComplexity, ModelTier]] = [
            # AGENTIC
            (
                "build a complete e-commerce application from scratch",
                TaskComplexity.AGENTIC,
                ModelTier.AGENTIC,
            ),
            (
                "create an autonomous agent that researches topics and writes reports",
                TaskComplexity.AGENTIC,
                ModelTier.AGENTIC,
            ),
            (
                "refactor the entire codebase to use dependency injection",
                TaskComplexity.AGENTIC,
                ModelTier.AGENTIC,
            ),
            (
                "deploy a production-grade microservices cluster with monitoring",
                TaskComplexity.AGENTIC,
                ModelTier.AGENTIC,
            ),
            # COMPLEX
            (
                "design the database schema for a multi-tenant SaaS platform",
                TaskComplexity.COMPLEX,
                ModelTier.PREMIUM,
            ),
            (
                "evaluate the trade-offs between PostgreSQL and MongoDB for our use case",
                TaskComplexity.COMPLEX,
                ModelTier.PREMIUM,
            ),
            (
                "perform a security audit of our authentication system",
                TaskComplexity.COMPLEX,
                ModelTier.PREMIUM,
            ),
            (
                "design a scalable event-driven architecture for real-time analytics",
                TaskComplexity.COMPLEX,
                ModelTier.PREMIUM,
            ),
            # MODERATE
            (
                "implement a JWT authentication middleware",
                TaskComplexity.MODERATE,
                ModelTier.STANDARD,
            ),
            (
                "write a function to parse CSV files with error handling",
                TaskComplexity.MODERATE,
                ModelTier.STANDARD,
            ),
            ("add pagination to the API endpoint", TaskComplexity.MODERATE, ModelTier.STANDARD),
            (
                "debug why the database connection pool is exhausted",
                TaskComplexity.MODERATE,
                ModelTier.STANDARD,
            ),
            # SIMPLE
            (
                "what is the syntax for list comprehension in Python",
                TaskComplexity.SIMPLE,
                ModelTier.HAIKU,
            ),
            ("convert this JSON to YAML", TaskComplexity.SIMPLE, ModelTier.HAIKU),
            (
                "find all files modified in the last 24 hours",
                TaskComplexity.SIMPLE,
                ModelTier.HAIKU,
            ),
            ("what does the git status command do", TaskComplexity.SIMPLE, ModelTier.HAIKU),
            # TRIVIAL
            ("hello", TaskComplexity.TRIVIAL, ModelTier.LOCAL_SLM),
            ("yes", TaskComplexity.TRIVIAL, ModelTier.LOCAL_SLM),
            ("thanks", TaskComplexity.TRIVIAL, ModelTier.LOCAL_SLM),
            ("good morning", TaskComplexity.TRIVIAL, ModelTier.LOCAL_SLM),
        ]

        self._corpus_texts: list[str] = []
        self._corpus_complexities: list[TaskComplexity] = []
        self._corpus_tiers: list[ModelTier] = []

        for text, complexity, tier in examples:
            self._corpus_texts.append(text)
            self._corpus_complexities.append(complexity)
            self._corpus_tiers.append(tier)

        # Build TF-IDF vocabulary
        self._build_tfidf()

    def _build_tfidf(self) -> None:
        """Build TF-IDF from the reference corpus."""
        from math import log

        corpus_size = len(self._corpus_texts)
        if corpus_size == 0:
            return

        # Document frequency
        df: Counter[str] = Counter()
        tokenized_docs: list[list[str]] = []
        for text in self._corpus_texts:
            tokens = self._tokenize(text)
            tokenized_docs.append(tokens)
            df.update(set(tokens))

        # IDF
        self._tfidf_idf = {term: log(corpus_size / (freq + 1)) + 1 for term, freq in df.items()}

        # Vocabulary index
        self._tfidf_vocab = {term: idx for idx, term in enumerate(sorted(df.keys()))}

    def _tokenize(self, text: str) -> list[str]:
        """Simple whitespace + punctuation tokenization."""
        return re.findall(r"[a-zA-Z0-9]+", text.lower())

    def _compute_tfidf(self, text: str) -> dict[int, float]:
        """Compute TF-IDF vector for a text as a sparse dict."""

        tokens = self._tokenize(text)
        if not tokens:
            return {}

        token_counts = Counter(tokens)
        max_freq = max(token_counts.values()) if token_counts else 1
        vec: dict[int, float] = {}
        for token, count in token_counts.items():
            idx = self._tfidf_vocab.get(token)
            if idx is not None:
                tf = count / max_freq
                idf = self._tfidf_idf.get(token, 1.0)
                vec[idx] = tf * idf
        return vec

    def _cosine_similarity(self, a: dict[int, float], b: dict[int, float]) -> float:
        """Cosine similarity between two sparse TF-IDF vectors."""
        if not a or not b:
            return 0.0

        dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def route(self, task: str, context: dict[str, Any] | None = None) -> TierResult | None:
        """
        Classify a task using semantic similarity.

        Tries sentence-transformers first, falls back to TF-IDF.
        """
        if self._encoder is not None:
            return self._route_with_embeddings(task)

        return self._route_with_tfidf(task)

    def _route_with_embeddings(self, task: str) -> TierResult | None:
        """Route using sentence-transformers embeddings."""
        try:
            import numpy as np

            if self._corpus_embeddings is None:
                texts = self._corpus_texts
                embeddings = self._encoder.encode(
                    texts, convert_to_numpy=True
                )  # type: ignore[union-attr]
                self._corpus_embeddings = embeddings

            task_embedding = self._encoder.encode(
                [task], convert_to_numpy=True
            )  # type: ignore[union-attr]
            # type: ignore[union-attr]
            similarities = np.dot(self._corpus_embeddings, task_embedding.T).flatten()
            best_idx = int(np.argmax(similarities))
            best_sim = float(similarities[best_idx])

            complexity = self._corpus_complexities[best_idx]
            tier = self._corpus_tiers[best_idx]
            confidence = min(0.85, best_sim)

            return TierResult(
                complexity=complexity,
                model_tier=tier,
                confidence=confidence,
                reasoning=(
                    f"Semantic match to '{self._corpus_texts[best_idx][:60]}...' (cosine="
                    f"{best_sim:.2f})"
                ),
                matched_rule=f"semantic:embedding({best_sim:.2f})",
            )
        except Exception as exc:
            logger.debug("Embedding routing failed: %s, falling back to TF-IDF", exc)
            self._encoder = None
            return self._route_with_tfidf(task)

    def _route_with_tfidf(self, task: str) -> TierResult | None:
        """Route using TF-IDF cosine similarity (fallback)."""
        task_vec = self._compute_tfidf(task)
        if not task_vec:
            return None

        best_idx = 0
        best_sim = -1.0
        for idx, text in enumerate(self._corpus_texts):
            corpus_vec = self._compute_tfidf(text)
            sim = self._cosine_similarity(task_vec, corpus_vec)
            if sim > best_sim:
                best_sim = sim
                best_idx = idx

        confidence = min(0.75, best_sim + 0.1)  # TF-IDF is less reliable

        if best_sim < 0.1:
            # Not confident enough — delegate to Tier 3
            return None

        return TierResult(
            complexity=self._corpus_complexities[best_idx],
            model_tier=self._corpus_tiers[best_idx],
            confidence=confidence,
            reasoning=(
                f"TF-IDF match to '{self._corpus_texts[best_idx][:60]}...' (cosine={best_sim:.2f})"
            ),
            matched_rule=f"semantic:tfidf({best_sim:.2f})",
        )

    def add_example(self, text: str, complexity: TaskComplexity, tier: ModelTier) -> None:
        """Add a new example to the reference corpus."""
        self._corpus_texts.append(text)
        self._corpus_complexities.append(complexity)
        self._corpus_tiers.append(tier)
        self._corpus_embeddings = None  # Invalidate cache
        self._build_tfidf()


# ────────────────────────────────────────────────────────────────────
# Tier 3 — Neural Router (MLP classifier)
# ────────────────────────────────────────────────────────────────────


class NeuralTier:
    """
    Tier 3 — MLP-based classifier with online learning.

    Characteristics:
    - Latency: 20-100ms
    - Cost: ~$0.001
    - Hit rate target: Catch remainder after Tier 1 + 2

    Uses sklearn's MLPClassifier if available; falls back to a
    simple numpy-based logistic regression implementation.
    """

    _num_classes = 5  # Corresponds to TaskComplexity

    def __init__(self) -> None:
        self._model: Any = None
        self._use_sklearn = False
        self._init_model()

    def _init_model(self) -> None:
        """Initialize the model (sklearn preferred, numpy fallback)."""
        try:
            from sklearn.neural_network import MLPClassifier  # type: ignore[import-untyped]

            self._model = MLPClassifier(
                hidden_layer_sizes=(64, 32),
                activation="relu",
                solver="adam",
                max_iter=200,
                random_state=42,
                warm_start=True,
            )
            self._use_sklearn = True
            self._X: list[list[float]] = []
            self._y: list[int] = []
            self._fitted = False
            logger.info("NeuralTier: loaded sklearn MLPClassifier")
        except ImportError:
            self._model = None
            self._use_sklearn = False
            self._X = []
            self._y = []
            logger.info("NeuralTier: sklearn unavailable, using simple logistic fallback")

    # ── Feature extraction ─────────────────────────────────────────

    @staticmethod
    def _extract_features(task: str, context: dict[str, Any] | None = None) -> list[float]:
        """
        Extract a fixed-length feature vector from a task string.

        Features:
        - 0: task length (chars)
        - 1: word count
        - 2: avg word length
        - 3: question mark count
        - 4: code indicators (backticks, indentation)
        - 5: number of capitalized words ratio
        - 6: presence of "please" (politeness)
        - 7: technical term count
        - 8: imperative verb count
        - 9: URL/path indicators
        """
        words = task.split()
        word_count = len(words)
        char_count = len(task)
        avg_word_len = char_count / max(word_count, 1)
        question_count = task.count("?")
        code_indicators = task.count("`") + task.count("def ") + task.count("function ")
        cap_ratio = sum(1 for w in words if w and w[0].isupper()) / max(word_count, 1)

        technical_terms = [
            "api",
            "database",
            "server",
            "client",
            "endpoint",
            "json",
            "xml",
            "http",
            "docker",
            "kubernetes",
            "microservice",
            "sql",
            "nosql",
            "redis",
            "cache",
            "queue",
            "async",
            "thread",
            "process",
            "lambda",
            "class",
            "interface",
            "module",
            "package",
            "dependency",
        ]
        tech_count = sum(1 for term in technical_terms if term in task.lower())

        imperative_verbs = [
            "implement",
            "create",
            "build",
            "fix",
            "debug",
            "add",
            "remove",
            "update",
            "delete",
            "write",
            "read",
            "run",
            "deploy",
            "configure",
        ]
        imperative_count = sum(1 for v in imperative_verbs if v in task.lower().split())

        return [
            float(char_count),
            float(word_count),
            avg_word_len,
            float(question_count),
            float(code_indicators),
            cap_ratio,
            1.0 if "please" in task.lower() else 0.0,
            float(tech_count),
            float(imperative_count),
            1.0 if "://" in task else 0.0,
        ]

    # ── Method: route ──────────────────────────────────────────────

    def route(self, task: str, context: dict[str, Any] | None = None) -> TierResult | None:
        """Route using the neural model — always returns a result."""
        if self._use_sklearn and self._fitted:
            return self._route_sklearn(task)
        if self._use_sklearn and not self._fitted:
            # Not enough data for sklearn — use heuristic until trained
            return self._route_heuristic(task)
        return self._route_heuristic(task)

    def _route_sklearn(self, task: str) -> TierResult | None:
        """Route using trained sklearn model."""
        try:
            features = self._extract_features(task)
            pred = int(self._model.predict([features])[0])
            probs = self._model.predict_proba([features])[0]
            confidence = float(probs[pred])

            complexity = _int_to_complexity(pred)
            tier = _complexity_to_tier(complexity)

            return TierResult(
                complexity=complexity,
                model_tier=tier,
                confidence=confidence,
                reasoning=f"Neural classifier prediction (confidence={confidence:.2f})",
                matched_rule=f"neural:sklearn({confidence:.2f})",
            )
        except Exception as exc:
            logger.warning("Sklearn routing failed: %s", exc)
            return self._route_heuristic(task)

    def _route_heuristic(self, task: str) -> TierResult | None:
        """
        Fallback heuristic when no trained model is available.

        Uses feature thresholds to estimate complexity.
        """
        features = self._extract_features(task)
        char_count, word_count, _avg_word_len, question_count, code_indicators = (
            features[0],
            features[1],
            features[2],
            features[3],
            features[4],
        )
        tech_count, imperative_count = features[7], features[8]

        # Simple decision tree
        if word_count <= 3 and char_count < 20 and question_count == 0 and code_indicators == 0:
            complexity = TaskComplexity.TRIVIAL
            confidence = 0.70
        elif tech_count >= 3 or imperative_count >= 3:
            if char_count > 100:
                complexity = TaskComplexity.AGENTIC
                confidence = 0.55
            else:
                complexity = TaskComplexity.COMPLEX
                confidence = 0.55
        elif code_indicators > 2 or tech_count >= 2:
            complexity = TaskComplexity.MODERATE
            confidence = 0.50
        elif question_count >= 1 and word_count < 15:
            complexity = TaskComplexity.SIMPLE
            confidence = 0.60
        elif word_count < 10:
            complexity = TaskComplexity.SIMPLE
            confidence = 0.45
        else:
            complexity = TaskComplexity.MODERATE
            confidence = 0.40

        tier = _complexity_to_tier(complexity)

        return TierResult(
            complexity=complexity,
            model_tier=tier,
            confidence=confidence,
            reasoning=f"Neural heuristic (features: {len(task)} chars, {word_count} words)",
            matched_rule=f"neural:heuristic({confidence:.2f})",
        )

    # ── Online learning ────────────────────────────────────────────

    def train(self, task: str, complexity: TaskComplexity) -> None:
        """
        Record a training example for online learning.

        For sklearn: accumulates data and fits incrementally.
        For the fallback: stores data for retraining.
        """
        features = self._extract_features(task)
        label = _complexity_to_int(complexity)
        self._X.append(features)
        self._y.append(label)

        if self._use_sklearn and len(self._X) >= 10:
            try:
                self._model.partial_fit(self._X, self._y, classes=list(range(self._num_classes)))
                self._X.clear()
                self._y.clear()
                self._fitted = True
                logger.debug("NeuralTier: partial_fit with batch of 10 examples")
            except Exception as exc:
                logger.warning("NeuralTier training failed: %s", exc)

    def fit(self) -> bool:
        """Fit the model on all accumulated data. Returns True on success."""
        if not self._use_sklearn or len(self._X) < 5:
            return False
        try:
            self._model.fit(self._X, self._y)
            self._fitted = True
            self._X.clear()
            self._y.clear()
            logger.info("NeuralTier: model fitted on accumulated examples")
            return True
        except Exception as exc:
            logger.warning("NeuralTier fit failed: %s", exc)
            return False


# ── Helpers ─────────────────────────────────────────────────────────


def _complexity_to_int(complexity: TaskComplexity) -> int:
    """Map TaskComplexity to integer label."""
    mapping = {
        TaskComplexity.TRIVIAL: 0,
        TaskComplexity.SIMPLE: 1,
        TaskComplexity.MODERATE: 2,
        TaskComplexity.COMPLEX: 3,
        TaskComplexity.AGENTIC: 4,
    }
    return mapping[complexity]


def _int_to_complexity(label: int) -> TaskComplexity:
    """Map integer label back to TaskComplexity."""
    mapping = {
        0: TaskComplexity.TRIVIAL,
        1: TaskComplexity.SIMPLE,
        2: TaskComplexity.MODERATE,
        3: TaskComplexity.COMPLEX,
        4: TaskComplexity.AGENTIC,
    }
    return mapping.get(label, TaskComplexity.MODERATE)


def _complexity_to_tier(complexity: TaskComplexity) -> ModelTier:
    """Map task complexity to the default model tier."""
    return {
        TaskComplexity.TRIVIAL: ModelTier.LOCAL_SLM,
        TaskComplexity.SIMPLE: ModelTier.HAIKU,
        TaskComplexity.MODERATE: ModelTier.STANDARD,
        TaskComplexity.COMPLEX: ModelTier.PREMIUM,
        TaskComplexity.AGENTIC: ModelTier.AGENTIC,
    }[complexity]
