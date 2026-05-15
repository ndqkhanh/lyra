"""Interactive skills picker — Claude-Code-style /skills dialog.

Mirrors :mod:`dialog_model` shape (full-screen ``Application`` driven
by ``KeyBindings``, type-to-filter, arrow navigation) but renders the
skills lineup with per-row enable/disable cycling:

    Skills
    %d skills · Space to cycle, Enter to save, / to search,
    t to sort, Esc to cancel

      🔒 on   surgical-changes        · packaged · ~120 tok
        on   tdd-sprint               · packaged · ~340 tok
        off  ad-hoc-debugging         · user     · ~80 tok
    ❯   on   project:surgical-tweak   · project  · ~95 tok

The picker is launched by ``/skills`` (no args) when stdin is a TTY,
and by the ``Alt+K`` chord. It returns a :class:`SkillsDialogResult`
on Enter or ``None`` on Esc; ``_cmd_skills`` persists the result.

Locked skills (under the packaged-pack root) show a 🔒 prefix and
ignore Space — they can only be removed via ``lyra skill remove``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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

from lyra_skills.state import SkillsState, with_toggled

__all__ = ["SkillsDialogResult", "build_entries", "run_skills_dialog"]


# ── data model ───────────────────────────────────────────────────


@dataclass(frozen=True)
class _Entry:
    """One row in the picker.

    ``locked`` is read from the manifest's on-disk path (set via
    :func:`lyra_cli.interactive.skills_inject.is_locked_skill`). The
    picker uses ``source`` ∈ {``packaged``, ``user``, ``project``}
    only for display — locking is the actual lever.
    """

    skill_id: str
    description: str
    source: str
    tokens: int
    locked: bool
    utility: float = 0.0


@dataclass
class SkillsDialogResult:
    """What the picker returns on Enter.

    ``new_state`` is the full :class:`SkillsState` to persist;
    ``changed_ids`` is a sorted list of skill ids whose active flag
    flipped (handy for the post-save status line).
    """

    new_state: SkillsState
    changed_ids: list[str] = field(default_factory=list)


# ── pure helpers (testable without a TTY) ────────────────────────


def _classify_source(skill_path: str, packaged_root: Optional[Path]) -> str:
    """Tag a skill's discovery root for the meta column."""
    try:
        sp = Path(skill_path).resolve()
    except (OSError, RuntimeError):
        return "unknown"
    if packaged_root is not None:
        try:
            sp.relative_to(Path(packaged_root).resolve())
            return "packaged"
        except ValueError:
            pass
    parts = sp.parts
    if ".lyra" in parts:
        # Distinguish project (.lyra under repo) vs user (under ~/.lyra)
        idx = parts.index(".lyra")
        if idx > 0 and parts[idx - 1] == ".lyra":
            return "project"
        # user-global lives at <home>/.lyra/skills/...
        if any(p.startswith(".") and p == ".lyra" for p in parts[:idx + 1]):
            home = str(Path.home())
            return "user" if str(sp).startswith(home) else "project"
    return "unknown"


