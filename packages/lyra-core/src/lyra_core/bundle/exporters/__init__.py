"""L311-9 — Cross-harness portable export.

Each module in this package transforms a :class:`~lyra_core.bundle.SourceBundle`
into the **target harness's native layout**, so any Lyra bundle can
"light up" inside Claude Code, Cursor, Codex, or Gemini-CLI without
rewriting it. The bundle is the canonical form; exporters are
view-transformers.

The 2026 cross-harness lesson ([`docs/07`](../../../../../../../docs/07-model-context-protocol.md),
[`docs/62`](../../../../../../../docs/62-everything-claude-code.md), [`docs/239`](../../../../../../../docs/239-software-3-0-paradigm.md)):
**Skills + hooks + agents + rules + MCP form a de-facto portable
extension contract** — the same source bundle, projected per target,
runs inside multiple harnesses.

Design discipline:

* Exporters are **pure functions over a SourceBundle** + a target dir.
  No live LLM calls, no network IO, no installer-style smoke evals
  (those are L311-5's job, run *before* export).
* Every exporter writes a ``MANIFEST.txt`` listing every file it
  emitted — so callers know exactly what landed and can ``rm -rf`` to
  uninstall.
* Bright-line ``LBL-EXPORT-NO-LEAK``: exporters never read or write
  outside the supplied target directory.

Usage::

    from lyra_core.bundle import SourceBundle
    from lyra_core.bundle.exporters import ClaudeCodeExporter

    bundle = SourceBundle.load("./orion-code/bundle/")
    bundle.validate()
    ClaudeCodeExporter().export(bundle, target=Path.home() / ".claude")
"""
from __future__ import annotations

from .base import (
    Exporter,
    ExportError,
    ExportManifest,
    ExportTarget,
    list_exporters,
    resolve_exporter,
)
from .claude_code import ClaudeCodeExporter
from .codex import CodexExporter
from .cursor import CursorExporter
from .gemini_cli import GeminiCLIExporter

__all__ = [
    "ClaudeCodeExporter",
    "CodexExporter",
    "CursorExporter",
    "ExportError",
    "ExportManifest",
    "ExportTarget",
    "Exporter",
    "GeminiCLIExporter",
    "list_exporters",
    "resolve_exporter",
]
