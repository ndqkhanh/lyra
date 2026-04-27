"""Wave-E Task 15: repo wiki + team onboarding generators.

The wiki crawls the repo and produces a small, durable knowledge
base under ``.lyra/wiki/``: a top-level index, one page per
top-level package, and a per-language inventory. The onboarding
generator turns the wiki into a "first-week" briefing tailored to
a teammate's role.

Both generators are intentionally I/O-light and offline so they
ship as part of the default install (no LLM call required). A
team can layer richer LLM-based summaries on top by passing a
``summariser`` callable.
"""
from __future__ import annotations

from .generator import (
    OnboardingPlan,
    WikiBundle,
    WikiPage,
    generate_onboarding,
    generate_wiki,
)

__all__ = [
    "OnboardingPlan",
    "WikiBundle",
    "WikiPage",
    "generate_onboarding",
    "generate_wiki",
]
