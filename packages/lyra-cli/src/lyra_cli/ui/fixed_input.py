"""Fixed input box - Always visible at bottom during streaming"""

import sys
import shutil
from typing import TextIO


class FixedInputBox:
    """Input box that stays at bottom during streaming

    Uses ANSI escape codes to position input box at bottom of terminal,
    ensuring it never scrolls away during response streaming.
    """

    def __init__(self, output: TextIO = sys.stdout):
        self.output = output
        self.height = 4  # divider + input + divider + status
        self.prompt_symbol = "❯"
        self.current_text = ""

    def get_terminal_size(self) -> tuple[int, int]:
        """Get terminal size (width, height)"""
        size = shutil.get_terminal_size()
        return size.columns, size.lines

    def render(self, prompt_text: str = "") -> None:
        """Render input box at bottom of terminal

        Args:
            prompt_text: Current input text to display
        """
        width, height = self.get_terminal_size()

        # Save cursor position
        self.output.write("\033[s")

        # Move to bottom (3 lines from bottom for divider + input + divider)
        row = height - 3
        self.output.write(f"\033[{row};1H")

        # Top divider
        divider = "─" * width
        self.output.write(f"\033[2m{divider}\033[0m")

        # Input line
        self.output.write(f"\033[{row + 1};1H")
        self.output.write(f"{self.prompt_symbol} {prompt_text}")

        # Clear rest of line
        self.output.write("\033[K")

        # Bottom divider
        self.output.write(f"\033[{row + 2};1H")
        self.output.write(f"\033[2m{divider}\033[0m")

        # Restore cursor position
        self.output.write("\033[u")
        self.output.flush()

    def clear_input_area(self) -> None:
        """Clear the input area"""
        width, height = self.get_terminal_size()
        row = height - 3

        # Clear 3 lines (divider + input + divider)
        for i in range(3):
            self.output.write(f"\033[{row + i};1H\033[K")

        self.output.flush()

    def move_cursor_to_input(self) -> None:
        """Move cursor to input line"""
        width, height = self.get_terminal_size()
        row = height - 2  # Input line

        # Position after prompt symbol
        col = len(self.prompt_symbol) + 2 + len(self.current_text)
        self.output.write(f"\033[{row};{col}H")
        self.output.flush()

    def update_text(self, text: str) -> None:
        """Update input text and re-render

        Args:
            text: New input text
        """
        self.current_text = text
        self.render(text)
        self.move_cursor_to_input()
