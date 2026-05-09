"""Secret-pattern redactor for the memory write path.

Mirrors the regex pack used by the v3.7 secrets-scan hook
(:mod:`lyra_core.hooks.secrets_scan`) but emits redacted text rather
than blocking. Memory is the wrong layer to *block* — the agent has
already produced the text, and the right hop is to *strip secrets
before persistence* so they never land in
``~/.lyra/memory/<project>/memory.md`` and the JSONL audit log.

Plumbed through :meth:`~lyra_core.memory.memory_tools.MemoryToolset.remember`.
A redaction emits a ``memory.remember.redacted`` HIR event with the
matched pattern names so audit can spot a near-miss.

Bright-line: ``LBL-MEMORY-WRITE-REDACT`` — every text that reaches a
memory substore via the toolset has been through this redactor.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple


_REDACTED_TOKEN = "[REDACTED:{name}]"


# Same pattern set as ``hooks/secrets_scan._PATTERNS`` (v3.7), but kept
# here so memory has its own copy and isn't coupled to a tool-call hook.
# Adding a pattern is a backward-compatible change; widening / removing
# is not.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA|AIDA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("slack_bot_token", re.compile(r"\bxox[bpaor]-[A-Za-z0-9-]{10,}\b")),
    (
        "rsa_private_key",
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |DSA |EC )?PRIVATE KEY-----"),
    ),
    ("stripe_secret", re.compile(r"\bsk_(?:live|test)_[0-9A-Za-z]{16,}\b")),
    ("openai_secret", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("generic_bearer", re.compile(r"[Bb]earer\s+[A-Za-z0-9_\-\.=]{20,}")),
)


@dataclass(frozen=True)
class RedactionResult:
    """Outcome of one ``redact`` call.

    ``hits`` is the list of matched-pattern names (e.g. ``("github_token",)``);
    callers use it for HIR audit + ``LBL-MEMORY-WRITE-REDACT`` emission.
    """

    text: str
    hits: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.hits)


def redact(text: str) -> RedactionResult:
    """Return ``text`` with every known secret pattern replaced by
    ``[REDACTED:<name>]``. ``hits`` records which patterns fired (so
    ``len(hits)`` ≥ number of unique pattern names that matched).
    """
    if not text:
        return RedactionResult(text="", hits=())
    out = text
    fired: list[str] = []
    for name, pat in _PATTERNS:
        if not pat.search(out):
            continue
        fired.append(name)
        out = pat.sub(_REDACTED_TOKEN.format(name=name), out)
    return RedactionResult(text=out, hits=tuple(fired))


def redact_pair(*texts: str) -> Tuple[tuple[str, ...], tuple[str, ...]]:
    """Convenience for ``remember(text, title=...)``: redact both, return
    the pair of redacted strings + the union of pattern hits."""
    redacted: list[str] = []
    hits: list[str] = []
    seen: set[str] = set()
    for t in texts:
        r = redact(t)
        redacted.append(r.text)
        for h in r.hits:
            if h not in seen:
                seen.add(h)
                hits.append(h)
    return tuple(redacted), tuple(hits)


__all__ = ["RedactionResult", "redact", "redact_pair"]
