"""Skill Picker Modal — browse, search, and select installed skills.

Ports dialog_skill_picker.py (257 lines) + dialog_skills.py (454 lines)
into a single Textual ModalScreen showing the full skill catalog with
search, toggle, and selection.

Access: /skills in the REPL or integrated into TUI.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

# ── Skill discovery ────────────────────────────────────────────────────

SKILL_ROOTS = [
    Path.home() / ".lyra" / "skills",
    Path.cwd() / ".lyra" / "skills",
    Path.home() / ".claude" / "skills",
    Path.home() / ".codex" / "skills",
]


@dataclass
class SkillEntry:
    name: str
    description: str
    category: str = ""
    version: str = ""

    @property
    def summary(self) -> str:
        cat = f"[dim]{'[' + self.category + ']'}[/]" if self.category else ""
        ver = f"[dim]v{self.version}[/]" if self.version else ""
        parts = [p for p in [cat, ver] if p]
        tail = f"  {' '.join(parts)}" if parts else ""
        return f"[bold]{self.name}[/]{tail}"


def _discover_skills() -> list[SkillEntry]:
    """Discover skills from all known roots."""
    seen: set[str] = set()
    skills: list[SkillEntry] = []
    for root in SKILL_ROOTS:
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            sid = d.name
            if sid in seen:
                continue
            seen.add(sid)

            skill_md = d / "SKILL.md"
            name = sid
            description = ""
            category = ""
            version = ""

            if skill_md.exists():
                try:
                    content = skill_md.read_text().split("\n")
                    for line in content[:20]:
                        if line.startswith("# ") and not line.startswith("##"):
                            name = line[2:].strip()
                    for line in content[:20]:
                        if line.strip() and not line.startswith("#") and not line.startswith("---"):
                            description = line.strip()[:80]
                            break
                    for line in content[:20]:
                        if line.startswith("## ") or line.startswith("### "):
                            cat_candidate = line.strip("# ").strip()
                            if category and cat_candidate in ("Applicability", "Procedure", "Verifier"):
                                continue
                    # Version from filename or parent
                except Exception:
                    pass

            skills.append(SkillEntry(
                name=name, description=description,
                category=category, version=version,
            ))
    return skills


class SkillPickerModal(ModalScreen[Optional[SkillEntry]]):
    """Browse and select an installed skill."""

    DEFAULT_CSS = """
    SkillPickerModal {
        align: center middle;
    }
    SkillPickerModal > Vertical {
        width: 70;
        height: 75%;
        min-height: 20;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    SkillPickerModal #sp-search {
        dock: top;
        margin: 0 0 1 0;
    }
    SkillPickerModal #sp-list {
        height: 1fr;
        border: solid $border;
    }
    SkillPickerModal #sp-list ListItem {
        padding: 0 1;
        height: 2;
    }
    SkillPickerModal #sp-list ListItem:hover {
        background: $accent 20%;
    }
    SkillPickerModal #sp-footer {
        dock: bottom;
        height: 2;
        content-align: center middle;
        color: $text-muted;
    }
    SkillPickerModal .skill-count {
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Cancel"),
        Binding("enter", "select_skill", "Select"),
        Binding("/", "focus_search", "Search"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self):
        super().__init__()
        self._all_skills: list[SkillEntry] = []
        self._filtered: list[SkillEntry] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Skill Browser[/]  browse installed skills")
            yield Input(placeholder="Search skills… (or / to focus)", id="sp-search")
            yield ListView(id="sp-list")
            yield Label("enter=select · /=search · r=refresh · esc=cancel", id="sp-footer")

    def on_mount(self) -> None:
        self._refresh()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "sp-search":
            q = event.value.lower().strip()
            if not q:
                self._filtered = list(self._all_skills)
            else:
                self._filtered = [
                    s for s in self._all_skills
                    if q in s.name.lower()
                    or q in s.description.lower()
                    or q in s.category.lower()
                ]
            self._rebuild()

    def on_list_view_selected(self, _) -> None:
        self.action_select_skill()

    def action_select_skill(self) -> None:
        lv = self.query_one("#sp-list", ListView)
        if lv.index is not None and 0 <= lv.index < len(self._filtered):
            self.dismiss(self._filtered[lv.index])

    def action_focus_search(self) -> None:
        self.query_one("#sp-search", Input).focus()

    def action_refresh(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self._all_skills = _discover_skills()
        self._filtered = list(self._all_skills)
        self._rebuild()

    def _rebuild(self) -> None:
        lv = self.query_one("#sp-list", ListView)
        lv.clear()
        if not self._filtered:
            lv.append(ListItem(Static("[dim]  No skills found[/]")))
            # Update header with count
            try:
                parent = self.query_one("Label")
                parent.update(
                    f"[bold]Skill Browser[/]  [dim]0 skills[/]"
                )
            except Exception:
                pass
            return
        for skill in self._filtered:
            lv.append(ListItem(
                Static(f"  {skill.summary}"),
            ))

