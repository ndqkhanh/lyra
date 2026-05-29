"""Continuous Prompt-Level (CPL) verification.

Real-time prompt/output checking with rule-based and ML-based checks,
streaming verification for long outputs, and inline correction suggestions.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from .verification_mesh import VerificationLayer, VerificationResult, VerificationStatus

logger = logging.getLogger(__name__)


# ── Data classes ────────────────────────────────────────────────────────


class CheckSeverity(Enum):
    """Severity of a CPL check failure."""

    INFO = auto()
    WARNING = auto()
    BLOCKING = auto()


@dataclass
class CPLRule:
    """A single CPL check rule.

    Attributes:
        name: Unique rule name.
        description: What the rule checks.
        pattern: Optional regex pattern to match.
        check_fn: Optional callable for custom checks.
        severity: What happens when the rule triggers.
        enabled: Whether this rule is active.
    """

    name: str
    description: str = ""
    pattern: str | None = None
    check_fn: Callable[[str], tuple[bool, str]] | None = None
    severity: CheckSeverity = CheckSeverity.WARNING
    enabled: bool = True

    def check(self, text: str) -> tuple[bool, str]:
        """Check text against this rule.

        Returns:
            Tuple of (passed, message).
        """
        if self.check_fn:
            return self.check_fn(text)

        if self.pattern:
            compiled = re.compile(self.pattern, re.IGNORECASE | re.MULTILINE)
            match = compiled.search(text)
            if match:
                return False, f"Pattern '{self.name}' matched: {match.group()[:100]}"
            return True, ""

        return True, ""


@dataclass
class CPLCorrection:
    """An inline correction suggestion.

    Attributes:
        start_index: Start position in the text.
        end_index: End position in the text.
        original: Original text.
        suggested: Suggested replacement.
        reason: Why this correction is suggested.
        confidence: Confidence in the correction (0-1).
    """

    start_index: int
    end_index: int
    original: str
    suggested: str
    reason: str = ""
    confidence: float = 0.5


# ── CPL Verifier ────────────────────────────────────────────────────────


class CPLVerifier:
    """Real-time continuous prompt-level verification.

    Checks prompts and outputs as they are generated, applying rules
    for safety, consistency, and quality. Supports streaming verification
    and inline correction suggestions.
    """

    def __init__(self) -> None:
        self._rules: dict[str, CPLRule] = {}
        self._corrections: list[CPLCorrection] = []
        self._verification_callbacks: list[
            Callable[[str, VerificationResult], Any]
        ] = []
        self._streaming_buffer: str = ""

        # Register default safety rules
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """Register sensible default rules for safety and quality."""
        defaults = [
            CPLRule(
                name="no_injection",
                description="Detect common prompt injection patterns",
                pattern=r"(ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|commands?))",
                severity=CheckSeverity.BLOCKING,
            ),
            CPLRule(
                name="no_hallucination_markers",
                description="Detect hallucination markers like 'I don't know the answer but...'",
                pattern=r"I(?:'m|\s+am)\s+not\s+(?:sure|certain|confident).*but",
                severity=CheckSeverity.WARNING,
            ),
            CPLRule(
                name="no_unsafe_code",
                description="Detect dangerous code patterns",
                pattern=r"(rm\s+-rf\s+/|sudo\s+rm|:\(\)\s*\{\s*:\|:&\s*\};:)",
                severity=CheckSeverity.BLOCKING,
            ),
            CPLRule(
                name="min_length",
                description="Output should be meaningful (not empty/too short)",
                check_fn=lambda text: (
                    len(text.strip()) >= 2,
                    "Output too short" if len(text.strip()) < 2 else "",
                ),
                severity=CheckSeverity.INFO,
            ),
        ]
        for rule in defaults:
            self.add_rule(rule)

    # ── Rule management ────────────────────────────────────────────────

    def add_rule(self, rule: CPLRule) -> None:
        """Add a verification rule."""
        self._rules[rule.name] = rule
        logger.debug("CPL rule '%s' added (severity=%s)", rule.name, rule.severity.name)

    def remove_rule(self, name: str) -> bool:
        """Remove a verification rule."""
        if name in self._rules:
            del self._rules[name]
            return True
        return False

    def enable_rule(self, name: str) -> bool:
        """Enable a rule."""
        if name in self._rules:
            self._rules[name].enabled = True
            return True
        return False

    def disable_rule(self, name: str) -> bool:
        """Disable a rule."""
        if name in self._rules:
            self._rules[name].enabled = False
            return True
        return False

    def list_rules(self) -> list[dict[str, Any]]:
        """List all rules with their status."""
        return [
            {
                "name": r.name,
                "description": r.description,
                "severity": r.severity.name,
                "enabled": r.enabled,
            }
            for r in self._rules.values()
        ]

    # ── Verification ────────────────────────────────────────────────────

    async def verify_prompt(self, text: str) -> VerificationResult:
        """Verify an input prompt against all rules.

        Args:
            text: The prompt text to verify.

        Returns:
            VerificationResult with pass/fail status.
        """
        all_messages: list[str] = []
        worst_severity = CheckSeverity.INFO
        confidence = 1.0

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            passed, message = rule.check(text)
            if not passed:
                all_messages.append(f"[{rule.name}] {message}")

                if rule.severity.value > worst_severity.value:
                    worst_severity = rule.severity

                # Reduce confidence based on severity
                if rule.severity == CheckSeverity.BLOCKING:
                    confidence *= 0.5
                elif rule.severity == CheckSeverity.WARNING:
                    confidence *= 0.8

        if not all_messages:
            return VerificationResult(
                status=VerificationStatus.PASS,
                layer=VerificationLayer.DURING_EXECUTION,
                verifier="CPLVerifier",
                check_name="prompt_check",
                message="All prompt checks passed",
                confidence=1.0,
            )

        status_map = {
            CheckSeverity.INFO: VerificationStatus.WARN,
            CheckSeverity.WARNING: VerificationStatus.WARN,
            CheckSeverity.BLOCKING: VerificationStatus.FAIL,
        }

        return VerificationResult(
            status=status_map.get(worst_severity, VerificationStatus.WARN),
            layer=VerificationLayer.DURING_EXECUTION,
            verifier="CPLVerifier",
            check_name="prompt_check",
            message="; ".join(all_messages),
            confidence=confidence,
            details={
                "rule_failures": len(all_messages),
                "total_rules": len([r for r in self._rules.values() if r.enabled]),
            },
        )

    async def verify_output(self, text: str) -> VerificationResult:
        """Verify a generated output against all rules.

        Args:
            text: The output text to verify.

        Returns:
            VerificationResult with pass/fail and corrections.
        """
        result = await self.verify_prompt(text)  # Reuse prompt check logic
        result.check_name = "output_check"
        result.verifier = "CPLVerifier"

        # Add length-based quality check
        if len(text.strip()) < 2:
            result.status = VerificationStatus.WARN
            result.message += "; Output is very short"
            result.confidence *= 0.7

        return result

    async def verify_event(self, event: dict[str, Any]) -> VerificationResult:
        """Verify a trace event.

        Args:
            event: The execution trace event.

        Returns:
            VerificationResult.
        """
        messages: list[str] = []

        # Check for error events
        event_type = str(event.get("type", "")).lower()
        if "error" in event_type:
            messages.append(f"Error event detected: {event.get('message', 'unknown error')}")

        # Check for unexpected field values
        if "status" in event and event["status"] in ("failed", "cancelled"):
            messages.append(f"Event with {event['status']} status")

        if not messages:
            return VerificationResult(
                status=VerificationStatus.PASS,
                layer=VerificationLayer.DURING_EXECUTION,
                verifier="CPLVerifier",
                check_name="event_check",
                message="Event OK",
                confidence=1.0,
                details={"event_type": event_type},
            )

        return VerificationResult(
            status=VerificationStatus.WARN,
            layer=VerificationLayer.DURING_EXECUTION,
            verifier="CPLVerifier",
            check_name="event_check",
            message="; ".join(messages),
            confidence=0.7,
            details={"event_type": event_type},
        )

    # ── Streaming verification ──────────────────────────────────────────

    async def verify_stream(self, token: str) -> VerificationResult | None:
        """Verify a token as it arrives in a stream.

        Accumulates tokens in a buffer and runs light-weight checks
        on recent context.

        Args:
            token: The new token.

        Returns:
            VerificationResult if an issue is detected, None otherwise.
        """
        self._streaming_buffer += token

        # Only check periodically (every ~50 chars) to avoid overhead
        if len(self._streaming_buffer) % 50 > len(token) + 5:
            return None

        # Run lightweight regex checks
        for rule in self._rules.values():
            if not rule.enabled or rule.severity != CheckSeverity.BLOCKING:
                continue
            if rule.pattern:
                compiled = re.compile(rule.pattern, re.IGNORECASE)
                if compiled.search(self._streaming_buffer):
                    self._streaming_buffer = ""
                    return VerificationResult(
                        status=VerificationStatus.FAIL,
                        layer=VerificationLayer.DURING_EXECUTION,
                        verifier="CPLVerifier",
                        check_name="streaming_check",
                        message=f"Rule '{rule.name}' triggered during streaming",
                        confidence=0.5,
                    )

        return None

    def reset_stream_buffer(self) -> None:
        """Reset the streaming verification buffer."""
        self._streaming_buffer = ""

    # ── Correction suggestions ──────────────────────────────────────────

    def suggest_corrections(self, text: str) -> list[CPLCorrection]:
        """Generate inline correction suggestions for text.

        Args:
            text: The text to analyze.

        Returns:
            List of suggested corrections.
        """
        corrections: list[CPLCorrection] = []

        # Common corrections
        patterns = [
            (r"it's\s+it's", "it's its", "incorrect contraction", 0.9),
            (r"their\s+their", "their there", "incorrect homophone", 0.9),
            (r"your\s+your", "your you're", "incorrect homophone", 0.9),
            (r"\b[Aa]lso\b.*\b[Aa]lso\b", "(repeated 'also')", "redundant word", 0.7),
        ]

        for pattern, suggestion, reason, confidence in patterns:
            compiled = re.compile(pattern, re.IGNORECASE)
            for match in compiled.finditer(text):
                corrections.append(CPLCorrection(
                    start_index=match.start(),
                    end_index=match.end(),
                    original=match.group(),
                    suggested=suggestion,
                    reason=reason,
                    confidence=confidence,
                ))

        return corrections

    # ── Statistics ──────────────────────────────────────────────────────

    @property
    def rule_count(self) -> int:
        """Number of registered rules."""
        return len(self._rules)

    @property
    def enabled_rule_count(self) -> int:
        """Number of enabled rules."""
        return sum(1 for r in self._rules.values() if r.enabled)
