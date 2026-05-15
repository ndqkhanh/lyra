"""Sub-agent return-bundle schema (Phase CE.1, P0-3).

The motivation (Anthropic + ECC): a spawned sub-agent typically
explores 10k+ tokens worth of files/tools/notes and must hand back a
small, structured summary to the parent — *not* a raw transcript. This
module pins down the contract so every sub-agent caller agrees on the
shape.

A :class:`SubagentBundle` rides inside
:class:`lyra_core.subagent.orchestrator.SubagentResult.payload`. The
``payload`` field there is intentionally ``object | None`` so other
shapes remain possible; the helpers below wrap a bundle into a result
when that's the caller's intent.

Token budget: the summary is hard-capped (``MAX_SUMMARY_TOKENS``). Use
the ``rough_token_count`` helper for a cheap, dependency-free check;
production builds can swap in ``tiktoken`` without changing the
contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import SubagentResult


# Hard caps. The summary's primary purpose is to keep the parent's
# context budget intact — Anthropic's reference number is 1k–2k
# tokens, so we cap at 2k.
MAX_SUMMARY_TOKENS = 2000
# Per-finding evidence string cap — a single finding shouldn't be able
# to blow the budget by itself.
MAX_FINDING_CLAIM_CHARS = 400


class SubagentBundleError(ValueError):
    """Raised when a bundle violates the contract (over-budget, etc)."""


@dataclass(frozen=True)
class Finding:
    """One structured claim the sub-agent extracted from its exploration.

    ``evidence_hash`` is a pointer the parent can resolve via the
    artifact store (``View(hash)``); it's not the evidence body — that
    stays in the artifact, not in context.
    """

    claim: str
    evidence_hash: str
    confidence: float  # [0.0, 1.0]

    def __post_init__(self) -> None:
        if not self.claim or not self.claim.strip():
            raise SubagentBundleError("Finding.claim must be non-empty")
        if len(self.claim) > MAX_FINDING_CLAIM_CHARS:
            raise SubagentBundleError(
                f"Finding.claim exceeds {MAX_FINDING_CLAIM_CHARS} chars "
                f"({len(self.claim)})"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise SubagentBundleError(
                f"Finding.confidence must be in [0, 1]; got {self.confidence}"
            )


def rough_token_count(text: str) -> int:
    """Char-based token estimate (~4 chars / token). Min 1 for nonempty."""
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass(frozen=True)
class SubagentBundle:
    """Structured payload returned by a sub-agent to its parent.

    The parent reads ``summary`` + ``findings`` directly and pulls
    ``artifacts`` only when a finding warrants drilling in. The
    ``open_questions`` field is the explicit handoff: things the sub-
    agent could not resolve and the parent (or next sub-agent) should.
    """

    summary: str
    findings: tuple[Finding, ...] = ()
    artifacts: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    tokens_consumed: int = 0
    elapsed_ms: int = 0
    # Free-form provenance — sub-agent id, model name, etc. Optional.
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary or not self.summary.strip():
            raise SubagentBundleError("SubagentBundle.summary must be non-empty")
        est = rough_token_count(self.summary)
        if est > MAX_SUMMARY_TOKENS:
            raise SubagentBundleError(
                f"SubagentBundle.summary exceeds {MAX_SUMMARY_TOKENS} tokens "
                f"(estimated {est}). Tighten before returning."
            )
        if self.tokens_consumed < 0:
            raise SubagentBundleError(
                f"tokens_consumed must be >= 0, got {self.tokens_consumed}"
            )
        if self.elapsed_ms < 0:
            raise SubagentBundleError(
                f"elapsed_ms must be >= 0, got {self.elapsed_ms}"
            )

    # ------------------------------------------------------------------ views
    def summary_token_estimate(self) -> int:
        return rough_token_count(self.summary)

    def has_open_questions(self) -> bool:
        return any(q.strip() for q in self.open_questions)

    def best_findings(self, *, min_confidence: float = 0.7) -> list[Finding]:
        """Return findings whose confidence clears the floor, ordered desc."""
        keep = [f for f in self.findings if f.confidence >= min_confidence]
        return sorted(keep, key=lambda f: f.confidence, reverse=True)


def bundle_to_result(
    bundle: SubagentBundle, *, spec_id: str
) -> "SubagentResult":
    """Wrap a bundle in a :class:`SubagentResult` envelope.

    Centralises the convention so every caller emits the same
    ``status="ok"`` and the bundle lands in ``payload``. Importing
    ``SubagentResult`` here (vs. at module-top) keeps the cycle clean
    for typing while still giving a runtime symbol.
    """
    from .orchestrator import SubagentResult

    return SubagentResult(id=spec_id, status="ok", payload=bundle, error=None)


def result_to_bundle(result: "SubagentResult") -> SubagentBundle:
    """Recover the bundle from a result.

    Raises :class:`SubagentBundleError` when the payload is the wrong
    shape — callers can branch on this to know whether a sub-agent
    actually returned a bundle vs. a legacy object.
    """
    payload = result.payload
    if isinstance(payload, SubagentBundle):
        return payload
    raise SubagentBundleError(
        f"SubagentResult {result.id!r} payload is not a SubagentBundle "
        f"(got {type(payload).__name__})"
    )


__all__ = [
    "Finding",
    "MAX_FINDING_CLAIM_CHARS",
    "MAX_SUMMARY_TOKENS",
    "SubagentBundle",
    "SubagentBundleError",
    "bundle_to_result",
    "result_to_bundle",
    "rough_token_count",
]
