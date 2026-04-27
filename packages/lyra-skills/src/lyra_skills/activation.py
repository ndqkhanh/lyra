"""Progressive skill activation (Phase N.7).

Skills marked ``progressive: true`` keep their full body out of
the default system prompt — only the *description* is advertised.
The full body is materialised only when the skill *activates*,
either because:

1. The user prompt mentions one of the skill's ``keywords``
   (case-insensitive substring match — cheap, no NLP needed).
2. The model explicitly invokes the skill (the chat handler
   detects e.g. ``USE SKILL: <id>``).
3. The caller force-activates a skill by id.

Non-progressive skills always inject their body — that's the
existing behaviour for canonical packs (TDD, surgical-changes, …).

This module is *pure*: it takes a list of :class:`SkillManifest`
plus a prompt and returns the activation set. Wiring into the
chat loop (and the system-prompt block) lives in
:mod:`lyra_cli.interactive.skills_inject`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from .loader import SkillManifest


# Phase O.6: optional resolver that maps a skill id → utility score
# (typically via the on-disk ledger). Returning a higher number
# means "prefer this skill"; ``None`` from the resolver is treated
# as 0.0 so unrecorded skills don't get penalised. The resolver is
# best-effort: if it raises, the activation logic falls back to
# pre-O.6 insertion order rather than aborting the turn.
UtilityResolver = Callable[[str], float]


# How long a body can grow before we truncate it for safety. The
# default is generous (4 KiB) — way bigger than any reasonable
# skill — but stops a pathological pack from blowing the context
# window single-handedly.
_DEFAULT_MAX_BODY_CHARS = 4_096


# Cap on activated skills per turn. Even with progressive loading,
# 50 simultaneously-active skills would torch the token budget.
_DEFAULT_MAX_ACTIVE = 6


@dataclass(frozen=True)
class ActivatedSkill:
    """One skill that has been promoted from "advertised" to "loaded".

    Attributes:
        manifest: The skill's parsed manifest.
        reason: Free-form string explaining *why* this skill
            activated. Surfaced in debug logs and the chat-mode
            "skills active" footer so the user can audit which
            keyword pulled the body in.
        body: Truncated body content ready to splice into the
            system prompt. Capped at ``max_body_chars`` to avoid
            runaway prompt growth.
    """

    manifest: SkillManifest
    reason: str
    body: str


def _norm(text: str) -> str:
    """Lowercase + collapse whitespace for keyword matching."""
    return re.sub(r"\s+", " ", text or "").strip().lower()


def match_keywords(
    prompt: str,
    skills: Iterable[SkillManifest],
) -> list[tuple[SkillManifest, str]]:
    """Return ``(skill, matched_keyword)`` tuples for keyword hits.

    The match is a *substring* check on a normalised prompt — cheap
    and sufficient for the small keyword lists skills declare. We
    return only the *first* matching keyword per skill so callers
    don't have to dedupe before showing the user.

    Skills without keywords are skipped — they have no opt-in
    surface, so there's nothing for the user to trigger.
    """
    haystack = _norm(prompt)
    if not haystack:
        return []
    out: list[tuple[SkillManifest, str]] = []
    for skill in skills:
        for kw in skill.keywords or ():
            needle = _norm(kw)
            if needle and needle in haystack:
                out.append((skill, kw))
                break
    return out


def match_explicit_invocations(
    prompt: str,
    skills: Iterable[SkillManifest],
) -> list[tuple[SkillManifest, str]]:
    """Detect explicit ``USE SKILL: <id>`` directives.

    Power-users (and other agents going through ``lyra serve``)
    can pin a skill that wouldn't otherwise activate by writing
    ``USE SKILL: surgical-changes`` somewhere in the prompt.
    Multiple directives stack.
    """
    if not prompt:
        return []
    pattern = re.compile(r"USE\s+SKILL\s*:\s*([A-Za-z0-9_\-./]+)", re.IGNORECASE)
    requested = {m.group(1).strip().lower() for m in pattern.finditer(prompt)}
    if not requested:
        return []
    out: list[tuple[SkillManifest, str]] = []
    for skill in skills:
        if skill.id.lower() in requested:
            out.append((skill, f"explicit `USE SKILL: {skill.id}`"))
    return out


def _safe_utility(
    resolver: UtilityResolver | None, skill_id: str
) -> float:
    """Best-effort utility lookup.

    Returns ``0.0`` when the resolver is missing, raises, or returns
    a non-numeric value. We never let ledger problems crash the
    activation pipeline (telemetry must never break a chat turn).
    """
    if resolver is None:
        return 0.0
    try:
        v = resolver(skill_id)
    except Exception:
        return 0.0
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def select_active_skills(
    prompt: str,
    skills: Sequence[SkillManifest],
    *,
    force_ids: Iterable[str] = (),
    max_active: int = _DEFAULT_MAX_ACTIVE,
    max_body_chars: int = _DEFAULT_MAX_BODY_CHARS,
    utility_resolver: UtilityResolver | None = None,
) -> list[ActivatedSkill]:
    """Resolve which **progressive** skill bodies land in the system prompt.

    Pre-N.7 every skill was description-only — bodies were fetched
    via the ``Read`` tool on demand. N.7 keeps that as the default
    (non-progressive skills are still description-only) and adds a
    new opt-in path: a skill that declares ``progressive: true``
    can be *activated* mid-turn. The body of an activated skill is
    inlined into the prompt so the model gets the full procedure
    without a round-trip.

    Activation precedence — caller intent always wins:

    1. **Force-activated** ids (passed by the caller, e.g. a CLI
       flag) win first regardless of utility — explicit caller
       intent must never be silently dropped.
    2. **Explicit invocations** in the prompt (``USE SKILL: id``).
       Phase O.6: when utility data is available, ties between
       multiple explicit directives are broken by ledger utility
       (highest first).
    3. **Keyword matches** against ``skill.keywords``. Phase O.6:
       sorted by ledger utility (highest first) before applying
       the ``max_active`` cap, so a saturated prompt picks the
       skills that have actually worked in the past.

    The activation set is capped at ``max_active`` so a chatty
    prompt can't blow the prompt budget. Bodies are truncated to
    ``max_body_chars`` + an ellipsis.

    Non-progressive skills are intentionally *not* returned — they
    stay in the advertised list with description-only semantics
    (matching pre-N.7 behaviour).

    Args:
        prompt: The user's most recent message. Empty is fine.
        skills: Every discovered skill.
        force_ids: Skill ids the caller wants pinned (CLI flag,
            programmatic API). Non-progressive skills passed here
            *do* get force-activated — the caller has explicitly
            asked for the body.
        max_active: Cap on activations per turn.
        max_body_chars: Cap on each skill's injected body.
        utility_resolver: Phase O.6 — optional callable that maps a
            skill id to a utility score (typically the ledger
            ``utility_score``). When set, keyword/explicit matches
            are ranked by utility before the cap is applied. A
            resolver that raises is silently ignored (the activator
            falls back to pre-O.6 insertion order).
    """
    out: dict[str, ActivatedSkill] = {}
    force_set = {fid.strip().lower() for fid in force_ids if fid}

    def add(skill: SkillManifest, reason: str) -> None:
        sid = skill.id
        if sid in out or len(out) >= max_active:
            return
        out[sid] = ActivatedSkill(
            manifest=skill,
            reason=reason,
            body=_clip(skill.body, max_body_chars),
        )

    # Force activations win first — caller-pinned skills are
    # honoured regardless of their progressive flag and utility.
    for skill in skills:
        if skill.id.lower() in force_set:
            add(skill, "force-activated by caller")

    # Explicit USE SKILL directives. Only progressive skills are
    # eligible; non-progressive ones already have always-advertised
    # descriptions and the user can :Read the body if they want it.
    explicit = [
        (skill, reason)
        for skill, reason in match_explicit_invocations(prompt, skills)
        if getattr(skill, "progressive", False)
    ]
    if utility_resolver is not None and len(explicit) > 1:
        explicit.sort(
            key=lambda pair: _safe_utility(utility_resolver, pair[0].id),
            reverse=True,
        )
    for skill, reason in explicit:
        add(skill, reason)

    # Keyword matches (progressive only). Phase O.6: rank by ledger
    # utility before applying the cap so the activator picks proven
    # winners when the prompt would otherwise saturate.
    keyword_matches = [
        (skill, kw)
        for skill, kw in match_keywords(prompt, skills)
        if getattr(skill, "progressive", False)
    ]
    if utility_resolver is not None and len(keyword_matches) > 1:
        keyword_matches.sort(
            key=lambda pair: _safe_utility(utility_resolver, pair[0].id),
            reverse=True,
        )
    for skill, kw in keyword_matches:
        add(skill, f"matched keyword {kw!r}")

    return list(out.values())


def render_active_block(active: Iterable[ActivatedSkill]) -> str:
    """Render the activated-skills section of the system prompt.

    Returns an empty string when nothing is active (so the chat
    handler can skip the header). Otherwise emits one labelled
    block per skill with the (possibly truncated) body inline.
    """
    rows = list(active)
    if not rows:
        return ""
    parts: list[str] = ["## Active skills (loaded for this turn)", ""]
    for entry in rows:
        m = entry.manifest
        parts.append(f"### {m.name} (`{m.id}`)")
        parts.append(f"_Activated because: {entry.reason}._")
        parts.append("")
        parts.append(entry.body.strip())
        parts.append("")
    return "\n".join(parts)


def _clip(body: str, max_chars: int) -> str:
    """Trim *body* to *max_chars*, marking the cut with an ellipsis."""
    if not body:
        return ""
    body = body.strip()
    if len(body) <= max_chars:
        return body
    return body[: max_chars - 1].rstrip() + "…"


__all__ = [
    "ActivatedSkill",
    "UtilityResolver",
    "match_explicit_invocations",
    "match_keywords",
    "render_active_block",
    "select_active_skills",
]
