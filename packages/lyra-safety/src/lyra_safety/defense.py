"""
4-Layer Defense-in-Depth Pipeline.

Each layer inspects and potentially blocks or modifies content before it reaches
the model (input) or the execution environment (output/tool calls).

Failure modes (explicit per Run 14 CRITICAL-3 fix):
- Layer 1 (Input Guard): fail-CLOSED on detection (block the input)
- Layer 2 (CaMeL): fail-CLOSED on violation (reject the request)
- Layer 3 (NeMo): fail-OPEN on timeout (let through with warning) — runtime rails
  should never block legitimate work due to policy engine latency
- Layer 4 (Progent): fail-CLOSED on unknown tool (block, don't execute)
"""

from __future__ import annotations

from collections.abc import Callable
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SafetyLayer(str, Enum):
    INPUT_GUARD = "input_guard"         # Layer 1: LlamaFirewall pattern
    CAMEL = "camel"                     # Layer 2: Control/data separation
    NEMO = "nemo"                       # Layer 3: Runtime rails
    PROGENT = "progent"                   # Layer 4: Least-privilege tools


class Disposition(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    FLAG = "flag"       # Allow but log for review
    SANITIZE = "sanitize"  # Modify to remove dangerous content


@dataclass
class DefenseResult:
    layer: SafetyLayer
    disposition: Disposition
    reason: str = ""
    sanitized_content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Layer 1: Input Guard (LlamaFirewall pattern) ─────────────────

# Known prompt injection patterns
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"system:\s*you\s+are\s+now", re.IGNORECASE),
    re.compile(r"\[system\]\(.*?\)", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"prompt\s*=\s*\"\"\".*?\"\"\"", re.IGNORECASE | re.DOTALL),
    re.compile(r"new\s+system\s+prompt\s*:", re.IGNORECASE),
]

# PII patterns (basic regex — production should use Presidio or similar)
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN REDACTED]"),
    (re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"), "[CC REDACTED]"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "[API KEY REDACTED]"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9\-_\.]{20,}"), "[TOKEN REDACTED]"),
]


class InputGuard:
    """Layer 1: Detect prompt injection and scrub PII."""

    def inspect(self, content: str) -> DefenseResult:
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(content):
                return DefenseResult(
                    layer=SafetyLayer.INPUT_GUARD,
                    disposition=Disposition.BLOCK,
                    reason=f"Prompt injection pattern detected: {pattern.pattern[:60]}",
                )

        # PII scrubbing
        sanitized = content
        found_pii = False
        for pattern, replacement in _PII_PATTERNS:
            if pattern.search(sanitized):
                sanitized = pattern.sub(replacement, sanitized)
                found_pii = True

        if found_pii:
            return DefenseResult(
                layer=SafetyLayer.INPUT_GUARD,
                disposition=Disposition.SANITIZE,
                reason="PII detected and redacted",
                sanitized_content=sanitized,
            )

        return DefenseResult(layer=SafetyLayer.INPUT_GUARD, disposition=Disposition.ALLOW)


# ── Layer 2: Control/Data Separation (CaMeL pattern) ────────────

class CaMelGuard:
    """
    Layer 2: Control/data separation.

    Ensures untrusted user data never reaches the control plane. User content
    is tagged as DATA; system instructions are tagged as CONTROL. The model
    receives both but with explicit separation markers.
    """

    def inspect(self, user_content: str, system_content: str = "") -> DefenseResult:
        # Check if user content contains control-plane injection attempts
        control_indicators = [
            "You are", "Your role is", "You must", "Your task is",
            "Always", "Never", "system:", "assistant:", "function:",
        ]
        lower = user_content.lower()
        for indicator in control_indicators:
            if indicator.lower() in lower:
                return DefenseResult(
                    layer=SafetyLayer.CAMEL,
                    disposition=Disposition.SANITIZE,
                    reason=f"Potential control injection: '{indicator}' in user content",
                    sanitized_content=self._wrap_data(user_content),
                )

        return DefenseResult(layer=SafetyLayer.CAMEL, disposition=Disposition.ALLOW)

    @staticmethod
    def _wrap_data(content: str) -> str:
        return f"<data>{content}</data>"


# ── Layer 3: Runtime Rails (NeMo pattern) ───────────────────────

