"""Interactive model picker — Claude-Code-style /model dialog.

Runs as a self-contained ``prompt_toolkit.Application`` after the
parent ``PromptSession.prompt()`` returns, so there's no nested-app
conflict. Bound to ``/model`` with no arguments; the args-form
(``/model <slug>``, ``/model fast=...``, ``/model smart=...``) keeps
its existing handler in :mod:`session`.

UX matches Claude Code's panel:

    Select model
    Switch between models. Applies to this session and future Lyra
    sessions. For models not listed below, type /model <slug>.

      RECOMMENDED
        1. Default (auto)              Auto-pick best configured backend
    ❯   2. Opus 4.7                    Most capable for complex work · $5/$25
        3. Sonnet 4.6 ✔                Best for everyday tasks · $3/$15
        4. Haiku 4.5                   Fastest for quick answers · $1/$5

      OPENAI
        5. GPT-5.5 Pro                 OpenAI flagship · $30/$180
        6. GPT-5.5                     OpenAI default · $5/$30
        ...

    filter: <typed text shrinks/expands matches across all 126 slugs>
    Enter to confirm · Esc to cancel · type to filter

Pricing strings are sourced from public docs as of May 2026; they're
display-only and don't drive routing or billing.
"""
from __future__ import annotations

import os
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

__all__ = ["run_model_dialog"]


@dataclass(frozen=True)
class _Entry:
    slug: str        # canonical slug to set on session.model (or "" for "auto")
    name: str        # display name
    meta: str        # right-column description / pricing


@dataclass(frozen=True)
class _Group:
    label: str
    entries: tuple[_Entry, ...]


# Curated lineup, May 2026. Pricing is per-million tokens (input/output).
# Sources: anthropic.com, openai.com, ai.google.dev, deepseek.com, x.ai.
_GROUPS: tuple[_Group, ...] = (
    _Group(
        "RECOMMENDED",
        (
            _Entry("", "Default (auto)", "Auto-pick best configured backend"),
            _Entry("claude-opus-4.7", "Opus 4.7", "Most capable for complex work · $5/$25"),
            _Entry("claude-sonnet-4.6", "Sonnet 4.6", "Best for everyday tasks · $3/$15"),
            _Entry("claude-haiku-4.5", "Haiku 4.5", "Fastest for quick answers · $1/$5"),
        ),
    ),
    _Group(
        "ANTHROPIC",
        (
            _Entry("claude-opus-4.6", "Opus 4.6", "Prior flagship · $5/$25"),
            _Entry("claude-opus-4.5", "Opus 4.5", "Mature flagship · $5/$25"),
            _Entry("claude-sonnet-4.5", "Sonnet 4.5", "Prior workhorse · $3/$15"),
            _Entry("claude-3.7-sonnet", "Sonnet 3.7", "Legacy"),
        ),
    ),
    _Group(
        "OPENAI",
        (
            _Entry("gpt-5.5-pro", "GPT-5.5 Pro", "Smartest reasoning · $30/$180"),
            _Entry("gpt-5.5", "GPT-5.5", "Default · $5/$30"),
            _Entry("gpt-5.5-thinking", "GPT-5.5 Thinking", "Extended reasoning"),
            _Entry("gpt-5.5-instant", "GPT-5.5 Instant", "Fastest tier"),
            _Entry("gpt-5", "GPT-5", "Prior flagship"),
            _Entry("o3-pro", "o3-pro", "Deep reasoning"),
            _Entry("o3", "o3", "Reasoning model"),
        ),
    ),
    _Group(
        "GOOGLE",
        (
            _Entry("gemini-3.1-pro", "Gemini 3.1 Pro", "Reasoning-first, 1M ctx"),
            _Entry("gemini-3.1-flash", "Gemini 3.1 Flash", "Fast multimodal"),
            _Entry("gemini-3.1-flash-lite", "Gemini 3.1 Flash-Lite", "Cheapest, high-throughput"),
            _Entry("gemini-2.5-pro", "Gemini 2.5 Pro", "Prior flagship"),
            _Entry("gemini-2.5-deep-think", "Gemini 2.5 Deep Think", "Extended reasoning"),
        ),
    ),
    _Group(
        "OPEN-WEIGHTS",
        (
            _Entry("deepseek-reasoner", "DeepSeek Reasoner", "R1-style reasoning · $0.55/$2.19"),
            _Entry("deepseek-chat", "DeepSeek Chat", "General-purpose · $0.27/$1.10"),
            _Entry("qwen3-coder", "Qwen3 Coder", "Code-specialised"),
            _Entry("qwen3-max", "Qwen3 Max", "Alibaba flagship"),
            _Entry("grok-4", "Grok 4", "xAI flagship"),
            _Entry("grok-4-fast", "Grok 4 Fast", "xAI fast tier"),
            _Entry("kimi-k2.5", "Kimi K2.5", "Moonshot flagship"),
        ),
    ),
)

