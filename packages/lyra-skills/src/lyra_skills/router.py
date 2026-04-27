"""Description-based skill router (naive keyword overlap).

v1 matches tokens in the user query against each skill's description and
name. Ties break by user-root precedence (first-seen in the loaded list,
which honours the loader's later-root-wins order).
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from .loader import SkillManifest

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
    def __init__(self, skills: Sequence[SkillManifest]) -> None:
        self._skills = list(skills)

    def route(self, query: str, *, top_k: int = 3) -> list[SkillManifest]:
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
