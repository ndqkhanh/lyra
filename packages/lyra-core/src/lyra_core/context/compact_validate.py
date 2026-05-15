"""Validated compaction (Phase CE.1, P0-4).

Wraps :func:`lyra_core.context.compactor.compact_messages` with an
invariant-preservation check. The motivation (Gunaseela #1 +
Anthropic): a summary that quietly drops a failing-test name or a
deny-reason can poison subsequent turns — the model "forgets" the
constraint and re-triggers the same failure.

We keep this strictly as a *report*, not an auto-retry:
``validate_compaction`` returns a :class:`ValidationReport` and
callers decide what to do. No fallback shim, no implicit retry — the
upstream compaction is already deterministic; if it dropped an
invariant, the right move is to surface the failure and let the
operator (or a later phase) decide on the policy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .compactor import CompactResult, compact_messages


@dataclass(frozen=True)
class Invariant:
    """One thing that must appear in the post-compaction transcript.

    ``kind`` is freeform but conventional values keep the metrics
    legible: ``file_anchor`` (``path/to/x.py:123``), ``deny_reason``,
    ``test_name``, or ``free`` for caller-supplied strings.
    """

    kind: str
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("Invariant.value must be non-empty")


@dataclass(frozen=True)
class ValidationReport:
    """Outcome of an invariant check over a :class:`CompactResult`."""

    invariants_checked: int
    invariants_failed: tuple[Invariant, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.invariants_failed

    @property
    def invariants_passed(self) -> int:
        return self.invariants_checked - len(self.invariants_failed)


# ────────────────────────────────────────────────────────────────
# Default invariant extraction
# ────────────────────────────────────────────────────────────────

# ``path/segment.py:42`` or ``path/segment.py:42:7`` — a deliberately
# loose path matcher so we catch real anchors without being clever.
_FILE_ANCHOR_RE = re.compile(
    r"\b([\w./\-]+\.(?:py|js|ts|tsx|jsx|go|rs|java|kt|cpp|c|h|hpp|rb)):(\d+)(?::\d+)?\b"
)
# A test name like ``test_thing_does_x``. Wrapped in word boundaries
# so we don't grab the substring of a larger identifier.
_TEST_NAME_RE = re.compile(r"\btest_[\w]+\b")
# Permission-denied reasons surface in lyra as ``deny: <reason>`` lines.
_DENY_RE = re.compile(r"\bdeny:\s*([^\n]+)")


def _msg_text(msg: dict) -> str:
    content = msg.get("content")
    return content if isinstance(content, str) else ""


def extract_default_invariants(messages: list[dict]) -> list[Invariant]:
    """Best-effort scan for invariants that should survive compaction.

    Order in the returned list is stable but undefined; callers should
    not depend on it. Duplicates are collapsed.
    """
    file_anchors: set[str] = set()
    test_names: set[str] = set()
    deny_reasons: set[str] = set()

    for msg in messages:
        text = _msg_text(msg)
        if not text:
            continue
        for m in _FILE_ANCHOR_RE.finditer(text):
            file_anchors.add(f"{m.group(1)}:{m.group(2)}")
        for m in _TEST_NAME_RE.finditer(text):
            test_names.add(m.group(0))
        for m in _DENY_RE.finditer(text):
            deny_reasons.add(m.group(1).strip())

    out: list[Invariant] = []
    out.extend(Invariant("file_anchor", v) for v in sorted(file_anchors))
    out.extend(Invariant("test_name", v) for v in sorted(test_names))
    out.extend(Invariant("deny_reason", v) for v in sorted(deny_reasons))
    return out


# ────────────────────────────────────────────────────────────────
# Validation
# ────────────────────────────────────────────────────────────────


def _transcript_text(messages: list[dict]) -> str:
    return "\n".join(_msg_text(m) for m in messages)


def validate_compaction(
    result: CompactResult, invariants: list[Invariant]
) -> ValidationReport:
    """Check each invariant appears verbatim in the post-compaction text.

    ``kept_raw`` *and* ``summary`` count — an invariant the summary
    dropped but the trailing raw turns preserved is still preserved.
    """
    if not invariants:
        return ValidationReport(invariants_checked=0)
    # Check against the *full* surfaced transcript: kept_raw plus the
    # summary message. Joining via summarised_messages ensures we use
    # whatever the compactor surfaces upstream.
    body = _transcript_text(result.summarised_messages)
    missing = tuple(inv for inv in invariants if inv.value not in body)
    return ValidationReport(
        invariants_checked=len(invariants),
        invariants_failed=missing,
    )


@dataclass
class ValidatedCompactResult:
    """:class:`CompactResult` plus its :class:`ValidationReport`."""

    result: CompactResult
    report: ValidationReport
    metrics: dict[str, Any] = field(default_factory=dict)


def compact_messages_validated(
    messages: list[dict],
    *,
    llm: Callable[..., Any],
    keep_last: int = 4,
    max_summary_tokens: int = 800,
    invariants: list[Invariant] | None = None,
    extract_invariants: bool = True,
    on_metric: Callable[[str, Any], None] | None = None,
) -> ValidatedCompactResult:
    """Compact + validate in one call.

    Args:
        messages, llm, keep_last, max_summary_tokens: forwarded to
            :func:`compact_messages`.
        invariants: Explicit invariants the caller wants preserved.
            Merged with auto-extracted invariants when
            ``extract_invariants`` is True.
        extract_invariants: When True (default), call
            :func:`extract_default_invariants` on the input messages and
            merge with ``invariants``.
        on_metric: Optional callback ``(name, value)``. Emitted metrics:
            ``context.compaction.validation.checked``,
            ``context.compaction.validation.passed`` (int 0/1),
            ``context.compaction.validation.failed_count``.

    Returns:
        A :class:`ValidatedCompactResult` carrying both the
        :class:`CompactResult` and the :class:`ValidationReport`.
    """
    auto = extract_default_invariants(messages) if extract_invariants else []
    combined = list(auto) + list(invariants or [])
    # Dedupe by (kind, value).
    seen: set[tuple[str, str]] = set()
    unique: list[Invariant] = []
    for inv in combined:
        key = (inv.kind, inv.value)
        if key in seen:
            continue
        seen.add(key)
        unique.append(inv)

    result = compact_messages(
        messages,
        llm=llm,
        keep_last=keep_last,
        max_summary_tokens=max_summary_tokens,
    )
    report = validate_compaction(result, unique)

    metrics = {
        "context.compaction.validation.checked": report.invariants_checked,
        "context.compaction.validation.passed": 1 if report.passed else 0,
        "context.compaction.validation.failed_count": len(report.invariants_failed),
    }
    if on_metric is not None:
        for name, value in metrics.items():
            on_metric(name, value)

    return ValidatedCompactResult(result=result, report=report, metrics=metrics)


__all__ = [
    "Invariant",
    "ValidatedCompactResult",
    "ValidationReport",
    "compact_messages_validated",
    "extract_default_invariants",
    "validate_compaction",
]
