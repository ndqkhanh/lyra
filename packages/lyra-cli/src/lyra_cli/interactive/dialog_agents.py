"""Interactive agents picker — Claude-Code-style /agents dialog.

Mirrors :mod:`dialog_skills` shape. Two stacked views toggled by
``Tab``:

* **Catalog** (default) — every :class:`SubagentPreset` lyra knows
  about: built-ins (``explore``, ``general``, ``plan``) plus any
  YAML/JSON file the user dropped into ``~/.lyra/agents``.
* **Live** — currently spawned :class:`SubagentRecord`s from the
  attached :class:`SubagentRegistry` (one row per ``/spawn`` call
  this session).

Enter on a catalog row "picks" the preset (caller decides what to do
with the chosen name — e.g. ``_cmd_agents`` prints the full
definition). Enter on a live row picks the record for inspection.

The picker is non-destructive: it doesn't kill, edit, or spawn —
those actions still go through ``/spawn`` and ``/agents kill <id>``.
The point is *visibility*: get a single overview the way Claude
Code's panel does it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.styles import Style

__all__ = [
    "AgentsDialogResult",
    "build_catalog_entries",
    "build_live_entries",
    "run_agents_dialog",
]


# ── data model ───────────────────────────────────────────────────


@dataclass(frozen=True)
class _CatalogEntry:
    """One catalog row — a preset the user could ``/spawn``."""

    name: str
    description: str
    model: str
    role: str
    tools: tuple[str, ...]
    source: str  # "builtin" | "user" | "user-overrides-builtin"
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class _LiveEntry:
    """One live row — a currently-spawned subagent record."""

    record_id: str
    state: str
    description: str
    subagent_type: str = ""


@dataclass
class AgentsDialogResult:
    """What the picker returns on Enter.

    Exactly one of ``catalog_pick`` / ``live_pick`` is non-None — the
    caller switches on which view the user was in when they hit Enter.
    """

    catalog_pick: Optional[_CatalogEntry] = None
    live_pick: Optional[_LiveEntry] = None


# ── pure helpers (testable without a TTY) ────────────────────────


def build_catalog_entries(
    *,
    user_dir: Path | None = None,
) -> list[_CatalogEntry]:
    """Load presets from ``user_dir`` (or ``~/.lyra/agents``) + built-ins.

    Failures inside :func:`lyra_core.subagent.presets.load_presets`
    surface as the bundle's ``errors`` list — not as exceptions —
    so the picker can render the catalog even when one user file is
    malformed. We swallow any *truly* fatal exception and return an
    empty list rather than crash the picker.
    """
    try:
        from lyra_core.subagent.presets import list_user_dirs, load_presets
    except Exception:
        return []

    if user_dir is not None:
        bundle = load_presets(user_dir=user_dir)
    else:
        # Use the conventional ~/.lyra/agents location. The helper
        # yields lazily; we take the first hit (today there's only one).
        try:
            user_root = next(iter(list_user_dirs()))
        except StopIteration:
            user_root = Path.home() / ".lyra" / "agents"
        bundle = load_presets(user_dir=user_root)

    out: list[_CatalogEntry] = []
    for preset in bundle.presets.values():
        out.append(
            _CatalogEntry(
                name=preset.name,
                description=(preset.description or "").strip().replace("\n", " "),
                model=preset.model or "(default)",
                role=preset.role,
                tools=tuple(preset.tools),
                source=preset.source,
                aliases=tuple(preset.aliases),
            )
        )
    return out


def build_live_entries(registry: Any | None) -> list[_LiveEntry]:
    """Snapshot the registry's current records for the live view.

    Empty list when no registry is attached (the common case until the
    user runs ``/spawn`` for the first time).
    """
    if registry is None:
        return []
    try:
        records = registry.list_all()
    except Exception:
        return []
    out: list[_LiveEntry] = []
    for rec in records:
        out.append(
            _LiveEntry(
                record_id=str(getattr(rec, "id", "")),
                state=str(getattr(rec, "state", "")),
                description=str(getattr(rec, "description", "")),
                subagent_type=str(getattr(rec, "subagent_type", "")),
            )
        )
    return out


_CATALOG_SORTS: tuple[str, ...] = ("name", "model", "source", "role")
_LIVE_SORTS: tuple[str, ...] = ("id", "state", "description")


def _sort_catalog(rows: list[_CatalogEntry], mode: str) -> list[_CatalogEntry]:
    if mode == "model":
        return sorted(rows, key=lambda e: (e.model, e.name))
    if mode == "source":
        return sorted(rows, key=lambda e: (e.source, e.name))
    if mode == "role":
        return sorted(rows, key=lambda e: (e.role, e.name))
    return sorted(rows, key=lambda e: e.name)


def _sort_live(rows: list[_LiveEntry], mode: str) -> list[_LiveEntry]:
    if mode == "state":
        return sorted(rows, key=lambda e: (e.state, e.record_id))
    if mode == "description":
        return sorted(rows, key=lambda e: (e.description, e.record_id))
    return sorted(rows, key=lambda e: e.record_id)


def _matches_catalog(entry: _CatalogEntry, q: str) -> bool:
    if not q:
        return True
    qlow = q.lower()
    return (
        qlow in entry.name.lower()
        or qlow in entry.description.lower()
        or qlow in entry.model.lower()
        or qlow in entry.role.lower()
        or qlow in entry.source.lower()
        or any(qlow in t.lower() for t in entry.tools)
    )


def _matches_live(entry: _LiveEntry, q: str) -> bool:
    if not q:
        return True
    qlow = q.lower()
    return (
        qlow in entry.record_id.lower()
        or qlow in entry.state.lower()
        or qlow in entry.description.lower()
        or qlow in entry.subagent_type.lower()
    )


# ── interactive driver ───────────────────────────────────────────


_TITLE = "Agents"
_HEADER_FMT = (
    "{n} agents · Enter to view, Tab to switch {view}, / to search, "
    "s to sort, Esc to cancel"
)
_FOOTER = (
    "Built-ins: explore · general · plan. Drop YAML/JSON in "
    "~/.lyra/agents/ for custom presets."
)
_PAGE = 8


def run_agents_dialog(
    *,
    registry: Any | None = None,
    user_dir: Path | None = None,
) -> Optional[AgentsDialogResult]:
    """Drive the picker; return the user's pick or None on cancel."""
    catalog = build_catalog_entries(user_dir=user_dir)
    live = build_live_entries(registry)

    if not catalog and not live:
        return None

    # Pick the initial view: live if it has rows (the user just
    # spawned something — they probably want to see live first),
    # otherwise catalog.
    initial_view = "live" if live else "catalog"

    ui = {
        "view": initial_view,
        "filter": "",
        "cursor": 0,
        "sort_catalog": _CATALOG_SORTS[0],
        "sort_live": _LIVE_SORTS[0],
        "result": None,
    }

    filter_buffer = Buffer(multiline=False)

    def visible_catalog() -> list[_CatalogEntry]:
        rows = _sort_catalog(catalog, ui["sort_catalog"])
        return [e for e in rows if _matches_catalog(e, ui["filter"])]

    def visible_live() -> list[_LiveEntry]:
        rows = _sort_live(live, ui["sort_live"])
        return [e for e in rows if _matches_live(e, ui["filter"])]

    def visible_count() -> int:
        return (
            len(visible_catalog())
            if ui["view"] == "catalog"
            else len(visible_live())
        )

    def render_catalog_rows(
        rows: list[_CatalogEntry], cursor: int
    ) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        max_name = max((len(e.name) for e in rows), default=10)
        for i, e in enumerate(rows):
            is_cursor = i == cursor
            arrow = "❯ " if is_cursor else "  "
            source_glyph = (
                "🔒"
                if e.source == "builtin"
                else "✎"
                if e.source == "user-overrides-builtin"
                else " "
            )
            cls_arrow = "class:cursor" if is_cursor else "class:dim"
            cls_name = "class:cursor-row" if is_cursor else "class:name"
            cls_meta = "class:meta-current" if is_cursor else "class:meta"
            pad = " " * max(1, max_name - len(e.name) + 2)
            tools_label = (
                f"{len(e.tools)} tool"
                if len(e.tools) == 1
                else f"{len(e.tools)} tools"
            )
            meta = (
                f"· {e.model:<8} · {e.role:<13} · {tools_label:<8} "
                f"· {e.source}"
            )
            out.append((cls_arrow, f"  {arrow}"))
            out.append(("class:lock", f"{source_glyph} "))
            out.append((cls_name, e.name))
            out.append((cls_meta, f"{pad}{meta}\n"))
            if e.description:
                desc = e.description
                if len(desc) > 90:
                    desc = desc[:89] + "…"
                out.append(("class:dim", f"      {desc}\n"))
        return out

    def render_live_rows(
        rows: list[_LiveEntry], cursor: int
    ) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        max_id = max((len(e.record_id) for e in rows), default=8)
        for i, e in enumerate(rows):
            is_cursor = i == cursor
            arrow = "❯ " if is_cursor else "  "
            state_glyph = {
                "running": "▶",
                "pending": "·",
                "done": "✓",
                "completed": "✓",
                "cancelled": "✗",
                "failed": "✗",
                "error": "✗",
            }.get(e.state.lower(), "?")
            cls_arrow = "class:cursor" if is_cursor else "class:dim"
            cls_name = "class:cursor-row" if is_cursor else "class:name"
            cls_meta = "class:meta-current" if is_cursor else "class:meta"
            pad = " " * max(1, max_id - len(e.record_id) + 2)
            meta = f"· {e.state:<10}"
            if e.subagent_type:
                meta += f" · {e.subagent_type}"
            out.append((cls_arrow, f"  {arrow}"))
            out.append(("class:lock", f"{state_glyph} "))
            out.append((cls_name, e.record_id))
            out.append((cls_meta, f"{pad}{meta}\n"))
            if e.description:
                desc = e.description
                if len(desc) > 90:
                    desc = desc[:89] + "…"
                out.append(("class:dim", f"      {desc}\n"))
        return out

    def render_list() -> FormattedText:
        if ui["view"] == "catalog":
            cat_rows = visible_catalog()
            if not cat_rows:
                return FormattedText(
                    [("class:dim", "  (no matches — try a different filter)\n")]
                )
            cursor = min(max(ui["cursor"], 0), len(cat_rows) - 1)
            ui["cursor"] = cursor
            return FormattedText(render_catalog_rows(cat_rows, cursor))
        live_rows = visible_live()
        if not live_rows:
            return FormattedText(
                [("class:dim", "  (no live subagents — /spawn one first)\n")]
            )
        cursor = min(max(ui["cursor"], 0), len(live_rows) - 1)
        ui["cursor"] = cursor
        return FormattedText(render_live_rows(live_rows, cursor))

    def render_filter() -> FormattedText:
        q = ui["filter"]
        sort_label = (
            ui["sort_catalog"] if ui["view"] == "catalog" else ui["sort_live"]
        )
        view_hint = f"  view: {ui['view']}  sort: {sort_label}"
        if not q:
            return FormattedText(
                [
                    ("class:dim", "  filter: (type to narrow)"),
                    ("class:dim", view_hint),
                ]
            )
        return FormattedText(
            [
                ("class:dim", "  filter: "),
                ("class:filter", q),
                ("class:dim", view_hint),
            ]
        )

    def on_filter_change(_: Buffer) -> None:
        ui["filter"] = filter_buffer.text
        ui["cursor"] = 0
        app.invalidate()

    filter_buffer.on_text_changed += on_filter_change

    kb = KeyBindings()

    def _move(delta: int) -> None:
        n = visible_count()
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
        ui["cursor"] = max(0, visible_count() - 1)

    @kb.add("tab")
    def _(_e: object) -> None:
        # Toggle catalog ↔ live (only meaningful when both have rows;
        # if one is empty we still allow the toggle so the user sees
        # the empty-state hint instead of getting stuck).
        ui["view"] = "live" if ui["view"] == "catalog" else "catalog"
        ui["cursor"] = 0

    @kb.add("s")
    def _(_e: object) -> None:
        if filter_buffer.text:
            filter_buffer.insert_text("s")
            return
        if ui["view"] == "catalog":
            idx = (_CATALOG_SORTS.index(ui["sort_catalog"]) + 1) % len(
                _CATALOG_SORTS
            )
            ui["sort_catalog"] = _CATALOG_SORTS[idx]
        else:
            idx = (_LIVE_SORTS.index(ui["sort_live"]) + 1) % len(_LIVE_SORTS)
            ui["sort_live"] = _LIVE_SORTS[idx]
        ui["cursor"] = 0

    @kb.add("/")
    def _(_e: object) -> None:
        # Focus is already on the filter buffer; consume the slash so
        # it isn't inserted as text.
        pass

    @kb.add("enter")
    def _(_e: object) -> None:
        if ui["view"] == "catalog":
            rows = visible_catalog()
            if rows:
                ui["result"] = AgentsDialogResult(
                    catalog_pick=rows[ui["cursor"]]
                )
        else:
            rows = visible_live()
            if rows:
                ui["result"] = AgentsDialogResult(
                    live_pick=rows[ui["cursor"]]
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
            "title": "bold #5fafff",
            "description": "#888888",
            "cursor": "bold #5fafff",
            "cursor-row": "bold #ffffff",
            "name": "#cccccc",
            "lock": "bold #ffaf00",
            "meta": "italic #666666",
            "meta-current": "italic #aaaaaa",
            "footer": "#888888",
            "filter": "bold #ffaf00",
            "dim": "#555555",
        }
    )

    total = len(catalog) + len(live)
    other_view = "live" if initial_view == "catalog" else "catalog"

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
                                    _HEADER_FMT.format(
                                        n=total, view=f"to {other_view}"
                                    ),
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
