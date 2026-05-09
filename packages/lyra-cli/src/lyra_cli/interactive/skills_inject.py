"""Inject SKILL.md descriptions into the chat system prompt.

Lyra ships ``lyra-skills`` with packaged ``SKILL.md`` packs (atomic-
skills, karpathy heuristics, safety triage, the 7-phase TDD sprint),
and lets users define more under ``.lyra/skills/`` (project-local) or
``~/.lyra/skills/`` (user-global). Pre-v2.4 those skills lived in
storage but were *invisible* to the chat-mode LLM — the model couldn't
say "let me apply the surgical-changes skill here" because it didn't
know the skill existed.

This module fixes that by emitting a compact, line-budget-respecting
"available skills" block that the chat handler prepends to the active
mode system prompt:

.. code-block:: text

    ## Available skills

    Below are the SKILL.md packs you may invoke this turn. Read the
    full body via ``Read .lyra/skills/<id>/SKILL.md`` if you choose
    one — only the description is in your context.

    - surgical-changes: minimal edits, no drive-by refactors.
    - test-gen: write the smallest failing test that locks the bug.
    - injection-triage: classify untrusted input as benign / suspicious / hostile.
    …

The block is *capped* (default 32 entries, 240-char line limit) so a
user with 200 skills doesn't blow the system prompt budget. Skills
not surfaced this turn are still on disk and addressable via the
``Read`` tool — the LLM just won't know they exist by name unless it
goes looking.

Discovery roots (low → high precedence; later overrides earlier):

1. ``lyra_skills.packs/*/`` — the in-package packs that always ship
   with ``pip install lyra-skills``.
2. ``~/.lyra/skills/`` — user-global skills (the equivalent of
   claw-code's ``$HOME/.claude/skills``).
3. ``<repo>/.lyra/skills/`` — project-local skills, top priority so
   the team can override a packaged pack with a project-tuned
   variant.

Conflicts (same ``id`` in two roots) resolve to the highest-precedence
root, mirroring :func:`lyra_skills.loader.load_skills`'s
``later-wins`` semantics.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def _packaged_pack_root() -> Optional[Path]:
    """Locate the ``lyra_skills.packs`` directory inside the installed package.

    Returns ``None`` when ``lyra_skills`` isn't on the import path
    (rare — both packages always ship together — but tests that mask
    out ``lyra_skills`` exercise this branch).
    """
    try:
        import lyra_skills  # type: ignore
    except Exception:
        return None
    pkg_init = getattr(lyra_skills, "__file__", None)
    if not pkg_init:
        return None
    root = Path(pkg_init).parent / "packs"
    return root if root.is_dir() else None


def _user_skill_root() -> Optional[Path]:
    """Honour ``$LYRA_HOME`` first; fall back to ``~/.lyra/skills``."""
    home = os.environ.get("LYRA_HOME")
    base = Path(home) if home else Path.home() / ".lyra"
    skills = base / "skills"
    return skills if skills.is_dir() else None


def discover_skill_roots(repo_root: Path) -> list[Path]:
    """Collect every directory the loader should walk for ``SKILL.md`` files.

    Order matters — :func:`lyra_skills.loader.load_skills` resolves
    duplicates with later-wins semantics, so list packaged → user →
    project so a project skill always beats a packaged default.
    """
    roots: list[Path] = []
    pkg = _packaged_pack_root()
    if pkg is not None:
        roots.append(pkg)
    user = _user_skill_root()
    if user is not None:
        roots.append(user)
    project = Path(repo_root) / ".lyra" / "skills"
    if project.is_dir():
        roots.append(project)
    return roots


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


_DEFAULT_MAX_SKILLS = 32
_DEFAULT_LINE_LIMIT = 240


def render_skill_block(
    repo_root: Path,
    *,
    max_skills: int = _DEFAULT_MAX_SKILLS,
    line_limit: int = _DEFAULT_LINE_LIMIT,
    prompt: str | None = None,
    force_ids: Iterable[str] = (),
) -> str:
    """Build the system-prompt suffix listing available skills.

    Returns the empty string when no skills are discovered (fresh
    install with no packaged packs, e.g. a stripped wheel) or when
    ``lyra_skills`` isn't installed. Callers should prepend the
    block only when non-empty so the system prompt doesn't carry a
    dangling "## Available skills" header.

    Phase N.7 split the rendering in two:

    * The advertised list (one line per skill — description only)
      is what every turn sees.
    * The progressive activation block (full body inline) appears
      *additionally* when the caller passes ``prompt`` and one or
      more skills match its keywords / explicit ``USE SKILL:``
      directives. Non-progressive skills always have their body
      injected (preserving pre-N.7 behaviour for canonical packs).

    Args:
        repo_root: project root used for ``<repo>/.lyra/skills`` discovery.
        max_skills: cap on entries surfaced this turn. Skills past
            the cap remain accessible via ``Read`` once the model
            knows their path, but won't be advertised by name.
        line_limit: per-entry char cap before truncation (so a
            verbose description can't dominate the prompt).
        prompt: most recent user message used to drive progressive
            activation. ``None`` (the default) keeps the old N.6
            behaviour and never injects bodies via this path.
        force_ids: skills the caller wants pinned-on regardless
            of keyword matches (e.g. a ``--skill foo`` CLI flag).
    """
    skills = _load_skills_safely(discover_skill_roots(repo_root))
    if not skills:
        return ""

    skills.sort(key=lambda s: s.id)
    advertised = skills if len(skills) <= max_skills else skills[:max_skills]

    lines = [
        "## Available skills",
        "",
        (
            "Below are the SKILL.md packs you may invoke this turn. "
            "Read the full body via the ``Read`` tool on the skill "
            "path if you decide to apply one — only the description "
            "is in your context unless the skill activates. Skills "
            "are advisory: cite the id, explain why it fits, then "
            "run the steps."
        ),
        "",
    ]
    for s in advertised:
        desc = (s.description or "").strip().replace("\n", " ")
        marker = " [progressive]" if getattr(s, "progressive", False) else ""
        entry = f"- {s.id}{marker}: {desc}" if desc else f"- {s.id}{marker}"
        if len(entry) > line_limit:
            entry = entry[: line_limit - 1] + "…"
        lines.append(entry)
    lines.append("")

    active_block = _render_active_block(
        skills=skills,
        prompt=prompt or "",
        force_ids=force_ids,
    )
    if active_block:
        lines.append(active_block)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_active_block(
    *,
    skills: list,
    prompt: str,
    force_ids: Iterable[str],
) -> str:
    """Compute & render the per-turn activation block.

    Soft-imports :mod:`lyra_skills.activation` so an older
    ``lyra-skills`` version that pre-dates progressive loading
    still parses the system prompt without exploding.
    """
    try:
        from lyra_skills.activation import (
            render_active_block,
            select_active_skills,
        )
    except Exception:
        return ""
    active = select_active_skills(
        prompt=prompt or "",
        skills=skills,
        force_ids=list(force_ids),
    )
    return render_active_block(active)


def _build_utility_resolver():
    """Return a callable mapping ``skill_id → utility`` from the ledger.

    Phase O.6 (v3.5.0): when two progressive skills tie on keyword
    match, we want the activator to prefer the one with proven
    track record (per ``~/.lyra/skill_ledger.json``). Loading the
    ledger once per turn is cheap (a few KB JSON read) and avoids
    spreading ledger imports through the activation core.

    Returns ``None`` when the ledger module is unavailable or the
    file fails to load — callers fall back to pre-O.6 ordering.
    """
    try:
        from lyra_skills.ledger import load_ledger, utility_score
    except Exception:
        return None
    try:
        ledger = load_ledger()
    except Exception:
        return None

    def _resolve(sid: str) -> float:
        stats = ledger.get(sid)
        if stats is None:
            return 0.0
        try:
            return float(utility_score(stats))
        except Exception:
            return 0.0

    return _resolve


def _select_active_skills_safely(
    *,
    skills: list,
    prompt: str,
    force_ids: Iterable[str],
) -> list:
    """Return the list of :class:`ActivatedSkill` for this turn, or ``[]``.

    Mirrors the soft-import pattern in :func:`_render_active_block` so
    older ``lyra-skills`` builds (pre-N.7) silently degrade rather
    than crash the chat path. Phase O.6 wires in the ledger-backed
    utility resolver so saturated keyword matches go to the
    proven-good skills first.
    """
    try:
        from lyra_skills.activation import select_active_skills
    except Exception:
        return []
    resolver = _build_utility_resolver()
    try:
        return list(
            select_active_skills(
                prompt=prompt or "",
                skills=skills,
                force_ids=list(force_ids),
                utility_resolver=resolver,
            )
        )
    except TypeError:
        # Older lyra-skills (pre-O.6) won't accept ``utility_resolver``.
        # Fall back to the resolver-free signature so chat keeps working.
        return list(
            select_active_skills(
                prompt=prompt or "",
                skills=skills,
                force_ids=list(force_ids),
            )
        )


@dataclass(frozen=True)
class SkillBlockResult:
    """Structured return value for :func:`render_skill_block_with_activations`.

    Phase O.2 wants both the rendered Markdown (which the chat handler
    splices into the system prompt) *and* the list of activated skill
    ids (which the lifecycle hook records on the ledger). Returning
    them together avoids a second walk of the skills directory.

    Attributes:
        text: The same string :func:`render_skill_block` returns —
            advertised list + (optional) "## Active skills" body.
        activated_ids: Skill ids whose body got injected this turn,
            in id-sorted order (deterministic across turns so the
            telemetry record stays stable).
        activation_reasons: Map of ``id → reason`` so audit logs and
            ``lyra skill stats`` can show *why* a skill activated
            (``"keyword: dive"``, ``"forced via --skill"``, etc.).
    """

    text: str
    activated_ids: list[str] = field(default_factory=list)
    activation_reasons: dict[str, str] = field(default_factory=dict)


def render_skill_block_with_activations(
    repo_root: Path,
    *,
    max_skills: int = _DEFAULT_MAX_SKILLS,
    line_limit: int = _DEFAULT_LINE_LIMIT,
    prompt: str | None = None,
    force_ids: Iterable[str] = (),
) -> SkillBlockResult:
    """Same as :func:`render_skill_block` but reports activations.

    Phase O.2 introduced this so the chat handler can credit / debit
    activated skills on the ledger after the turn settles. Pure
    callers that only want the prompt block keep using the original
    function — this one is for the per-turn telemetry path.
    """
    skills = _load_skills_safely(discover_skill_roots(repo_root))
    if not skills:
        return SkillBlockResult(text="")

    skills.sort(key=lambda s: s.id)
    advertised = skills if len(skills) <= max_skills else skills[:max_skills]

    lines = [
        "## Available skills",
        "",
        (
            "Below are the SKILL.md packs you may invoke this turn. "
            "Read the full body via the ``Read`` tool on the skill "
            "path if you decide to apply one — only the description "
            "is in your context unless the skill activates. Skills "
            "are advisory: cite the id, explain why it fits, then "
            "run the steps."
        ),
        "",
    ]
    for s in advertised:
        desc = (s.description or "").strip().replace("\n", " ")
        marker = " [progressive]" if getattr(s, "progressive", False) else ""
        entry = f"- {s.id}{marker}: {desc}" if desc else f"- {s.id}{marker}"
        if len(entry) > line_limit:
            entry = entry[: line_limit - 1] + "…"
        lines.append(entry)
    lines.append("")

    active = _select_active_skills_safely(
        skills=skills,
        prompt=prompt or "",
        force_ids=force_ids,
    )

    activated_ids: list[str] = []
    reasons: dict[str, str] = {}
    for entry in active:
        sid = getattr(getattr(entry, "manifest", None), "id", None)
        if not sid:
            continue
        activated_ids.append(sid)
        reasons[sid] = getattr(entry, "reason", "") or ""
    activated_ids.sort()

    if active:
        try:
            from lyra_skills.activation import render_active_block

            block = render_active_block(active)
        except Exception:
            block = ""
        if block:
            lines.append(block)
            lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    return SkillBlockResult(
        text=text,
        activated_ids=activated_ids,
        activation_reasons=reasons,
    )


def _load_skills_safely(roots: Iterable[Path]) -> list:
    """Best-effort wrapper around :func:`lyra_skills.loader.load_skills`.

    A malformed ``SKILL.md`` somewhere in user-land would otherwise
    break the chat turn; we'd rather suppress the broken pack than
    refuse to answer.
    """
    try:
        from lyra_skills.loader import SkillLoaderError, load_skills
    except Exception:
        return []
    try:
        return list(load_skills(list(roots)))
    except SkillLoaderError:
        return []


__all__ = [
    "SkillBlockResult",
    "discover_skill_roots",
    "render_skill_block",
    "render_skill_block_with_activations",
]
