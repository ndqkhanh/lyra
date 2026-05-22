"""SkillsLifecycleWidget — TUI panel for skill lifecycle management.

Ports skills_lifecycle.py and skills_inject.py into a visual panel.
Shows:
  • Available skills count and discovery roots
  • Skill grid with status (active/admitted/pending/pruned)
  • Quick-admit gate (required sections check)
  • Per-skill token budget impact

Ctrl+Shift+K to toggle. /skills in the REPL.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

# ── Skill discovery roots ──────────────────────────────────────────────

SKILL_ROOTS: list[Path] = [
    Path.home() / ".lyra" / "skills",
    Path.cwd() / ".lyra" / "skills",
]


def _discover_skills() -> list[dict[str, Any]]:
    """Discover available skills from all roots."""
    skills: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in SKILL_ROOTS:
        if not root.is_dir():
            continue
        for skill_dir in sorted(root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            sid = skill_dir.name
            if sid in seen:
                continue
            seen.add(sid)

            # Read name from first heading
            name = sid
            description = ""
            try:
                content = skill_md.read_text().split("\n")
                for line in content[:10]:
                    if line.startswith("# ") and not line.startswith("##"):
                        name = line[2:].strip()
                        break
                # Read description from second paragraph
                for line in content[1:15]:
                    if line.strip() and not line.startswith("#") and not line.startswith("---"):
                        description = line.strip()[:80] + ("…" if len(line.strip()) > 80 else "")
                        break
            except Exception:
                pass

            skills.append({
                "id": sid,
                "name": name,
                "description": description,
                "root": str(root),
            })
    return skills


def _required_sections(path: Path) -> list[str]:
    """Check which required sections a skill has."""
    required = ["## Applicability", "## Procedure", "## Verifier"]
    if not path.exists():
        return required
    content = path.read_text()
    return [s for s in required if s not in content]


# ── TUI Widget ─────────────────────────────────────────────────────────

class SkillsLifecycleWidget(Widget):
    """Skill management panel — Ctrl+Shift+K to toggle.

    Shows: available skills count, discovery roots, skill grid with
    admission status, quick-admit gate results.
    """

    DEFAULT_CSS = """
    SkillsLifecycleWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    SkillsLifecycleWidget.collapsed {
        height: 1;
        border: none;
    }

    SkillsLifecycleWidget #sk-header {
        height: 1;
        color: $text-muted;
    }

    SkillsLifecycleWidget #sk-roots {
        height: auto;
        margin: 0 0 0 1;
    }

    SkillsLifecycleWidget #sk-skills {
        height: auto;
        max-height: 10;
        margin: 0 0 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+k", "toggle_skills", "Skills"),
    ]

    expanded: reactive[bool] = reactive(False)
    skill_count: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Static("", id="sk-header")
        yield Static("", id="sk-roots")
        yield Static("", id="sk-skills")

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        skills = _discover_skills()
        self.skill_count = len(skills)
        self._render()

    def action_toggle_skills(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        if self.expanded:
            self._refresh()
        self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_header()
            self._render_roots()
            self._render_skills()
        except Exception:
            pass

    def _render_header(self) -> None:
        hint = "[dim](ctrl+shift+k)[/]"
        if self.expanded:
            self.query_one("#sk-header", Static).update(
                f"[bold]Skills[/]  [green]{self.skill_count}[/] available  {hint}"
            )
        else:
            self.query_one("#sk-header", Static).update(
                f"[bold]Skills[/]  [green]{self.skill_count}[/]  {hint}"
            )

    def _render_roots(self) -> None:
        if not self.expanded:
            self.query_one("#sk-roots", Static).update("")
            return
        lines = ["[dim]Discovery roots:[/]"]
        for root in SKILL_ROOTS:
            glyph = "[green]✓[/]" if root.is_dir() else "[dim]○[/]"
            lines.append(f"  {glyph} [dim]{root}[/]")
        self.query_one("#sk-roots", Static).update("\n".join(lines))

    def _render_skills(self) -> None:
        if not self.expanded:
            self.query_one("#sk-skills", Static).update("")
            return

        skills = _discover_skills()
        if not skills:
            self.query_one("#sk-skills", Static).update(
                "  [dim]No skills found[/]"
            )
            return

        lines = ["[dim]Skills:[/]"]
        for s in skills[:15]:
            sid = s["id"][:20]
            name = s["name"][:30]
            desc = f"[dim]— {s['description']}[/]" if s["description"] else ""

            # Check admission gate
            skill_path = Path(s["root"]) / s["id"] / "SKILL.md"
            missing = _required_sections(skill_path)
            if missing:
                glyph = "[yellow]⚠[/]"
            else:
                glyph = "[green]✓[/]"

            lines.append(f"  {glyph} [bold]{name:<30}[/] {desc}")
        if len(skills) > 15:
            lines.append(f"  [dim]… +{len(skills) - 15} more[/]")

        self.query_one("#sk-skills", Static).update("\n".join(lines))
