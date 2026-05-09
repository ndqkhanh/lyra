"""Start-up banner for the interactive session.

Claude Code uses a minimal, high-contrast banner that sets the tone for
the whole session. We follow the same discipline: the banner ships
the brand mark, tagline, working repo, active model, mode, and the two
hints a new user needs — ``/help`` and how to exit.

Three render paths:

- ``plain=True`` (non-TTY / CI / piped output) — pure ASCII, no colour.
- Fancy wide (≥ 40 cols) — full ANSI-Shadow ``LYRA`` logo in a rounded
  panel, with a three-stop colour gradient pulled from the active skin
  and a metadata block below.
- Fancy compact (TTY but < 40 cols) — no ASCII logo; a small rounded
  panel with the brand + tagline + metadata, keeping the colour treatment.

Why three paths? The ANSI-Shadow logo is 30 columns wide and looks
great in any modern terminal, but on a sub-40-col shell (cramped split
panes, watch-faces, etc.) even that 30-col block risks the "one glyph
per line" wrap. Detecting width up-front and dropping to a compact
panel keeps the UX tasteful everywhere.

Skin awareness: every visible colour and the wordmark text are pulled
from :mod:`.themes` at render time, so ``/theme hermes`` actually
re-skins the **next** banner you see (e.g. on ``/clear`` or ``Ctrl-L``).
Falls back to the historical aurora palette if a skin is missing a
specific token, so user-written YAML skins don't have to enumerate
every key to be safe.

Design notes:

- The metadata block (``Repo``, ``Model``, ``Mode``) renders *below*
  the panel with no width constraint — otherwise long absolute paths
  either wrap awkwardly inside the box or get elided with ``…``.
- The hint row highlights the two slash commands and the exit key-chord
  in bold so they're scannable at a glance.
- We never pass the pre-rendered string through another Rich console;
  the driver writes it straight to ``sys.stdout`` to preserve the
  embedded ANSI escapes (if we double-processed through Rich, those
  escapes would be counted as visible characters and re-wrapped).
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
from collections.abc import Iterator
from pathlib import Path

from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from .. import __version__
from . import themes as _themes


@contextlib.contextmanager
def _forced_columns(width: int) -> Iterator[None]:
    """Force a minimum console width for the banner render.

    Rich 15 reads terminal size via ``shutil.get_terminal_size()``,
    which only honours env overrides when BOTH ``COLUMNS`` and ``LINES``
    are set. Without this, an 80-column terminal would clip our logo.
    Restores prior values on exit.
    """
    prior_cols = os.environ.get("COLUMNS")
    prior_lines = os.environ.get("LINES")
    os.environ["COLUMNS"] = str(width)
    os.environ["LINES"] = prior_lines or "50"
    try:
        yield
    finally:
        if prior_cols is None:
            os.environ.pop("COLUMNS", None)
        else:
            os.environ["COLUMNS"] = prior_cols
        if prior_lines is None:
            os.environ.pop("LINES", None)
        else:
            os.environ["LINES"] = prior_lines


# "ANSI Shadow" figlet font, uppercase "LYRA".
# Four letters, so the logo is deliberately compact — 30 columns by 6 rows.
# Each row is right-padded to 30 chars so character-index-to-gradient-stop
# mapping stays stable across the whole block.
_LOGO = (
    "██╗  ██╗   ██╗██████╗  █████╗ \n"
    "██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗\n"
    "██║   ╚████╔╝ ██████╔╝███████║\n"
    "██║    ╚██╔╝  ██╔══██╗██╔══██║\n"
    "███████╗██║   ██║  ██║██║  ██║\n"
    "╚══════╝╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝"
)

_LOGO_WIDTH = 30
_FANCY_PANEL_WIDTH = 36  # 30-col logo + 2+2 padding + 2 borders = 36 exactly
_FANCY_MIN_TERMINAL_COLS = 40  # fits almost any terminal (80-col default)

# Default gradient stops (hex, no '#') — cyan → indigo → magenta —
# preserved as a fallback when the active skin doesn't declare its
# own gradient. Same palette we use in the docs hero, so the CLI
# "feels" on-brand.
_AURORA_STOPS: tuple[tuple[float, tuple[int, int, int]], ...] = (
    (0.00, (0x00, 0xE5, 0xFF)),  # cyan
    (0.50, (0x7C, 0x4D, 0xFF)),  # indigo
    (1.00, (0xFF, 0x2D, 0x95)),  # magenta/pink
)


def _terminal_cols(default: int = 80) -> int:
    """Best-effort terminal width. Returns ``default`` if unknown."""
    try:
        return shutil.get_terminal_size(fallback=(default, 24)).columns
    except OSError:
        return default


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    """Parse a ``#RRGGBB`` (case-insensitive) into a 0-255 RGB triple.

    Any malformed input falls back to the aurora cyan so a typo in a
    user skin can't crash the banner. We deliberately don't import
    ``re``/``colorsys`` here — slicing is enough for the canonical
    ``#RRGGBB`` shape every skin uses.
    """
    val = value.lstrip("#").strip()
    if len(val) != 6:
        return (0x00, 0xE5, 0xFF)
    try:
        return (int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16))
    except ValueError:
        return (0x00, 0xE5, 0xFF)


def _gradient_stops_from_skin() -> tuple[tuple[float, tuple[int, int, int]], ...]:
    """Pick the three-stop gradient for the *active* skin.

    Strategy: prefer dedicated ``banner_gradient_*`` tokens if the
    skin declares them (lets a skin author hand-tune the wordmark
    independent of the rest of the chrome). Otherwise derive a sane
    sweep from ``accent → secondary → danger`` — those are the three
    "personality" tokens every built-in skin already defines, so this
    "just works" for ``/theme hermes`` / ``opencode`` / ``claude``
    without touching the skin schema.

    Returns the same shape as :data:`_AURORA_STOPS` so the
    interpolator stays unchanged.
    """
    skin = _themes.get_active_skin()
    keys = ("banner_gradient_start", "banner_gradient_mid", "banner_gradient_end")
    explicit = [skin.color(k) for k in keys]
    if all(explicit):
        a, b, c = (_hex_to_rgb(v) for v in explicit)
        return ((0.00, a), (0.50, b), (1.00, c))
    # Fall back to the personality triple; defaults match aurora so an
    # under-configured skin still gets the historical look.
    a = _hex_to_rgb(skin.color("accent", "#00E5FF"))
    b = _hex_to_rgb(skin.color("secondary", "#7C4DFF"))
    c = _hex_to_rgb(skin.color("danger", "#FF2D95"))
    return ((0.00, a), (0.50, b), (1.00, c))


def _wordmark_text() -> str:
    """Brand string the banner displays — pulled from the active skin.

    ``branding.agent_name`` defaults to ``Lyra`` for every built-in
    skin, but a YAML user skin can override it (e.g. for a fork that
    wants its own product name in the banner).
    """
    return _themes.get_active_skin().brand("agent_name", "Lyra")


def render_banner(
    *,
    repo_root: Path,
    model: str,
    mode: str,
    plain: bool = False,
    term_cols: int | None = None,
) -> str:
    """Return a ready-to-print banner string.

    ``plain=True`` strips colour / box drawing so redirected streams and
    test captures don't get polluted with ANSI escapes.

    ``term_cols`` lets callers (or tests) override width detection. If
    not given, we read the real terminal size. When the detected width
    is below :data:`_FANCY_MIN_TERMINAL_COLS`, we fall back to the
    compact panel so the output never overflows / wraps awkwardly.
    """
    if plain:
        return _render_plain(repo_root=repo_root, model=model, mode=mode)
    cols = term_cols if term_cols is not None else _terminal_cols()
    if cols < _FANCY_MIN_TERMINAL_COLS:
        return _render_compact(
            repo_root=repo_root, model=model, mode=mode, cols=cols
        )
    return _render_fancy(
        repo_root=repo_root, model=model, mode=mode, cols=cols
    )


def _render_plain(*, repo_root: Path, model: str, mode: str) -> str:
    """Plain banner — no colour, no box, just the essentials.

    Used for non-TTY / CI / piped runs. We still pick up the active
    skin's *agent name* so a fork that re-brands the CLI sees its own
    name in CI logs, but every visual flourish is dropped to keep the
    output diff-friendly. Aurora-default tests stay green because the
    word ``Lyra`` is the default for every built-in skin.
    """
    name = _wordmark_text()
    skin_tag = _skin_subtitle().lstrip()  # drop the leading spaces
    lines = [
        f"{name}  v{__version__}",
        "general-purpose · multi-provider · self-evolving coding agent harness",
        "",
        f"Repo    {repo_root}",
        f"Model   {model}",
        f"Mode    {mode}",
        f"CLI     lyra · alias: ly",
    ]
    if skin_tag:
        # Only printed when the user has switched off the default skin,
        # so existing tests asserting the legacy 8-line shape stay green.
        lines.append(skin_tag)
    lines += [
        "",
        "Type /help for commands, /status for setup, or Ctrl-D to exit.",
        "",
    ]
    return "\n".join(lines)


def _interp_color(
    t: float,
    stops: tuple[tuple[float, tuple[int, int, int]], ...] | None = None,
) -> str:
    """Two-segment linear RGB interpolation between gradient stops.

    *stops* defaults to the active skin's gradient. Tests pass an
    explicit triple to keep their assertions independent of any
    user-installed skin overrides.
    """
    if stops is None:
        stops = _gradient_stops_from_skin()
    t = max(0.0, min(1.0, t))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if p0 <= t <= p1:
            local = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            r = int(c0[0] + (c1[0] - c0[0]) * local)
            g = int(c0[1] + (c1[1] - c0[1]) * local)
            b = int(c0[2] + (c1[2] - c0[2]) * local)
            return f"#{r:02X}{g:02X}{b:02X}"
    r, g, b = stops[-1][1]
    return f"#{r:02X}{g:02X}{b:02X}"


def _gradient_logo() -> Text:
    """Render the ANSI-Shadow logo with the active skin's gradient sweep."""
    stops = _gradient_stops_from_skin()
    rows = _LOGO.splitlines()
    cols = max(len(row) for row in rows)
    text = Text(no_wrap=True, overflow="crop")
    last = len(rows) - 1
    for idx, row in enumerate(rows):
        for col, ch in enumerate(row):
            if ch == " ":
                text.append(" ")
                continue
            color = _interp_color(col / max(cols - 1, 1), stops)
            text.append(ch, style=f"bold {color}")
        if idx != last:
            text.append("\n")
    return text


