# Lyra UI Sequential Output Pattern - Ultra Implementation Plan

**Goal**: Replicate Claude Code's sequential output pattern where streaming responses push bottom UI blocks down, but blocks always stay visible.

**Date**: 2026-05-23  
**Status**: Planning Phase

---

## Problem Statement

Current Lyra UI shows a welcome banner, but the **bottom UI components** (input box, status line) are not properly implemented to:
1. Stay fixed at the bottom during streaming
2. Be pushed down by streaming content (not overlaid)
3. Always remain visible (never scroll away)

### Claude Code's Pattern

```
[Streaming Content Area - grows upward]
  ⏺ Response text...
  ⎿ Tool calls...
  ✻ Stats...

────────────────────────────────────────────────────────────────────
❯ [user input]
────────────────────────────────────────────────────────────────────
  ⏵⏵ mode · hints
```

**Key Behavior**: As content streams, it pushes the bottom 4 lines down, but those 4 lines are ALWAYS rendered at the bottom of the terminal.

---

## Current State Analysis

### ✅ Already Implemented (from Phase 1-7)
- Event protocol (TurnStarted, TextDelta, ToolStarted, etc.)
- StreamingRenderer with append-only buffer
- FixedInputBox component
- StatusLine component
- ResponseFormatter with all symbols (⏺ ✻ ✶ ⎿)
- AgentTree with collapse/expand
- SelectionMenu for interactive prompts
- ScrollManager for virtualized scrolling
- WelcomeBanner with responsive layouts

### ❌ Missing: Sequential Output Integration
The components exist but are NOT integrated into a **sequential output REPL** that:
1. Renders welcome banner ONCE at startup
2. Streams responses that push bottom UI down
3. Keeps bottom UI always visible
4. Handles terminal resize
5. Manages scrollback properly

---

## Architecture: Sequential Output REPL

### Core Concept

```
┌─────────────────────────────────────────────────────────┐
│ Scrollback Buffer (unlimited history)                  │
│   - Welcome banner                                      │
│   - Previous turns                                      │
│   - Current turn streaming content                      │
│                                                         │
│ [Content grows downward, pushing bottom UI]            │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ Fixed Bottom UI (always visible, 4 lines)              │
│   Line 1: ──────────────────────────────────────────   │
│   Line 2: ❯ [input]                                    │
│   Line 3: ──────────────────────────────────────────   │
│   Line 4:   ⏵⏵ mode · hints                            │
└─────────────────────────────────────────────────────────┘
```

### Key Insight

**NOT** a TUI framework approach (Textual, Rich, etc.) - those use absolute positioning.

**YES** a sequential output approach:
1. Print content line by line (grows downward)
2. After each line, re-render bottom UI at current terminal bottom
3. Use ANSI escape codes to position bottom UI
4. Content naturally scrolls up as terminal fills

---

## Phase 1: Sequential Output REPL Core (4-6 hours)

### 1.1 Create SequentialREPL Class

**File**: `packages/lyra-cli/src/lyra_cli/repl/sequential_repl.py`

