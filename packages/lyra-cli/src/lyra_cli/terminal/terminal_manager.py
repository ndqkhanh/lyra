"""Terminal manager - Handle terminal size, resize events, and cursor positioning"""

import os
import sys
import signal
import shutil
from typing import Callable, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TerminalSize:
    """Terminal size information"""
    width: int
    height: int


class TerminalManager:
    """Manages terminal state, resize events, and cursor positioning

    Features:
    - Terminal size detection
    - SIGWINCH signal handling for resize events
    - Cursor position tracking
    - Bottom UI positioning
    - Screen clearing and restoration
    """

    def __init__(self):
        self.width = 80
        self.height = 24
        self.bottom_ui_height = 4  # divider + input + divider + status

        # Resize callback
        self.on_resize: Optional[Callable[[int, int], None]] = None

        # Update initial size
        self.update_size()

        # Setup signal handler for terminal resize
        self._setup_resize_handler()

    def _setup_resize_handler(self):
        """Setup SIGWINCH signal handler for terminal resize"""
        def handle_resize(signum, frame):
            """Handle terminal resize signal"""
            old_width, old_height = self.width, self.height
            self.update_size()

            # Call resize callback if registered
            if self.on_resize and (old_width != self.width or old_height != self.height):
                self.on_resize(self.width, self.height)

        # Register signal handler
        signal.signal(signal.SIGWINCH, handle_resize)

    def update_size(self):
        """Update terminal size from current terminal"""
        try:
            size = shutil.get_terminal_size()
            self.width = size.columns
            self.height = size.lines
        except OSError:
            # Fallback to defaults if terminal size cannot be determined
            self.width = 80
            self.height = 24

    def get_size(self) -> TerminalSize:
        """Get current terminal size

        Returns:
            TerminalSize with width and height
        """
        return TerminalSize(width=self.width, height=self.height)

    def get_content_height(self) -> int:
        """Get height available for content (excluding bottom UI)

        Returns:
            Number of lines available for content
        """
        return max(1, self.height - self.bottom_ui_height)

    def get_bottom_ui_start_line(self) -> int:
        """Get line number where bottom UI starts (1-indexed)

        Returns:
            Line number (1-indexed)
        """
        return self.height - self.bottom_ui_height + 1

    def move_cursor(self, line: int, column: int = 1):
        """Move cursor to specific position

        Args:
            line: Line number (1-indexed)
            column: Column number (1-indexed, default: 1)
        """
        sys.stdout.write(f"\033[{line};{column}H")
        sys.stdout.flush()

    def move_cursor_to_bottom_ui(self):
        """Move cursor to start of bottom UI"""
        start_line = self.get_bottom_ui_start_line()
        self.move_cursor(start_line, 1)

    def move_cursor_to_input_line(self):
        """Move cursor to input line (second line of bottom UI)"""
        input_line = self.get_bottom_ui_start_line() + 1
        self.move_cursor(input_line, 1)

    def move_cursor_to_status_line(self):
        """Move cursor to status line (last line of terminal)"""
        self.move_cursor(self.height, 1)

    def clear_screen(self):
        """Clear entire screen"""
        sys.stdout.write("\033[2J")
        sys.stdout.flush()

    def clear_line(self, line: Optional[int] = None):
        """Clear a specific line or current line

        Args:
            line: Line number to clear (1-indexed), or None for current line
        """
        if line is not None:
            self.move_cursor(line, 1)
        sys.stdout.write("\033[K")
        sys.stdout.flush()

    def clear_from_cursor(self):
        """Clear from cursor to end of screen"""
        sys.stdout.write("\033[J")
        sys.stdout.flush()

    def clear_bottom_ui(self):
        """Clear the bottom UI area"""
        start_line = self.get_bottom_ui_start_line()
        for i in range(self.bottom_ui_height):
            self.clear_line(start_line + i)

    def save_cursor_position(self):
        """Save current cursor position"""
        sys.stdout.write("\033[s")
        sys.stdout.flush()

    def restore_cursor_position(self):
        """Restore saved cursor position"""
        sys.stdout.write("\033[u")
        sys.stdout.flush()

    def hide_cursor(self):
        """Hide cursor"""
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    def show_cursor(self):
        """Show cursor"""
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    def render_divider(self, line: int, char: str = "─"):
        """Render a horizontal divider line

        Args:
            line: Line number (1-indexed)
            char: Character to use for divider
        """
        self.move_cursor(line, 1)
        divider = char * self.width
        sys.stdout.write(divider)
        sys.stdout.flush()

    def render_bottom_ui_frame(self):
        """Render the frame for bottom UI (dividers only)"""
        start_line = self.get_bottom_ui_start_line()

        # Top divider
        self.render_divider(start_line)

        # Bottom divider (before status line)
        self.render_divider(start_line + 2)

    def scroll_content_area(self, lines: int = 1):
        """Scroll content area up by N lines

        Args:
            lines: Number of lines to scroll
        """
        # Move to content area
        content_end = self.get_content_height()
        self.move_cursor(content_end, 1)

        # Insert newlines to scroll
        for _ in range(lines):
            sys.stdout.write("\n")

        sys.stdout.flush()

    def set_scroll_region(self, top: int = 1, bottom: Optional[int] = None):
        """Set scrolling region

        Args:
            top: Top line of scroll region (1-indexed)
            bottom: Bottom line of scroll region (1-indexed), or None for content area
        """
        if bottom is None:
            bottom = self.get_content_height()

        sys.stdout.write(f"\033[{top};{bottom}r")
        sys.stdout.flush()

    def reset_scroll_region(self):
        """Reset scrolling region to full screen"""
        sys.stdout.write("\033[r")
        sys.stdout.flush()

    def enable_alternate_screen(self):
        """Enable alternate screen buffer"""
        sys.stdout.write("\033[?1049h")
        sys.stdout.flush()

    def disable_alternate_screen(self):
        """Disable alternate screen buffer"""
        sys.stdout.write("\033[?1049l")
        sys.stdout.flush()

    def get_cursor_position(self) -> Tuple[int, int]:
        """Get current cursor position

        Returns:
            Tuple of (line, column) both 1-indexed

        Note: This requires reading from stdin which may not work in all contexts
        """
        # Save current terminal settings
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            # Request cursor position
            sys.stdout.write("\033[6n")
            sys.stdout.flush()

            # Read response
            tty.setraw(fd)
            response = ""
            while True:
                char = sys.stdin.read(1)
                response += char
                if char == "R":
                    break

            # Parse response: ESC[line;columnR
            import re
            match = re.match(r"\033\[(\d+);(\d+)R", response)
            if match:
                line = int(match.group(1))
                column = int(match.group(2))
                return (line, column)
            else:
                return (1, 1)

        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def is_tty(self) -> bool:
        """Check if stdout is a TTY

        Returns:
            True if stdout is a TTY, False otherwise
        """
        return sys.stdout.isatty()

    def supports_color(self) -> bool:
        """Check if terminal supports color

        Returns:
            True if terminal supports color, False otherwise
        """
        if not self.is_tty():
            return False

        # Check TERM environment variable
        term = os.getenv("TERM", "")
        if "color" in term or "256" in term or "24bit" in term:
            return True

        # Check for common color-supporting terminals
        if term in ["xterm", "screen", "tmux", "linux"]:
            return True

        return False

    def get_terminal_info(self) -> dict:
        """Get terminal information

        Returns:
            Dictionary with terminal information
        """
        return {
            "width": self.width,
            "height": self.height,
            "content_height": self.get_content_height(),
            "bottom_ui_height": self.bottom_ui_height,
            "bottom_ui_start": self.get_bottom_ui_start_line(),
            "is_tty": self.is_tty(),
            "supports_color": self.supports_color(),
            "term": os.getenv("TERM", "unknown"),
        }


def main():
    """Test terminal manager"""
    manager = TerminalManager()

    print("Terminal Manager Test")
    print("=" * 40)
    print()

    # Show terminal info
    info = manager.get_terminal_info()
    for key, value in info.items():
        print(f"{key}: {value}")

    print()
    print("Testing resize handler...")
    print("Try resizing your terminal window.")
    print("Press Ctrl+C to exit.")

    # Setup resize callback
    def on_resize(width, height):
        print(f"\nTerminal resized to {width}x{height}")

    manager.on_resize = on_resize

    # Wait for resize events
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    main()
