"""Context Router — intelligent context routing for agent harness systems.

Routes context payloads to the appropriate subsystem (memory retrieval, working
memory, long-term storage, compaction, progressive disclosure) based on signal
characteristics. Composes a pluggable Classifier with a routing table — follows
the same Protocol-based architecture as BELLERouter.

BREAKTHROUGH primitive (P1-B1): high impact, low effort. Sits between the agent
loop and all context-consuming subsystems.
"""
from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Protocol


class ContextRoute(str, enum.Enum):
    """Routing destinations for context payloads."""

    MEMORY_RETRIEVAL = "memory_retrieval"    # query the 3-layer memory search
    WORKING_MEMORY = "working_memory"         # hot context, active session
    LONG_TERM_STORE = "long_term_store"       # persist to cold/graph tier
    COMPACTION = "compaction"                 # summarise / compress
    DISCLOSURE = "disclosure"                 # progressive disclosure gate
    DIRECT_PASS = "direct_pass"              # inline, no routing needed


@dataclass(frozen=True)
class ContextDecision:
    """The router's verdict for a context signal."""

    signal: str
    route: ContextRoute
    confidence: float  # 0.0..1.0
    reason: str
    strategy_hints: tuple[str, ...] = ()  # e.g. ("three_layer", "bm25")

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")


