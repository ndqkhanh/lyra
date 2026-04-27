"""Team roles & multi-agent orchestration — MetaGPT pattern.

Inspired by *MetaGPT* (hong2024metagpt; ICLR 2024 oral) and the
``Code = SOP(Team)`` philosophy: materialise each role's Standard
Operating Procedure as data, then orchestrate them as a pipeline.

A :class:`TeamRole` carries:

* a ``system_prompt`` — the role's persona / brief
* a ``toolset`` name — pulls one of the named bundles registered in
  :mod:`lyra_core.tools.toolsets` (so ``Engineer`` gets ``coding``,
  ``Reviewer`` gets ``safe``, etc.)
* a ``sop`` — an ordered list of bullet-point operating procedures
  the role must follow (these are surfaced verbatim to the LLM)

A :class:`TeamPlan` is an ordered list of role names with optional
per-step task overrides. :func:`run_team_plan` executes the plan
sequentially: each step's output is threaded as input context to the
next step. The :class:`TeamRunReport` records every handoff so the
trace is auditable.

Five built-in roles (sourced from MetaGPT's software-company SOP):

* ``pm``         — Product Manager (clarify intent, write user stories)
* ``architect``  — System Architect (decompose into components / APIs)
* ``engineer``   — Engineer (implement the smallest reversible diff)
* ``reviewer``   — Reviewer (rubric pass over the diff)
* ``qa``         — QA / Tester (write or run the verification harness)

The orchestration layer is intentionally model-agnostic: callers wire
an :class:`AgentCallable` that knows how to talk to the live LLM
(``InteractiveSession`` ships one), which keeps this module testable
with a stub callable in unit tests.
"""
from __future__ import annotations

from .registry import (
    AgentCallable,
    TeamPlan,
    TeamRegistry,
    TeamRole,
    TeamRunReport,
    TeamStep,
    TeamStepResult,
    default_registry,
    default_software_plan,
    run_team_plan,
)

__all__ = [
    "AgentCallable",
    "TeamPlan",
    "TeamRegistry",
    "TeamRole",
    "TeamRunReport",
    "TeamStep",
    "TeamStepResult",
    "default_registry",
    "default_software_plan",
    "run_team_plan",
]
