"""Lyra brand identity for the harness-tui shell.

The logo is a stylised Lyra constellation — Vega (α Lyr, the brightest
star and the apex of the Summer Triangle) is highlighted in primary
gold, with the harp's four-star parallelogram (β, γ, δ, ζ) rendered in
the accent purple. The palette extends Catppuccin Mocha with Lyra's
gold + purple brand tokens; everything else (diff, syntax, semantics)
inherits cleanly so the chat / tool-card / modal surfaces stay
recognisable across all harness-engineering projects.
"""
from __future__ import annotations

from harness_tui.theme import Theme
from harness_tui.themes import catppuccin_mocha

# Brand palette — pulled from Lyra's existing identity (gold + purple).
PRIMARY = "#FACC15"      # Vega gold
PRIMARY_ALT = "#A16207"  # burnished gold for hover / muted brand
ACCENT = "#C084FC"       # plum accent for highlights, links, focus

# Wider ASCII banner. Stars are placed at the canonical positions of the
# Lyra constellation: Vega top-centre, then the rhombus (Sheliak β, Sulafat γ,
# δ Lyr, ζ Lyr). Rich markup colours map to the brand theme.
LYRA_LOGO = (
    "[bold #FACC15]            ✦  Vega[/]\n"
    "[bold #FACC15]            ★[/]\n"
    "[dim]            │[/]\n"
    "[bold #C084FC]          ✧   ✧[/]   [dim]β · γ[/]\n"
    "[dim]          │     │[/]\n"
    "[bold #C084FC]          ✧   ✧[/]   [dim]δ · ζ[/]\n"
    "\n"
    "[bold #FACC15]    L Y R A[/]   [dim]· the harp of the agent fleet[/]"
)


def lyra_theme() -> Theme:
    """Return the Lyra brand theme.

    Built on Catppuccin Mocha (dark, well-tested in harness-tui) with
    the three brand tokens (primary / primary_alt / accent) overridden
    and a custom spinner frame set matching the Lyra constellation
    motif. Spinner: ♪ ♫ ♬ ♩ — musical notes for the harp.
    """
    return catppuccin_mocha().with_brand(
        name="lyra",
        primary=PRIMARY,
        primary_alt=PRIMARY_ALT,
        accent=ACCENT,
        ascii_logo=LYRA_LOGO,
        spinner_frames=("♪", "♫", "♬", "♩"),
    )


def welcome_lines(version: str, *, model: str, mode: str, repo: str) -> list[str]:
    """Compose the welcome-pane lines shown on first paint.

    Mirrors the prompt_toolkit REPL's structure so muscle memory
    transfers cleanly:

        ✻ Welcome to Lyra v3.14.0!
        /help for help · /status for your setup · ⌥? for keybindings

        model    deepseek · deepseek-chat
        mode     default
        repo     lyra

    Pure (no Rich, no Textual) — the caller is responsible for choosing
    the renderable. Returns a list of strings so callers can join with
    their preferred separator (``\\n`` for chat_log, ``  ``-padded for a
    Panel, etc).
    """
    intro = f"[bold #FACC15]✻[/] Welcome to Lyra v{version}!"
    hint = (
        "[dim]/help[/] for help · "
        "[dim]/status[/] for your setup · "
        "[dim]⌥?[/] for keybindings"
    )
    rows = [
        ("model", model or "—"),
        ("mode", mode or "default"),
        ("repo", repo or "—"),
    ]
    width = max(len(k) for k, _ in rows)
    body = [f"  [dim]{k.ljust(width)}[/]  {v}" for k, v in rows]
    return [intro, hint, ""] + body
