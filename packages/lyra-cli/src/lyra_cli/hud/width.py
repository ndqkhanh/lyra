"""CJK-aware terminal width helpers for the HUD.

CJK ideographs and full-width punctuation occupy two columns in a
monospaced terminal; ASCII characters take one. ``len(s)`` is wrong
for layout decisions; ``unicodedata.east_asian_width`` is the
authoritative source.

Plain ASCII strings? ``column_width(s) == len(s)`` is the fast path.
The function only walks every code point if ``s`` contains any
non-ASCII character, so the common case (English log lines, JSON,
shell commands) stays cheap.
"""

from __future__ import annotations

import unicodedata


def column_width(text: str) -> int:
    """Number of terminal columns ``text`` occupies in a monospace cell.

    Counts:
      - CJK / wide / full-width as 2,
      - ASCII / narrow / half-width / neutral as 1,
      - zero-width joiners and combining marks as 0.

    Doesn't strip ANSI — call :func:`strip_ansi` first if your input
    has escape codes.
    """
    if text.isascii():
        return len(text)
    total = 0
    for ch in text:
        if unicodedata.category(ch).startswith("M"):
            # Combining mark — zero-width.
            continue
        eaw = unicodedata.east_asian_width(ch)
        if eaw in ("W", "F"):
            total += 2
        else:
            total += 1
    return total


def truncate_to_columns(text: str, max_columns: int, *, suffix: str = "…") -> str:
    """Truncate ``text`` to fit in ``max_columns`` columns.

    Appends ``suffix`` if truncation occurred and there's room. If
    ``max_columns`` is too small to fit even the suffix, returns the
    longest prefix that fits ignoring the suffix.

    Width-correct: counts each CJK char as 2 columns (matches what
    the terminal will actually render).
    """
    if column_width(text) <= max_columns:
        return text

    suffix_w = column_width(suffix)
    budget = max(0, max_columns - suffix_w)

    out: list[str] = []
    used = 0
    for ch in text:
        ch_w = column_width(ch)
        if used + ch_w > budget:
            break
        out.append(ch)
        used += ch_w

    if used + suffix_w <= max_columns:
        return "".join(out) + suffix
    return "".join(out)


def pad_to_columns(text: str, columns: int, *, align: str = "left", fillchar: str = " ") -> str:
    """Pad ``text`` to exactly ``columns`` columns wide.

    ``align`` is ``"left"`` (default), ``"right"``, or ``"center"``.
    If ``text`` already exceeds ``columns``, it is truncated.
    ``fillchar`` must itself be one column wide.
    """
    if column_width(fillchar) != 1:
        raise ValueError(f"fillchar must be exactly 1 column wide, got {fillchar!r}")
    text = truncate_to_columns(text, columns)
    deficit = columns - column_width(text)
    if deficit <= 0:
        return text
    if align == "right":
        return fillchar * deficit + text
    if align == "center":
        left = deficit // 2
        right = deficit - left
        return fillchar * left + text + fillchar * right
    return text + fillchar * deficit


__all__ = [
    "column_width",
    "pad_to_columns",
    "truncate_to_columns",
]
