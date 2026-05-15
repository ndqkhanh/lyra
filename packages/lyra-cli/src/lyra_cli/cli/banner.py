"""ASCII art and branding for Lyra CLI."""

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
