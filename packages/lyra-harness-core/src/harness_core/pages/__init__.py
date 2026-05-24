"""harness_core.pages — Lobe-Pages-style co-authored document surface.

Per [docs/205-lobehub-collaborative-teammate-platform.md](../../../../../../research/harness-engineering/docs/205-lobehub-collaborative-teammate-platform.md) §2.2,
[docs/206-collaborative-ai-canon-2026.md](../../../../../../research/harness-engineering/docs/206-collaborative-ai-canon-2026.md) §4 (branching + Pages),
and per-project apply plans:

    - [docs/203] §1 — Polaris co-authored research writeup
    - [docs/208] §4.5 — Lyra design doc
    - [docs/218] §4.5 — Atlas-Research report
    - [docs/219] §4.6 — Helix-Bio protocol/paper
    - [docs/220] §4.6 — Orion-Code design doc *before* implementation
    - [docs/221] §4.4 — Aegis-Ops co-authored runbook + post-mortem

Notion-style timeline-versioned multi-author document. Core operations:
    Page snapshots are immutable; edits produce new snapshots with parent
    pointers + author + diff summary. The :class:`PageHistory` is the full
    timeline; :class:`PageEditor` is the controller that produces new
    snapshots.

Concurrency model: optimistic — multiple authors can edit the same page;
each edit is appended to the history with a parent-version pointer. Conflicts
(two edits with the same parent) are recorded but not auto-resolved; the host
harness decides whether to surface them as branches or merge them.
"""
from __future__ import annotations

from .pages import (
    EditConflict,
    Page,
    PageEditor,
    PageHistory,
    PageSnapshot,
    line_diff_summary,
)

__all__ = [
    "EditConflict",
    "Page",
    "PageEditor",
    "PageHistory",
    "PageSnapshot",
    "line_diff_summary",
]