```python
"""Sequential output REPL - Claude Code style"""

import sys
import os
from typing import Optional
from ..events import EventDispatcher, StreamingRenderer
from ..ui import (
    FixedInputBox,
    StatusLine,
    ResponseFormatter,
    AgentTree,
    print_welcome_banner
)


class SequentialREPL:
    """REPL with sequential output and fixed bottom UI"""
    
    def __init__(self):
        # Components
        self.dispatcher = EventDispatcher()
        self.streaming = StreamingRenderer()
        self.input_box = FixedInputBox()
        self.status_line = StatusLine()
        self.formatter = ResponseFormatter()
        self.agent_tree = AgentTree()
        
        # State
        self.terminal_height = self._get_terminal_height()
        self.terminal_width = self._get_terminal_width()
        self.bottom_ui_height = 4  # divider + input + divider + status
        
        # Setup handlers
        self._setup_event_handlers()
    
    def _get_terminal_height(self) -> int:
        """Get terminal height"""
        return os.get_terminal_size().lines
    
    def _get_terminal_width(self) -> int:
        """Get terminal width"""
        return os.get_terminal_size().columns
    
    def _setup_event_handlers(self):
        """Setup event handlers"""
        self.dispatcher.on("text.delta", self._on_text_delta)
        self.dispatcher.on("tool.started", self._on_tool_started)
        self.dispatcher.on("turn.finished", self._on_turn_finished)
    
    def _on_text_delta(self, event):
        """Handle streaming text"""
        # Print text (grows downward)
        print(event.text, end="", flush=True)
        
        # Re-render bottom UI at new position
        self._render_bottom_ui()
    
    def _on_tool_started(self, event):
        """Handle tool started"""
        # Print tool call line
        tool_line = self.formatter.format_tool_call(event.name, str(event.input))
        print(f"\n{tool_line}")
        
        # Re-render bottom UI
        self._render_bottom_ui()
    
    def _on_turn_finished(self, event):
        """Handle turn finished"""
        # Print stats line
        stats = self.formatter.format_stats_line(
            duration_s=event.duration_ms / 1000,
            tool_count=event.tool_count,
            tokens=event.tokens_in + event.tokens_out
        )
        print(f"\n{stats}\n")
        
        # Re-render bottom UI
        self._render_bottom_ui()
    
    def _render_bottom_ui(self, prompt_text: str = ""):
        """Render fixed bottom UI at current terminal bottom"""
        # Save cursor position
        print("\033[s", end="")
        
        # Move to bottom - 4 lines
        current_row = self._get_cursor_row()
        bottom_start = self.terminal_height - self.bottom_ui_height + 1
        
        # Only render if we have space
        if current_row < bottom_start:
            # Move to bottom UI area
            print(f"\033[{bottom_start};1H", end="")
            
            # Clear bottom area
            for i in range(self.bottom_ui_height):
                print(f"\033[{bottom_start + i};1H\033[K", end="")
            
            # Render components
            print(f"\033[{bottom_start};1H", end="")
            print("─" * self.terminal_width)
            
            print(f"\033[{bottom_start + 1};1H", end="")
            print(f"❯ {prompt_text}")
            
            print(f"\033[{bottom_start + 2};1H", end="")
            print("─" * self.terminal_width)
            
            print(f"\033[{bottom_start + 3};1H", end="")
            self.status_line.render_inline()
        
        # Restore cursor position
        print("\033[u", end="", flush=True)
    
    def _get_cursor_row(self) -> int:
        """Get current cursor row (1-indexed)"""
        # Query cursor position
        print("\033[6n", end="", flush=True)
        
        # Read response (ESC[row;colR)
        response = ""
        while True:
            char = sys.stdin.read(1)
            response += char
            if char == "R":
                break
        
        # Parse row
        row_str = response.split(";")[0].replace("\033[", "")
        return int(row_str)
    
    def show_welcome(self):
        """Show welcome banner once at startup"""
        print_welcome_banner(
            version="0.1.0",
            model="Opus 4.7",
            effort="high",
            provider="Anthropic API",
            user_name=os.getenv("USER", "User")
        )
        print()  # Blank line after welcome
    
    def run(self):
        """Main REPL loop"""
        # Show welcome once
        self.show_welcome()
        
        # Initial bottom UI render
        self._render_bottom_ui()
        
        while True:
            # Get user input
            user_input = input("\n❯ ")
            
            if user_input.strip() in ["/exit", "/quit", "exit", "quit"]:
                break
            
            # Process input (emit events)
            self._process_input(user_input)
    
    def _process_input(self, user_input: str):
        """Process user input and emit events"""
        # Emit turn started
        self.dispatcher.emit("turn.started", {
            "turn_id": "turn-1",
            "user_text": user_input
        })
        
        # Simulate streaming response
        response = f"You asked: {user_input}"
        for char in response:
            self.dispatcher.emit("text.delta", {
                "turn_id": "turn-1",
                "text": char
            })
        
        # Emit turn finished
        self.dispatcher.emit("turn.finished", {
            "turn_id": "turn-1",
            "tokens_in": 10,
            "tokens_out": 20,
            "duration_ms": 1500,
            "tool_count": 0
        })
```