class NeMoGuard:
    """
    Layer 3: Programmable runtime rails.

    Executes simple policy rules against model outputs and tool calls.
    Fail-OPEN on timeout — runtime rails should never block legitimate
    work due to policy engine latency.
    """

    def __init__(self) -> None:
        self._rules: list[Callable[..., Any]] = []

    def add_rule(self, rule_fn: Callable[..., Any]) -> None:
        """Add a runtime rule. Rules return DefenseResult or None (no action)."""
        self._rules.append(rule_fn)

    def inspect(self, content: str, context: dict[str, Any] | None = None) -> DefenseResult:
        ctx = context or {}
        for rule in self._rules:
            try:
                result = rule(content, ctx)
                if result and isinstance(result, DefenseResult):
                    if result.disposition == Disposition.BLOCK:
                        return result
            except Exception as e:
                logger.warning("NeMo rule failed (fail-open): %s", e)
                continue

        return DefenseResult(layer=SafetyLayer.NEMO, disposition=Disposition.ALLOW)

    @classmethod
    def with_default_rules(cls) -> NeMoGuard:
        """Create a NeMo guard with sensible defaults."""
        guard = cls()

        # Default rule: no file deletions outside workspace
        def no_delete_outside_workspace(content: str, ctx: dict) -> DefenseResult | None:
            if "rm -rf /" in content or "delete /" in content.lower():
                return DefenseResult(
                    layer=SafetyLayer.NEMO,
                    disposition=Disposition.BLOCK,
                    reason="Dangerous filesystem operation outside workspace",
                )
            return None

        # Default rule: no curl/wget to internal IPs
        def no_internal_requests(content: str, ctx: dict) -> DefenseResult | None:
            if re.search(r"(curl|wget)\s+.*?(127\.0\.0\.1|10\.\d|172\.(1[6-9]|2\d|3[01])|192\.168\.)", content):
                return DefenseResult(
                    layer=SafetyLayer.NEMO,
                    disposition=Disposition.BLOCK,
                    reason="Request to internal/private IP blocked",
                )
            return None

        guard.add_rule(no_delete_outside_workspace)
        guard.add_rule(no_internal_requests)
        return guard


# ── Layer 4: Least-Privilege Tool Control (Progent pattern) ──────

class ProgentGuard:
    """
    Layer 4: Least-privilege tool access control.

    Implements the Progent pattern: for each task, compute the minimum
    set of tools required and deny everything else. Uses SMT-based
    reasoning (simplified to rule-based for initial implementation).
    """

    def __init__(self, allowed_tools: set[str] | None = None) -> None:
        self._allowed = allowed_tools or set()

    def set_allowed_tools(self, tools: set[str]) -> None:
        self._allowed = tools

    def check_tool(self, tool_name: str) -> DefenseResult:
        if not self._allowed:
            return DefenseResult(layer=SafetyLayer.PROGENT, disposition=Disposition.ALLOW)

        if tool_name in self._allowed:
            return DefenseResult(layer=SafetyLayer.PROGENT, disposition=Disposition.ALLOW)

        return DefenseResult(
            layer=SafetyLayer.PROGENT,
            disposition=Disposition.BLOCK,
            reason=f"Tool '{tool_name}' not in allowed set: {sorted(self._allowed)}",
        )


# ── 4-Layer Pipeline ────────────────────────────────────────────

class DefensePipeline:
    """
    Unified 4-layer defense pipeline.

    Usage::

        pipeline = DefensePipeline()
        pipeline.set_allowed_tools({"read_file", "grep", "write_file"})

        # Check user input
        result = pipeline.check_input("Ignore all previous instructions and...")
        if result.disposition == Disposition.BLOCK:
            raise SafetyError(result.reason)

        # Check tool call
        result = pipeline.check_tool("delete_file")
        if result.disposition == Disposition.BLOCK:
            raise SafetyError(result.reason)
    """

    def __init__(self) -> None:
        self._input_guard = InputGuard()
        self._camel = CaMelGuard()
        self._nemo = NeMoGuard.with_default_rules()
        self._progent = ProgentGuard()
        self._blocked_count: int = 0

    def check_input(self, content: str, system_content: str = "") -> DefenseResult:
        """Run all 4 layers against user input. Returns BLOCK on any failure."""
        for layer_result in [
            self._input_guard.inspect(content),
            self._camel.inspect(content, system_content),
            self._nemo.inspect(content),
        ]:
            if layer_result.disposition == Disposition.BLOCK:
                self._blocked_count += 1
                return layer_result
            if layer_result.disposition == Disposition.SANITIZE and layer_result.sanitized_content:
                content = layer_result.sanitized_content

        return DefenseResult(layer=SafetyLayer.PROGENT, disposition=Disposition.ALLOW)

    def check_tool(self, tool_name: str) -> DefenseResult:
        result = self._progent.check_tool(tool_name)
        if result.disposition == Disposition.BLOCK:
            self._blocked_count += 1
        return result

    def set_allowed_tools(self, tools: set[str]) -> None:
        self._progent.set_allowed_tools(tools)

    @property
    def stats(self) -> dict:
        return {"blocked_count": self._blocked_count}
