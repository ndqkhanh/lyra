"""Interactive sessions picker — Claude-Code-style /resume + /sessions dialog.

Mirrors :mod:`dialog_skills` and :mod:`dialog_agents` shape. Lists every
session under ``<repo>/.lyra/sessions/<id>/turns.jsonl`` with its
turn-count, recorded name, and created-at timestamp. Enter picks the
session id; Esc cancels.

The bare slash commands route here:

* ``/resume`` (no args) — opens the picker; the chosen id is
  restored via the existing ``InteractiveSession.resume_session``
  code path in :func:`session._cmd_resume`.
* ``/sessions`` — same picker, just exposing the same data via a
  different verb so muscle-memory keeps working.

When stdin isn't a TTY (piped runs, tests) the slash handlers fall
back to their legacy text path.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.styles import Style

from .palette import PALETTE
from .sessions_store import SessionMeta, SessionsStore


__all__ = [
    "SessionsDialogResult",
    "build_session_entries",
    "run_sessions_dialog",
]


# ── entries ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Entry:
    """One row — a saved session under the sessions root."""

    session_id: str
    name: str
    turn_count: int
    created_at: str  # ISO-ish string; "?" when unknown


@dataclass
class SessionsDialogResult:
    """Returned from the picker on Enter; ``None`` is returned on Esc."""

    session_id: str


def build_session_entries(sessions_root: Path) -> list[_Entry]:
    """Snapshot the sessions store, swallowing IO errors."""
    try:
        rows: list[SessionMeta] = SessionsStore(sessions_root).list()
    except Exception:
        return []
    out: list[_Entry] = []
    for r in rows:
        out.append(
            _Entry(
                session_id=r.session_id,
                name=(r.name or "").strip(),
                turn_count=int(r.turn_count or 0),
                created_at=(r.created_at or "").strip() or "?",
            )
        )
    return out


# ── sort modes ──────────────────────────────────────────────────


_SORT_MODES: tuple[str, ...] = ("recent", "id", "turns", "name")


def _sort_entries(rows: list[_Entry], mode: str) -> list[_Entry]:
    """Order rows for display. ``recent`` puts the freshest session on top."""
    if mode == "turns":
        return sorted(rows, key=lambda e: (-e.turn_count, e.session_id))
    if mode == "name":
        return sorted(rows, key=lambda e: (e.name or "~", e.session_id))
    if mode == "recent":
        # Session ids are time-ordered (``sess-YYYYMMDD-HHMM``) so a
        # reverse-id sort is the cheapest "freshest first" we get.
        return sorted(rows, key=lambda e: e.session_id, reverse=True)
    return sorted(rows, key=lambda e: e.session_id)


def _matches(entry: _Entry, q: str) -> bool:
    if not q:
        return True
    qlow = q.lower()
    return (
        qlow in entry.session_id.lower()
        or qlow in entry.name.lower()
        or qlow in entry.created_at.lower()
    )


# ── runtime ─────────────────────────────────────────────────────


_TITLE = "Sessions"
_HEADER_FMT = (
    "{n} sessions · Enter to resume, / to search, s to sort, "
    "Esc to cancel"
)
_FOOTER = (
    "Sessions live under <repo>/.lyra/sessions/. "
    "Fork or rename via /fork and /rename."
)
_PAGE = 8


def run_sessions_dialog(
    sessions_root: Path,
) -> Optional[SessionsDialogResult]:
    """Drive the picker; return the chosen session id or None on cancel."""
    entries = build_session_entries(sessions_root)
    if not entries:
        return None

    ui = {
        "filter": "",
        "cursor": 0,
        "sort": _SORT_MODES[0],
        "result": None,
    }

    filter_buffer = Buffer(multiline=False)

    def visible() -> list[_Entry]:
        rows = _sort_entries(entries, ui["sort"])
        return [e for e in rows if _matches(e, ui["filter"])]

    def render_list() -> FormattedText:
        rows = visible()
        if not rows:
            return FormattedText(
                [("class:dim", "  (no matches — try a different filter)\n")]
            )
        cursor = min(max(ui["cursor"], 0), len(rows) - 1)
        ui["cursor"] = cursor

        max_id = max((len(e.session_id) for e in rows), default=20)
        max_name = max((len(e.name) for e in rows), default=0)
        out: list[tuple[str, str]] = []
        for i, e in enumerate(rows):
            is_cursor = i == cursor
            arrow = "❯ " if is_cursor else "  "
            cls_arrow = "class:cursor" if is_cursor else "class:dim"
            cls_id = "class:cursor-row" if is_cursor else "class:name"
            cls_meta = "class:meta-current" if is_cursor else "class:meta"
            pad_id = " " * max(1, max_id - len(e.session_id) + 2)
            name_part = (
                f"{e.name:<{max_name}}" if max_name else ""
            )
            meta = (
                f"{name_part}"
                + (f"  " if name_part else "")
                + f"{e.turn_count} turn"
                + ("" if e.turn_count == 1 else "s")
                + f"  {e.created_at}"
            )
            out.append((cls_arrow, f"  {arrow}"))
            out.append((cls_id, e.session_id))
            out.append((cls_meta, f"{pad_id}{meta}\n"))
        return FormattedText(out)

    def render_filter() -> FormattedText:
        q = ui["filter"]
        sort_hint = f"  sort: {ui['sort']}"
        if not q:
            return FormattedText(
                [
                    ("class:dim", "  filter: (type to narrow)"),
                    ("class:dim", sort_hint),
                ]
            )
        return FormattedText(
            [
                ("class:dim", "  filter: "),
                ("class:filter", q),
                ("class:dim", sort_hint),
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

    @kb.add("s")
    def _(_e: object) -> None:
        if filter_buffer.text:
            filter_buffer.insert_text("s")
            return
        idx = (_SORT_MODES.index(ui["sort"]) + 1) % len(_SORT_MODES)
        ui["sort"] = _SORT_MODES[idx]
        ui["cursor"] = 0

    @kb.add("/")
    def _(_e: object) -> None:
        pass  # filter buffer already focused — consume to avoid duplicate

    @kb.add("enter")
    def _(_e: object) -> None:
        rows = visible()
        if rows:
            ui["result"] = SessionsDialogResult(
                session_id=rows[ui["cursor"]].session_id
            )
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
            "title": f"bold {PALETTE['accent']}",
            "description": PALETTE["meta"],
            "cursor": f"bold {PALETTE['accent']}",
            "cursor-row": f"bold {PALETTE['text_strong']}",
            "name": PALETTE["text"],
            "meta": f"italic {PALETTE['meta']}",
            "meta-current": f"italic {PALETTE['text']}",
            "footer": PALETTE["meta"],
            "filter": f"bold {PALETTE['accent_warm']}",
            "dim": PALETTE["dim"],
        }
    )

    layout = Layout(
        HSplit(
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
                Window(height=1, char=" "),
                Window(
                    FormattedTextControl(FormattedText([("class:footer", _FOOTER)])),
                    height=1,
                ),
            ]
        )
    )
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