### 1.2 Update StatusLine for Inline Rendering

**File**: `packages/lyra-cli/src/lyra_cli/ui/status_line.py`

Add method:
```python
def render_inline(self):
    """Render status line inline (no newline)"""
    status = f"  ⏵⏵ {self.mode}"
    if self.hints:
        status += " · " + " · ".join(self.hints)
    print(status, end="", flush=True)
```

### 1.3 Test Sequential Output

**File**: `test_sequential_repl.py`

```python
#!/usr/bin/env python3
"""Test sequential output REPL"""

import sys
import os
sys.path.insert(0, 'packages/lyra-cli/src')

from lyra_cli.repl.sequential_repl import SequentialREPL

if __name__ == "__main__":
    repl = SequentialREPL()
    repl.run()
```

**Deliverables**:
- [ ] SequentialREPL class with bottom UI rendering
- [ ] Event-driven streaming that re-renders bottom UI
- [ ] Cursor position tracking
- [ ] Terminal size detection
- [ ] Test script

---

## Phase 2: Terminal Management & Resize Handling (2-3 hours)

### 2.1 Terminal State Manager

**File**: `packages/lyra-cli/src/lyra_cli/repl/terminal_manager.py`

```python
"""Terminal state management"""

import os
import sys
import signal
from typing import Callable, Optional


class TerminalManager:
    """Manage terminal state and resize events"""
    
    def __init__(self):
        self.width = 80
        self.height = 24
        self.resize_callbacks: list[Callable] = []
        
        # Setup resize handler
        signal.signal(signal.SIGWINCH, self._on_resize)
        
        # Initial size
        self._update_size()
    
    def _update_size(self):
        """Update terminal size"""
        try:
            size = os.get_terminal_size()
            self.width = size.columns
            self.height = size.lines
        except OSError:
            pass
    
    def _on_resize(self, signum, frame):
        """Handle terminal resize"""
        self._update_size()
        
        # Notify callbacks
        for callback in self.resize_callbacks:
            callback(self.width, self.height)
    
    def on_resize(self, callback: Callable):
        """Register resize callback"""
        self.resize_callbacks.append(callback)
    
    def enable_raw_mode(self):
        """Enable raw terminal mode"""
        import tty
        tty.setraw(sys.stdin.fileno())
    
    def disable_raw_mode(self):
        """Disable raw terminal mode"""
        import termios
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._original_settings)
    
    def save_settings(self):
        """Save terminal settings"""
        import termios
        self._original_settings = termios.tcgetattr(sys.stdin.fileno())
    
    def restore_settings(self):
        """Restore terminal settings"""
        import termios
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._original_settings)
```

### 2.2 Integrate Terminal Manager

Update `SequentialREPL` to use `TerminalManager`:

```python
def __init__(self):
    # ... existing code ...
    
    # Terminal manager
    self.terminal = TerminalManager()
    self.terminal.on_resize(self._on_terminal_resize)

def _on_terminal_resize(self, width: int, height: int):
    """Handle terminal resize"""
    self.terminal_width = width
    self.terminal_height = height
    
    # Re-render bottom UI with new size
    self._render_bottom_ui()
```

**Deliverables**:
- [ ] TerminalManager with resize handling
- [ ] SIGWINCH signal handler
- [ ] Raw mode support (for future keyboard handling)
- [ ] Integration with SequentialREPL

---

## Phase 3: Scrollback Buffer Management (2-3 hours)

### 3.1 Scrollback Buffer

**File**: `packages/lyra-cli/src/lyra_cli/repl/scrollback.py`

