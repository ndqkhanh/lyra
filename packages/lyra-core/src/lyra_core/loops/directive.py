"""L312-5 — HUMAN_DIRECTIVE.md async-control file watcher.

Anchor: ``docs/160-deep-researcher-agent-24x7.md`` § HUMAN_DIRECTIVE.md
mechanism. The pattern: a long-running loop watches a single Markdown
file. If the file's ``mtime`` advances since the last consumption, the
next iteration reads its contents and treats them as a top-priority
directive, *before* anything else.

Three operational properties:

1. **Cheap.** ``mtime`` check, no inotify/fsevents dependency.
2. **Atomic at iteration boundary.** Mid-iteration edits don't tear; the
   file is read once at the start of an iteration.
3. **Archived after consumption.** The live file is rewound (truncated)
   after consumption so the next directive is a *new* event, not a
   replay of the prior one. Consumed text is preserved under
   ``directives/NNN-YYYYMMDDHHMM.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


__all__ = ["HumanDirective"]


@dataclass
class HumanDirective:
    """Watch a single ``HUMAN_DIRECTIVE.md`` file by mtime.

    On ``consume_if_changed()``: returns the file's text if its
    ``mtime`` advanced since the last consumption (or returns ``None``
    if unchanged / missing). Truncates the live file after consumption
    and writes a numbered archive under ``archive_dir`` (or ``directives/``
    next to the live file by default).
    """

    path: Path
    archive_dir: Optional[Path] = None
    _last_mtime: float = 0.0
    _seq: int = 0

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        if self.archive_dir is None:
            self.archive_dir = self.path.parent / "directives"
        else:
            self.archive_dir = Path(self.archive_dir)

    # ---- public API ------------------------------------------------- #

    def consume_if_changed(self) -> Optional[str]:
        if not self.path.exists():
            return None
        try:
            stat = self.path.stat()
        except OSError:
            return None
        if stat.st_mtime <= self._last_mtime:
            return None
        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError:
            return None
        if not text.strip():
            # Empty file — refresh mtime so we don't keep re-reading.
            self._last_mtime = stat.st_mtime
            return None
        self._archive(text)
        # Truncate the live file so the next mtime advance is a real edit.
        try:
            self.path.write_text("", encoding="utf-8")
            self._last_mtime = self.path.stat().st_mtime
        except OSError:
            self._last_mtime = stat.st_mtime
        return text

    # ---- internal --------------------------------------------------- #

    def _archive(self, text: str) -> None:
        try:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            self._seq += 1
            ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            name = f"{self._seq:03d}-{ts}.md"
            (self.archive_dir / name).write_text(text, encoding="utf-8")
        except OSError:
            # Archiving failure must not block consumption.
            return
