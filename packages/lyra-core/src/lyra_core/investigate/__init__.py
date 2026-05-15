"""Direct Corpus Interaction (DCI) — Lyra's investigate-mode primitives.

This package ports the *Direct Corpus Interaction* design from
Li et al., "Beyond Semantic Similarity: Rethinking Retrieval for
Agentic Search via Direct Corpus Interaction" (arXiv:2605.05242,
May 2026) and the reference implementation
``github.com/DCI-Agent/DCI-Agent-Lite``.

The bet: when the agent is strong enough to write shell commands,
the cheapest way to find evidence in a corpus is to hand it the
raw files plus ``rg``/``find``/``sed``, *not* an embedding pipeline.
DCI-Agent-Lite reports gains of +11 % on BrowseComp-Plus, +30.7 %
on multi-hop QA, and +21.5 % on IR ranking against strong sparse,
dense, and reranker baselines.

Lyra v3.13 ships the **primitives** for that mode here. Higher
layers (the `investigate` REPL mode, the eval harness, the Argus
auto-routing skill) compose these primitives. Each piece is:

* **opt-in** — nothing in the existing 4-mode router changes;
* **offline-testable** — pure dataclasses + a deterministic
  level→pipeline map, no LLM dependency;
* **citation-chained** — every module head links to the paper.

Public surface:

* :class:`CorpusMount` — a read-only (or read-write) corpus root with
  globs and file-size guards.
* :class:`InvestigationBudget` — turn / bash-call / bytes / wall-clock
  caps mirroring DCI-Agent-Lite's 300-turn ceiling but with finer
  knobs.
* :class:`ContextLevel` — the DCI level0..level4 ladder, mapped onto
  Lyra's existing compactor/NGC/grid stack.
* :func:`build_system_prompt` — the terse two-paragraph prompt the
  paper showed beats long ReAct scaffolds.
"""
from __future__ import annotations

from .budget import BudgetExceeded, InvestigationBudget
from .compactor import CompactionReport, Summarizer, compact_messages
from .corpus import CorpusMount, CorpusMountError
from .levels import ContextLevel, ContextLevelPlan, plan_for_level
from .plugin import InvestigationBudgetPlugin, TrajectoryLedgerPlugin
from .profile import READ_ONLY, InvestigateProfile, read_write
from .prompt import INVESTIGATE_PROMPT_BODY, build_system_prompt
from .runner import InvestigationResult, InvestigationRunner
from .tools import make_investigate_tools

__all__ = [
    "INVESTIGATE_PROMPT_BODY",
    "READ_ONLY",
    "BudgetExceeded",
    "CompactionReport",
    "ContextLevel",
    "ContextLevelPlan",
    "CorpusMount",
    "CorpusMountError",
    "InvestigateProfile",
    "InvestigationBudget",
    "InvestigationBudgetPlugin",
    "InvestigationResult",
    "InvestigationRunner",
    "Summarizer",
    "TrajectoryLedgerPlugin",
    "build_system_prompt",
    "compact_messages",
    "make_investigate_tools",
    "plan_for_level",
    "read_write",
]
