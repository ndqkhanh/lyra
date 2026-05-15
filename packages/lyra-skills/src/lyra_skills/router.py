"""Description-based skill router (naive keyword overlap).

v1 matches tokens in the user query against each skill's description and
name. Ties break by user-root precedence (first-seen in the loaded list,
which honours the loader's later-root-wins order).

V3.8 Theme A — when an :class:`~lyra_skills.argus_cascade.LyraArgusCascade`
is wired in via the constructor or :meth:`SkillRouter.with_argus`,
:meth:`route` delegates to Argus's five-tier cascade (BM25 + embedding +
cross-encoder + hierarchical navigation) and projects results back to
:class:`SkillManifest`. The original token-overlap path remains the
primary path when no cascade is provisioned.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .loader import SkillManifest

if TYPE_CHECKING:  # pragma: no cover
    from .argus_cascade import CascadeResult, LyraArgusCascade

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")
_STOPWORDS = {
    "i", "to", "the", "a", "an", "of", "in", "on", "at", "for", "and", "or",
    "with", "from", "by", "is", "this", "that", "be", "need", "want", "please",
    "it", "into",
}

# Lightweight coding-verb synonyms: expand the query (and skill descriptions)
# so "change" still reaches the "edit" skill without embeddings.
_SYNONYMS = {
    "change": "edit",
    "changes": "edit",
    "modify": "edit",
    "update": "edit",
    "alter": "edit",
    "rewrite": "edit",
    "fix": "edit",
    "patch": "edit",
    "add": "edit",
    "remove": "edit",
    "delete": "edit",
    "refactor": "edit",
    "edits": "edit",
    "check": "review",
    "audit": "review",
    "inspect": "review",
    "find": "localize",
    "locate": "localize",
    "search": "localize",
    "where": "localize",
    "test": "test-gen",
    "tests": "test-gen",
}


def _stem(tok: str) -> str:
    if tok.endswith("ing") and len(tok) > 4:
        return tok[:-3]
    if tok.endswith("ed") and len(tok) > 3:
        return tok[:-2]
    if tok.endswith("s") and len(tok) > 3 and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def _tokens(text: str) -> set[str]:
    out: set[str] = set()
    for raw in _TOKEN_RE.findall(text):
        low = raw.lower()
        if low in _STOPWORDS:
            continue
        out.add(low)
        stem = _stem(low)
        if stem != low:
            out.add(stem)
        if low in _SYNONYMS:
            out.add(_SYNONYMS[low])
    return out


@dataclass
class _Scored:
    skill: SkillManifest
    score: int


class SkillRouter:
    def __init__(
        self,
        skills: Sequence[SkillManifest],
        *,
        argus_cascade: "LyraArgusCascade | None" = None,
    ) -> None:
        self._skills = list(skills)
        self._cascade = argus_cascade

    @classmethod
    def with_argus(
        cls,
        skills: Sequence[SkillManifest],
        *,
        cascade: "LyraArgusCascade | None" = None,
        **cascade_kwargs,
    ) -> "SkillRouter":
        """Build a router whose :meth:`route` delegates to an Argus cascade.

        When *cascade* is omitted, a fresh :class:`LyraArgusCascade` is
        constructed from ``cascade_kwargs`` (typically ``state_dir`` and
        ``harness_name``) and the *skills* are indexed into it. This is
        the one-call ergonomic for adopting Argus.
        """
        from .argus_cascade import LyraArgusCascade

        if cascade is None:
            cascade = LyraArgusCascade(**cascade_kwargs)
        cascade.index_manifests(skills)
        return cls(skills, argus_cascade=cascade)

    @property
    def argus_cascade(self) -> "LyraArgusCascade | None":
        """The wired cascade, or ``None`` for the default token-overlap router."""
        return self._cascade

    def route(self, query: str, *, top_k: int = 3) -> list[SkillManifest]:
        if self._cascade is not None:
            result = self._cascade.route(query, top_k=top_k)
            return [pick.manifest for pick in result.picks]
        return self._route_overlap(query, top_k=top_k)

    def route_with_trace(
        self, query: str, *, top_k: int = 3, mode: str = "auto",
    ) -> "CascadeResult":
        """Run the Argus cascade and return the full reasoning trace.

        Raises :class:`RuntimeError` when no cascade is wired — call
        :meth:`with_argus` first or pass ``argus_cascade=`` to the
        constructor. Pass ``mode="keyword"`` for deterministic BM25
        ranking on small catalogs where auto mode would otherwise
        admit every loadable skill.
        """
        if self._cascade is None:
            raise RuntimeError(
                "route_with_trace requires an Argus cascade; "
                "use SkillRouter.with_argus(skills) to wire one in."
            )
        return self._cascade.route(query, top_k=top_k, mode=mode)

    def _route_overlap(
        self, query: str, *, top_k: int,
    ) -> list[SkillManifest]:
        q = _tokens(query)
        if not q:
            return []
        scored: list[_Scored] = []
        for s in self._skills:
            body = f"{s.name} {s.description}"
            matches = _tokens(body) & q
            if matches:
                scored.append(_Scored(skill=s, score=len(matches)))
        scored.sort(key=lambda x: x.score, reverse=True)
        return [s.skill for s in scored[:top_k]]

    def system_prompt_index(self, *, limit: int | None = None) -> str:
        """Render a compact one-line-per-skill index for the system prompt.

        This is the Claude-Code-style "skill index" line list: the agent
        sees skill ids and their descriptions so it knows which skills
        exist and can request them on demand via the router. Keep it
        short — long prompts burn context.
        """
        skills = self._skills if limit is None else self._skills[:limit]
        if not skills:
            return ""
        lines = [
            f"- {s.id}: {s.description.splitlines()[0] if s.description else s.name}"
            for s in skills
        ]
        return "Available skills:\n" + "\n".join(lines)