def _approx_tokens(body: str) -> int:
    """Cheap token estimate — body length // 4 with a 1-tok floor.

    Avoids a hard ``tiktoken`` dependency; the picker only uses this
    for a UI hint, not for billing.
    """
    if not body:
        return 0
    return max(1, len(body) // 4)


def build_entries(
    repo_root: Path,
    *,
    state: SkillsState,
    utility_resolver=None,
) -> list[_Entry]:
    """Walk the discovery roots and build picker rows.

    Mirrors :func:`render_skill_block`'s discovery + load step so the
    picker shows exactly what the inject layer would render. Failures
    in any single skill are swallowed — one bad ``SKILL.md`` should
    not block the picker.
    """
    from .skills_inject import (
        _load_skills_safely,
        _packaged_pack_root,
        discover_skill_roots,
        is_locked_skill,
    )

    roots = discover_skill_roots(repo_root)
    skills = _load_skills_safely(roots)
    packaged_root = _packaged_pack_root()

    entries: list[_Entry] = []
    for s in skills:
        sid = getattr(s, "id", "") or ""
        if not sid:
            continue
        path = getattr(s, "path", "") or ""
        body = getattr(s, "body", "") or ""
        desc = (getattr(s, "description", "") or "").strip().replace("\n", " ")
        utility = 0.0
        if utility_resolver is not None:
            try:
                utility = float(utility_resolver(sid))
            except Exception:
                utility = 0.0
        entries.append(
            _Entry(
                skill_id=sid,
                description=desc,
                source=_classify_source(path, packaged_root),
                tokens=_approx_tokens(body),
                locked=is_locked_skill(s, packaged_root),
                utility=utility,
            )
        )
    return entries


_SORT_MODES: tuple[str, ...] = ("name", "tokens", "source", "utility")


def _sort_entries(entries: list[_Entry], mode: str) -> list[_Entry]:
    if mode == "tokens":
        return sorted(entries, key=lambda e: (-e.tokens, e.skill_id))
    if mode == "source":
        return sorted(entries, key=lambda e: (e.source, e.skill_id))
    if mode == "utility":
        return sorted(entries, key=lambda e: (-e.utility, e.skill_id))
    return sorted(entries, key=lambda e: e.skill_id)


def _matches(entry: _Entry, q: str) -> bool:
    if not q:
        return True
    qlow = q.lower()
    return (
        qlow in entry.skill_id.lower()
        or qlow in entry.description.lower()
        or qlow in entry.source.lower()
    )


# ── interactive driver ───────────────────────────────────────────


_TITLE = "Skills"
_HEADER_FMT = (
    "{n} skills · Space to cycle, Enter to save, / to search, "
    "t to sort, Esc to cancel"
)
_FOOTER = (
    "Locked skills are bundled with Lyra and managed via "
    "`lyra skill add/remove`."
)
_PAGE = 8


def run_skills_dialog(
    repo_root: Path,
    *,
    state: SkillsState,
    utility_resolver=None,
) -> Optional[SkillsDialogResult]:
    """Drive the picker; return changes on Enter or None on Esc.

    The dialog mutates a *working* :class:`SkillsState` in memory and
    only commits it (returns) when the user hits Enter — Esc drops
    pending changes.
    """
    entries = build_entries(repo_root, state=state, utility_resolver=utility_resolver)
    if not entries:
        return SkillsDialogResult(new_state=state, changed_ids=[])

    initial_state = state
    ui = {
        "filter": "",
        "cursor": 0,
        "sort": _SORT_MODES[0],
        "state": state,
        "result": None,
    }

    filter_buffer = Buffer(multiline=False)

    def _is_active(entry: _Entry) -> bool:
        if entry.locked:
            return True
        return entry.skill_id not in ui["state"].disabled

    def visible() -> list[_Entry]:
        sorted_entries = _sort_entries(entries, ui["sort"])
        return [e for e in sorted_entries if _matches(e, ui["filter"])]

    def render_list() -> FormattedText:
        rows = visible()
        if not rows:
            return FormattedText(
                [("class:dim", "  (no matches — try a different filter)\n")]
            )

        cursor = min(max(ui["cursor"], 0), len(rows) - 1)
        ui["cursor"] = cursor

        out: list[tuple[str, str]] = []
        max_id = max((len(e.skill_id) for e in rows), default=20)
        for i, e in enumerate(rows):
            is_cursor = i == cursor
            active = _is_active(e)
            arrow = "❯ " if is_cursor else "  "
            lock = "🔒 " if e.locked else "   "
            status = "on " if active else "off"
            cls_arrow = "class:cursor" if is_cursor else "class:dim"
            cls_status = (
                "class:on-active"
                if active
                else "class:off-active"
            ) if is_cursor else ("class:on" if active else "class:off")
            cls_id = "class:cursor-row" if is_cursor else "class:name"
            cls_meta = "class:meta-current" if is_cursor else "class:meta"
            cls_lock = "class:lock"
            pad = " " * max(1, max_id - len(e.skill_id) + 2)
            tokens = f"~{e.tokens} tok"
            meta = f"· {e.source:<8} · {tokens}"
            if e.locked:
                meta += " · locked by plugin"
            out.append((cls_arrow, f"  {arrow}"))
            out.append((cls_lock, lock))
            out.append((cls_status, f"{status} "))
            out.append((cls_id, f" {e.skill_id}"))
            out.append((cls_meta, f"{pad}{meta}\n"))
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

    @kb.add("space")
    def _(_e: object) -> None:
        rows = visible()
        if not rows:
            return
        target = rows[ui["cursor"]]
        if target.locked:
            return  # silent no-op; a beep would be a UX downgrade
        ui["state"] = with_toggled(
            ui["state"],
            target.skill_id,
            currently_active=_is_active(target),
        )

    @kb.add("t")
    def _(_e: object) -> None:
        if filter_buffer.text:
            # If the user is typing a filter, "t" is a literal letter,
            # not the sort cycle. Insert it into the buffer instead.
            filter_buffer.insert_text("t")
            return
        idx = (_SORT_MODES.index(ui["sort"]) + 1) % len(_SORT_MODES)
        ui["sort"] = _SORT_MODES[idx]
        ui["cursor"] = 0

    @kb.add("/")
    def _(_e: object) -> None:
        # Same convention as Claude Code — slash focuses the filter box.
        # The buffer already has focus, so this is a no-op aside from
        # making the slash key idempotent rather than treated as text.
        pass

    @kb.add("enter")
    def _(_e: object) -> None:
        new_state: SkillsState = ui["state"]
        # diff vs initial state to report what flipped
        before = initial_state.disabled
        after = new_state.disabled
        changed = sorted((before ^ after))
        ui["result"] = SkillsDialogResult(
            new_state=new_state,
            changed_ids=changed,
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
            "on": "bold #5fff87",
            "on-active": "bold #5fff87",
            "off": "#666666",
            "off-active": "italic #aaaaaa",
            "meta": "italic #666666",
            "meta-current": "italic #aaaaaa",
            "footer": "#888888",
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
            Window(height=1, char=" "),
            Window(
                FormattedTextControl(FormattedText([("class:footer", _FOOTER)])),
                height=1,
            ),
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
