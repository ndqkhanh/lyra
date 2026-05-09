"""L312-2 — completion-signal parser.

Implements the four-tier completion-signal hierarchy from
``docs/307-ralph-loop-variations-2026.md`` § "The completion-signal
hierarchy":

- **Tier 1** — string match: ``<promise>COMPLETE</promise>`` literal.
- **Tier 1 alt** — frankbria's ``EXIT_SIGNAL: true`` token.
- Tiers 2+ are layered above by the :class:`RalphRunner` (work-was-done
  pre-flight + verifier predicate + typed callback). Tier 1 lives here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


__all__ = [
    "CompletionSignal",
    "EXIT_SIGNAL_PATTERN",
    "PROMISE_COMPLETE_PATTERN",
    "parse_completion",
]


# ``<promise>COMPLETE</promise>`` — snarktank's literal token. We accept
# whitespace inside the tags but require the exact token. False
# positives are reduced by the prompt's discipline.
PROMISE_COMPLETE_PATTERN = re.compile(
    r"<\s*promise\s*>\s*COMPLETE\s*<\s*/\s*promise\s*>",
    re.IGNORECASE,
)

# frankbria's variant. Accepts ``EXIT_SIGNAL: true`` or ``EXIT_SIGNAL:true``.
# Case-insensitive on the keyword; canonical on the value.
EXIT_SIGNAL_PATTERN = re.compile(
    r"\bEXIT_SIGNAL\s*:\s*true\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CompletionSignal:
    """Parsed completion outcome for one iteration's text output.

    - ``found``: True iff any Tier-1 signal matched.
    - ``variant``: ``"promise"`` or ``"exit_signal"`` or ``""``.
    - ``span``: (start, end) byte offsets of the match in the input,
      for postmortem highlighting; ``(0, 0)`` if no match.
    """

    found: bool = False
    variant: str = ""
    span: tuple[int, int] = (0, 0)


def parse_completion(text: str) -> CompletionSignal:
    """Tier-1 completion parser. Order: promise then exit_signal.

    The ``<promise>COMPLETE</promise>`` form takes precedence because
    it is the canonical snarktank signal. ``EXIT_SIGNAL: true`` is the
    frankbria-compat fallback.
    """
    if not text:
        return CompletionSignal()

    m = PROMISE_COMPLETE_PATTERN.search(text)
    if m is not None:
        return CompletionSignal(found=True, variant="promise", span=m.span())

    m = EXIT_SIGNAL_PATTERN.search(text)
    if m is not None:
        return CompletionSignal(found=True, variant="exit_signal", span=m.span())

    return CompletionSignal()
