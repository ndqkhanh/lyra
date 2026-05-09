"""Skill loader: walks a set of roots, reads each ``SKILL.md``.

Skill frontmatter (Phase N.3) is the contract between authors and
Lyra's runtime. The loader parses it and exposes a :class:`SkillManifest`
with the fields below; consumers (chat-mode injection, ``lyra skill``
commands, the future progressive loader) only depend on this dataclass.

Frontmatter schema (all keys are optional unless noted):

* ``id`` *(required-ish)* — stable handle the model cites and the
  installer keys by. Defaults to the parent directory name when
  missing so legacy skills keep loading.
* ``name`` — human display label. Defaults to ``id``.
* ``description`` — one-line summary surfaced to chat mode.
* ``version`` — semver string (``"1.2.3"``). Empty when unset.
* ``keywords`` — list of trigger phrases the router can match against.
* ``applies_to`` — list of file globs the skill is relevant to
  (``["**/*.py", "tests/**"]``). Empty list = "always applicable".
* ``requires`` — list of Python distribution names the skill body
  expects. The loader doesn't install them; ``lyra skill add`` and
  ``lyra doctor`` surface missing requirements.
* ``progressive`` — bool; ``True`` means description-only at chat
  injection time, full body fetched on demand. N.7 will honour this.

Unknown keys are stashed verbatim in :attr:`SkillManifest.extras` so
authors can experiment without breaking forward-compat.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class SkillLoaderError(Exception):
    """Raised on malformed frontmatter or duplicate skill ids within a root."""


_KNOWN_KEYS: frozenset[str] = frozenset(
    {
        "id", "name", "description", "version", "keywords",
        "applies_to", "requires", "progressive",
    }
)


@dataclass
class SkillManifest:
    """Parsed view of one ``SKILL.md`` file.

    See module docstring for the frontmatter schema. Missing keys
    fall back to safe defaults (empty string / list / ``False``)
    so consumers never need to ``.get(...)`` with sentinels.

    Attributes:
        id: Stable identifier (parent dir name if frontmatter is silent).
        name: Display label.
        description: One-liner shown in chat-mode skill block.
        body: Markdown body after the closing ``---`` frontmatter.
        path: Absolute path of the source ``SKILL.md`` file.
        version: Semver string; empty when unspecified.
        keywords: Trigger phrases for the router.
        applies_to: File globs the skill targets.
        requires: Python dist names the skill body imports.
        progressive: ``True`` opts into N.7's lazy-body injection.
        extras: Frontmatter keys outside :data:`_KNOWN_KEYS`. Forward
            compatibility hatch — users can experiment without forcing
            the loader to recognise every flag.
    """

    id: str
    name: str
    description: str
    body: str
    path: str
    version: str = ""
    keywords: list[str] = field(default_factory=list)
    applies_to: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    progressive: bool = False
    extras: dict[str, Any] = field(default_factory=dict)


_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def _coerce_str_list(value: Any, *, field_name: str, source: Path) -> list[str]:
    """Best-effort coerce a frontmatter value to ``list[str]``.

    Authors often reach for the YAML scalar form (``keywords: foo``)
    when they only have one entry; we accept that and the canonical
    list form, but reject ``True``/``42``/dicts loudly so a typo
    doesn't silently degrade matching.
    """
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise SkillLoaderError(
                    f"{field_name} entries must be strings in {source} "
                    f"(got {type(item).__name__})"
                )
            out.append(item)
        return out
    raise SkillLoaderError(
        f"{field_name} must be a string or list of strings in {source} "
        f"(got {type(value).__name__})"
    )


def _coerce_bool(value: Any, *, field_name: str, source: Path) -> bool:
    """Accept native bool plus the YAML 'true'/'false' string fallback."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        norm = value.strip().lower()
        if norm in ("true", "1", "yes", "on"):
            return True
        if norm in ("false", "0", "no", "off", ""):
            return False
    raise SkillLoaderError(
        f"{field_name} must be a boolean in {source} "
        f"(got {type(value).__name__}: {value!r})"
    )


def _parse_skill_md(md_path: Path) -> SkillManifest:
    text = md_path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        raise SkillLoaderError(f"missing YAML frontmatter in {md_path}")
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise SkillLoaderError(f"malformed frontmatter in {md_path}: {e}") from e
    if not isinstance(fm, dict):
        raise SkillLoaderError(f"frontmatter must be a mapping in {md_path}")

    sid = str(fm.get("id") or md_path.parent.name)
    name = str(fm.get("name") or sid)
    description = str(fm.get("description") or "")
    version = str(fm.get("version") or "")
    keywords = _coerce_str_list(fm.get("keywords"), field_name="keywords", source=md_path)
    applies_to = _coerce_str_list(
        fm.get("applies_to"), field_name="applies_to", source=md_path
    )
    requires = _coerce_str_list(fm.get("requires"), field_name="requires", source=md_path)
    progressive = (
        _coerce_bool(fm.get("progressive"), field_name="progressive", source=md_path)
        if "progressive" in fm
        else False
    )
    extras = {k: v for k, v in fm.items() if k not in _KNOWN_KEYS}

    body = m.group(2).strip()
    return SkillManifest(
        id=sid,
        name=name,
        description=description,
        body=body,
        path=str(md_path),
        version=version,
        keywords=keywords,
        applies_to=applies_to,
        requires=requires,
        progressive=progressive,
        extras=extras,
    )


def load_skills(roots: Iterable[Path]) -> list[SkillManifest]:
    """Return skills with ``roots``-order resolution (later wins)."""
    by_id: dict[str, SkillManifest] = {}
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        local_ids: set[str] = set()
        for skill_md in sorted(root.rglob("SKILL.md")):
            manifest = _parse_skill_md(skill_md)
            if manifest.id in local_ids:
                raise SkillLoaderError(
                    f"duplicate skill id {manifest.id!r} in root {root}"
                )
            local_ids.add(manifest.id)
            by_id[manifest.id] = manifest
    return list(by_id.values())
