"""Single-source glyph alphabet for Lyra's REPL UI.

Every component that renders an in-band marker (tool calls, prompts,
status, picker rows, errors) imports its glyph from here. Centralising
the constants keeps the visual language coherent.

The set is the convergent core across Claude Code, OpenClaw, and
Hermes-Agent — every project we surveyed uses the same handful of
characters with very small variation.
"""
from __future__ import annotations

__all__ = [
    "ASSISTANT",
    "CHECK",
    "CONTINUE",
    "CROSS",
    "CURSOR",
    "DOT",
    "LOCK",
    "OUTPUT",
    "PROMPT",
    "RUNNING",
    "USER_OVERRIDE",
]


# User-input lead. Same character lyra's pickers already use as cursor.
PROMPT = "❯"

# Assistant turn / tool-call lead (HEAVY ROUND-TIPPED ROD U+23FA).
# Matches Claude Code's own bullet exactly.
ASSISTANT = "⏺"

# Tool result, indented one level under its call (RIGHT NORMAL FACTOR
# SEMIDIRECT PRODUCT U+23BF — the curve Claude Code uses).
OUTPUT = "⎿"

# Cursor row indicator inside pickers. Identical to PROMPT by design —
# the same shape on the input line and the picker row signals "this
# is the active position".
CURSOR = PROMPT

# Success — passed check / completed tool / "ok" toast.
CHECK = "✓"

# Failure — denied tool / blocked op / failed test.
CROSS = "✗"

# Locked (built-in / managed by plugin / shipped pack).
LOCK = "🔒"

# User override of a built-in (e.g. user-shadowed packaged skill).
USER_OVERRIDE = "✎"

# Pending dot — spinner fallback when braille not available.
DOT = "·"

# Currently running (spawned subagent, executing tool).
RUNNING = "▶"

# Continuation arrow — nested context in tracebacks, joined messages.
CONTINUE = "↳"