@dataclass
class ContextSignal:
    """A context payload submitted for routing.

    Attributes:
        content: The raw text content to route.
        urgency: How time-sensitive the signal is (0.0 = background, 1.0 = immediate).
        token_count: Approximate token count of the content.
        source: Which subsystem/agent produced this signal.
        tags: Optional categorical tags to guide routing.
    """

    content: str
    urgency: float = 0.0
    token_count: int = 0
    source: str = ""
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.urgency <= 1.0:
            raise ValueError(f"urgency must be in [0, 1], got {self.urgency}")
        if self.token_count == 0:
            # Rough estimate: ~4 chars per token for English text
            self.token_count = max(1, len(self.content) // 4)


class ContextClassifier(Protocol):
    """Pluggable context classifier. Production wires an LLM-backed one."""

    name: str

    def classify(self, signal: ContextSignal) -> ContextDecision: ...


# --- Rule-based default classifier -------------------------------------------


# Heuristic thresholds (tunable)
_COMPACTION_TOKEN_THRESHOLD = 4000   # above this → compact
_DISCLOSURE_TOKEN_THRESHOLD = 8000   # above this → progressive disclosure
_URGENCY_THRESHOLD = 0.7             # above this → working memory (hot path)

_RETRIEVAL_HINTS = (
    re.compile(r"\b(recall|remember|retrieve|find|search|look.?up|fetch)\b", re.I),
    re.compile(r"\b(what (?:is|was|are|were)|who (?:is|was|are)|when (?:did|is|was))\b", re.I),
    re.compile(r"\b(previous|earlier|past|history|prior)\b", re.I),
)
_STORE_HINTS = (
    re.compile(r"\b(save|store|persist|remember this|keep this|archive)\b", re.I),
    re.compile(r"\b(important|critical|crucial|key|essential) (?:to remember|fact|insight)\b", re.I),
    re.compile(r"\b(learned|discovered|found that|realized that)\b", re.I),
)
_COMPACT_HINTS = (
    re.compile(r"\b(summarize|summarise|summary|tl;dr|tldr|condense)\b", re.I),
    re.compile(r"\b(compress|shorten|abbreviate|digest)\b", re.I),
    re.compile(r"\b(too long|verbose|wall of text)\b", re.I),
)
_DISCLOSURE_HINTS = (
    re.compile(r"\b(progressively|step by step|gradually|layer|level of detail)\b", re.I),
    re.compile(r"\b(overview first|high.level|summary first)\b", re.I),
    re.compile(r"\b(expand|elaborate|drill down|more detail)\b", re.I),
)


@dataclass
class RuleBasedContextClassifier:
    """Pattern-based context classifier — zero-dep, deterministic.

    Heuristic default; production layers an LM-backed classifier on top,
    falling back to this for cold-start. Used for tests + baseline measurement.

    >>> sig = ContextSignal(content="what is the capital of France?")
    >>> RuleBasedContextClassifier().classify(sig).route
    <ContextRoute.MEMORY_RETRIEVAL: 'memory_retrieval'>
    """

    name: str = "rule-based-context-classifier-v1"

    def classify(self, signal: ContextSignal) -> ContextDecision:
        if not signal.content or not signal.content.strip():
            return ContextDecision(
                signal=signal.content,
                route=ContextRoute.DIRECT_PASS,
                confidence=0.0,
                reason="empty signal content",
            )

        # Score each route type; pick the highest.
        scores: dict[ContextRoute, int] = dict.fromkeys(ContextRoute, 0)

        for pat in _RETRIEVAL_HINTS:
            if pat.search(signal.content):
                scores[ContextRoute.MEMORY_RETRIEVAL] += 1
        for pat in _STORE_HINTS:
            if pat.search(signal.content):
                scores[ContextRoute.LONG_TERM_STORE] += 1
        for pat in _COMPACT_HINTS:
            if pat.search(signal.content):
                scores[ContextRoute.COMPACTION] += 1
        for pat in _DISCLOSURE_HINTS:
            if pat.search(signal.content):
                scores[ContextRoute.DISCLOSURE] += 1

        # Structural signals (overrideable by hints)
        if signal.token_count > _COMPACTION_TOKEN_THRESHOLD:
            scores[ContextRoute.COMPACTION] += 1
        if signal.token_count > _DISCLOSURE_TOKEN_THRESHOLD:
            scores[ContextRoute.DISCLOSURE] += 1
        if signal.urgency >= _URGENCY_THRESHOLD:
            scores[ContextRoute.WORKING_MEMORY] += 2  # strong signal for hot path

        max_score = max(scores.values())

        if max_score == 0:
            # Default routing: short → working memory, long → compaction
            if signal.content and len(signal.content.split()) <= 50:
                return ContextDecision(
                    signal=signal.content,
                    route=ContextRoute.WORKING_MEMORY,
                    confidence=0.5,
                    reason="short content, default to working memory",
                    strategy_hints=("inline",),
                )
            return ContextDecision(
                signal=signal.content,
                route=ContextRoute.COMPACTION,
                confidence=0.4,
                reason="no hint matched; default to compaction for longer content",
                strategy_hints=("summarize",),
            )

        # Tie-break priority: WORKING_MEMORY > RETRIEVAL > DISCLOSURE > COMPACTION > STORE > DIRECT
        priority = (
            ContextRoute.WORKING_MEMORY,
            ContextRoute.MEMORY_RETRIEVAL,
            ContextRoute.DISCLOSURE,
            ContextRoute.COMPACTION,
            ContextRoute.LONG_TERM_STORE,
        )
        chosen = next(
            (rt for rt in priority if scores[rt] == max_score),
            ContextRoute.DIRECT_PASS,
        )
        hints = _strategy_hints_for(chosen)
        confidence = min(0.9, 0.5 + 0.08 * max_score)
        return ContextDecision(
            signal=signal.content,
            route=chosen,
            confidence=confidence,
            reason=f"matched {max_score} hint(s) for {chosen.value}",
            strategy_hints=hints,
        )


def _strategy_hints_for(route: ContextRoute) -> tuple[str, ...]:
    return {
        ContextRoute.MEMORY_RETRIEVAL: ("three_layer", "bm25", "vector"),
        ContextRoute.WORKING_MEMORY: ("inline", "verbatim_cache"),
        ContextRoute.LONG_TERM_STORE: ("consolidation", "graph_tier"),
        ContextRoute.COMPACTION: ("summarize", "extractive", "ngc"),
        ContextRoute.DISCLOSURE: ("progressive", "leveled_summary"),
        ContextRoute.DIRECT_PASS: ("inline",),
    }[route]


# --- Context Router ----------------------------------------------------------


@dataclass
class ContextRouter:
    """Intelligent context router — composes a classifier with routing rules.

    Sits between the agent loop and all context-consuming subsystems (memory
    retrieval, working memory, long-term storage, compaction, disclosure).

    Usage::

        router = ContextRouter()
        signal = ContextSignal(content="what is the capital of France?")
        decision = router.route(signal)
        # decision.route → ContextRoute.MEMORY_RETRIEVAL
    """

    classifier: ContextClassifier = field(default_factory=RuleBasedContextClassifier)
    confidence_threshold: float = 0.3

    def route(self, signal: ContextSignal | str) -> ContextDecision:
        """Route a context signal to the appropriate subsystem.

        Args:
            signal: Either a ContextSignal or a plain string (wrapped as a
                    default ContextSignal with urgency=0.5).

        Returns:
            A ContextDecision with the chosen route, confidence, and strategy hints.
        """
        if isinstance(signal, str):
            signal = ContextSignal(content=signal, urgency=0.5)

        decision = self.classifier.classify(signal)
        if decision.confidence < self.confidence_threshold:
            return ContextDecision(
                signal=signal.content,
                route=ContextRoute.DIRECT_PASS,
                confidence=decision.confidence,
                reason=(
                    f"low confidence ({decision.confidence:.2f}); fell back from "
                    f"{decision.route.value} to direct pass"
                ),
                strategy_hints=("inline",),
            )
        return decision

    def route_batch(self, signals: list[ContextSignal]) -> list[ContextDecision]:
        """Route multiple context signals.

        Args:
            signals: List of context signals to route.

        Returns:
            List of ContextDecision objects, one per input signal.
        """
        return [self.route(s) for s in signals]


__all__ = [
    "ContextClassifier",
    "ContextDecision",
    "ContextRoute",
    "ContextRouter",
    "ContextSignal",
    "RuleBasedContextClassifier",
]
