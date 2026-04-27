r"""Fence-aware streaming markdown buffer.

Python port of claw-code's ``MarkdownStreamState`` (see
``rust/crates/rusty-claude-cli/src/render.rs``). While the model
streams tokens, we need to *defer* printing text that sits inside an
unclosed fenced code block so the terminal markdown renderer doesn't
start colorizing half of a python snippet and then flicker when the
closing triple-backtick arrives.

Strategy:

- Append every delta into an internal buffer.
- On each ``push``, search the buffer for the newest *safe boundary*:
  the latest newline that is outside any open ``\`\`\``-fence.
- Flush everything up to (and including) that newline, keeping the
  tail for the next push.
- :meth:`flush` always drains whatever is left (used when the stream
  ends — e.g. the LLM turn completes).
"""

from __future__ import annotations

from typing import Optional


class MarkdownStreamState:
    """Deferred-flush buffer for streaming markdown with code fences."""

    _FENCE = "```"

    def __init__(self) -> None:
        self._buf: str = ""

    def push(self, delta: str) -> Optional[str]:
        """Append ``delta``; return the prefix that is safe to flush now.

        Returns ``None`` (or an empty string, tolerated by callers)
        when nothing is safe yet. The caller is expected to render the
        returned slice incrementally and then discard it — the state
        retains only the unsafe tail.
        """
        if delta:
            self._buf += delta

        boundary = self._safe_boundary()
        if boundary <= 0:
            return None

        ready = self._buf[:boundary]
        self._buf = self._buf[boundary:]
        return ready

    def flush(self) -> str:
        """Drain the entire buffer, including any half-open fence.

        Called at the end of a stream (LLM turn complete). Returns ``""``
        if the buffer is already empty so the caller can ``print()`` the
        result unconditionally.
        """
        out = self._buf
        self._buf = ""
        return out

    # --- internal --------------------------------------------------- #

    def _safe_boundary(self) -> int:
        """Return the index *after* the last safe newline, or 0."""
        if not self._buf:
            return 0
        idx = self._buf.rfind("\n")
        while idx >= 0:
            prefix = self._buf[: idx + 1]
            if self._fence_count(prefix) % 2 == 0:
                return idx + 1
            # Inside an open fence at this newline — step back to the
            # previous candidate boundary.
            idx = self._buf.rfind("\n", 0, idx)
        return 0

    @classmethod
    def _fence_count(cls, text: str) -> int:
        """Count occurrences of the triple-backtick fence marker."""
        if not text:
            return 0
        count = 0
        i = 0
        while True:
            j = text.find(cls._FENCE, i)
            if j < 0:
                break
            count += 1
            i = j + len(cls._FENCE)
        return count


__all__ = ["MarkdownStreamState"]
