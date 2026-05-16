"""Interactive skill picker for Phase 1 skill system.

Full-screen dialog for browsing and selecting skills to execute.
Launched by `/skill` (no args) when stdin is a TTY.

UI Pattern:
    Skills
    2 skills · Enter to execute, / to search, Esc to cancel

      tdd-guide              [development] v1.0.0
        Test-Driven Development guide
    ❯ auto-research          [research] v1.0.0
        Autonomous deep research agent

Returns the selected skill name on Enter, or None on Esc.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.styles import Style

__all__ = ["run_skill_picker"]


@dataclass(frozen=True)
class _SkillEntry:
    """One row in the picker."""

    name: str
    description: str
    category: str
    version: str
    aliases: tuple[str, ...]


def _matches(entry: _SkillEntry, query: str) -> bool:
    """Check if entry matches the search query."""
    if not query:
        return True
    q = query.lower()
    return (
        q in entry.name.lower()
        or q in entry.description.lower()
        or q in entry.category.lower()
        or any(q in alias.lower() for alias in entry.aliases)
    )


_TITLE = "Skills"
_HEADER_FMT = "{n} skills · Enter to execute, / to search, Esc to cancel"
_PAGE = 8


def run_skill_picker(skills: dict) -> Optional[str]:
    """Run the interactive skill picker dialog.

    Args:
        skills: Dict of skill_name -> skill_data from SkillManager

    Returns:
        Selected skill name on Enter, None on Esc
    """
    if not skills:
        return None

    # Build entries
    entries = [
        _SkillEntry(
            name=name,
            description=skill.get("description", "No description"),
            category=skill.get("category", "unknown"),
            version=skill.get("version", "unknown"),
            aliases=tuple(skill.get("aliases", [])),
        )
        for name, skill in sorted(skills.items())
    ]

    ui = {
        "filter": "",
        "cursor": 0,
        "result": None,
    }

    filter_buffer = Buffer(multiline=False)

    def visible() -> list[_SkillEntry]:
        return [e for e in entries if _matches(e, ui["filter"])]

    def render_list() -> FormattedText:
        rows = visible()
        if not rows:
            return FormattedText(
                [("class:dim", "  (no matches — try a different filter)\n")]
            )

        cursor = min(max(ui["cursor"], 0), len(rows) - 1)
        ui["cursor"] = cursor

        out: list[tuple[str, str]] = []
        max_name = max((len(e.name) for e in rows), default=20)

        for i, e in enumerate(rows):
            is_cursor = i == cursor
            arrow = "❯ " if is_cursor else "  "
            cls_arrow = "class:cursor" if is_cursor else "class:dim"
            cls_name = "class:cursor-row" if is_cursor else "class:name"
            cls_meta = "class:meta-current" if is_cursor else "class:meta"
            cls_desc = "class:description-current" if is_cursor else "class:description"

            pad = " " * max(1, max_name - len(e.name) + 2)
            meta = f"[{e.category}] v{e.version}"

            out.append((cls_arrow, f"  {arrow}"))
            out.append((cls_name, f"{e.name}"))
            out.append((cls_meta, f"{pad}{meta}\n"))

            # Description on second line
            desc_indent = "      "
            out.append((cls_desc, f"{desc_indent}{e.description}\n"))

        return FormattedText(out)

    def render_filter() -> FormattedText:
        q = ui["filter"]
        if not q:
            return FormattedText([("class:dim", "  filter: (type to narrow)")])
        return FormattedText(
            [
                ("class:dim", "  filter: "),
                ("class:filter", q),
            ]
        )

    def on_filter_change(_: Buffer) -> None:
        ui["filter"] = filter_buffer.text
        ui["cursor"] = 0
        app.invalidate()

    filter_buffer.on_text_changed += on_filter_change

    kb = KeyBindings()

    def _move(delta: int) -> None:
        n = len(visible())
        if n == 0:
            return
        ui["cursor"] = (ui["cursor"] + delta) % n

    @kb.add("up")
    def _(_e: object) -> None:
        _move(-1)

    @kb.add("down")
    def _(_e: object) -> None:
        _move(1)

    @kb.add("pageup")
    def _(_e: object) -> None:
        _move(-_PAGE)

    @kb.add("pagedown")
    def _(_e: object) -> None:
        _move(_PAGE)

    @kb.add("home")
    def _(_e: object) -> None:
        ui["cursor"] = 0

    @kb.add("end")
    def _(_e: object) -> None:
        ui["cursor"] = max(0, len(visible()) - 1)

    @kb.add("/")
    def _(_e: object) -> None:
        # Slash focuses the filter box (idempotent)
        pass

    @kb.add("enter")
    def _(_e: object) -> None:
        rows = visible()
        if not rows:
            return
        selected = rows[ui["cursor"]]
        ui["result"] = selected.name
        app.exit()

    @kb.add("escape", eager=True)
    def _(_e: object) -> None:
        if ui["filter"]:
            filter_buffer.document = Document("")
            return
        app.exit()

    @kb.add("c-c")
    def _(_e: object) -> None:
        app.exit()

    style = Style.from_dict(
        {
            "title": "bold #5fafff",
            "description": "#888888",
            "description-current": "#aaaaaa",
            "cursor": "bold #5fafff",
            "cursor-row": "bold #ffffff",
            "name": "#cccccc",
            "meta": "italic #666666",
            "meta-current": "italic #aaaaaa",
            "filter": "bold #ffaf00",
            "dim": "#555555",
        }
    )

    header = HSplit(
        [
            Window(
                FormattedTextControl(
                    FormattedText(
                        [
                            ("class:title", _TITLE),
                            ("", "\n"),
                            (
                                "class:description",
                                _HEADER_FMT.format(n=len(entries)),
                            ),
                        ]
                    )
                ),
                height=2,
            ),
            Window(height=1, char=" "),
            Window(FormattedTextControl(render_list), wrap_lines=False),
            Window(height=1, char=" "),
            Window(FormattedTextControl(render_filter), height=1),
            Window(BufferControl(buffer=filter_buffer), height=1),
        ]
    )

    layout = Layout(header)
    app: Application = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=True,
        mouse_support=False,
    )
    layout.focus(filter_buffer)
    app.run()
    return ui["result"]
