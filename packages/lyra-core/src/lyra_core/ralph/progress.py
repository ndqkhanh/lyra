"""L312-2 — Ralph ``progress.txt`` parser/maintainer.

Two-section structure mirroring snarktank:

1. ``## Codebase Patterns`` — distilled, stable knowledge. The agent
   maintains this section across iterations.
2. ``## [DATE] - [STORY-ID]`` — append-only iteration log.

The class is intentionally read-light + write-light. The agent's
prompt does the curation; this module just provides the safe append /
codebase-patterns-update primitives the runner uses.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


__all__ = ["ProgressLog"]


_PATTERNS_HEADER = "## Codebase Patterns"
_LOG_BANNER = "# Ralph Progress Log"


@dataclass
class ProgressLog:
    path: Path

    def __post_init__(self) -> None:
        self.path = Path(self.path)

    # ---- public API ------------------------------------------------- #

    def init_if_missing(self) -> None:
        if self.path.exists():
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            f"{_LOG_BANNER}\nStarted: {_now()}\n\n"
            f"{_PATTERNS_HEADER}\n(none yet)\n\n",
            encoding="utf-8",
        )

    def reset(self) -> None:
        """Reset on branch change — wipes log, preserves nothing."""
        self.path.write_text(
            f"{_LOG_BANNER}\nStarted: {_now()}\n\n{_PATTERNS_HEADER}\n(none yet)\n\n",
            encoding="utf-8",
        )

    def append_iteration(
        self,
        *,
        story_id: str,
        what_was_done: str,
        files_changed: list[str] | None = None,
        learnings: list[str] | None = None,
    ) -> None:
        self.init_if_missing()
        chunk = self._render_iteration(
            story_id=story_id,
            what_was_done=what_was_done,
            files_changed=files_changed or [],
            learnings=learnings or [],
        )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(chunk)

    def add_codebase_pattern(self, pattern: str) -> None:
        """Idempotent — pattern is added only if not already present."""
        self.init_if_missing()
        text = self.path.read_text(encoding="utf-8")
        if pattern.strip() in text:
            return
        # Insert under the patterns header.
        if _PATTERNS_HEADER in text:
            text = text.replace(
                _PATTERNS_HEADER + "\n(none yet)\n",
                _PATTERNS_HEADER + f"\n- {pattern.strip()}\n",
                1,
            )
            if f"- {pattern.strip()}" not in text:
                # Already had patterns — append under the header.
                idx = text.find(_PATTERNS_HEADER)
                eol = text.find("\n", idx)
                text = text[:eol + 1] + f"- {pattern.strip()}\n" + text[eol + 1:]
        else:
            text = f"{_PATTERNS_HEADER}\n- {pattern.strip()}\n\n" + text
        self.path.write_text(text, encoding="utf-8")

    def codebase_patterns(self) -> list[str]:
        if not self.path.exists():
            return []
        text = self.path.read_text(encoding="utf-8")
        # Find the patterns section and read until the next ## header.
        m = re.search(rf"{re.escape(_PATTERNS_HEADER)}\n(.*?)(?=\n##\s|\Z)", text, re.DOTALL)
        if m is None:
            return []
        body = m.group(1)
        return [
            line.lstrip("- ").strip()
            for line in body.splitlines()
            if line.lstrip().startswith("-")
        ]

    # ---- internal --------------------------------------------------- #

    def _render_iteration(
        self,
        *,
        story_id: str,
        what_was_done: str,
        files_changed: list[str],
        learnings: list[str],
    ) -> str:
        lines = [f"\n## {_now()} — {story_id}"]
        lines.append(f"- {what_was_done.strip()}")
        if files_changed:
            lines.append("- Files changed:")
            lines.extend(f"  - `{f}`" for f in files_changed)
        if learnings:
            lines.append("- **Learnings for future iterations:**")
            lines.extend(f"  - {l}" for l in learnings)
        lines.append("---\n")
        return "\n".join(lines)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
