"""Fixed bottom layout - Claude Code-style terminal layout with anchored input/status

This module implements the core layout pattern where:
- Input box stays fixed at bottom (never scrolls away)
- Status line stays below input (always visible)
- Content streams into scrollable area above
- Terminal resize handled gracefully
"""

import os
import sys
from dataclasses import dataclass


@dataclass
class LayoutDimensions:
    """Terminal layout dimensions"""
    terminal_width: int
    terminal_height: int
    scrollable_height: int  # Rows available for content
    divider_row_1: int      # Row for divider above input
    input_row: int          # Row for input box
    divider_row_2: int      # Row for divider below input
    status_row: int         # Row for status line


class FixedBottomLayout:
    """
    Terminal layout with fixed bottom elements (Claude Code pattern)

    Layout structure (4 fixed rows at bottom):
    ┌─────────────────────────────────┐
    │ Scrollable content area         │ ← Rows 1 to (height - 4)
    │ (auto-scroll to bottom)         │
    ├─────────────────────────────────┤ ← Row (height - 3): divider
    │ ❯ Input box                     │ ← Row (height - 2): input
    ├─────────────────────────────────┤ ← Row (height - 1): divider
    │ ⏵⏵ Status line                  │ ← Row (height): status
    └─────────────────────────────────┘
    """

    def __init__(self):
        self.scroll_buffer: list[str] = []
        self.scroll_offset: int = 0
        self.input_text: str = ""
        self.status_text: str = ""
        self.dimensions = self._get_dimensions()

        # Enable alternate screen buffer (optional)
        self.use_alt_screen = False

    def _get_dimensions(self) -> LayoutDimensions:
        """Calculate layout dimensions from terminal size"""
        # Get terminal size
        try:
            size = os.get_terminal_size()
            width = size.columns
            height = size.lines
        except OSError:
            # Fallback if not a TTY
            width = 80
            height = 24

        # Calculate fixed row positions (from bottom up)
        status_row = height
        divider_row_2 = height - 1
        input_row = height - 2
        divider_row_1 = height - 3
        scrollable_height = height - 4

        return LayoutDimensions(
            terminal_width=width,
            terminal_height=height,
            scrollable_height=scrollable_height,
            divider_row_1=divider_row_1,
            input_row=input_row,
            divider_row_2=divider_row_2,
            status_row=status_row,
        )

    def refresh_dimensions(self):
        """Refresh dimensions after terminal resize"""
        self.dimensions = self._get_dimensions()

    def enter_alt_screen(self):
        """Enter alternate screen buffer"""
        if self.use_alt_screen:
            sys.stdout.write("\033[?1049h")  # Enable alt screen
            sys.stdout.write("\033[2J")      # Clear screen
            sys.stdout.flush()

    def exit_alt_screen(self):
        """Exit alternate screen buffer"""
        if self.use_alt_screen:
            sys.stdout.write("\033[?1049l")  # Disable alt screen
            sys.stdout.flush()

    def move_cursor(self, row: int, col: int):
        """Move cursor to absolute position (1-indexed)"""
        sys.stdout.write(f"\033[{row};{col}H")

    def clear_line(self):
        """Clear current line"""
        sys.stdout.write("\033[2K")

    def hide_cursor(self):
        """Hide cursor"""
        sys.stdout.write("\033[?25l")

    def show_cursor(self):
        """Show cursor"""
        sys.stdout.write("\033[?25h")

    def save_cursor(self):
        """Save cursor position"""
        sys.stdout.write("\033[s")

    def restore_cursor(self):
        """Restore cursor position"""
        sys.stdout.write("\033[u")

    def get_visible_lines(self) -> list[str]:
        """Get lines visible in scrollable area"""
        total_lines = len(self.scroll_buffer)
        max_visible = self.dimensions.scrollable_height

        if total_lines <= max_visible:
            # All lines fit
            return self.scroll_buffer

        # Return last N lines (auto-scroll to bottom)
        start_idx = total_lines - max_visible
        return self.scroll_buffer[start_idx:]

    def render_scrollable_area(self):
        """Render scrollable content area"""
        visible_lines = self.get_visible_lines()

        for i, line in enumerate(visible_lines):
            row = i + 1
            self.move_cursor(row, 1)
            self.clear_line()
            # Truncate line if too long
            if len(line) > self.dimensions.terminal_width:
                line = line[:self.dimensions.terminal_width - 1] + "…"
            sys.stdout.write(line)

        # Clear remaining rows in scrollable area
        for i in range(len(visible_lines), self.dimensions.scrollable_height):
            row = i + 1
            self.move_cursor(row, 1)
            self.clear_line()

    def render_divider(self, row: int):
        """Render horizontal divider"""
        self.move_cursor(row, 1)
        self.clear_line()
        sys.stdout.write("─" * self.dimensions.terminal_width)

    def render_input_box(self):
        """Render input box (fixed at bottom)"""
        self.move_cursor(self.dimensions.input_row, 1)
        self.clear_line()

        # Render prompt and input text
        prompt = "❯ "
        max_input_width = self.dimensions.terminal_width - len(prompt)

        # Truncate input if too long
        display_text = self.input_text
        if len(display_text) > max_input_width:
            display_text = display_text[:max_input_width - 1] + "…"

        sys.stdout.write(prompt + display_text)

    def render_status_line(self):
        """Render status line (fixed at bottom)"""
        self.move_cursor(self.dimensions.status_row, 1)
        self.clear_line()

        # Render status with inverse colors
        status_display = self.status_text
        if len(status_display) > self.dimensions.terminal_width:
            status_display = status_display[:self.dimensions.terminal_width - 1] + "…"

        # Inverse colors for status line
        sys.stdout.write(f"\033[7m{status_display}\033[27m")

    def render_frame(self):
        """Render complete frame (scrollable + fixed bottom)"""
        self.hide_cursor()

        # 1. Render scrollable area
        self.render_scrollable_area()

        # 2. Render divider above input
        self.render_divider(self.dimensions.divider_row_1)

        # 3. Render input box
        self.render_input_box()

        # 4. Render divider below input
        self.render_divider(self.dimensions.divider_row_2)

        # 5. Render status line
        self.render_status_line()

        # Move cursor to input position
        input_cursor_col = len("❯ ") + len(self.input_text) + 1
        self.move_cursor(self.dimensions.input_row, input_cursor_col)

        self.show_cursor()
        sys.stdout.flush()

    def append_content(self, text: str):
        """Append text to scrollable area (input stays at bottom)"""
        # Split into lines if multiline
        lines = text.split("\n")
        self.scroll_buffer.extend(lines)

        # Re-render frame
        self.render_frame()

    def set_input(self, text: str):
        """Update input text"""
        self.input_text = text
        self.render_input_box()
        sys.stdout.flush()

    def set_status(self, text: str):
        """Update status line"""
        self.status_text = text
        self.render_status_line()
        sys.stdout.flush()

    def clear_scrollable(self):
        """Clear scrollable content"""
        self.scroll_buffer = []
        self.render_frame()

    def handle_resize(self):
        """Handle terminal resize event"""
        self.refresh_dimensions()
        self.render_frame()