def _gradient_wordmark(word: str) -> Text:
    """Per-character gradient wordmark, sweeping the active skin's stops."""
    stops = _gradient_stops_from_skin()
    text = Text(no_wrap=True)
    n = max(len(word) - 1, 1)
    for i, ch in enumerate(word):
        color = _interp_color(i / n, stops)
        text.append(ch, style=f"bold {color}")
    return text


def _truncate_middle(s: str, max_width: int) -> str:
    """Collapse the middle of a string with ``…`` so it fits ``max_width``.

    Used to shorten absolute repo paths on narrow terminals while
    keeping both the drive-ish prefix and the leaf directory visible.
    """
    if len(s) <= max_width or max_width < 6:
        return s if len(s) <= max_width else s[: max(max_width - 1, 1)] + "…"
    keep = max_width - 1
    left = keep // 2
    right = keep - left
    return s[:left] + "…" + s[-right:]


def _metadata_block(
    *,
    repo_root: Path,
    model: str,
    mode: str,
    console: Console,
    cols: int,
    truncate_path: bool,
) -> None:
    """Print the Repo / Model-Mode / hint block to ``console``.

    ``cols`` is the real terminal width; we switch to a terser hint row
    at narrow widths. ``truncate_path=True`` also middle-ellipsizes
    overly long paths to keep the block from wrapping on small shells.
    We never truncate in wide mode — a user with a 140-col terminal
    would rather see the whole path.

    Colours come from the active skin so ``/clear`` after ``/theme``
    paints the metadata block in the new palette too.
    """
    skin = _themes.get_active_skin()
    accent = skin.color("accent", "#00E5FF")
    secondary = skin.color("secondary", "#7C4DFF")
    success = skin.color("success", "#7CFFB2")
    danger = skin.color("danger", "#FF2D95")

    if truncate_path:
        # 13 cols are reserved for "  ◆  Repo    ".
        path_budget = max(20, cols - 13)
        repo_str = _truncate_middle(str(repo_root), path_budget)
    else:
        repo_str = str(repo_root)

    repo_line = Text(no_wrap=True, overflow="crop")
    repo_line.append("  ◆  ", style=accent)
    repo_line.append("Repo    ", style="dim")
    repo_line.append(repo_str, style="bright_white")
    console.print(repo_line)

    model_line = Text(no_wrap=True)
    model_line.append("  ◆  ", style=secondary)
    model_line.append("Model   ", style="dim")
    model_line.append(model, style=f"bold {success}")
    model_line.append("     Mode   ", style="dim")
    model_line.append(mode, style=f"bold {danger}")
    console.print(model_line)

    cli_line = Text(no_wrap=True)
    cli_line.append("  ◆  ", style=accent)
    cli_line.append("CLI     ", style="dim")
    cli_line.append("lyra", style=f"bold {accent}")
    cli_line.append("  ·  ", style="dim")
    cli_line.append("alias: ", style="dim")
    cli_line.append("ly", style=f"bold {accent}")
    console.print(cli_line)

    console.print()

    hint = Text(no_wrap=True, overflow="crop")
    # Three visual densities so the row always fits its terminal:
    #   ≥ 80 cols: full verbose hint ("/help for commands · …")
    #   48-79    : canonical compact hint ("/help   ·   /status   ·   Ctrl-D to exit")
    #   < 48     : tight hint ("/help · /status · ^D") — drops " to exit" and
    #              collapses the inter-token padding so it fits 30-col panes.
    verbose = cols >= 80
    tight = cols < 48
    pad = " " if tight else "   "
    hint.append("  ", style="dim")
    hint.append("/help", style=f"bold {accent}")
    if verbose:
        hint.append(" for commands", style="dim")
    hint.append(pad, style="dim")
    hint.append("·", style=secondary)
    hint.append(pad, style="dim")
    hint.append("/status", style=f"bold {accent}")
    if verbose:
        hint.append(" for setup", style="dim")
    hint.append(pad, style="dim")
    hint.append("·", style=secondary)
    hint.append(pad, style="dim")
    if tight:
        hint.append("^D", style=f"bold {accent}")
    else:
        hint.append("Ctrl-D", style=f"bold {accent}")
        hint.append(" to exit", style="dim")
    console.print(hint)


