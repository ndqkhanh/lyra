"""Deception Detection — inconsistency, evasion, fabrication, omission, misdirection.

As agents become more autonomous, detecting deception becomes critical.
Extends lyra-verification-mesh with behavioral honesty checks.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "DeceptionSignal",
    "DeceptionScore",
    "DeceptionDetector",
]


@dataclass
class DeceptionSignal:
    signal_type: str
    severity: float
    evidence: str


@dataclass
class DeceptionScore:
    agent_id: str
    score: float
    signals: list[DeceptionSignal]
    verdict: str = "honest"


class DeceptionDetector:
    """Detect deception signals in agent outputs."""

    SIGNAL_TYPES = ["inconsistency", "evasion", "fabrication", "omission", "misdirection"]

    def __init__(self):
        self._checks_run = 0

    def analyze(self, agent_id: str, statement: str, context: Optional[dict] = None) -> DeceptionScore:
        self._checks_run += 1
        signals = []

        signals.extend(self._check_inconsistency(statement, context))
        signals.extend(self._check_evasion(statement))
        signals.extend(self._check_fabrication(statement))
        signals.extend(self._check_omission(statement, context))
        signals.extend(self._check_misdirection(statement))

        score = min(1.0, sum(s.severity for s in signals) / 5.0)
        verdict = "honest" if score < 0.2 else "suspicious" if score < 0.5 else "deceptive"

        return DeceptionScore(agent_id=agent_id, score=score, signals=signals, verdict=verdict)

    def _check_inconsistency(self, text: str, context: Optional[dict]) -> list[DeceptionSignal]:
        signals = []
        if context and "previous_statements" in context:
            prev = context["previous_statements"]
            for p in prev[-3:]:
                if self._contradicts(text, p):
                    signals.append(DeceptionSignal("inconsistency", 0.6, f"Contradicts earlier statement: {p[:50]}"))
        return signals

    def _check_evasion(self, text: str) -> list[DeceptionSignal]:
        signals = []
        evasion_patterns = [
            r"i (can'?t|won'?t|don'?t know)",
            r"that'?s (unclear|uncertain|not clear)",
            r"i'?m not (sure|certain|confident)",
            r"let me (check|look|think about it)",
            r"it (depends|varies|is complicated)",
        ]
        for pattern in evasion_patterns:
            if re.search(pattern, text.lower()):
                signals.append(DeceptionSignal("evasion", 0.3, f"Evasion pattern: {pattern}"))
                break
        return signals

    def _check_fabrication(self, text: str) -> list[DeceptionSignal]:
        signals = []
        fabrication_patterns = [
            r"according to (unpublished|internal|confidential)",
            r"studies show.*without (citation|reference)",
            r"research indicates.*(no source|unverified)",
            r"I have access to (data|information).*that",
            r"(never|always|everyone|nobody).*proven",
        ]
        for pattern in fabrication_patterns:
            if re.search(pattern, text.lower()):
                signals.append(DeceptionSignal("fabrication", 0.8, f"Possible fabrication: {pattern}"))
                break
        return signals

    def _check_omission(self, text: str, context: Optional[dict]) -> list[DeceptionSignal]:
        signals = []
        if context and "expected_topics" in context:
            for topic in context["expected_topics"]:
                if topic.lower() not in text.lower():
                    signals.append(DeceptionSignal("omission", 0.4, f"Missing expected topic: {topic}"))
        return signals

    def _check_misdirection(self, text: str) -> list[DeceptionSignal]:
        signals = []
        misdirection_patterns = [
            r"(that's |this is )?(not |doesn't |isn't )?(relevant|important)",
            r"you should focus on",
            r"the real (issue|problem|question) is",
            r"actually,? (the|what|that)",
            r"let me (rephrase|reframe|redirect)",
        ]
        for pattern in misdirection_patterns:
            if re.search(pattern, text.lower()):
                signals.append(DeceptionSignal("misdirection", 0.5, f"Misdirection pattern: {pattern}"))
                break
        return signals

    def _contradicts(self, text_a: str, text_b: str) -> bool:
        sentences_a = set(s.strip().lower() for s in text_a.split('.') if len(s) > 20)
        sentences_b = set(s.strip().lower() for s in text_b.split('.') if len(s) > 20)
        # Simple contradiction check via negation overlap
        for sa in sentences_a:
            for sb in sentences_b:
                words_a = set(sa.split())
                words_b = set(sb.split())
                overlap = words_a & words_b
                if len(overlap) > 3 and "not" in words_a and "not" not in words_b:
                    return True
                if len(overlap) > 3 and "not" in words_b and "not" not in words_a:
                    return True
        return False

    @property
    def stats(self) -> dict[str, Any]:
        return {"checks_run": self._checks_run}
