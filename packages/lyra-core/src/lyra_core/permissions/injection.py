"""Wave-D Task 6: prompt-injection guard.

Detects the most common patterns operators have seen leak through
tool outputs (web fetches, RAG snippets, code-search hits) and
hijack a downstream LLM. Conservative by default: false positives
are user-visible "blocked output" toasts, false negatives let an
attacker steer the model.

The guard is deliberately *not* a parser — it's a regex sweep.
Static analysis of natural language is brittle, but matching the
literal phrase ``ignore previous instructions`` (and a few
well-known siblings) buys a meaningful amount of safety with no
runtime cost worth measuring.

Categories covered (all case-insensitive):

- "ignore (all) previous (system) instructions"
- "disregard the above"
- "you are now ..." style role-rewrites
- explicit "system:" / "system override" headers
- "BEGIN/END SYSTEM" markdown blocks
- common jailbreak primer phrases ("DAN", "developer mode")

The pattern list is exposed via :data:`INJECTION_PATTERNS` so the
parity matrix and policy docs can enumerate it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class GuardResult:
    """One guard's verdict."""

    block: bool
    reason: str | None = None
    matched: str | None = None


_INJECTION_PATTERNS_RAW: tuple[tuple[str, str], ...] = (
    (
        "ignore_previous",
        r"\bignore\s+(?:all\s+)?(?:previous|prior|the\s+above)"
        r"\s+(?:system\s+)?(?:instructions|prompts|messages|rules)\b",
    ),
    (
        "disregard_previous",
        r"\bdisregard\s+(?:all\s+)?(?:previous|the\s+above|all\s+prior)\s+"
        r"(?:instructions|messages|context)\b",
    ),
    (
        "system_override",
        r"\bsystem\s*(?:override|prompt)\s*[:\-]\s",
    ),
    (
        "you_are_now",
        r"\byou\s+are\s+now\s+(?:a\s+)?(?:[A-Z][A-Za-z\-]*|developer)\b",
    ),
    (
        "system_marker",
        r"^\s*(?:#\s*)?(?:SYSTEM(?:\s+OVERRIDE)?|<\|system\|>)\s*[:\-]?\s*$",
    ),
    (
        "begin_system_block",
        r"\b(?:BEGIN|START)\s+SYSTEM\b",
    ),
    (
        "developer_mode",
        r"\b(?:developer|dev)\s+mode\s+(?:on|enabled|activate)\b",
    ),
    (
        "dan_jailbreak",
        r"\bDAN\b\s+(?:mode|prompt|persona)",
    ),
)


INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pat, re.IGNORECASE | re.MULTILINE))
    for name, pat in _INJECTION_PATTERNS_RAW
)


def injection_guard(text: str) -> GuardResult:
    """Return :class:`GuardResult` flagging the first matched pattern."""
    if not isinstance(text, str) or not text:
        return GuardResult(block=False)
    for name, pat in INJECTION_PATTERNS:
        m = pat.search(text)
        if m:
            return GuardResult(
                block=True,
                reason=(
                    f"prompt-injection guard: matched {name!r} "
                    f"(sample={m.group(0)[:48]!r})"
                ),
                matched=name,
            )
    return GuardResult(block=False)


__all__ = ["GuardResult", "INJECTION_PATTERNS", "injection_guard"]
