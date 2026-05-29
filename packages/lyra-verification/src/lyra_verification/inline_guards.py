"""Layer 1 — Inline Guards (<200 ms target).

Implements PII detection, toxicity scoring, NLI entailment, token entropy,
and prompt-injection detection. Each guard returns a structured result.
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from lyra_verification.models import SecurityCheck, Verdict, VerificationResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reusable patterns
# ---------------------------------------------------------------------------

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-.\s]?){3}\d{4}\b")
_IP_ADDRESS_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

_TOXIC_PATTERNS: list[tuple[re.Pattern, float]] = [
    (re.compile(r"(?i)\b(hate|stupid|idiot|dumb|moron|trash)\b"), 0.4),
    (re.compile(r"(?i)\b(kill|die|murder|destroy)\b.*?\b(you|everyone|them)\b"), 0.7),
    (re.compile(r"(?i)\b(fuck|shit|asshole|bastard)\b"), 0.5),
]

_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b"),
    re.compile(r"(?i)\bdisregard\s+(all\s+)?(previous|prior|above)\b"),
    re.compile(r"(?i)\bforget\s+(everything|all)\b"),
    re.compile(r"(?i)\brewrite\s+(your\s+)?(system\s+)?prompt\b"),
    re.compile(r"(?i)\byou\s+are\s+(now|not)\s+(an?\s+)?\w+\s*,\s*(not\s+)?an?\s+ai\b"),
    re.compile(r"(?i)\bnew\s+instructions?\s*:\s*"),
    re.compile(r"(?i)\boutput\s+the\s+(above|following)\s+(text|instructions?)\b"),
    re.compile(r"(?i)\bpwned|hacked|breach|exploit\b"),
]


@dataclass(frozen=True)
class InlineGuardResult:
    """Aggregated result from all Layer 1 guards."""

    passed: bool
    pii_redacted: str
    toxicity_score: float
    toxicity_details: dict[str, float]
    nli_entailment_score: float
    token_entropy: float
    injection_detected: bool
    injection_details: list[str]
    latency_ms: float
    checks: Sequence[SecurityCheck] = field(default_factory=list)
    num_pii_entities: int = 0


class InlineGuardSystem:
    """Layer 1 verification — all guards run inline with <200 ms target."""

    def __init__(self) -> None:
        self._nli_vocab: set[str] = {
            "therefore",
            "consequently",
            "thus",
            "hence",
            "accordingly",
            "implies",
            "entails",
            "follows",
            "so",
            "because",
        }

    # ------------------------------------------------------------------
    # PII detection & redaction
    # ------------------------------------------------------------------
    def check_pii(self, text: str) -> tuple[str, list[str], int]:
        """Detect and redact PII from *text*.

        Returns
        -------
        redacted : str
            Text with PII replaced by placeholders.
        found : list of str
            Human-readable descriptions of each finding.
        count : int
            Number of unique PII entities detected.
        """
        findings: list[str] = []
        redacted = text

        emails = _EMAIL_PATTERN.findall(redacted)
        if emails:
            findings.append(f"email(s): {len(emails)} found")
            redacted = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted)

        ssns = _SSN_PATTERN.findall(redacted)
        if ssns:
            findings.append(f"SSN(s): {len(ssns)} found")
            redacted = _SSN_PATTERN.sub("[REDACTED_SSN]", redacted)

        phones = _PHONE_PATTERN.findall(redacted)
        if phones:
            findings.append(f"phone(s): {len(phones)} found")
            redacted = _PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)

        cards = _CREDIT_CARD_PATTERN.findall(redacted)
        if cards:
            findings.append(f"credit card(s): {len(cards)} found")
            redacted = _CREDIT_CARD_PATTERN.sub("[REDACTED_CC]", redacted)

        ips = _IP_ADDRESS_PATTERN.findall(redacted)
        if ips:
            findings.append(f"IP address(es): {len(ips)} found")
            redacted = _IP_ADDRESS_PATTERN.sub("[REDACTED_IP]", redacted)

        total_count = len(emails) + len(ssns) + len(phones) + len(cards) + len(ips)
        return redacted, findings, total_count

    # ------------------------------------------------------------------
    # Toxicity
    # ------------------------------------------------------------------
    def check_toxicity(self, text: str) -> tuple[float, dict[str, float]]:
        """Compute a toxicity score in [0, 1] using keyword pattern matching.

        Returns (max_score, breakdown) where *breakdown* maps each matched
        pattern label to its partial score.
        """
        breakdown: dict[str, float] = {}
        for pattern, weight in _TOXIC_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                breakdown[pattern.pattern] = weight * min(len(matches), 3) / 3.0
        if not breakdown:
            return 0.0, {}
        return min(max(breakdown.values()), 1.0), breakdown

    # ------------------------------------------------------------------
    # Simple NLI entailment heuristic
    # ------------------------------------------------------------------
    def check_nli_entailment(self, premise: str, hypothesis: str) -> float:
        """Heuristic NLI score based on lexical overlap + entailment cues.

        Returns a score in [0, 1] where 1 = strong entailment.
        This is a lightweight stand-in for a full NLI model.
        """
        if not premise or not hypothesis:
            return 0.5

        premise_words = set(premise.lower().split())
        hypothesis_words = set(hypothesis.lower().split())
        if not hypothesis_words:
            return 0.5

        overlap = premise_words & hypothesis_words
        jaccard = len(overlap) / len(hypothesis_words)

        # Boost if the premise contains entailment-indicating connectives
        cue_boost = 0.0
        for word in hypothesis_words:
            if word in self._nli_vocab:
                cue_boost = 0.15
                break

        return min(jaccard + cue_boost, 1.0)

    # ------------------------------------------------------------------
    # Token entropy
    # ------------------------------------------------------------------
    def compute_token_entropy(self, tokens: Sequence[str]) -> float:
        """Compute normalised Shannon entropy over token frequencies.

        Returns a value in [0, 1] where 1 = maximum uncertainty.
        """
        if not tokens:
            return 0.0

        n = len(tokens)
        freq: dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1

        entropy = 0.0
        for count in freq.values():
            p = count / n
            if p > 0:
                entropy -= p * math.log2(p)

        max_entropy = math.log2(len(freq)) if len(freq) > 1 else 1.0
        normalised = entropy / max_entropy if max_entropy > 0 else 0.0
        return min(normalised, 1.0)

    # ------------------------------------------------------------------
    # Prompt injection
    # ------------------------------------------------------------------
    def detect_prompt_injection(self, prompt: str) -> tuple[bool, list[str]]:
        """Detect prompt-injection patterns.

        Returns (detected, details) where *detected* is True if any
        injection pattern matched, and *details* lists the patterns hit.
        """
        details: list[str] = []
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(prompt):
                details.append(f"matched: {pattern.pattern}")
        return len(details) > 0, details

    # ------------------------------------------------------------------
    # Aggregate
    # ------------------------------------------------------------------
    def run_all_guards(self, text: str) -> InlineGuardResult:
        """Run every Layer 1 guard on *text* and return an aggregate result.

        Performance target: <200 ms wall time.
        """
        start = time.perf_counter()

        # Run all guards (none should block)
        redacted, pii_findings, pii_count = self.check_pii(text)
        tox_score, tox_breakdown = self.check_toxicity(text)
        nli_score = self.check_nli_entailment(text, text)
        tokens = text.split()
        entropy = self.compute_token_entropy(tokens)
        injection_detected, injection_details = self.detect_prompt_injection(text)

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Build individual check records
        checks: list[SecurityCheck] = []
        checks.append(
            SecurityCheck(
                check_type="pii",
                passed=pii_count == 0,
                details="; ".join(pii_findings) if pii_findings else "no PII detected",
            )
        )
        checks.append(
            SecurityCheck(
                check_type="toxicity",
                passed=tox_score < 0.5,
                details=f"toxicity={tox_score:.3f}",
            )
        )
        checks.append(
            SecurityCheck(
                check_type="nli_entailment",
                passed=nli_score >= 0.3,
                details=f"nli_entailment={nli_score:.3f}",
            )
        )
        checks.append(
            SecurityCheck(
                check_type="injection",
                passed=not injection_detected,
                details=(
                    "; ".join(injection_details) if injection_details else "no injection detected"
                ),
            )
        )

        overall_passed = all(c.passed for c in checks)

        # Log if we exceeded the 200 ms budget
        if elapsed_ms > 200.0:
            logger.warning("Inline guard budget exceeded: %.1f ms (target <200 ms)", elapsed_ms)

        return InlineGuardResult(
            passed=overall_passed,
            pii_redacted=redacted,
            toxicity_score=tox_score,
            toxicity_details=tox_breakdown,
            nli_entailment_score=nli_score,
            token_entropy=entropy,
            injection_detected=injection_detected,
            injection_details=injection_details,
            latency_ms=elapsed_ms,
            checks=checks,
            num_pii_entities=pii_count,
        )

    def run_all_guards_as_verification_result(self, text: str) -> VerificationResult:
        """Convenience wrapper that returns a ``VerificationResult``."""
        guard = self.run_all_guards(text)
        return VerificationResult(
            layer=1,
            verdict=Verdict.PASS if guard.passed else Verdict.FAIL,
            confidence=1.0 - guard.toxicity_score if not guard.injection_detected else 0.0,
            evidence=f"inline guards: passed={guard.passed}, "
            f"toxicity={guard.toxicity_score:.3f}, "
            f"injection={guard.injection_detected}, "
            f"entropy={guard.token_entropy:.3f}",
            latency_ms=guard.latency_ms,
            checks=list(guard.checks),
        )
