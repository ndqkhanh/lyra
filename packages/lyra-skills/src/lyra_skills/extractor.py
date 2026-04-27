"""Minimal Hermes-style skill extractor: turns successful trajectories into
candidate ``SkillManifest`` proposals. User review is always required.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .loader import SkillManifest


@dataclass
class ExtractorInput:
    task: str
    outcome_verdict: str  # "pass" | "fail" | "needs_more"
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    skills_used: list[str] = field(default_factory=list)


@dataclass
class ExtractorOutput:
    promote: bool
    requires_user_review: bool
    manifest: SkillManifest | None = None
    reason: str | None = None


_MIN_TOOL_CALLS = 3


def _slug(task: str) -> str:
    s = task.lower().strip()
    s = re.sub(r"[^a-z0-9 _-]+", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s[:48] or "unnamed"


def extract_candidate(inp: ExtractorInput) -> ExtractorOutput:
    if inp.outcome_verdict != "pass":
        return ExtractorOutput(
            promote=False,
            requires_user_review=True,
            reason=f"trajectory verdict was {inp.outcome_verdict!r}; not promoting",
        )
    if len(inp.tool_calls) < _MIN_TOOL_CALLS:
        return ExtractorOutput(
            promote=False,
            requires_user_review=True,
            reason=(
                f"only {len(inp.tool_calls)} tool calls; too small to generalise "
                f"(min {_MIN_TOOL_CALLS})"
            ),
        )

    # Build a naive manifest from the tool-call trace.
    slug = _slug(inp.task)
    tool_names = [tc.get("name", "?") for tc in inp.tool_calls]
    tool_trace = " → ".join(tool_names)
    body = (
        f"## When to use\n"
        f"Task pattern: {inp.task}\n\n"
        f"## Tool sequence\n"
        f"{tool_trace}\n\n"
        f"## Skills invoked\n"
        + ("\n".join(f"- {s}" for s in inp.skills_used) or "- (none tracked)")
    )
    manifest = SkillManifest(
        id=slug,
        name=slug.replace("-", " ").title(),
        description=f"Learned pattern for: {inp.task[:80]}",
        body=body,
        path="(candidate, not yet on disk)",
    )
    return ExtractorOutput(
        promote=True,
        requires_user_review=True,
        manifest=manifest,
        reason="trajectory passed and met minimum length",
    )