```python
"""Scrollback buffer for terminal history"""

from typing import List
from dataclasses import dataclass


@dataclass
class Line:
    """A line in the scrollback buffer"""
    content: str
    timestamp: float
    type: str  # "user", "assistant", "tool", "system"


class ScrollbackBuffer:
    """Manage scrollback history"""
    
    def __init__(self, max_lines: int = 10000):
        self.lines: List[Line] = []
        self.max_lines = max_lines
    
    def append(self, content: str, line_type: str = "assistant"):
        """Append line to buffer"""
        import time
        
        line = Line(
            content=content,
            timestamp=time.time(),
            type=line_type
        )
        
        self.lines.append(line)
        
        # Trim if exceeds max
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines:]
    
    def get_visible_lines(self, count: int) -> List[Line]:
        """Get last N lines"""
        return self.lines[-count:] if count < len(self.lines) else self.lines
    
    def clear(self):
        """Clear buffer"""
        self.lines = []
    
    def save_to_file(self, filepath: str):
        """Save buffer to file"""
        with open(filepath, "w") as f:
            for line in self.lines:
                f.write(f"[{line.type}] {line.content}\n")
```

### 3.2 Integrate Scrollback

Update `SequentialREPL`:

```python
def __init__(self):
    # ... existing code ...
    
    # Scrollback buffer
    self.scrollback = ScrollbackBuffer()

def _on_text_delta(self, event):
    """Handle streaming text"""
    # Print text
    print(event.text, end="", flush=True)
    
    # Add to scrollback
    self.scrollback.append(event.text, "assistant")
    
    # Re-render bottom UI
    self._render_bottom_ui()
```

**Deliverables**:
- [ ] ScrollbackBuffer with line storage
- [ ] Max line limit (10,000 default)
- [ ] Save to file capability
- [ ] Integration with SequentialREPL

---

## Phase 4: Keyboard Input Handling (3-4 hours)

### 4.1 Keyboard Handler

**File**: `packages/lyra-cli/src/lyra_cli/repl/keyboard.py`

```python
"""Keyboard input handling"""

import sys
import tty
import termios
from typing import Optional, Callable


class KeyboardHandler:
    """Handle keyboard input with special keys"""
    
    def __init__(self):
        self.callbacks: dict[str, Callable] = {}
    
    def on_key(self, key: str, callback: Callable):
        """Register key callback"""
        self.callbacks[key] = callback
    
    def read_key(self) -> Optional[str]:
        """Read a single key press"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            tty.setraw(fd)
            char = sys.stdin.read(1)
            
            # Handle escape sequences
            if char == '\x1b':
                char += sys.stdin.read(2)
                
                # Arrow keys
                if char == '\x1b[A':
                    return 'up'
                elif char == '\x1b[B':
                    return 'down'
                elif char == '\x1b[C':
                    return 'right'
                elif char == '\x1b[D':
                    return 'left'
                else:
                    return 'esc'
            
            # Ctrl+O
            elif char == '\x0f':
                return 'ctrl+o'
            
            # Ctrl+C
            elif char == '\x03':
                return 'ctrl+c'
            
            # Enter
            elif char in ['\r', '\n']:
                return 'enter'
            
            # Backspace
            elif char in ['\x7f', '\x08']:
                return 'backspace'
            
            else:
                return char
        
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def handle_key(self, key: str):
        """Handle key press"""
        if key in self.callbacks:
            self.callbacks[key]()
```

### 4.2 Input Line Editor

**File**: `packages/lyra-cli/src/lyra_cli/repl/input_editor.py`

