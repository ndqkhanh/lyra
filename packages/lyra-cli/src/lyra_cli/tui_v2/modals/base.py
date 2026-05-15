"""LyraPickerModal — shared filter+list pattern for the three Lyra modals.

Layout (matches OpenCode's stack-modal convention):

    ┌─ title ──────────────────────────────────────────────────┐
    │ filter:                                                  │
    │ ┌────────────────────────┬─────────────────────────────┐ │
    │ │ entry one              │ preview / description       │ │
    │ │ entry two              │                             │ │
    │ │ …                      │                             │ │
    │ └────────────────────────┴─────────────────────────────┘ │
    │ hint line                                                │
    └──────────────────────────────────────────────────────────┘

Subclasses supply:

  * ``title``       — modal header text
  * ``entries()``   — list of ``Entry`` records (pure; no widgets)
  * ``_preview()``  — render the right-pane preview for a selection

The base owns:

  * filter Input on top (live filter via trigram fuzzy match)
  * ListView of matching entries
  * preview Static on the right
  * Esc / q to cancel, Enter to pick, ↑↓ to navigate

The returned value (when the user picks) is the entry's ``key`` string —
each subclass decides what that means semantically (model name, skill
name, mcp server name, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, Static


@dataclass(frozen=True)
class Entry:
    """One row in a picker.

    ``key``         — value returned to the caller on pick
    ``label``       — text shown in the list
    ``description`` — optional second line shown in the preview
    ``meta``        — free-form key/value pairs for preview / filter (e.g.
                      ``{"installed": "yes", "context": "200k"}``)
    """

    key: str
    label: str
    description: str = ""
    meta: dict[str, str] | None = None


class LyraPickerModal(ModalScreen[Optional[str]]):
    """Shared filter+list+preview modal for Lyra-specific pickers."""

    # OpenCode size tier: "medium". Subclasses can override DEFAULT_CSS to
    # bump up to large (88) or xlarge (116) when their content needs it.
    DEFAULT_CSS = """
    LyraPickerModal {
        align: center middle;
    }
    LyraPickerModal > Vertical {
        width: 80;
        height: 24;
        background: $surface;
        border: tall $primary;
        padding: 1 2;
    }
    LyraPickerModal #title {
        height: 1;
        color: $primary;
        text-style: bold;
    }
    LyraPickerModal #filter {
        height: 3;
        margin-bottom: 1;
    }
    LyraPickerModal #cols {
        height: 1fr;
    }
    LyraPickerModal ListView {
        width: 30;
        background: $bg;
    }
    LyraPickerModal #preview {
        width: 1fr;
        background: $bg;
        padding: 0 1;
    }
    LyraPickerModal #hint {
        height: 1;
        color: $fg_muted;
    }
    """

    BINDINGS = [
        Binding("escape,q", "cancel", "Cancel", priority=True),
        Binding("enter", "pick", "Pick", priority=True),
    ]

    # ``title`` is a reactive on Textual's Screen base — use a different
    # attribute name so subclasses can set it without shadowing the base
    # reactive's typing contract.
    picker_title: str = "Pick"

    def __init__(self) -> None:
        super().__init__()
        self._all = list(self.entries())
        self._filtered = list(self._all)
        self._row_keys: list[str] = []  # parallel array to ListView items

    # -- subclass hooks ------------------------------------------------

    def entries(self) -> list[Entry]:  # pragma: no cover — abstract
        raise NotImplementedError

    def _preview(self, key: str) -> str:
        """Render the right-pane preview for the selected entry key."""
        for e in self._all:
            if e.key == key:
                lines = [f"[bold]{e.label}[/]"]
                if e.description:
                    lines.append("")
                    lines.append(e.description)
                if e.meta:
                    lines.append("")
                    for k, v in e.meta.items():
                        lines.append(f"[dim]{k}:[/] {v}")
                return "\n".join(lines)
        return ""

    # -- Composition ---------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.picker_title, id="title")
            yield Input(placeholder="filter…", id="filter")
            with Horizontal(id="cols"):
                yield ListView(*self._items_for(self._filtered), id="list")
                yield Static(self._initial_preview(), id="preview")
            yield Static(
                "[dim]↑↓ to browse · Enter to pick · Esc to cancel[/]",
                id="hint",
            )

    # -- Lifecycle -----------------------------------------------------

    def on_mount(self) -> None:
        self.call_after_refresh(self._set_initial_focus)

    def _set_initial_focus(self) -> None:
        try:
            lv = self.query_one("#list", ListView)
            if self._row_keys:
                lv.index = 0
            self.query_one("#filter", Input).focus()
        except Exception:
            return

    # -- Filter --------------------------------------------------------

    def on_input_changed(self, message: Input.Changed) -> None:
        if message.input.id != "filter":
            return
        self._filtered = _fuzzy_filter(self._all, message.value)
        try:
            lv = self.query_one("#list", ListView)
            lv.clear()
            for item in self._items_for(self._filtered):
                lv.append(item)
            if self._row_keys:
                lv.index = 0
                self._update_preview(self._row_keys[0])
            else:
                self._update_preview("")
        except Exception:
            return

    def on_list_view_highlighted(self, message) -> None:
        # ``message.item`` is the highlighted ListItem; we stored the key
        # as its id (sanitised). The parallel ``_row_keys`` array maps
        # index → key, which is more robust than parsing the id.
        try:
            lv = self.query_one("#list", ListView)
            idx = lv.index or 0
            if 0 <= idx < len(self._row_keys):
                self._update_preview(self._row_keys[idx])
        except Exception:
            return

    # -- Actions -------------------------------------------------------

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_pick(self) -> None:
        try:
            lv = self.query_one("#list", ListView)
            idx = lv.index or 0
            if 0 <= idx < len(self._row_keys):
                self.dismiss(self._row_keys[idx])
                return
        except Exception:
            pass
        self.dismiss(None)

    # -- Helpers -------------------------------------------------------

    def _items_for(self, entries: list[Entry]) -> list[ListItem]:
        self._row_keys = [e.key for e in entries]
        return [
            ListItem(Static(e.label), id=f"row-{i}")
            for i, e in enumerate(entries)
        ]

    def _initial_preview(self) -> str:
        if not self._filtered:
            return "[dim](no entries)[/]"
        return self._preview(self._filtered[0].key)

    def _update_preview(self, key: str) -> None:
        try:
            preview = self.query_one("#preview", Static)
            preview.update(self._preview(key) if key else "[dim](no entries)[/]")
        except Exception:
            return


# ---------------------------------------------------------------------
# Pure helper — fuzzy filter (tested in isolation)
# ---------------------------------------------------------------------


def _fuzzy_filter(entries: list[Entry], query: str) -> list[Entry]:
    """Case-insensitive substring + subsequence match across label/key/desc.

    Empty query returns the input list unchanged. Ordering: exact prefix
    matches first, substring matches next, subsequence matches last.
    """
    q = query.strip().lower()
    if not q:
        return list(entries)

    scored: list[tuple[float, Entry]] = []
    for entry in entries:
        haystack = " ".join(filter(None, [entry.label, entry.key, entry.description])).lower()
        if entry.key.lower().startswith(q) or entry.label.lower().startswith(q):
            scored.append((100.0, entry))
        elif q in haystack:
            scored.append((50.0, entry))
        elif _subsequence(q, haystack):
            scored.append((10.0, entry))
    scored.sort(key=lambda kv: (-kv[0], kv[1].label.lower()))
    return [e for _, e in scored]


def _subsequence(needle: str, haystack: str) -> bool:
    """True iff every char of needle appears in haystack in order."""
    if not needle:
        return True
    it = iter(haystack)
    return all(ch in it for ch in needle)