def _tagline_text(skin_subtitle: str) -> Text:
    """Build the centered tagline + active-skin subtitle.

    Skin name appears as a small dim tag so a user who's themed the
    REPL sees the active skin name on every fresh banner ("oh right,
    I'm wearing hermes today"). Defaults stay invisible when the user
    is on the default aurora.
    """
    return Text(
        f"general-purpose · multi-provider · self-evolving   ·   v{__version__}{skin_subtitle}",
        style="italic #A1A7B3",
        justify="center",
    )


def _skin_subtitle() -> str:
    """Return ``""`` for aurora (the default) or ``  ·   skin: name``."""
    skin = _themes.get_active_skin()
    if skin.name == "aurora":
        return ""
    return f"   ·   skin: {skin.name}"


def _render_fancy(
    *, repo_root: Path, model: str, mode: str, cols: int
) -> str:
    """Wide render: full ASCII-Shadow logo inside a rounded panel."""
    skin = _themes.get_active_skin()
    accent = skin.color("accent", "#00E5FF")
    border = skin.color("banner_border", accent)
    title_colour = skin.color("banner_title", accent)
    wordmark_text = _wordmark_text()
    welcome = skin.brand("welcome", "ready.")

    buf = io.StringIO()
    # The *panel* is pinned to ``_FANCY_PANEL_WIDTH`` (36 cols) so the
    # LYRA wordmark always lands in the same rectangle. But the
    # ``Console`` itself must be as wide as the real terminal,
    # otherwise the metadata block below (``Model  … Mode  …``) and
    # the hint row wrap at the panel width and look broken on a 140-col
    # shell. ``len(repo_root)+20`` is the historical floor so paths
    # never get ellipsized in fancy mode.
    width = max(cols, _FANCY_PANEL_WIDTH, len(str(repo_root)) + 20)
    with _forced_columns(width):
        console = Console(
            file=buf,
            force_terminal=True,
            color_system="truecolor",
            soft_wrap=False,
            legacy_windows=False,
        )

        logo = _gradient_logo()
        tagline = _tagline_text(_skin_subtitle())

        panel = Panel(
            Group(Align.center(logo, width=_LOGO_WIDTH), Text(""), tagline),
            box=ROUNDED,
            border_style=border,
            padding=(1, 2),
            width=_FANCY_PANEL_WIDTH,
            title=f"[bold {title_colour}]{wordmark_text}[/] [dim]v{__version__}[/]",
            title_align="left",
            subtitle=f"[dim italic]{welcome}[/]",
            subtitle_align="right",
        )
        console.print(panel)
        console.print()
        _metadata_block(
            repo_root=repo_root,
            model=model,
            mode=mode,
            console=console,
            cols=cols,
            truncate_path=False,
        )
    return buf.getvalue()


