# Lyra Keybindings V2

**Version**: 2.0  
**Date**: 2026-05-29  
**Status**: Design Proposal

## Overview

This document defines 20+ productive keybindings for Lyra's terminal interface, inspired by Hermes Agent and Textual framework best practices. Keybindings are organized by category and designed for both keyboard-first and mouse-friendly workflows.

## Design Principles

1. **Consistency**: Use standard terminal conventions (Ctrl+C, Ctrl+D, etc.)
2. **Discoverability**: Show keybindings in footer and help overlay
3. **Muscle memory**: Align with popular tools (vim, emacs, tmux)
4. **Accessibility**: Provide mouse alternatives for all actions
5. **Context-aware**: Different bindings for different modes

## Keybinding Categories

### 1. Session Management (6 bindings)

| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+X` | Switch Session | Open live session switcher with ↑/↓ navigation |
| `Ctrl+N` | New Session | Create new session with optional model selection |
| `Ctrl+D` | Close Session | Close current session (confirm if unsaved) |
| `Ctrl+R` | Resume Session | Resume last session or select from history |
| `Ctrl+S` | Save Session | Save current session state to disk |
| `Ctrl+L` | List Sessions | Show all sessions with status and metadata |

**Implementation notes**:
- `Ctrl+X` opens modal overlay with session list
- `↑/↓` or `j/k` for navigation, `Enter` to switch
- `Ctrl+D` on highlighted session closes it
- `+new` row at bottom for quick session creation

### 2. Input Enhancement (7 bindings)

| Key | Action | Description |
|-----|--------|-------------|
| `Alt+Enter` | Newline | Insert newline without submitting |
| `Ctrl+J` | Newline (Alt) | Alternative newline binding |
| `Shift+Enter` | Newline (Alt 2) | Terminal-dependent newline |
| `Ctrl+G` | Open Editor | Open input buffer in `$EDITOR` |
| `Ctrl+X Ctrl+E` | Open Editor (Alt) | Emacs-style editor binding |
| `Cmd+V` / `Ctrl+V` | Smart Paste | Paste text with image detection |
| `Alt+V` | Paste Image | Force image paste (terminal-dependent) |

**Implementation notes**:
- Backslash continuation: end line with `\` for implicit newline
- Editor opens with current buffer content
- Smart paste shows preview: `[pasted: 47 lines, 1,842 chars]`
- Image paste requires terminal with image protocol support

### 3. Execution Control (5 bindings)

| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+C` | Interrupt | Interrupt current operation (double-press to force exit) |
| `Ctrl+Z` | Pause | Pause current operation (resume with `fg`) |
| `Ctrl+\` | Force Stop | Force stop with SIGKILL (emergency only) |
| `Ctrl+B` | Background | Move current task to background |
| `Ctrl+P` | Priority | Adjust task priority (high/normal/low) |

**Implementation notes**:
- `Ctrl+C` sends SIGTERM, waits 1s, then SIGKILL
- Double `Ctrl+C` within 2s forces immediate exit
- Background tasks show `▶ N` indicator in status bar
- Priority affects model routing (high→opus, normal→sonnet, low→haiku)

### 4. Navigation & Search (6 bindings)

| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+F` | Search | Search in current session transcript |
| `Ctrl+H` | History | Show command/prompt history |
| `Ctrl+Up` | Previous Prompt | Navigate to previous prompt |
| `Ctrl+Down` | Next Prompt | Navigate to next prompt |
| `Ctrl+Home` | First Message | Jump to first message in session |
| `Ctrl+End` | Last Message | Jump to last message in session |

**Implementation notes**:
- Search highlights matches and allows `n/N` for next/previous
- History shows last 50 prompts with fuzzy search
- Prompt navigation preserves scroll position

### 5. View & Display (8 bindings)

| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+T` | Toggle Theme | Cycle through available themes |
| `Ctrl+K` | Toggle Thinking | Show/hide thinking process |
| `Ctrl+O` | Toggle Tools | Show/hide tool execution details |
| `Ctrl+A` | Toggle Activity | Show/hide activity panel |
| `Ctrl+M` | Toggle Markdown | Raw markdown vs rendered view |
| `Ctrl+W` | Toggle Wrap | Enable/disable text wrapping |
| `Ctrl++` | Zoom In | Increase font size |
| `Ctrl+-` | Zoom Out | Decrease font size |

**Implementation notes**:
- Toggles persist across sessions
- Theme cycling shows preview before applying
- Zoom affects entire terminal (if supported)

### 6. Slash Commands (Quick Access)

| Key | Action | Equivalent Slash Command |
|-----|--------|--------------------------|
| `Alt+M` | Model Picker | `/model` |
| `Alt+S` | Skills Browser | `/skills browse` |
| `Alt+T` | Tools List | `/tools` |
| `Alt+H` | Help Overlay | `/help` |
| `Alt+B` | Background Task | `/background` |
| `Alt+R` | Reasoning Level | `/reasoning` |

**Implementation notes**:
- Opens modal overlay with autocomplete
- `Esc` to cancel, `Enter` to execute
- Shows recent commands for quick access

### 7. Advanced Features (5 bindings)

| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+Y` | Yank Output | Copy last agent response to clipboard |
| `Ctrl+U` | Undo | Undo last message (if not yet processed) |
| `Ctrl+I` | Inspect | Inspect current session state (debug mode) |
| `Ctrl+Q` | Quick Command | Execute user-defined quick command |
| `F1-F12` | Custom Actions | User-configurable function keys |

**Implementation notes**:
- Yank copies markdown-stripped text
- Undo only works before agent processes message
- Inspect shows JSON state, token usage, model info
- Quick commands defined in `~/.lyra/config.yaml`

## Context-Aware Bindings

### Modal Overlay (Session Switcher, Model Picker, etc.)

| Key | Action |
|-----|--------|
| `↑` / `k` | Move up |
| `↓` / `j` | Move down |
| `Enter` | Select |
| `Esc` | Cancel |
| `Tab` | Next section |
| `Shift+Tab` | Previous section |
| `/` | Filter/search |

### Editor Mode (Multiline Input)

| Key | Action |
|-----|--------|
| `Ctrl+Enter` | Submit |
| `Esc` | Cancel |
| `Ctrl+K` | Delete to end of line |
| `Ctrl+U` | Delete to start of line |
| `Ctrl+W` | Delete word backward |

### Search Mode

| Key | Action |
|-----|--------|
| `n` | Next match |
| `N` | Previous match |
| `Esc` | Exit search |
| `Enter` | Jump to match |

## Mouse Support

### Click Actions

- **Single click**: Focus input, select text
- **Double click**: Select word
- **Triple click**: Select line
- **Click + drag**: Select text range
- **Right click**: Context menu (copy, paste, search)

### Scroll Actions

- **Scroll wheel**: Scroll transcript
- **Shift + scroll**: Horizontal scroll (if wrapped)
- **Ctrl + scroll**: Zoom in/out

### Status Bar Clicks

- **Model name**: Open model picker
- **Token usage**: Show detailed token breakdown
- **Progress bar**: Show context usage details
- **Cost**: Show cost breakdown by model/operation
- **Duration**: Show timing breakdown

## Configuration

### User Configuration (~/.lyra/config.yaml)

```yaml
keybindings:
  # Override default bindings
  session_switcher: "ctrl+x"
  new_session: "ctrl+n"
  interrupt: "ctrl+c"
  
  # Custom quick commands
  quick_commands:
    f1: "/help"
    f2: "/model"
    f3: "/skills browse"
    f4: "/tools"
    ctrl+q: "status"  # User-defined command
  
  # Disable specific bindings
  disabled:
    - "ctrl+z"  # Don't pause (conflicts with shell)
  
  # Mouse support
  mouse:
    enabled: true
    tracking: "buttons"  # wheel | buttons | all
    drag_to_select: true

  # Vim-style navigation
  vim_mode: false  # Enable j/k navigation everywhere
```

### Runtime Keybinding Help

```bash
# Show all keybindings
lyra keybindings

# Show keybindings for specific category
lyra keybindings --category session

# Interactive keybinding customizer
lyra keybindings --customize
```

## Implementation Guide

### Textual Framework Integration

```python
from textual.app import App
from textual.binding import Binding

class LyraApp(App):
    BINDINGS = [
        # Session management
        Binding("ctrl+x", "switch_session", "Switch Session", show=True),
        Binding("ctrl+n", "new_session", "New Session", show=True),
        Binding("ctrl+d", "close_session", "Close Session", show=True),
        
        # Input enhancement
        Binding("alt+enter", "newline", "Newline", show=False),
        Binding("ctrl+g", "open_editor", "Open Editor", show=True),
        Binding("ctrl+v", "smart_paste", "Paste", show=False),
        
        # Execution control
        Binding("ctrl+c", "interrupt", "Interrupt", show=True),
        Binding("ctrl+b", "background", "Background", show=True),
        
        # Navigation
        Binding("ctrl+f", "search", "Search", show=True),
        Binding("ctrl+h", "history", "History", show=True),
        
        # View toggles
        Binding("ctrl+t", "toggle_theme", "Theme", show=True),
        Binding("ctrl+k", "toggle_thinking", "Thinking", show=True),
        Binding("ctrl+o", "toggle_tools", "Tools", show=True),
        
        # Advanced
        Binding("ctrl+y", "yank_output", "Yank", show=True),
        Binding("ctrl+i", "inspect", "Inspect", show=False),
    ]
    
    def action_switch_session(self):
        """Open session switcher modal"""
        self.push_screen(SessionSwitcherModal())
    
    def action_new_session(self):
        """Create new session"""
        self.create_session()
    
    def action_interrupt(self):
        """Interrupt current operation"""
        self.interrupt_current_task()
    
    # ... implement other actions
```

