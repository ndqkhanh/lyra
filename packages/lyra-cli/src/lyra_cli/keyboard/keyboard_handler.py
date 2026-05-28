"""Keyboard handler - Capture special keys and key combinations"""

import sys
import termios
import tty
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class KeyPress:
    """Represents a key press event"""
    key: str
    char: str | None = None
    is_special: bool = False


class KeyboardHandler:
    """Handle keyboard input with special key support

    Features:
    - Arrow keys (up, down, left, right)
    - Shift+Tab for mode cycling
    - Enter, Escape, Backspace
    - Ctrl+C for interrupt
    - Regular character input
    """

    # Special key sequences
    ARROW_UP = "\x1b[A"
    ARROW_DOWN = "\x1b[B"
    ARROW_RIGHT = "\x1b[C"
    ARROW_LEFT = "\x1b[D"
    SHIFT_TAB = "\x1b[Z"
    ENTER = "\r"
    ESCAPE = "\x1b"
    BACKSPACE = "\x7f"
    CTRL_C = "\x03"
    CTRL_D = "\x04"

    def __init__(self):
        self.callbacks: dict[str, Callable] = {}

    def on_key(self, key: str, callback: Callable):
        """Register callback for specific key

        Args:
            key: Key name (e.g., 'shift+tab', 'arrow_up', 'enter')
            callback: Function to call when key is pressed
        """
        self.callbacks[key] = callback

    def read_key(self) -> KeyPress | None:
        """Read a single key press

        Returns:
            KeyPress object or None if interrupted
        """
        if not sys.stdin.isatty():
            # Fallback for non-TTY
            try:
                char = sys.stdin.read(1)
                if not char:
                    return None
                return KeyPress(key="char", char=char, is_special=False)
            except (KeyboardInterrupt, EOFError):
                return None

        # Save terminal settings
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            # Set raw mode
            tty.setraw(fd)

            # Read first character
            char = sys.stdin.read(1)

            # Check for escape sequences
            if char == "\x1b":
                # Read next characters for escape sequence
                seq = char + sys.stdin.read(2)

                if seq == self.ARROW_UP:
                    return KeyPress(key="arrow_up", is_special=True)
                elif seq == self.ARROW_DOWN:
                    return KeyPress(key="arrow_down", is_special=True)
                elif seq == self.ARROW_RIGHT:
                    return KeyPress(key="arrow_right", is_special=True)
                elif seq == self.ARROW_LEFT:
                    return KeyPress(key="arrow_left", is_special=True)
                elif seq == self.SHIFT_TAB:
                    return KeyPress(key="shift+tab", is_special=True)
                else:
                    return KeyPress(key="escape", is_special=True)

            # Check for special characters
            elif char == self.ENTER:
                return KeyPress(key="enter", char="\n", is_special=True)
            elif char == self.BACKSPACE:
                return KeyPress(key="backspace", is_special=True)
            elif char == self.CTRL_C:
                return KeyPress(key="ctrl+c", is_special=True)
            elif char == self.CTRL_D:
                return KeyPress(key="ctrl+d", is_special=True)
            else:
                # Regular character
                return KeyPress(key="char", char=char, is_special=False)

        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def read_line(self, prompt: str = "") -> str | None:
        """Read a line of input with special key support

        Args:
            prompt: Prompt to display

        Returns:
            Input string or None if interrupted
        """
        if prompt:
            sys.stdout.write(prompt)
            sys.stdout.flush()

        buffer = []
        cursor_pos = 0

        while True:
            key_press = self.read_key()

            if key_press is None:
                return None

            # Handle special keys
            if key_press.key == "enter":
                sys.stdout.write("\n")
                sys.stdout.flush()
                return "".join(buffer)

            elif key_press.key == "ctrl+c":
                sys.stdout.write("^C\n")
                sys.stdout.flush()
                raise KeyboardInterrupt()

            elif key_press.key == "ctrl+d":
                if not buffer:
                    raise EOFError()
                continue

            elif key_press.key == "backspace":
                if cursor_pos > 0:
                    buffer.pop(cursor_pos - 1)
                    cursor_pos -= 1
                    # Redraw line
                    self._redraw_line(buffer, cursor_pos)

            elif key_press.key == "arrow_left":
                if cursor_pos > 0:
                    cursor_pos -= 1
                    sys.stdout.write("\x1b[D")
                    sys.stdout.flush()

            elif key_press.key == "arrow_right":
                if cursor_pos < len(buffer):
                    cursor_pos += 1
                    sys.stdout.write("\x1b[C")
                    sys.stdout.flush()

            elif key_press.key == "shift+tab":
                # Trigger callback if registered
                if "shift+tab" in self.callbacks:
                    self.callbacks["shift+tab"]()

            elif key_press.key == "char" and key_press.char:
                # Insert character at cursor position
                buffer.insert(cursor_pos, key_press.char)
                cursor_pos += 1
                # Redraw line
                self._redraw_line(buffer, cursor_pos)

    def _redraw_line(self, buffer: list[str], cursor_pos: int):
        """Redraw the input line

        Args:
            buffer: Current input buffer
            cursor_pos: Current cursor position
        """
        # Move to start of line
        sys.stdout.write("\r")

        # Clear line
        sys.stdout.write("\x1b[K")

        # Write buffer
        sys.stdout.write("".join(buffer))

        # Move cursor to correct position
        if cursor_pos < len(buffer):
            # Move back from end
            moves = len(buffer) - cursor_pos
            sys.stdout.write(f"\x1b[{moves}D")

        sys.stdout.flush()


def main():
    """Test keyboard handler"""
    handler = KeyboardHandler()

    print("Keyboard Handler Test")
    print("=" * 40)
    print("Try these keys:")
    print("  - Arrow keys (up/down/left/right)")
    print("  - Shift+Tab")
    print("  - Enter to submit")
    print("  - Ctrl+C to exit")
    print()

    # Register Shift+Tab callback
    def on_shift_tab():
        print("\n[Shift+Tab pressed!]")

    handler.on_key("shift+tab", on_shift_tab)

    # Read input
    try:
        while True:
            line = handler.read_line("❯ ")
            if line is not None:
                print(f"You entered: {line}")
    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    main()