def _render_compact(
    *, repo_root: Path, model: str, mode: str, cols: int
) -> str:
    """Compact render: wordmark + tagline in a small rounded panel.

    Used when the real terminal is narrower than the big-logo panel.
    Panel width clamps to ``(terminal width − 2)`` so nothing wraps;
    the floor is 24 cols so the brand + version are still readable on
    a cramped watch-face or tmux sub-pane, and the ceiling is 78 cols
    so we never get an awkward half-filled rectangle on very wide
    terminals that for some reason picked this path.
    """
    skin = _themes.get_active_skin()
    accent = skin.color("accent", "#00E5FF")
    border = skin.color("banner_border", accent)
    title_colour = skin.color("banner_title", accent)
    wordmark_text = _wordmark_text()
    welcome = skin.brand("welcome", "ready.")

    panel_width = max(24, min(cols - 2, 78))
    buf = io.StringIO()
    with _forced_columns(max(panel_width + 4, len(str(repo_root)) + 6)):
        console = Console(
            file=buf,
            force_terminal=True,
            color_system="truecolor",
            soft_wrap=False,
            legacy_windows=False,
        )

        wordmark = _gradient_wordmark(wordmark_text)
        wordmark.append(f"   v{__version__}", style="dim")
        tagline = Text(
            f"general-purpose · multi-provider · self-evolving{_skin_subtitle()}",
            style="italic #A1A7B3",
        )

        panel = Panel(
            Group(wordmark, tagline),
            box=ROUNDED,
            border_style=border,
            padding=(0, 2),
            width=panel_width,
            title=f"[bold {title_colour}]{wordmark_text}[/]",
            title_align="left",
            subtitle=f"[dim italic]{welcome}[/]",
            subtitle_align="right",
        )
        console.print(panel)
        console.print()
        _metadata_block(
            repo_root=repo_root,
            model=model,
            mode=mode,
            console=console,
            cols=cols,
            truncate_path=True,
        )
    return buf.getvalue()