```python
"""Input line editor with history"""

from typing import List


class InputEditor:
    """Line editor with history and editing"""
    
    def __init__(self):
        self.buffer = ""
        self.cursor_pos = 0
        self.history: List[str] = []
        self.history_index = -1
    
    def insert_char(self, char: str):
        """Insert character at cursor"""
        self.buffer = (
            self.buffer[:self.cursor_pos] +
            char +
            self.buffer[self.cursor_pos:]
        )
        self.cursor_pos += 1
    
    def delete_char(self):
        """Delete character before cursor"""
        if self.cursor_pos > 0:
            self.buffer = (
                self.buffer[:self.cursor_pos - 1] +
                self.buffer[self.cursor_pos:]
            )
            self.cursor_pos -= 1
    
    def move_cursor_left(self):
        """Move cursor left"""
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
    
    def move_cursor_right(self):
        """Move cursor right"""
        if self.cursor_pos < len(self.buffer):
            self.cursor_pos += 1
    
    def history_prev(self):
        """Navigate to previous history item"""
        if self.history and self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.buffer = self.history[-(self.history_index + 1)]
            self.cursor_pos = len(self.buffer)
    
    def history_next(self):
        """Navigate to next history item"""
        if self.history_index > 0:
            self.history_index -= 1
            self.buffer = self.history[-(self.history_index + 1)]
            self.cursor_pos = len(self.buffer)
        elif self.history_index == 0:
            self.history_index = -1
            self.buffer = ""
            self.cursor_pos = 0
    
    def submit(self) -> str:
        """Submit current buffer"""
        result = self.buffer
        
        # Add to history
        if result.strip():
            self.history.append(result)
        
        # Reset
        self.buffer = ""
        self.cursor_pos = 0
        self.history_index = -1
        
        return result
    
    def get_display_text(self) -> str:
        """Get text for display"""
        return self.buffer
```

**Deliverables**:
- [ ] KeyboardHandler with special key detection
- [ ] InputEditor with history navigation
- [ ] Arrow key support (↑↓ for history, ←→ for cursor)
- [ ] Ctrl+O for expand/collapse
- [ ] Integration with SequentialREPL

---

## Phase 5: Complete Integration & Polish (3-4 hours)

### 5.1 Full SequentialREPL with All Features

Update `SequentialREPL` to include:
- Keyboard handling
- Input editing
- History navigation
- Agent tree expand/collapse (Ctrl+O)
- Background tasks panel (↓ key)

### 5.2 Main Entry Point

**File**: `packages/lyra-cli/src/lyra_cli/repl/__init__.py`

```python
"""Lyra REPL - Sequential output with Claude Code-style UI"""

from .sequential_repl import SequentialREPL
from .terminal_manager import TerminalManager
from .scrollback import ScrollbackBuffer
from .keyboard import KeyboardHandler
from .input_editor import InputEditor

__all__ = [
    "SequentialREPL",
    "TerminalManager",
    "ScrollbackBuffer",
    "KeyboardHandler",
    "InputEditor",
]
```

### 5.3 Update CLI Entry Point

**File**: `packages/lyra-cli/src/lyra_cli/__main__.py`

```python
"""Lyra CLI entry point"""

from .repl import SequentialREPL

def main():
    """Main entry point"""
    repl = SequentialREPL()
    repl.run()

if __name__ == "__main__":
    main()
```

**Deliverables**:
- [ ] Complete SequentialREPL with all features
- [ ] CLI entry point integration
- [ ] Keyboard shortcuts working
- [ ] History navigation working
- [ ] Agent tree expand/collapse working

---

## Phase 6: Testing & Verification (2-3 hours)

### 6.1 Test Suite

Create comprehensive tests:

**File**: `test_sequential_output_complete.py`

```python
#!/usr/bin/env python3
"""Complete test of sequential output REPL"""

import sys
import os
sys.path.insert(0, 'packages/lyra-cli/src')

from lyra_cli.repl import SequentialREPL

def test_welcome_banner():
    """Test welcome banner renders once"""
    print("Testing welcome banner...")
    repl = SequentialREPL()
    repl.show_welcome()
    print("✓ Welcome banner rendered")

def test_streaming_output():
    """Test streaming output pushes bottom UI"""
    print("\nTesting streaming output...")
    repl = SequentialREPL()
    
    # Simulate streaming
    for i in range(10):
        repl.dispatcher.emit("text.delta", {
            "turn_id": "test",
            "text": f"Line {i}\n"
        })
    
    print("✓ Streaming output working")

def test_bottom_ui_always_visible():
    """Test bottom UI stays visible"""
    print("\nTesting bottom UI visibility...")
    repl = SequentialREPL()
    
    # Fill screen with content
    for i in range(100):
        print(f"Content line {i}")
    
    # Render bottom UI
    repl._render_bottom_ui()
    
    print("✓ Bottom UI rendered at bottom")

def test_terminal_resize():
    """Test terminal resize handling"""
    print("\nTesting terminal resize...")
    repl = SequentialREPL()
    
    # Simulate resize
    repl._on_terminal_resize(120, 40)
    
    print(f"✓ Terminal resized to {repl.terminal_width}x{repl.terminal_height}")

if __name__ == "__main__":
    print("=" * 80)
    print("SEQUENTIAL OUTPUT REPL - COMPLETE TEST SUITE")
    print("=" * 80)
    print()
    
    test_welcome_banner()
    test_streaming_output()
    test_bottom_ui_always_visible()
    test_terminal_resize()
    
    print()
    print("=" * 80)
    print("✓ ALL TESTS PASSED")
    print("=" * 80)
```

