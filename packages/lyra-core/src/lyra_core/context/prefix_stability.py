"""Prefix stability checker — detect conditions that bust the prompt cache.

Research grounding: §5.1 (Anthropic prompt caching mechanics), Anthropic April
2026 postmortem — clear_thinking_20251015 with keep:1 fired every turn, dropped
thinking blocks, and busted the cache silently for weeks. "The cache prefix is
sacred." (§11 design choices).

Detected cache-busters:
  - Timestamps or epoch integers embedded above the breakpoint
  - Request-ID strings in the stable prefix
  - Thinking blocks toggled on/off across turns
  - cache_control breakpoint shifting between calls
  - No cache_control block present at all
  - Non-deterministic terms (uuid, nonce, random, salt) in the prefix
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence


class StabilityIssue(str, Enum):
    TIMESTAMP_IN_PREFIX = "timestamp_in_prefix"
    REQUEST_ID_IN_PREFIX = "request_id_in_prefix"
    THINKING_BLOCK_TOGGLE = "thinking_block_toggle"
    BREAKPOINT_SHIFT = "breakpoint_shift"
    NONDETERMINISTIC_CONTENT = "nondeterministic_content"
    MISSING_CACHE_CONTROL = "missing_cache_control"


# ISO-8601 timestamps and Unix epoch integers (10–13 digits)
_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
    r"|\b\d{10,13}\b"
)
_REQUEST_ID_RE = re.compile(
    r"\b(?:req_|request_id|x-request-id)[_-]?[a-f0-9-]{8,}\b",
    re.IGNORECASE,
)
_NONDETERMINISTIC_RE = re.compile(
    r"\b(?:random|uuid|nonce|salt)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class StabilityReport:
    """Result of one prefix stability check."""

    is_stable: bool
    issues: tuple[StabilityIssue, ...]
    details: tuple[str, ...]
    recommended_breakpoint: int  # msg index after which to place cache_control

    def summary(self) -> str:
        if self.is_stable:
            return (
                f"Prefix is cache-stable "
                f"(breakpoint after message {self.recommended_breakpoint})"
            )
        lines = [f"Cache-busting issues detected ({len(self.issues)}):"]
        for issue, detail in zip(self.issues, self.details):
            lines.append(f"  [{issue.value}] {detail}")
        return "\n".join(lines)


class PrefixStabilityChecker:
    """Scan outgoing messages for known cache-busting conditions.

    Usage::
        checker = PrefixStabilityChecker()
        report = checker.check(messages, previous_breakpoint=2)
        if not report.is_stable:
            logging.warning(report.summary())
    """

    def check(
        self,
        messages: Sequence[dict[str, Any]],
        *,
        previous_breakpoint: int | None = None,
    ) -> StabilityReport:
        issues: list[StabilityIssue] = []
        details: list[str] = []

        bp = self._find_breakpoint(messages)
        prefix = list(messages[:bp]) if bp else list(messages)

        self._check_timestamps(prefix, issues, details)
        self._check_request_ids(prefix, issues, details)
        self._check_nondeterministic(prefix, issues, details)
        self._check_thinking_toggle(messages, issues, details)
        self._check_missing_cache_control(messages, issues, details)

        if previous_breakpoint is not None and bp != previous_breakpoint:
            issues.append(StabilityIssue.BREAKPOINT_SHIFT)
            details.append(
                f"cache_control breakpoint moved from {previous_breakpoint} "
                f"to {bp} — this invalidates the cached prefix"
            )

        return StabilityReport(
            is_stable=len(issues) == 0,
            issues=tuple(issues),
            details=tuple(details),
            recommended_breakpoint=bp,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_breakpoint(self, messages: Sequence[dict[str, Any]]) -> int:
        """Return the index after the last message containing cache_control."""
        bp = 0
        for i, msg in enumerate(messages):
            content = msg.get("content", [])
            if isinstance(content, list) and any(
                isinstance(b, dict) and "cache_control" in b for b in content
            ):
                bp = i + 1
        return bp

    def _extract_text(self, messages: Sequence[dict[str, Any]]) -> str:
        parts: list[str] = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        parts.append(block.get("text", ""))
        return " ".join(parts)

    def _check_timestamps(
        self,
        prefix: Sequence[dict[str, Any]],
        issues: list[StabilityIssue],
        details: list[str],
    ) -> None:
        text = self._extract_text(prefix)
        matches = _TIMESTAMP_RE.findall(text)
        if matches:
            issues.append(StabilityIssue.TIMESTAMP_IN_PREFIX)
            details.append(
                f"Timestamp-like content in stable prefix: {matches[:3]!r} "
                "— this changes every turn and busts the cache"
            )

    def _check_request_ids(
        self,
        prefix: Sequence[dict[str, Any]],
        issues: list[StabilityIssue],
        details: list[str],
    ) -> None:
        text = self._extract_text(prefix)
        matches = _REQUEST_ID_RE.findall(text)
        if matches:
            issues.append(StabilityIssue.REQUEST_ID_IN_PREFIX)
            details.append(
                f"Request-ID-like strings in prefix: {matches[:3]!r}"
            )

    def _check_nondeterministic(
        self,
        prefix: Sequence[dict[str, Any]],
        issues: list[StabilityIssue],
        details: list[str],
    ) -> None:
        text = self._extract_text(prefix)
        matches = _NONDETERMINISTIC_RE.findall(text)
        if matches:
            issues.append(StabilityIssue.NONDETERMINISTIC_CONTENT)
            details.append(
                f"Potentially non-deterministic terms in prefix: "
                f"{list(dict.fromkeys(m.lower() for m in matches))!r}"
            )

    def _check_thinking_toggle(
        self,
        messages: Sequence[dict[str, Any]],
        issues: list[StabilityIssue],
        details: list[str],
    ) -> None:
        """Detect thinking blocks present in some turns but not others."""
        flags: list[tuple[int, bool]] = []
        for i, msg in enumerate(messages):
            content = msg.get("content", [])
            has_thinking = isinstance(content, list) and any(
                isinstance(b, dict) and b.get("type") == "thinking"
                for b in content
            )
            flags.append((i, has_thinking))

        present = [i for i, flag in flags if flag]
        absent = [i for i, flag in flags if not flag]
        if present and absent:
            issues.append(StabilityIssue.THINKING_BLOCK_TOGGLE)
            details.append(
                f"Thinking blocks present in turns {present} but absent in "
                f"{absent} — toggling per-turn busts cache "
                "(April 2026 postmortem)"
            )

    def _check_missing_cache_control(
        self,
        messages: Sequence[dict[str, Any]],
        issues: list[StabilityIssue],
        details: list[str],
    ) -> None:
        if len(messages) < 2:
            return
        has_cache = any(
            isinstance(b, dict) and "cache_control" in b
            for msg in messages
            for b in (
                msg.get("content", [])
                if isinstance(msg.get("content"), list)
                else []
            )
        )
        if not has_cache:
            issues.append(StabilityIssue.MISSING_CACHE_CONTROL)
            details.append(
                "No cache_control block found — add "
                'cache_control: {"type": "ephemeral"} after the stable '
                "prefix to enable Anthropic prompt caching"
            )


__all__ = [
    "StabilityIssue",
    "StabilityReport",
    "PrefixStabilityChecker",
]