class StreamingRenderer:
    """
    Streaming text renderer that appends to fixed layout

    Usage:
        layout = FixedBottomLayout()
        renderer = StreamingRenderer(layout)

        # Stream response
        for chunk in response_stream:
            renderer.append_delta(chunk)

        renderer.finalize()
    """

    def __init__(self, layout: FixedBottomLayout):
        self.layout = layout
        self.current_line = ""

    def append_delta(self, text: str):
        """Append text delta (streaming)"""
        # Accumulate text
        self.current_line += text

        # If newline, flush to layout
        if "\n" in self.current_line:
            lines = self.current_line.split("\n")
            # Add all complete lines
            for line in lines[:-1]:
                self.layout.append_content(line)
            # Keep incomplete line
            self.current_line = lines[-1]
        else:
            # Update last line in buffer
            if self.layout.scroll_buffer:
                self.layout.scroll_buffer[-1] = self.current_line
            else:
                self.layout.scroll_buffer.append(self.current_line)
            self.layout.render_frame()

    def finalize(self):
        """Finalize streaming (flush remaining text)"""
        if self.current_line:
            self.layout.append_content(self.current_line)
            self.current_line = ""


# Example usage
if __name__ == "__main__":
    import time

    # Create layout
    layout = FixedBottomLayout()
    layout.enter_alt_screen()

    try:
        # Set initial status
        layout.set_status("  ⏵⏵ ready · type to chat")

        # Simulate streaming response
        layout.append_content("⏺ Analyzing your request...")
        time.sleep(0.5)

        layout.append_content("  ⎿ Read file.py (228 lines)")
        time.sleep(0.5)

        layout.append_content("  ⎿ Edit src/main.py")
        time.sleep(0.5)

        layout.append_content("")
        layout.append_content("Here's the analysis of your code:")
        time.sleep(0.5)

        # Simulate long response
        for i in range(20):
            layout.append_content(f"Line {i + 1} of the response...")
            time.sleep(0.1)

        layout.append_content("")
        layout.append_content("✻ 2.3s · 3 tools · 1,234 tokens")

        # Update status
        layout.set_status("  ⏵⏵ ready · 1 message")

        # Wait for user
        input("\nPress Enter to exit...")

    finally:
        layout.exit_alt_screen()
