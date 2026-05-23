"""Symbol registry - Unicode symbols for terminal UI"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SymbolSet:
    """Unicode symbol set for terminal UI"""

    # Status symbols
    running: str = "⏺"      # U+23FA
    idle: str = "◯"         # U+25EF
    completed: str = "✔"    # U+2714
    failed: str = "✗"       # U+2717
    compacted: str = "✻"    # U+273B
    thinking: str = "✶"     # U+2736
    flowing: str = "✳"      # U+2733

    # Interactive symbols
    selected: str = "❯"     # U+276F
    radio: str = "●"        # U+25CF
    checkbox: str = "◻"     # U+25FB
    checkbox_checked: str = "◼"  # U+25FC

    # Tree symbols
    bullet: str = "⏺"       # U+23FA
    connector: str = "⎿"    # U+23BF

    # Arrow symbols
    upload: str = "↑"       # U+2191
    download: str = "↓"     # U+2193
    left: str = "←"         # U+2190
    right: str = "→"        # U+2192

    # Box drawing
    horizontal: str = "─"   # U+2500
    vertical: str = "│"     # U+2502
    top_left: str = "╭"     # U+256D
    top_right: str = "╮"    # U+256E
    bottom_left: str = "╰"  # U+2570
    bottom_right: str = "╯" # U+256F
    branch: str = "├"       # U+251C
    last_branch: str = "└"  # U+2514

    # Misc
    ellipsis: str = "…"     # U+2026
    separator: str = "·"    # U+00B7


# Global symbol registry
STATUS_SYMBOLS = {
    "running": "⏺",
    "idle": "◯",
    "completed": "✔",
    "failed": "✗",
    "compacted": "✻",
    "thinking": "✶",
    "flowing": "✳",
}

BOX_CHARS = {
    "horizontal": "─",
    "vertical": "│",
    "top_left": "╭",
    "top_right": "╮",
    "bottom_left": "╰",
    "bottom_right": "╯",
    "branch": "├",
    "last_branch": "└",
    "continuation": "│",
    "summary": "⎿",
}


class SymbolRegistry:
    """Registry for terminal UI symbols with fallback support"""

    def __init__(self, use_unicode: bool = True):
        self.use_unicode = use_unicode
        self.symbols = SymbolSet()
        self._ascii_fallbacks = {
            "⏺": "o",
            "◯": "O",
            "✔": "✓",
            "✗": "x",
            "✻": "*",
            "✶": "*",
            "✳": "*",
            "❯": ">",
            "●": "*",
            "◻": "[ ]",
            "◼": "[x]",
            "⎿": "└",
            "↑": "^",
            "↓": "v",
            "←": "<",
            "→": ">",
            "─": "-",
            "│": "|",
            "╭": "+",
            "╮": "+",
            "╰": "+",
            "╯": "+",
            "├": "+",
            "└": "+",
            "…": "...",
            "·": "·",
        }

    def get(self, symbol: str) -> str:
        """Get symbol with fallback to ASCII if needed"""
        if self.use_unicode:
            return symbol
        return self._ascii_fallbacks.get(symbol, symbol)

    def status(self, status: Literal["running", "idle", "completed", "failed", "thinking", "flowing"]) -> str:
        """Get status symbol"""
        symbol_map = {
            "running": self.symbols.running,
            "idle": self.symbols.idle,
            "completed": self.symbols.completed,
            "failed": self.symbols.failed,
            "thinking": self.symbols.thinking,
            "flowing": self.symbols.flowing,
        }
        return self.get(symbol_map[status])

    def box(self, position: Literal["top_left", "top_right", "bottom_left", "bottom_right", "horizontal", "vertical"]) -> str:
        """Get box drawing character"""
        symbol_map = {
            "top_left": self.symbols.top_left,
            "top_right": self.symbols.top_right,
            "bottom_left": self.symbols.bottom_left,
            "bottom_right": self.symbols.bottom_right,
            "horizontal": self.symbols.horizontal,
            "vertical": self.symbols.vertical,
        }
        return self.get(symbol_map[position])
