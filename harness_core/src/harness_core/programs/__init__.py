"""harness_core.programs — DSPy-style compilable multi-hop programs.

Per [docs/93-dspy.md](../../../../../../research/harness-engineering/docs/93-dspy.md),
[docs/199-multi-hop-reasoning-techniques-arc.md](../../../../../../research/harness-engineering/docs/199-multi-hop-reasoning-techniques-arc.md)
Phase 2 (declarative pipelines), and per-project apply plans citing this as
Tier-1: [docs/203] §4.1 Polaris, [docs/208] §4.1 Lyra, [docs/218] §4.1 Atlas,
[docs/219] §4.1 Helix, [docs/220] §4.1 Orion.

A *program* is a typed wrapper around :class:`MultiHopPipeline` that adds:

    1. A :class:`Signature` — declared input field names + output field +
       instruction. The DSPy concept that makes prompts programmable.
    2. A demonstration buffer — bootstrapped (input, trace, output) examples
       prepended to the prompt to lift accuracy via in-context learning.
    3. A compile step — given a trainset + eval function, run the program,
       keep the top-k high-scoring trajectories as demonstrations, return a
       new program with the demonstrations attached.

Composes with :class:`MultiHopPipeline`'s budget tracking + cache + gates so
compiled programs inherit the discipline of the underlying pipeline.
"""
from __future__ import annotations

from .multi_hop_program import (
    Demonstration,
    Example,
    MultiHopProgram,
    ProgramOutput,
    Signature,
    evaluate,
)
from .optimizer import BootstrapFewShot

__all__ = [
    "BootstrapFewShot",
    "Demonstration",
    "Example",
    "MultiHopProgram",
    "ProgramOutput",
    "Signature",
    "evaluate",
]