_TITLE = "Select model"
_DESCRIPTION = (
    "Switch between models. Applies to this session and future Lyra sessions. "
    "Type /model <slug> for any other model."
)
_FOOTER = "Enter to confirm · Esc to cancel · type to filter all 126 slugs"
_PAGE = 8

# Effort slider — mirrors effort.py's _LEVELS and blurbs but kept local
# so dialog_model.py stays importable without pulling in effort.py.
_EFFORT_LEVELS: tuple[str, ...] = ("low", "medium", "high", "xhigh", "max")
_EFFORT_LABELS: dict[str, str] = {
    "low":   "Low effort",
    "medium": "Medium effort",
    "high":  "High effort",
    "xhigh": "Very high effort",
    "max":   "Maximum effort",
}


def _flatten() -> list[_Entry]:
    out: list[_Entry] = []
    for g in _GROUPS:
        out.extend(g.entries)
    return out


def _all_slugs() -> list[_Entry]:
    """Build ``_Entry`` records for every slug in the registry not already
    surfaced in ``_GROUPS``. Used as the long-tail when the user filters.
    """
    surfaced = {e.slug for g in _GROUPS for e in g.entries if e.slug}
    try:
        from lyra_core.providers.aliases import DEFAULT_ALIASES

        slugs = DEFAULT_ALIASES.canonical_slugs()
    except Exception:
        slugs = []
    return [_Entry(s, s, "") for s in slugs if s not in surfaced]


def _matches(entry: _Entry, q: str) -> bool:
    if not q:
        return True
    qlow = q.lower()
    return qlow in entry.slug.lower() or qlow in entry.name.lower()


