"""Model Picker Modal — ECC-inspired model selection dialog for the TUI.

Ports dialog_model.py's 411-line prompt_toolkit model picker into a
Textual modal screen, showing the same curated model catalog with
pricing, provider grouping, and quick-search.

Access: /model in the REPL, or Alt+M in the TUI.
"""
from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

# ── Curated model catalog (from dialog_model.py _GROUPS) ──────────────

MODEL_GROUPS: list[tuple[str, list[tuple[str, str, str]]]] = [
    ("RECOMMENDED", [
        ("", "Default (auto)", "Auto-pick best configured backend"),
        ("claude-opus-4.7", "Opus 4.7", "Most capable · $5/$25"),
        ("claude-sonnet-4.6", "Sonnet 4.6", "Everyday tasks · $3/$15"),
        ("claude-haiku-4.5", "Haiku 4.5", "Fastest · $1/$5"),
    ]),
    ("ANTHROPIC", [
        ("claude-opus-4.6", "Opus 4.6", "Prior flagship · $5/$25"),
        ("claude-sonnet-4.5", "Sonnet 4.5", "Prior workhorse · $3/$15"),
        ("claude-3.7-sonnet", "Sonnet 3.7", "Legacy"),
    ]),
    ("OPENAI", [
        ("gpt-5.5-pro", "GPT-5.5 Pro", "Smartest reasoning · $30/$180"),
        ("gpt-5.5", "GPT-5.5", "Default · $5/$30"),
        ("gpt-5.5-thinking", "GPT-5.5 Thinking", "Extended reasoning"),
        ("gpt-5.5-instant", "GPT-5.5 Instant", "Fastest tier"),
        ("o3-pro", "o3-pro", "Deep reasoning"),
    ]),
    ("GOOGLE", [
        ("gemini-3.1-pro", "Gemini 3.1 Pro", "Reasoning-first, 1M ctx"),
        ("gemini-3.1-flash", "Gemini 3.1 Flash", "Fast multimodal"),
    ]),
    ("DEEPSEEK", [
        ("deepseek-chat", "DeepSeek Chat", "Best value · $8/$24"),
        ("deepseek-reasoner", "DeepSeek Reasoner", "Chain-of-thought · $16/$80"),
    ]),
    ("XAI", [
        ("grok-5", "Grok 5", "Real-time aware"),
        ("grok-5-thinking", "Grok 5 Thinking", "Extended reasoning"),
    ]),
    ("ALL OTHER", [
        ("qwen-max", "Qwen Max", "Strong open-weight"),
        ("mistral-large-3", "Mistral Large 3", "Multilingual"),
        ("command-r7b", "Cohere Command R7B", "RAG-optimized"),
        ("cerebras", "Cerebras", "Fastest inference"),
        ("together", "Together AI", "Router"),
    ]),
]

MODEL_FLAT: list[tuple[str, str, str, str]] = [
    (slug, name, group, desc)
    for group, models in MODEL_GROUPS
    for slug, name, desc in models
]


class ModelPickerModal(ModalScreen[str]):
    """Browse and select an LLM model from the curated catalog."""

    DEFAULT_CSS = """
    ModelPickerModal {
        align: center middle;
    }
    ModelPickerModal > Vertical {
        width: 66;
        height: 80%;
        min-height: 20;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    ModelPickerModal #mp-search {
        dock: top;
        margin: 0 0 1 0;
    }
    ModelPickerModal #mp-list {
        height: 1fr;
        border: solid $border;
    }
    ModelPickerModal #mp-list ListItem {
        padding: 0 1;
        height: 2;
    }
    ModelPickerModal #mp-list ListItem:hover { background: $accent 20%; }
    ModelPickerModal #mp-footer {
        dock: bottom;
        height: 2;
        content-align: center middle;
        color: $text-muted;
    }
    ModelPickerModal .group-header {
        text-style: bold;
        color: $accent;
        background: $surface 50%;
    }
    ModelPickerModal .pricing { color: $text-muted; }
    """

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Cancel"),
        Binding("enter", "select_model", "Select"),
        Binding("/", "focus_search", "Search"),
    ]

    def __init__(self, current: str = ""):
        super().__init__()
        self._current = current
        self._filtered: list[tuple[str, str, str, str]] = list(MODEL_FLAT)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Model Picker[/]  browse the catalog")
            yield Input(placeholder="Search models… (or / to focus)", id="mp-search")
            yield ListView(id="mp-list")
            yield Label("enter=select · /=search · esc=cancel", id="mp-footer")

    def on_mount(self) -> None:
        self._rebuild()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "mp-search":
            q = event.value.lower().strip()
            if not q:
                self._filtered = list(MODEL_FLAT)
            else:
                self._filtered = [
                    m for m in MODEL_FLAT
                    if q in m[0].lower() or q in m[1].lower()
                ]
            self._rebuild()

    def on_list_view_selected(self, _) -> None:
        self.action_select_model()

    def action_select_model(self) -> None:
        lv = self.query_one("#mp-list", ListView)
        if lv.index is not None and 0 <= lv.index < len(self._filtered):
            self.dismiss(self._filtered[lv.index][0])

    def action_focus_search(self) -> None:
        self.query_one("#mp-search", Input).focus()

    def _rebuild(self) -> None:
        lv = self.query_one("#mp-list", ListView)
        lv.clear()
        prev_group = ""
        for slug, name, group, desc in self._filtered:
            # Group header
            if group != prev_group:
                lv.append(ListItem(Static(
                    f"  [accent]{group}[/]", classes="group-header"
                )))
                prev_group = group
            # Model entry
            marker = "[green]●[/]" if slug == self._current else " "
            lv.append(ListItem(Static(
                f"  {marker} [bold]{name}[/]  [dim]{desc}[/]"
            )))