### 6.2 Manual Testing Checklist

- [ ] Welcome banner shows once at startup
- [ ] Streaming content pushes bottom UI down
- [ ] Bottom UI always visible (4 lines at bottom)
- [ ] Input box accepts text
- [ ] Status line shows mode and hints
- [ ] ↑↓ arrows navigate history
- [ ] Ctrl+O expands/collapses agent tree
- [ ] ↓ key opens background tasks
- [ ] Terminal resize updates layout
- [ ] Long content scrolls properly
- [ ] No flicker during streaming

**Deliverables**:
- [ ] Complete test suite
- [ ] Manual testing checklist
- [ ] All tests passing
- [ ] Documentation updated

---

## Success Criteria

### Visual Parity with Claude Code
- [x] Welcome banner matches layout
- [ ] Streaming responses push bottom UI down
- [ ] Bottom UI always visible (never scrolls away)
- [ ] Response symbols match (⏺ ✻ ✶ ⎿ ❯)
- [ ] Agent tree rendering matches
- [ ] Status line matches

### Functional Requirements
- [ ] Sequential output (not TUI framework)
- [ ] Content grows downward
- [ ] Bottom UI re-rendered after each line
- [ ] Terminal resize handled
- [ ] Keyboard shortcuts work
- [ ] History navigation works
- [ ] No flicker during streaming

### Performance
- [ ] < 16ms per line render
- [ ] < 50ms bottom UI re-render
- [ ] Smooth scrolling
- [ ] No memory leaks

---

## Implementation Timeline

**Total Estimated Time**: 16-23 hours (2-3 days)

- **Phase 1**: Sequential REPL Core (4-6 hours)
- **Phase 2**: Terminal Management (2-3 hours)
- **Phase 3**: Scrollback Buffer (2-3 hours)
- **Phase 4**: Keyboard Input (3-4 hours)
- **Phase 5**: Integration & Polish (3-4 hours)
- **Phase 6**: Testing & Verification (2-3 hours)

---

## Key Technical Decisions

### Why Sequential Output (Not TUI Framework)?

**TUI frameworks** (Textual, Rich, urwid):
- Use absolute positioning
- Require full screen management
- Complex layout engines
- Harder to integrate with streaming

**Sequential output**:
- Natural terminal behavior
- Content grows downward
- Simple ANSI escape codes
- Easy to integrate with streaming
- Matches Claude Code's approach

### Bottom UI Rendering Strategy

**Approach**: Re-render after each content line

```python
def print_content_line(line: str):
    # 1. Print content line
    print(line)
    
    # 2. Save cursor position
    print("\033[s", end="")
    
    # 3. Move to bottom - 4 lines
    print(f"\033[{terminal_height - 3};1H", end="")
    
    # 4. Render bottom UI (4 lines)
    render_bottom_ui()
    
    # 5. Restore cursor position
    print("\033[u", end="", flush=True)
```

This ensures bottom UI is ALWAYS at the bottom, even as content streams.

---

## Next Steps

1. **Review this plan** with user
2. **Get approval** to proceed
3. **Start Phase 1** - Sequential REPL Core
4. **Implement phases** sequentially
5. **Test after each phase**
6. **Push to main** after verification

---

**Ready to start implementation?** 🚀
