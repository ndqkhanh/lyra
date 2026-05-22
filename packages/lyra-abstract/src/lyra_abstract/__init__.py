"""Abstract Reasoning — pattern recognition beyond surface, analogical thinking, rule induction."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)
__all__ = ["AbstractPattern", "AbstractReasoningAgent"]

@dataclass
class AbstractPattern:
    rule: str; examples: list[str]; confidence: float = 0.5

class AbstractReasoningAgent:
    def __init__(self):
        self.patterns: list[AbstractPattern] = []

    def induce_rule(self, examples: list[str]) -> Optional[AbstractPattern]:
        if not examples: return None
        words = [e.lower().split() for e in examples]
        common = set(words[0]) if words else set()
        for w in words[1:]:
            common &= set(w)
        rule = f"All items contain: {', '.join(sorted(common))}" if common else "No common pattern detected"
        pattern = AbstractPattern(rule=rule, examples=examples, confidence=0.3 + 0.7 * (len(common) / max(len(words[0]), 1)))
        self.patterns.append(pattern)
        return pattern

    def apply_pattern(self, pattern: AbstractPattern, new_item: str) -> bool:
        return any(c in new_item.lower() for c in pattern.rule.lower().split(":")[-1].split(",")) if ":" in pattern.rule else False

    @property
    def stats(self) -> dict: return {"patterns_induced": len(self.patterns)}
