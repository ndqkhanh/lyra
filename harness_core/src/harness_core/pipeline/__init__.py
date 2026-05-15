"""harness_core.pipeline — composable end-to-end pipelines.

Per [docs/199-multi-hop-reasoning-techniques-arc.md](../../../../../../research/harness-engineering/docs/199-multi-hop-reasoning-techniques-arc.md)
Phase 2 (DSPy declarative pipelines) — wraps the harness_core primitives
(router + operators + gates + cache + budget) into a single composable
callable. Each project either uses :class:`MultiHopPipeline` directly or
sub-classes it with project-specific gate insertions.

Per-project consumers from the apply plans:
    - [docs/203] Polaris — Tier 1 (`polaris-skills/research/dspy_program.py`)
    - [docs/208] Lyra — Tier 1 (`lyra-skills/research/dspy_swe_program.py`)
    - [docs/218] Atlas-Research — Tier 1
    - [docs/219] Helix-Bio — Tier 1 (with retraction+dual-use+KG-fact gates)
    - [docs/220] Orion-Code — Tier 1 (with verifier composition)

The pipeline is a thin coordinator — it doesn't add logic the operators don't
already have. It exists to *guarantee* that the canonical sequence runs in
the canonical order, with budget tracked + cache consulted + gates fired in
the right places.
"""
from __future__ import annotations

from .multi_hop_pipeline import (
    MultiHopPipeline,
    PipelineResult,
    PipelineStep,
)

__all__ = ["MultiHopPipeline", "PipelineResult", "PipelineStep"]
