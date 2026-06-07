"""AdversarialQualityGate — challenges outputs to find weaknesses before release."""

import re

from .models import AttackPattern, GateResult


class AdversarialQualityGate:
    """Applies adversarial challenge patterns to detect output weaknesses.

    Five attack patterns inspired by red-teaming research:
    1. Contradiction — provide contradictory premises, check consistency
    2. Ambiguity — test handling of deliberately vague inputs
    3. Edge case — probe boundary conditions and corner cases
    4. Prompt injection — test resistance to instruction override
    5. Hallucination trap — ask about non-existent facts, check honesty
    """

    def __init__(self, resilience_threshold: float = 0.6):
        self._results: dict[str, GateResult] = {}
        self._resilience_threshold = resilience_threshold

    def challenge(self, pattern: AttackPattern, content: str) -> GateResult:
        """Run a specific adversarial challenge against content."""
        weaknesses: list[str] = []

        if pattern == AttackPattern.CONTRADICTION:
            weaknesses = self._check_contradiction(content)
        elif pattern == AttackPattern.AMBIGUITY:
            weaknesses = self._check_ambiguity(content)
        elif pattern == AttackPattern.EDGE_CASE:
            weaknesses = self._check_edge_case(content)
        elif pattern == AttackPattern.PROMPT_INJECTION:
            weaknesses = self._check_prompt_injection(content)
        elif pattern == AttackPattern.HALLUCINATION_TRAP:
            weaknesses = self._check_hallucination(content)

        passed = len(weaknesses) == 0
        resilience = 1.0 - min(len(weaknesses) * 0.2, 1.0)

        result = GateResult(
            pattern=pattern,
            passed=passed,
            weaknesses_found=tuple(weaknesses),
            resilience_score=round(resilience, 4),
        )
        self._results[pattern.value] = result
        return result

    def full_audit(self, content: str) -> dict[str, GateResult]:
        """Run all five attack patterns against content."""
        import uuid

        results: dict[str, GateResult] = {}
        for pattern in AttackPattern:
            result = self.challenge(pattern, content)
            self._results[f"{pattern.value}_{uuid.uuid4().hex[:8]}"] = result
            results[pattern.value] = result
        return results

    @staticmethod
    def _check_contradiction(content: str) -> list[str]:
        weaknesses: list[str] = []
        lower = content.lower()
        if "however" in lower and re.search(r"(always|never|all|none|every)", lower):
            weaknesses.append("Uses absolute qualifiers near contrastive language")
        if re.findall(r"\d+%", content):
            percentages = re.findall(r"(\d+)%", content)
            if len(set(percentages)) > 3:
                weaknesses.append("Multiple percentage claims without source anchoring")
        return weaknesses

    @staticmethod
    def _check_ambiguity(content: str) -> list[str]:
        weaknesses: list[str] = []
        vague = ["might", "could", "possibly", "maybe", "potentially", "seems", "appears"]
        count = sum(1 for v in vague if v in content.lower())
        if count >= 4:
            weaknesses.append(f"High hedging ({count} vague qualifiers)")
        if "it depends" in content.lower():
            weaknesses.append("Non-committal stance without conditions specified")
        return weaknesses

    @staticmethod
    def _check_edge_case(content: str) -> list[str]:
        weaknesses: list[str] = []
        lower = content.lower()
        if "always" in lower and "except" not in lower:
            weaknesses.append("Unconditional 'always' without exceptions noted")
        if "never" in lower and "unless" not in lower:
            weaknesses.append("Unconditional 'never' without caveats")
        if re.search(r"(all|every)\s+\w+", lower) and "some" not in lower:
            weaknesses.append("Universal quantifier without boundary acknowledgment")
        return weaknesses

    @staticmethod
    def _check_prompt_injection(content: str) -> list[str]:
        weaknesses: list[str] = []
        injection_markers = [
            "ignore previous", "system prompt", "you are now",
            "disregard", "override", "new instructions",
        ]
        for marker in injection_markers:
            if marker in content.lower():
                weaknesses.append(f"Injection pattern echoed: '{marker}'")
        return weaknesses

    @staticmethod
    def _check_hallucination(content: str) -> list[str]:
        weaknesses: list[str] = []
        lower = content.lower()
        fabricated_markers = [
            "according to a 2027 study",
            "as shown by dr. nonexistent",
            "the journal of fabricated",
        ]
        for marker in fabricated_markers:
            if marker in lower:
                weaknesses.append(f"Potentially fabricated reference: '{marker}'")
        if re.search(r"(?:study|research|paper)\s+(?:published\s+)?in\s+20\d{2}", lower):
            if "http" not in lower:
                weaknesses.append("Cites year-specific research without URL or DOI")
        return weaknesses

    def overall_resilience(self) -> float:
        if not self._results:
            return 1.0
        return round(
            sum(r.resilience_score for r in self._results.values()) / len(self._results), 4
        )

    def failed_gates(self) -> list[GateResult]:
        return [r for r in self._results.values() if not r.passed]

    @property
    def result_count(self) -> int:
        return len(self._results)
