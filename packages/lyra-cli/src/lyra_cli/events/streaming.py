"""Streaming renderer - Append-only rendering without flicker"""

import sys
from typing import TextIO


class StreamingRenderer:
    """Append-only streaming renderer (no flicker)

    Implements monotonic append-only buffer pattern for smooth streaming
    without re-rendering entire content on each token.
    """

    def __init__(self, output: TextIO = sys.stdout):
        self.output = output
        self.buffer: list[str] = []
        self.current_line = ""
        self.total_chars = 0

    def append_delta(self, text: str) -> None:
        """Append text without re-rendering entire buffer

        Args:
            text: Text delta to append
        """
        self.current_line += text
        self.total_chars += len(text)

        # Only print the new delta
        self.output.write(text)
        self.output.flush()

    def finalize_line(self) -> None:
        """Complete current line and move to next"""
        if self.current_line:
            self.buffer.append(self.current_line)
            self.current_line = ""

        self.output.write("\n")
        self.output.flush()

    def append_line(self, line: str) -> None:
        """Append a complete line

        Args:
            line: Complete line to append
        """
        self.buffer.append(line)
        self.total_chars += len(line)

        self.output.write(line)
        self.output.write("\n")
        self.output.flush()

    def clear(self) -> None:
        """Clear the buffer"""
        self.buffer.clear()
        self.current_line = ""
        self.total_chars = 0

    def get_content(self) -> str:
        """Get all buffered content as string"""
        lines = self.buffer.copy()
        if self.current_line:
            lines.append(self.current_line)
        return "\n".join(lines)

    def get_line_count(self) -> int:
        """Get number of complete lines"""
        return len(self.buffer)