### Footer Display

```python
from textual.widgets import Footer

class LyraFooter(Footer):
    """Custom footer showing context-aware keybindings"""
    
    def compose(self):
        # Show most relevant bindings based on current mode
        if self.app.mode == "input":
            bindings = ["ctrl+x Switch", "ctrl+n New", "ctrl+g Editor"]
        elif self.app.mode == "modal":
            bindings = ["↑↓ Navigate", "enter Select", "esc Cancel"]
        elif self.app.mode == "search":
            bindings = ["n Next", "N Prev", "esc Exit"]
        else:
            bindings = ["ctrl+x Switch", "ctrl+f Search", "ctrl+h Help"]
        
        yield Footer(bindings)
```

### Help Overlay

```python
from textual.screen import ModalScreen
from textual.widgets import Static

class HelpOverlay(ModalScreen):
    """Full-screen help overlay with all keybindings"""
    
    def compose(self):
        yield Static("""
        # Lyra Keybindings
        
        ## Session Management
        Ctrl+X    Switch Session
        Ctrl+N    New Session
        Ctrl+D    Close Session
        
        ## Input Enhancement
        Alt+Enter Newline
        Ctrl+G    Open Editor
        Ctrl+V    Smart Paste
        
        ## Execution Control
        Ctrl+C    Interrupt
        Ctrl+B    Background
        
        ## Navigation
        Ctrl+F    Search
        Ctrl+H    History
        
        ## View & Display
        Ctrl+T    Toggle Theme
        Ctrl+K    Toggle Thinking
        Ctrl+O    Toggle Tools
        
        Press Esc to close
        """)
```

## Accessibility Considerations

### Keyboard-Only Navigation

- All features accessible via keyboard
- Tab order follows logical flow
- Focus indicators clearly visible
- Skip links for long content

### Screen Reader Support

- ARIA labels for all interactive elements
- Announce state changes (theme switched, session created)
- Describe visual indicators (progress bar, status)

### Customization

- Allow remapping all keybindings
- Support alternative input methods
- Provide text-based alternatives to visual indicators

## Testing Checklist

- [ ] All keybindings work in iTerm2, Terminal.app, Alacritty
- [ ] No conflicts with terminal emulator shortcuts
- [ ] Context-aware bindings switch correctly
- [ ] Mouse support works with all actions
- [ ] Help overlay shows all bindings
- [ ] Footer updates based on mode
- [ ] Custom bindings load from config
- [ ] Disabled bindings don't trigger
- [ ] Vim mode works correctly (if enabled)
- [ ] Screen reader announces actions

## Comparison with Other Tools

### Hermes Agent
- ✓ Session switcher (`Ctrl+X`)
- ✓ Editor integration (`Ctrl+G`)
- ✓ Smart paste with preview
- ✓ Interrupt model (double `Ctrl+C`)

### Textual Framework
- ✓ Standard bindings (Ctrl+C, Ctrl+D)
- ✓ Modal navigation (↑↓, Enter, Esc)
- ✓ Footer display
- ✓ Context-aware bindings

### tmux/screen
- ✓ Session management metaphor
- ✓ Background tasks
- ✗ No prefix key (direct bindings)

### vim/emacs
- ✓ Optional vim mode (j/k navigation)
- ✓ Emacs-style editor binding (`Ctrl+X Ctrl+E`)
- ✗ Not modal by default (simpler for beginners)

## Future Enhancements

1. **Chord bindings** - Multi-key sequences (e.g., `Ctrl+X Ctrl+S`)
2. **Leader key** - tmux-style prefix key for advanced commands
3. **Macro recording** - Record and replay key sequences
4. **Gesture support** - Touchpad gestures for navigation
5. **Voice commands** - Speak keybinding names
6. **Learning mode** - Show keybinding hints for new users
7. **Conflict detection** - Warn about terminal emulator conflicts
8. **Profile switching** - Different keybinding sets for different workflows

---

**Design by**: Document Specialist Agent  
**Date**: 2026-05-29  
**Status**: Ready for implementation
