"""Hermes-style skill extractor (Phase 4d upgrade — v3.5).

Turns successful tool-call trajectories into candidate
:class:`SkillManifest` proposals. User review is always required;
the extractor never writes to disk.

v3.5 upgrades over the v3.4 minimal version (Hermes-agent v0.12
absorption):

1. **Rubric-first review** — before promotion, the candidate is
   scored against a small deterministic rubric (sufficient diversity
   in tool calls, has structured sections, references no secrets,
   slug is unique). Each rubric criterion gets a pass/fail; the
   candidate is rejected if any HARD criterion fails.
2. **Active-update bias** — when ``existing_skill_ids`` is supplied,
   collisions on slug or near-collisions are reported so the caller
   can prefer "update existing skill" over "create new". The
   reviewer does not silently shadow an existing skill with the
   same slug.
3. **Inherited runtime context** — the optional ``trace_id`` /
   ``session_id`` / ``operator`` fields propagate into the manifest
   ``extras`` so audits can trace each candidate back to the
   trajectory that produced it.

Backward compat: the old ``extract_candidate(ExtractorInput)`` API
still works unchanged. The new fields are additive and default to
empty / safe values.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from .loader import SkillManifest


@dataclass
class ExtractorInput:
    """Inputs the extractor consumes.

    Attributes
    ----------
    task
        Free-form description of the trajectory (typically the user's
        first turn, or a one-line summary).
    outcome_verdict
        ``"pass"`` | ``"fail"`` | ``"needs_more"``. Only ``"pass"``
        is eligible for promotion.
    tool_calls
        Ordered list of ``{"name": str, "args": dict, ...}`` records.
    skills_used
        Ids of skills that fired during the trajectory.
    existing_skill_ids
        Optional list of skill ids already on disk. When supplied,
        the extractor refuses to propose a slug already in use and
        reports the collision so the caller can route to ``lyra
        skill reflect <id>`` instead. Phase 4d active-update bias.
    trace_id
        Optional OTel trace id, propagated into manifest extras.
    session_id
        Optional Lyra session id, propagated into manifest extras.
    operator
        Optional human operator name, propagated into manifest
        extras for audit trails.
    """

    task: str
    outcome_verdict: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    skills_used: list[str] = field(default_factory=list)
    existing_skill_ids: Sequence[str] = field(default_factory=list)
    trace_id: str = ""
    session_id: str = ""
    operator: str = ""


@dataclass
class RubricCheck:
    """Outcome of one deterministic rubric criterion."""

    name: str
    passed: bool
    hard: bool
    detail: str = ""


@dataclass
class ExtractorOutput:
    promote: bool
    requires_user_review: bool
    manifest: SkillManifest | None = None
    reason: str | None = None
    rubric: list[RubricCheck] = field(default_factory=list)


# Promotion thresholds. Bumped from 3 → 4 in v3.5 to match Hermes'
# observation that 3-call trajectories produce too-narrow skills
# (they end up brittle to small task variations).
_MIN_TOOL_CALLS = 4
_MIN_DISTINCT_TOOLS = 2
_MAX_BODY_LINES = 200  # rubric-quality bound; not enforced as failure

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),       # OpenAI / Anthropic
    re.compile(r"AIza[A-Za-z0-9_-]{20,}"),     # Google API
    re.compile(r"AKIA[A-Z0-9]{16}"),           # AWS access key
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),       # GitHub fine-grained
    re.compile(r"glpat-[A-Za-z0-9_-]{20,}"),   # GitLab personal token
]


def _slug(task: str) -> str:
    s = task.lower().strip()
    s = re.sub(r"[^a-z0-9 _-]+", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s[:48] or "unnamed"


def _build_rubric(inp: ExtractorInput, *, slug: str, body: str) -> list[RubricCheck]:
    """Run the deterministic checks. Caller decides what to do with the verdict."""
    checks: list[RubricCheck] = []

    # 1. enough tool calls (HARD)
    n_calls = len(inp.tool_calls)
    checks.append(RubricCheck(
        name="min_tool_calls",
        passed=n_calls >= _MIN_TOOL_CALLS,
        hard=True,
        detail=f"{n_calls} tool calls (require ≥ {_MIN_TOOL_CALLS})",
    ))

    # 2. enough distinct tool names — single-tool trajectories don't
    #    generalise to skill-shaped patterns (HARD)
    distinct = len({tc.get("name", "?") for tc in inp.tool_calls})
    checks.append(RubricCheck(
        name="distinct_tools",
        passed=distinct >= _MIN_DISTINCT_TOOLS,
        hard=True,
        detail=f"{distinct} distinct tool name(s) (require ≥ {_MIN_DISTINCT_TOOLS})",
    ))

    # 3. slug not already taken (HARD if existing_skill_ids supplied)
    collision = slug in inp.existing_skill_ids
    checks.append(RubricCheck(
        name="slug_unique",
        passed=not collision,
        hard=bool(inp.existing_skill_ids),
        detail=(
            f"slug {slug!r} already exists; consider `lyra skill reflect {slug}`"
            if collision
            else f"slug {slug!r} is unused"
        ),
    ))

    # 4. body has the expected sections (SOFT — informational)
    has_sections = all(s in body for s in ("## When to use", "## Tool sequence"))
    checks.append(RubricCheck(
        name="has_sections",
        passed=has_sections,
        hard=False,
        detail="manifest body has expected section headers",
    ))

    # 5. no obvious leaked secrets in either body or tool args (HARD)
    secret_hit = _scan_secrets(body) or _scan_secrets_in_tool_args(inp.tool_calls)
    checks.append(RubricCheck(
        name="no_leaked_secrets",
        passed=not secret_hit,
        hard=True,
        detail=(
            f"redacted-style secret found in {secret_hit!r}"
            if secret_hit
            else "no secret-shaped strings detected"
        ),
    ))

    # 6. body length is reasonable (SOFT)
    body_lines = body.count("\n") + 1
    checks.append(RubricCheck(
        name="body_length_bounded",
        passed=body_lines <= _MAX_BODY_LINES,
        hard=False,
        detail=f"{body_lines} body lines (recommended ≤ {_MAX_BODY_LINES})",
    ))

    return checks


def _scan_secrets(text: str) -> str:
    """Return the matched secret-shaped string, or empty if none found."""
    for pat in _SECRET_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(0)
    return ""


def _scan_secrets_in_tool_args(calls: list[dict[str, Any]]) -> str:
    for tc in calls:
        args = tc.get("args") or tc.get("input") or {}
        as_text = str(args)
        hit = _scan_secrets(as_text)
        if hit:
            return hit
    return ""


def extract_candidate(inp: ExtractorInput) -> ExtractorOutput:
    """Promote a trajectory into a candidate :class:`SkillManifest` if eligible."""
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

    rubric = _build_rubric(inp, slug=slug, body=body)
    hard_failures = [c for c in rubric if c.hard and not c.passed]
    if hard_failures:
        first = hard_failures[0]
        return ExtractorOutput(
            promote=False,
            requires_user_review=True,
            reason=f"rubric: {first.name}: {first.detail}",
            rubric=rubric,
        )

    extras: dict[str, Any] = {}
    if inp.trace_id:
        extras["trace_id"] = inp.trace_id
    if inp.session_id:
        extras["session_id"] = inp.session_id
    if inp.operator:
        extras["operator"] = inp.operator
    if inp.skills_used:
        extras["parent_skills"] = list(inp.skills_used)

    manifest = SkillManifest(
        id=slug,
        name=slug.replace("-", " ").title(),
        description=f"Learned pattern for: {inp.task[:80]}",
        body=body,
        path="(candidate, not yet on disk)",
        extras=extras,
    )
    return ExtractorOutput(
        promote=True,
        requires_user_review=True,
        manifest=manifest,
        reason="trajectory passed rubric and met minimum length",
        rubric=rubric,
    )


__all__ = [
    "ExtractorInput",
    "ExtractorOutput",
    "RubricCheck",
    "extract_candidate",
]
