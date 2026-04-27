"""``skill_manage`` — LLM-callable tool for managing project skills.

Operations:

- ``list``    — list all skills under the configured roots.
- ``create``  — write a new ``SKILL.md`` under the project-local root
  (``.lyra/skills/<skill_id>/SKILL.md``).
- ``patch``   — append or replace the body of an existing skill.
- ``delete``  — remove a skill directory.

This is the tool a forked :class:`AgentLoop` can call during the
post-turn skill review (see
:mod:`lyra_skills.review.background`). All ops are idempotent
and safe to call from background threads.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ..loader import SkillLoaderError, SkillManifest, load_skills

SkillOp = Literal["list", "create", "patch", "delete"]


def _default_local_root() -> Path:
    """Project-local skills root — matches ``RepoLayout.skills_dir``."""
    return Path.cwd() / ".lyra" / "skills"


def _default_user_root() -> Path:
    """User-global skills root — matches hermes' ``~/.hermes-agent/skills``."""
    return Path.home() / ".lyra" / "skills"


@dataclass
class SkillManageResult:
    op: str
    ok: bool
    detail: str
    items: list[dict]

    def to_dict(self) -> dict:
        return {
            "op": self.op,
            "ok": self.ok,
            "detail": self.detail,
            "items": self.items,
        }


def _list_skills(roots: list[Path]) -> SkillManageResult:
    try:
        skills = load_skills(roots)
    except SkillLoaderError as exc:
        return SkillManageResult(
            op="list", ok=False, detail=f"load failed: {exc}", items=[]
        )
    items = [
        {"id": s.id, "name": s.name, "description": s.description, "path": s.path}
        for s in skills
    ]
    return SkillManageResult(
        op="list",
        ok=True,
        detail=f"loaded {len(items)} skill(s) from {len(roots)} root(s)",
        items=items,
    )


def _create_skill(root: Path, *, skill_id: str, name: str, description: str, body: str) -> SkillManageResult:
    skill_dir = root / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        return SkillManageResult(
            op="create",
            ok=False,
            detail=f"skill {skill_id!r} already exists at {skill_md}",
            items=[],
        )
    front = f"---\nid: {skill_id}\nname: {name}\ndescription: {description}\n---\n"
    skill_md.write_text(front + (body.strip() + "\n"), encoding="utf-8")
    return SkillManageResult(
        op="create", ok=True, detail=f"created {skill_md}", items=[{"path": str(skill_md)}]
    )


def _patch_skill(root: Path, *, skill_id: str, body: str, mode: str) -> SkillManageResult:
    skill_md = root / skill_id / "SKILL.md"
    if not skill_md.exists():
        return SkillManageResult(
            op="patch",
            ok=False,
            detail=f"skill {skill_id!r} not found at {skill_md}",
            items=[],
        )
    text = skill_md.read_text(encoding="utf-8")
    marker = "\n---\n"
    idx = text.find(marker, 4)
    if idx < 0:
        return SkillManageResult(
            op="patch",
            ok=False,
            detail=f"malformed frontmatter in {skill_md}",
            items=[],
        )
    head = text[: idx + len(marker)]
    tail = text[idx + len(marker) :]
    new_body = body.strip() + "\n"
    new_text = head + (new_body if mode == "replace" else tail.rstrip() + "\n\n" + new_body)
    skill_md.write_text(new_text, encoding="utf-8")
    return SkillManageResult(
        op="patch",
        ok=True,
        detail=f"{mode} body of {skill_id} ({skill_md})",
        items=[{"path": str(skill_md)}],
    )


def _delete_skill(root: Path, *, skill_id: str) -> SkillManageResult:
    skill_dir = root / skill_id
    if not skill_dir.exists():
        return SkillManageResult(
            op="delete",
            ok=False,
            detail=f"skill {skill_id!r} not found at {skill_dir}",
            items=[],
        )
    shutil.rmtree(skill_dir)
    return SkillManageResult(
        op="delete",
        ok=True,
        detail=f"removed {skill_dir}",
        items=[{"path": str(skill_dir)}],
    )


def skill_manage(
    op: SkillOp = "list",
    *,
    skill_id: str | None = None,
    name: str | None = None,
    description: str | None = None,
    body: str | None = None,
    patch_mode: Literal["replace", "append"] = "append",
    local_root: str | Path | None = None,
    user_root: str | Path | None = None,
) -> dict:
    """Create, list, patch, or delete project skills.

    Args:
        op: Operation to run. One of ``list``, ``create``, ``patch``, ``delete``.
        skill_id: Skill identifier (directory name). Required for
            create/patch/delete.
        name: Display name. Used by ``create``.
        description: Short description. Used by ``create``.
        body: Markdown body. Used by ``create`` and ``patch``.
        patch_mode: ``append`` (default) or ``replace`` for ``patch``.
        local_root: Override the project-local skills root.
        user_root: Override the user-global skills root.
    """
    local = Path(local_root) if local_root else _default_local_root()
    user = Path(user_root) if user_root else _default_user_root()

    if op == "list":
        return _list_skills([user, local]).to_dict()

    if not skill_id:
        return SkillManageResult(
            op=op, ok=False, detail="skill_id is required for create/patch/delete", items=[]
        ).to_dict()

    if op == "create":
        return _create_skill(
            local,
            skill_id=skill_id,
            name=name or skill_id,
            description=description or "",
            body=body or "",
        ).to_dict()

    if op == "patch":
        return _patch_skill(local, skill_id=skill_id, body=body or "", mode=patch_mode).to_dict()

    if op == "delete":
        return _delete_skill(local, skill_id=skill_id).to_dict()

    return SkillManageResult(op=op, ok=False, detail=f"unknown op {op!r}", items=[]).to_dict()


skill_manage.__tool_schema__ = {  # type: ignore[attr-defined]
    "name": "skill_manage",
    "description": "Create, list, patch, or delete project skills (SKILL.md files).",
    "parameters": {
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["list", "create", "patch", "delete"]},
            "skill_id": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "body": {"type": "string"},
            "patch_mode": {"type": "string", "enum": ["append", "replace"]},
        },
        "required": ["op"],
    },
}


__all__ = ["skill_manage", "SkillManageResult", "SkillOp"]
