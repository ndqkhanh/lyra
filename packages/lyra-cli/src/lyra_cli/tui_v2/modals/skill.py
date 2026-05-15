"""SkillPicker — browse installed skills.

Read-only for Phase 5: surfaces project + global skill manifests
discovered by the slash-command helper. Picking a skill returns its
name so the caller can echo it into the prompt (a common workflow
is ``@skill <name>`` to inject the skill content into a turn).
"""
from __future__ import annotations

from pathlib import Path

from ..commands.skills_mcp import _list_skills
from .base import Entry, LyraPickerModal


def skill_entries(working_dir: Path) -> list[Entry]:
    """Return the picker rows. Pure — testable without Textual."""
    rows = _list_skills(working_dir)
    return [
        Entry(
            key=name,
            label=f"[dim][{source}][/] {name}",
            description=desc or "[dim](no description)[/]",
            meta={"source": source, "name": name},
        )
        for source, name, desc in rows
    ]


class SkillPicker(LyraPickerModal):
    picker_title = "Skills · browse installed"

    def __init__(self, working_dir: Path) -> None:
        self._working_dir = Path(working_dir)
        super().__init__()

    def entries(self) -> list[Entry]:
        return skill_entries(self._working_dir)