def run_model_dialog(
    current: Optional[str],
    effort: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Drive the model picker; return ``(slug, effort)`` or ``(None, None)`` on cancel.

    ``slug`` is ``""`` when the user picks ``Default (auto)``; callers should
    treat that as "use the default cascade".  ``effort`` is one of the five
    canonical levels (``low`` / ``medium`` / ``high`` / ``xhigh`` / ``max``)
    or ``None`` when the caller should leave the current effort unchanged.

    The effort slider is shown at the bottom of the dialog and responds to
    ``←``/``→`` **only when the filter buffer is empty** so that typing a
    filter query never accidentally shifts the effort level.
    """
    long_tail = _all_slugs()

    # Resolve initial effort: explicit arg → env var → "medium".
    _init_effort = effort or os.environ.get("HARNESS_REASONING_EFFORT", "") or "medium"
    if _init_effort not in _EFFORT_LEVELS:
        _init_effort = "medium"

    state: dict = {
        "filter": "",
        "cursor": 0,
        "result": None,
        "effort_idx": _EFFORT_LEVELS.index(_init_effort),
        "effort_result": None,
    }

    filter_buffer = Buffer(multiline=False)

    def visible_groups() -> list[tuple[Optional[str], list[_Entry]]]:
        """Yield (group_label, entries) pairs honoring the current filter.

        With no filter we show curated groups verbatim. With a filter we
        flatten + search across curated + long-tail and present a single
        "MATCHES" group so cursor math stays simple.
        """
        q = state["filter"]
        if not q:
            return [(g.label, list(g.entries)) for g in _GROUPS]
        all_entries = _flatten() + long_tail
        matches = [e for e in all_entries if _matches(e, q)]
        return [("MATCHES", matches)] if matches else [("NO MATCHES", [])]

    def visible_flat() -> list[_Entry]:
        return [e for _, entries in visible_groups() for e in entries]

    def render_list() -> FormattedText:
        groups = visible_groups()
        flat = [e for _, entries in groups for e in entries]
        if not flat:
            return FormattedText([("class:dim", "  (no matches — try a different filter)\n")])

        cursor = min(max(state["cursor"], 0), len(flat) - 1)
        state["cursor"] = cursor

        rows: list[tuple[str, str]] = []
        idx = 0
        max_name = max((len(e.name) for e in flat), default=20)
        for label, entries in groups:
            if not entries:
                continue
            rows.append(("class:group", f"  {label}\n"))
            for e in entries:
                is_cursor = idx == cursor
                is_current = (current is not None) and (e.slug == current or (e.slug == "" and current in (None, "auto", "")))
                arrow = "❯ " if is_cursor else "  "
                check = " ✔" if is_current else "  "
                cls_arrow = "class:cursor" if is_cursor else "class:dim"
                cls_name = "class:current" if is_current else (
                    "class:cursor-row" if is_cursor else "class:name"
                )
                cls_meta = "class:meta-current" if is_cursor else "class:meta"
                num = f"{idx + 1:>2}."
                pad = " " * max(1, max_name - len(e.name) + 2)
                rows.append((cls_arrow, f"  {arrow}"))
                rows.append((cls_name, f"{num} {e.name}"))
                rows.append(("class:check", check))
                rows.append((cls_meta, f"{pad}{e.meta}\n"))
                idx += 1
            rows.append(("", "\n"))
        return FormattedText(rows)

    def render_filter() -> FormattedText:
        q = state["filter"]
        if not q:
            return FormattedText([("class:dim", "  filter: (type to narrow)")])
        return FormattedText([("class:dim", "  filter: "), ("class:filter", q)])

    def render_effort_row() -> FormattedText:
        """Render the inline effort slider row.

        Example:  ● High effort   ←/→ to adjust
        When filter is non-empty, dims the row with a note that ←/→ is inactive.
        """
        idx = state["effort_idx"]
        level = _EFFORT_LEVELS[idx]
        label = _EFFORT_LABELS[level]
        is_default = level == "medium"
        suffix = " (default)" if is_default else ""
        hint = "←/→ to adjust" if not state["filter"] else "←/→ adjusts effort (clear filter first)"
        return FormattedText([
            ("class:effort-dot", "  ● "),
            ("class:effort-label", f"{label}{suffix}"),
            ("class:effort-hint", f"   {hint}"),
        ])

    def on_filter_change(_: Buffer) -> None:
        state["filter"] = filter_buffer.text
        state["cursor"] = 0
        app.invalidate()

    filter_buffer.on_text_changed += on_filter_change

    kb = KeyBindings()

    def _move(delta: int) -> None:
        n = len(visible_flat())
        if n == 0:
            return
        state["cursor"] = (state["cursor"] + delta) % n

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
        state["cursor"] = 0

    @kb.add("end")
    def _(_e: object) -> None:
        n = len(visible_flat())
        state["cursor"] = max(0, n - 1)

    @kb.add("left")
    def _(_e: object) -> None:
        # Only shift effort when the filter buffer is empty; otherwise the
        # left-arrow is just cursor movement inside the filter text.
        if not state["filter"]:
            state["effort_idx"] = max(0, state["effort_idx"] - 1)

    @kb.add("right")
    def _(_e: object) -> None:
        if not state["filter"]:
            state["effort_idx"] = min(len(_EFFORT_LEVELS) - 1, state["effort_idx"] + 1)

    @kb.add("enter")
    def _(_e: object) -> None:
        flat = visible_flat()
        if flat:
            picked = flat[state["cursor"]]
            state["result"] = picked.slug or "auto"
        state["effort_result"] = _EFFORT_LEVELS[state["effort_idx"]]
        app.exit()

    @kb.add("escape", eager=True)
    def _(_e: object) -> None:
        if state["filter"]:
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
            "group": "bold #ffaf00",
            "cursor": "bold #5fafff",
            "cursor-row": "bold #ffffff",
            "name": "#cccccc",
            "current": "bold #5fff87",
            "check": "bold #5fff87",
            "meta": "italic #666666",
            "meta-current": "italic #aaaaaa",
            "footer": "#888888",
            "filter": "bold #ffaf00",
            "dim": "#555555",
            # Effort slider row
            "effort-dot": "bold #5fafff",
            "effort-label": "bold #ffffff",
            "effort-hint": "#555555",
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
                                ("class:description", _DESCRIPTION),
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
                Window(FormattedTextControl(render_effort_row), height=1),
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
    return state["result"], state["effort_result"]
