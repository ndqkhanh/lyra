"""ASCII art and branding for Lyra CLI — Wave 4: two-column welcome dashboard."""

LYRA_BANNER = r"""
    __
   / /   __  __ _____ ____
  / /   / / / // ___// __ \
 / /___/ /_/ // /   / /_/ /
/_____/\__, //_/    \__,_/
      /____/
"""

LYRA_BANNER_COMPACT = r"""
 _
| |   _   _ _ __ __ _
| |  | | | | '__/ _` |
| |__| |_| | | | (_| |
|_____\__, |_|  \__,_|
      |___/
"""

CLAUDE_CODE_STYLE_BANNER = r"""
╭─────────────────────────────────────────────────────────────╮
│                                                             │
│   ██╗  ██╗   ██╗██████╗  █████╗     ██████╗██╗     ██╗    │
│   ██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗   ██╔════╝██║     ██║    │
│   ██║   ╚████╔╝ ██████╔╝███████║   ██║     ██║     ██║    │
│   ██║    ╚██╔╝  ██╔══██╗██╔══██║   ██║     ██║     ██║    │
│   ███████╗██║   ██║  ██║██║  ██║   ╚██████╗███████╗██║    │
│   ╚══════╝╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝    ╚═════╝╚══════╝╚═╝    │
│                                                             │
│              Deep Research AI Agent Framework               │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
"""

_TIPS_LINES = [
    "ctrl+c     interrupt agent",
    "ctrl+d     exit",
    "ctrl+o     expand last tool",
    "ctrl+h     history / context",
    "ctrl+r     search history",
    "alt+enter  newline",
    "shift+tab  cycle mode",
    "",
    "/model     switch model",
    "/help      all commands",
    "/verbosity lite|full|ultra",
    "/memory    manage memory",
]

_PROVIDER_COLORS = {
    "anthropic": "\033[34m",   # blue
    "deepseek":  "\033[36m",   # cyan
    "openai":    "\033[32m",   # green
}


def render_welcome(
    model: str,
    version: str,
    cwd: str,
    api_provider: str = "",
) -> str:
    """Two-column ╭╮╰╯ welcome dashboard.

    Falls back to a compact single-column banner when terminal is <84 cols.
    """
    try:
        import shutil
        term_width = shutil.get_terminal_size().columns
    except Exception:
        term_width = 80

    if term_width < 84:
        return _compact_welcome(model, version, cwd, api_provider)

    return _two_col_welcome(model, version, cwd, api_provider, term_width)


def _compact_welcome(model: str, version: str, cwd: str, api_provider: str) -> str:
    pcolor = _PROVIDER_COLORS.get(api_provider, "\033[37m")
    lines = [
        "",
        LYRA_BANNER_COMPACT,
        f"  v{version}  ·  \033[36m{model}\033[0m  ·  {pcolor}[{api_provider}]\033[0m",
        f"  \033[2m{cwd}\033[0m",
        "",
        "  \033[2mType \033[0m\033[36m/help\033[0m\033[2m · shift+tab cycle mode · ctrl+c interrupt\033[0m",
        "",
    ]
    return "\n".join(lines)


def _two_col_welcome(
    model: str, version: str, cwd: str, api_provider: str, term_width: int
) -> str:
    # Each column width (inner content, excluding borders)
    total_inner = term_width - 6  # 2×│space + 2×space│ + 2×space gap
    col_w = total_inner // 2      # inner width per column

    pcolor = _PROVIDER_COLORS.get(api_provider, "\033[37m")

    # ── Left column: logo + info ───────────────────────────────────────────
    logo_lines = [
        " _     _  _ _ __ __ _",
        "| |   | || | '__/ _` |",
        "| |___| \\/ / | | (_| |",
        "|_____|\\__/|_|  \\__,_|",
    ]
    short_cwd = cwd if len(cwd) <= col_w - 4 else "…" + cwd[-(col_w - 5):]
    model_disp = model if len(model) <= col_w - 4 else model[:col_w - 7] + "…"

    left_content = [
        "",
        *logo_lines,
        "",
        f"\033[1mLyra\033[0m v{version}",
        f"\033[36m{model_disp}\033[0m",
        f"{pcolor}[{api_provider}]\033[0m  \033[2m{short_cwd}\033[0m",
        "",
        "\033[2mDeep Research AI Agent\033[0m",
        "",
    ]

    # ── Right column: tips ────────────────────────────────────────────────
    right_content = [
        "",
        "\033[1mTips & Shortcuts\033[0m",
        "\033[2m" + "─" * (col_w - 2) + "\033[0m",
        *_TIPS_LINES,
        "",
    ]

    # ── Pad both columns to equal height ─────────────────────────────────
    height = max(len(left_content), len(right_content))
    while len(left_content) < height:
        left_content.append("")
    while len(right_content) < height:
        right_content.append("")

    def strip_ansi_len(s: str) -> int:
        import re
        return len(re.sub(r'\033\[[0-9;]*m', '', s))

    def pad_to(s: str, width: int) -> str:
        pad = width - strip_ansi_len(s)
        return s + " " * max(pad, 0)

    border = "─" * (col_w + 2)
    top    = f"╭{border}╮  ╭{border}╮"
    bot    = f"╰{border}╯  ╰{border}╯"

    rows = [top]
    for l, r in zip(left_content, right_content):
        lpad = pad_to(l, col_w)
        rpad = pad_to(r, col_w)
        rows.append(f"│ {lpad} │  │ {rpad} │")
    rows.append(bot)

    return "\n".join(["", *rows, ""])


def get_banner(style: str = "default") -> str:
    """Get ASCII banner for Lyra.

    Args:
        style: Banner style (default, compact, claude)

    Returns:
        ASCII art banner
    """
    if style == "compact":
        return LYRA_BANNER_COMPACT
    elif style == "claude":
        return CLAUDE_CODE_STYLE_BANNER
    else:
        return LYRA_BANNER
