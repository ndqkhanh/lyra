# UI/UX & Interaction Research for Lyra
## Comprehensive Analysis of Terminal UI, Theming, Voice Systems & Interaction Patterns

**Research Date:** 2026-05-29  
**Researcher:** Senior UX Architect & Interaction Designer  
**Target:** Lyra AI Coding Agent Enhancement

---

## Executive Summary

This research synthesizes breakthrough UX patterns from leading AI coding agents (Claude Code, Hermes Agent, Warp), terminal multiplexers (tmux, cmux, rmux, AlphaClaw), and accessibility standards to create a delightful, productive developer experience for Lyra.

### Key Findings

1. **Modal Interaction is King**: Vim-style modal editing dramatically improves productivity in terminal UIs
2. **Notification Architecture Matters**: Visual + audio feedback systems prevent context-switching overhead
3. **Session Persistence is Critical**: Developers expect workspace state to survive disconnections
4. **Hooks Enable Extensibility**: Lifecycle hooks (PreToolUse, PostToolUse, Stop) unlock powerful automation
5. **Accessibility is Non-Negotiable**: Modern TUIs must explicitly support screen readers and keyboard navigation
6. **Color Themes Drive Adoption**: Beautiful, accessible themes with dark/light modes are table stakes
7. **Streaming Output UX**: Progress indicators and collapsible output reduce user anxiety

---

## 1. UI/UX Patterns Catalog

### 1.1 Terminal UI Best Practices

#### Information Density & Layout

**Three-Tier Hierarchy** (from cmux):
- **Workspaces**: Top-level organization (⌘1-8 navigation)
- **Surfaces/Tabs**: Within workspaces (⌃1-8 navigation)
- **Split Panes**: Within surfaces (⌥⌘ arrows for directional focus)

**Status Bar Design** (from tmux/cmux):
- Git branch and PR status with color-coded review state
- Working directory breadcrumb
- Listening ports
- Latest notification text
- Task list toggle (Ctrl+T in Claude Code)

**Sidebar Metadata** (from cmux):
- Per-surface metadata cards
- Visual notification indicators (blue rings for waiting panes)
- Centralized notification panel (⌘I)
- Jump to latest unread (⌘⇧U)

#### Progress Indicators & Status Displays

**Collapsible Output Pattern** (from Claude Code):
```
✓ Task completed successfully
✗ Task failed with error
⏸ Awaiting user approval
⏳ Running in background (task ID: abc123)
```

**Streaming Output Best Practices**:
- Buffer lines and print on EOF for clean output
- Stream immediately for real-time feedback
- Clear animation lines before live prints to avoid artifacts
- Use descriptive titles with spinners during execution

**Indeterminate Progress** (when duration unknown):
- Spinning wheels communicate "system is alive"
- Better than silence even without ETA
- Reduces user anxiety and premature termination

#### Error Presentation & Recovery Flows

**Error Display Hierarchy**:
1. **Inline errors**: Show at point of failure with context
2. **Status bar alerts**: Persistent indicators for background failures
3. **Detailed logs**: Accessible via transcript viewer (Ctrl+O)

**Recovery Patterns**:
- Interrupt mid-turn with Esc to redirect
- Rewind menu (double Esc) to restore previous states
- Background task management (Ctrl+B to background, Ctrl+X Ctrl+K to kill all)

#### Multi-Pane Layouts & Workspace Management

**Split Management** (from cmux):
- ⌘D split right, ⌘⇧D split down
- Directional pane focus without tmux dependency
- ⌘⇧H flashes focused panel for orientation

**Session Persistence** (from cmux/rmux):
- Save on quit, restore on launch
- Window/workspace/pane layout preserved
- Working directories maintained
- Terminal scrollback (best effort)
- Browser URL and navigation history

#### Real-Time Streaming Output Patterns

**Transcript Viewer** (from Claude Code):
- Toggle with Ctrl+O for detailed tool usage
- Expands MCP calls (collapsed to "Called slack 3 times" by default)
- Keyboard shortcuts: `{` / `}` jump between prompts
- `[` writes conversation to native scrollback for Cmd+F search
- `v` opens in $VISUAL/$EDITOR

### 1.2 Interactive Features

#### Auto-Completion & Suggestions

**Prompt Suggestions** (from Claude Code):
- Grayed-out example commands on session start
- Context-aware follow-up suggestions after responses
- Press Tab or Right arrow to accept
- Reuses prompt cache for minimal cost
- Skipped in plan mode and after first turn

**History-Based Autocomplete**:
- Shell mode (`!` prefix) supports Tab completion from previous commands
- Reverse search with Ctrl+R for interactive history navigation
- Scope cycling: this session → this project → all projects (Ctrl+S)

#### Fuzzy Search & Filtering

**Command Palette** (from Claude Code):
- Type `/` to see all commands
- Filter by typing letters after `/`
- Shows built-in commands, skills, plugins, and MCP prompts

**Search Patterns**:
- Ctrl+R for reverse history search with highlighted matches
- Tab to accept and continue editing
- Enter to accept and execute immediately
- Ctrl+C to cancel and restore original input

#### Context Menus & Quick Actions

**Quick Commands**:
- `/` at start: Command or skill
- `!` at start: Shell mode (direct command execution)
- `@` anywhere: File path mention with autocomplete

**Side Questions** (`/btw`):
- Ask quick questions without cluttering history
- Full visibility into current conversation
- No tool access (answers from context only)
- Dismissible overlay with fork option (`f` key)

#### Inline Documentation & Help

**Contextual Help**:
- `?` in transcript viewer shows keyboard shortcuts (fullscreen mode)
- `/help` command for general assistance
- Hover/tooltip patterns for complex UI elements

#### Session History & Replay

**Command History** (from Claude Code):
- Per-directory input history
- Resets on `/clear` but preserves previous session for resume
- Deduplicates consecutive identical prompts
- Up/Down arrows for navigation

**Session Recap**:
- One-line recap after 3+ minutes away from terminal
- Generates in background when terminal unfocused
- Only appears after 3+ turns, never twice in a row
- `/recap` for on-demand summary

---

## 2. Color Theme Library

### 2.1 Theme Collections

#### Large Theme Repositories

1. **[Gogh](https://github.com/Gogh-Co/Gogh)**: Color schemes for Gnome Terminal, Pantheon Terminal, Tilix, XFCE4 Terminal, iTerm
2. **[Terminal-Color-Schemes](https://github.com/ei9h7/Terminal-Color-Schemes)**: 230+ themes for iTerm/iTerm2, Terminal, Konsole, PuTTY, Kitty, Alacritty, Windows Terminal
3. **[macOS Terminal Themes](https://github.com/lysyi3m/macos-terminal-themes)**: Focused on default macOS Terminal.app

#### Popular Dual-Mode Themes

**Solarized** ([altercation/solarized](https://github.com/altercation/solarized)):
- Precision color scheme with dark/light modes
- Carefully balanced for readability
- Widely adopted across terminals and editors

**Ayu** ([ayu-theme](https://github.com/ayu-theme)):
- Modern theme family
- Available across multiple platforms
- Clean, minimal aesthetic

### 2.2 Recommended Themes for Lyra

#### Theme 1: Solarized Dark
```
Background: #002b36
Foreground: #839496
Black:      #073642
Red:        #dc322f
Green:      #859900
Yellow:     #b58900
Blue:       #268bd2
Magenta:    #d33682
Cyan:       #2aa198
White:      #eee8d5
```
**Use Case**: Default dark theme, excellent readability, proven accessibility

#### Theme 2: Solarized Light
```
Background: #fdf6e3
Foreground: #657b83
Black:      #073642
Red:        #dc322f
Green:      #859900
Yellow:     #b58900
Blue:       #268bd2
Magenta:    #d33682
Cyan:       #2aa198
White:      #eee8d5
```
**Use Case**: Bright environments, daylight coding

#### Theme 3: Ayu Dark
```
Background: #0f1419
Foreground: #e6e1cf
Black:      #000000
Red:        #f07178
Green:      #c2d94c
Yellow:     #ffb454
Blue:       #59c2ff
Magenta:    #d2a6ff
Cyan:       #95e6cb
White:      #ffffff
```
**Use Case**: Modern aesthetic, vibrant colors

#### Theme 4: Ayu Light
```
Background: #fafafa
Foreground: #5c6166
Black:      #000000
Red:        #f07178
Green:      #86b300
Yellow:     #f2ae49
Blue:       #399ee6
Magenta:    #a37acc
Cyan:       #4cbf99
White:      #ffffff
```
**Use Case**: Clean light mode, minimal eye strain

#### Theme 5: Dracula
```
Background: #282a36
Foreground: #f8f8f2
Black:      #21222c
Red:        #ff5555
Green:      #50fa7b
Yellow:     #f1fa8c
Blue:       #bd93f9
Magenta:    #ff79c6
Cyan:       #8be9fd
White:      #f8f8f2
```
**Use Case**: High contrast, popular among developers

#### Theme 6: Nord
```
Background: #2e3440
Foreground: #d8dee9
Black:      #3b4252
Red:        #bf616a
Green:      #a3be8c
Yellow:     #ebcb8b
Blue:       #81a1c1
Magenta:    #b48ead
Cyan:       #88c0d0
White:      #e5e9f0
```
**Use Case**: Arctic-inspired, low contrast, easy on eyes

#### Theme 7: Gruvbox Dark
```
Background: #282828
Foreground: #ebdbb2
Black:      #282828
Red:        #cc241d
Green:      #98971a
Yellow:     #d79921
Blue:       #458588
Magenta:    #b16286
Cyan:       #689d6a
White:      #a89984
```
**Use Case**: Retro, warm colors, excellent for long sessions

#### Theme 8: Gruvbox Light
```
Background: #fbf1c7
Foreground: #3c3836
Black:      #fbf1c7
Red:        #cc241d
Green:      #98971a
Yellow:     #d79921
Blue:       #458588
Magenta:    #b16286
Cyan:       #689d6a
White:      #7c6f64
```
**Use Case**: Warm light mode alternative

#### Theme 9: One Dark
```
Background: #282c34
Foreground: #abb2bf
Black:      #282c34
Red:        #e06c75
Green:      #98c379
Yellow:     #e5c07b
Blue:       #61afef
Magenta:    #c678dd
Cyan:       #56b6c2
White:      #abb2bf
```
**Use Case**: Atom-inspired, balanced contrast

#### Theme 10: Tokyo Night
```
Background: #1a1b26
Foreground: #c0caf5
Black:      #15161e
Red:        #f7768e
Green:      #9ece6a
Yellow:     #e0af68
Blue:       #7aa2f7
Magenta:    #bb9af7
Cyan:       #7dcfff
White:      #a9b1d6
```
**Use Case**: Modern, vibrant, night-optimized

### 2.3 Semantic Color Usage

**Success States**: Green tones (#859900, #98c379, #50fa7b)
**Warning States**: Yellow/Orange tones (#b58900, #e5c07b, #f1fa8c)
**Error States**: Red tones (#dc322f, #e06c75, #ff5555)
**Info States**: Blue tones (#268bd2, #61afef, #7aa2f7)

**PR Review Status Colors** (from Claude Code):
- Green underline: Approved
- Yellow underline: Pending review
- Red underline: Changes requested
- Gray underline: Draft

### 2.4 Theme Switching Mechanisms

**Configuration Approaches**:
1. **Runtime switching**: `/theme` command with live preview
2. **Config file**: `~/.lyra/config.toml` with `theme = "solarized-dark"`
3. **Environment variable**: `LYRA_THEME=nord lyra`
4. **Auto-detection**: Match terminal theme if possible

**User Customization**:
- Override individual colors in config
- Custom theme definitions in `~/.lyra/themes/`
- Import from popular formats (iTerm2, Alacritty, etc.)

---

## 3. Keybindings Reference

### 3.1 Essential Keybindings for Productivity

#### General Controls

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl+C` | Interrupt or clear input | First press clears, second exits |
| `Ctrl+D` | Exit session | EOF signal |
| `Ctrl+L` | Redraw screen | Recovery from garbled display |
| `Ctrl+O` | Toggle transcript viewer | Detailed tool usage |
| `Ctrl+R` | Reverse search history | Interactive search |
| `Ctrl+T` | Toggle task list | Show/hide tasks |
| `Esc` | Interrupt Claude | Stop mid-turn |
| `Esc Esc` | Clear input or rewind | Double-tap for rewind menu |

#### Text Editing (Emacs-style)

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl+A` | Move to start of line | Current logical line |
| `Ctrl+E` | Move to end of line | Current logical line |
| `Ctrl+K` | Delete to end of line | Stores for paste |
| `Ctrl+U` | Delete to line start | Stores for paste |
| `Ctrl+W` | Delete previous word | Stores for paste |
| `Ctrl+Y` | Paste deleted text | Yank |
| `Alt+Y` | Cycle paste history | After Ctrl+Y |
| `Alt+B` | Move back one word | Word navigation |
| `Alt+F` | Move forward one word | Word navigation |

#### Multiline Input

| Method | Shortcut | Context |
|--------|----------|---------|
| Quick escape | `\` + `Enter` | Works in all terminals |
| Option key | `Option+Enter` | macOS with Option as Meta |
| Shift+Enter | `Shift+Enter` | iTerm2, WezTerm, Ghostty, Kitty, Warp |
| Control sequence | `Ctrl+J` | Universal |
| Paste mode | Paste directly | For code blocks |

#### Model & Mode Switching

| Shortcut | Action | Context |
|----------|--------|---------|
| `Alt+P` | Switch model | Without clearing prompt |
| `Alt+T` | Toggle extended thinking | Enable/disable |
| `Alt+O` | Toggle fast mode | Enable/disable |
| `Shift+Tab` or `Alt+M` | Cycle permission modes | default → acceptEdits → plan → auto |

### 3.2 Vim Modal Editing

#### Mode Switching

| Command | Action | From Mode |
|---------|--------|-----------|
| `Esc` | Enter NORMAL mode | INSERT, VISUAL |
| `i` | Insert before cursor | NORMAL |
| `I` | Insert at beginning of line | NORMAL |
| `a` | Insert after cursor | NORMAL |
| `A` | Insert at end of line | NORMAL |
| `o` | Open line below | NORMAL |
| `O` | Open line above | NORMAL |
| `v` | Character-wise visual | NORMAL |
| `V` | Line-wise visual | NORMAL |

#### Navigation (NORMAL mode)

| Command | Action |
|---------|--------|
| `h`/`j`/`k`/`l` | Move left/down/up/right |
| `w` | Next word |
| `e` | End of word |
| `b` | Previous word |
| `0` | Beginning of line |
| `$` | End of line |
| `^` | First non-blank character |
| `gg` | Beginning of input |
| `G` | End of input |
| `f{char}` | Jump to next occurrence |
| `F{char}` | Jump to previous occurrence |
| `;` | Repeat last f/F/t/T |
| `/` | Reverse history search |

#### Editing (NORMAL mode)

| Command | Action |
|---------|--------|
| `x` | Delete character |
| `dd` | Delete line |
| `D` | Delete to end of line |
| `dw`/`de`/`db` | Delete word/to end/back |
| `cc` | Change line |
| `C` | Change to end of line |
| `cw`/`ce`/`cb` | Change word/to end/back |
| `yy`/`Y` | Yank (copy) line |
| `yw`/`ye`/`yb` | Yank word/to end/back |
| `p` | Paste after cursor |
| `P` | Paste before cursor |
| `u` | Undo |
| `.` | Repeat last change |

#### Text Objects

| Command | Action |
|---------|--------|
| `iw`/`aw` | Inner/around word |
| `iW`/`aW` | Inner/around WORD |
| `i"`/`a"` | Inner/around double quotes |
| `i'`/`a'` | Inner/around single quotes |
| `i(`/`a(` | Inner/around parentheses |
| `i[`/`a[` | Inner/around brackets |
| `i{`/`a{` | Inner/around braces |

### 3.3 Custom Keybinding Configuration

**Configuration File**: `~/.lyra/keybindings.json`

```json
{
  "keybindings": [
    {
      "key": "ctrl+shift+p",
      "command": "commandPalette"
    },
    {
      "key": "ctrl+`",
      "command": "toggleTerminal"
    }
  ]
}
```

---

## 4. Voice System Design

### 4.1 Audio Feedback Architecture

#### Hook-Based Voice Integration

**Implementation Pattern** (from Claude Code hooks):

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "afplay ~/.lyra/sounds/session-start.mp3 &"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "afplay ~/.lyra/sounds/task-complete.mp3 &"
      }]
    }]
  }
}
```

**Critical Design Note**: The trailing `&` runs audio in background to avoid blocking execution.

#### Cross-Platform Audio Players

| Platform | Command | Notes |
|----------|---------|-------|
| macOS | `afplay` | Built-in, no dependencies |
| Linux | `aplay` or `paplay` | ALSA or PulseAudio |
| Windows WSL | `powershell.exe -c (New-Object Media.SoundPlayer "path").PlaySync()` | Requires PowerShell |

### 4.2 Voice Notification Events

**Session Lifecycle**:
- `SessionStart`: Welcome sound when session begins
- `SessionEnd`: Farewell sound when session closes
- `SessionResume`: Notification when resuming saved session

**Task Events**:
- `TaskComplete`: Success sound when task finishes
- `TaskFailed`: Error sound when task fails
- `TaskWaiting`: Attention sound when user input needed

**Background Events**:
- `BackgroundTaskComplete`: Notification for background task completion
- `BackgroundTaskFailed`: Alert for background task failure

### 4.3 Text-to-Speech Integration

**Voice Customization Options**:
- Voice selection (male/female, accent)
- Speech rate (words per minute)
- Pitch adjustment
- Volume control

**TTS Engines**:
- **macOS**: `say` command with built-in voices
- **Linux**: `espeak` or `festival`
- **Windows**: SAPI voices via PowerShell

**Example Configuration**:
```json
{
  "voice": {
    "enabled": true,
    "engine": "say",
    "voice": "Samantha",
    "rate": 200,
    "events": ["TaskComplete", "TaskFailed", "TaskWaiting"]
  }
}
```

### 4.4 Audio Accessibility Features

**Screen Reader Compatibility**:
- ARIA labels for UI elements
- Semantic HTML structure
- Keyboard-navigable interfaces

**Audio Cues for Status**:
- Different tones for success/warning/error
- Spatial audio for multi-pane layouts
- Volume normalization across sounds

**User Control**:
- Global mute toggle
- Per-event volume control
- Custom sound file uploads

---

## 5. Terminal Multiplexer Integration

### 5.1 tmux Patterns

**Session Management**:
```bash
# Create named session
tmux new-session -s lyra-work

# Detach and reattach
tmux detach
tmux attach -t lyra-work

# List sessions
tmux list-sessions
```

**Window & Pane Management**:
```bash
# Split panes
Ctrl+b %    # Split vertically
Ctrl+b "    # Split horizontally

# Navigate panes
Ctrl+b arrow keys

# Resize panes
Ctrl+b Ctrl+arrow keys
```

**Status Bar Customization**:
```bash
# ~/.tmux.conf
set -g status-style 'bg=#1a1b26 fg=#c0caf5'
set -g status-left '#[fg=#7aa2f7]#S '
set -g status-right '#[fg=#9ece6a]%H:%M '
```

### 5.2 cmux Patterns

**Workspace Organization**:
- ⌘1-8: Switch workspaces
- ⌃1-8: Switch tabs within workspace
- ⌥⌘ arrows: Navigate panes

**Notification System**:
```bash
# Trigger notification from script
cmux notify "Build complete"

# Check notification panel
⌘I
```

**Agent Resume Integration**:
```bash
# Setup hooks
cmux hooks setup

# Configure resume binding
cmux surface resume set --kind lyra --checkpoint work --shell "lyra resume work"
```

### 5.3 rmux Patterns

**Programmatic Control via SDK**:
```rust
use rmux_sdk::Client;

let client = Client::connect().await?;
let session = client.create_session("lyra-dev").await?;
let pane = session.create_pane().await?;

pane.send_text("lyra start\n").await?;
pane.wait_for_text("Ready").await?;
```

### 5.4 AlphaClaw Patterns

**Multi-Agent Dashboard**:
- Sidebar navigation with per-agent cards
- Live terminal for gateway monitoring
- File explorer with inline edits
- Usage tracking with cost breakdowns

**Self-Healing Watchdog**:
- Crash detection and auto-repair
- Event log with interactive terminal
- Notification via Telegram/Discord/Slack

---

## 6. Accessibility Guidelines

### 6.1 WCAG Compliance for Terminal UIs

#### Principle 1: Perceivable

**Color Contrast** (WCAG 2.1 Level AA):
- Normal text: 4.5:1 contrast ratio minimum
- Large text (18pt+): 3:1 contrast ratio minimum
- UI components: 3:1 contrast ratio minimum

**Text Alternatives**:
- Provide text descriptions for visual indicators
- Use semantic labels for status icons (✓, ✗, ⏸)
- Screen reader announcements for state changes

#### Principle 2: Operable

**Keyboard Navigation** (WCAG 2.1.1):
- All functionality accessible via keyboard
- Logical tab order (left-to-right, top-to-bottom)
- No keyboard traps
- Visible focus indicators

**Timing** (WCAG 2.2.1):
- No time limits on user input
- Adjustable timeouts for operations
- Warning before session timeout

#### Principle 3: Understandable

**Readable Text** (WCAG 3.1.1):
- Clear, concise language in prompts and messages
- Consistent terminology throughout interface
- Error messages with actionable guidance

**Predictable Behavior** (WCAG 3.2.1):
- Consistent navigation patterns
- No unexpected context changes
- Clear indication of current state

#### Principle 4: Robust

**Compatibility** (WCAG 4.1.2):
- Works with screen readers (VoiceOver, NVDA, JAWS)
- Semantic markup for assistive technologies
- Graceful degradation in limited terminals

### 6.2 Dark Mode Accessibility

**Avoiding Halation**:
- Don't use pure white (#FFFFFF) on pure black (#000000)
- Prefer slightly off-white (#e6e1cf, #c0caf5) on dark gray (#0f1419, #1a1b26)
- Reduces glowing effect for some readers

**Contrast Testing**:
- Test both light and dark modes separately
- Use tools like WebAIM Contrast Checker
- Verify with actual users who have visual impairments

**Current State** (2026):
- 83.9% of homepages flagged for low contrast (up from 79.1% in 2025)
- Problem is getting worse, not better
- Terminal UIs must explicitly prioritize contrast

### 6.3 Screen Reader Support

**ARIA Labels**:
```html
<div role="status" aria-live="polite">Task completed successfully</div>
<button aria-label="Toggle transcript viewer">Ctrl+O</button>
```

**Semantic Structure**:
- Use proper heading hierarchy
- Mark up lists as `<ul>` or `<ol>`
- Identify regions with landmarks

**Announcements**:
- State changes announced to screen readers
- Progress updates at reasonable intervals
- Error messages immediately announced

---

## 7. Lyra UX Upgrade Plan

### 7.1 Migration from Textual TUI to Streaming CLI

**Current State**:
- Textual-based TUI with heavy dependencies
- ~2s startup time, ~200MB memory usage
- Limited portability (TTY requirements)

**Target State**:
- Claude Code-style streaming CLI
- <500ms startup, <100MB memory
- Works in any terminal, CI/CD friendly

**Migration Strategy** (5 weeks):
1. **Week 1**: Core CLI infrastructure with streaming output
2. **Week 2**: Agent loop refactor with hook system
3. **Week 3**: Multi-agent orchestration (lazy-spawn blueprints)
4. **Week 4**: SSE streaming for web UI (optional)
5. **Week 5**: Cleanup, documentation, polish

### 7.2 Notification System Enhancement

**Visual Indicators** (inspired by cmux):
- Blue rings on panes awaiting input
- Lit tabs in sidebar for active agents
- Status bar with latest notification text
- Centralized notification panel (⌘I)

**Audio Feedback** (via hooks):
- Session start/end sounds
- Task completion notifications
- Error alerts
- Background task completion

**Implementation**:
```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "afplay ~/.lyra/sounds/start.mp3 &"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "afplay ~/.lyra/sounds/complete.mp3 &"
      }]
    }],
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "if": "Bash(rm *)",
        "command": "afplay ~/.lyra/sounds/warning.mp3 &"
      }]
    }]
  }
}
```

### 7.3 Theme System Implementation

**Phase 1: Built-in Themes**
- Ship with 10 themes (Solarized, Dracula, Nord, Gruvbox, Tokyo Night, etc.)
- Runtime switching via `/theme` command
- Config file: `~/.lyra/config.toml`

**Phase 2: Custom Themes**
- User-defined themes in `~/.lyra/themes/`
- Import from iTerm2, Alacritty, Windows Terminal formats
- Theme editor with live preview

**Phase 3: Auto-Detection**
- Detect terminal theme if possible
- Match system dark/light mode preference
- Graceful fallback to default theme

### 7.4 Keybinding Enhancements

**Essential Additions**:
- Vim modal editing (optional, via `/config`)
- Customizable keybindings (`~/.lyra/keybindings.json`)
- Chord sequences for advanced users
- Context-aware bindings (different in plan mode vs normal mode)

**Configuration Example**:
```json
{
  "editorMode": "vim",
  "keybindings": [
    {
      "key": "ctrl+shift+p",
      "command": "commandPalette"
    },
    {
      "key": "ctrl+shift+t",
      "command": "toggleTheme"
    },
    {
      "key": "ctrl+shift+v",
      "command": "toggleVoice"
    }
  ]
}
```

### 7.5 Voice System Integration

**Phase 1: Hook-Based Audio**
- Session lifecycle sounds
- Task completion notifications
- Error alerts
- Platform-specific audio players (afplay, aplay, PowerShell)

**Phase 2: Text-to-Speech**
- Announce task completions
- Read error messages
- Voice selection and customization
- Rate and pitch control

**Phase 3: Voice Input** (future)
- Dictation mode (hold Space to record)
- Voice commands for common operations
- Transcription via Whisper or cloud APIs

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Deliverables**:
- [ ] Streaming CLI with markdown rendering
- [ ] Tool execution display (`[Using ToolName...] done`)
- [ ] Multiline input support
- [ ] Session persistence
- [ ] Basic theme system (3 themes: Solarized Dark/Light, Dracula)

**Success Metrics**:
- Startup time <500ms
- Memory usage <100MB
- All existing tests pass

### Phase 2: Enhanced UX (Weeks 3-4)

**Deliverables**:
- [ ] Transcript viewer (Ctrl+O)
- [ ] Command palette with fuzzy search
- [ ] Prompt suggestions
- [ ] Session recap
- [ ] Side questions (`/btw`)
- [ ] 10 built-in themes
- [ ] Theme switching (`/theme` command)

**Success Metrics**:
- User satisfaction >80%
- Theme adoption >50%
- Reduced support tickets for "how do I..."

### Phase 3: Voice & Accessibility (Weeks 5-6)

**Deliverables**:
- [ ] Hook-based audio feedback
- [ ] Cross-platform audio player detection
- [ ] Voice configuration in settings
- [ ] WCAG 2.1 Level AA compliance
- [ ] Screen reader support
- [ ] Keyboard navigation audit

**Success Metrics**:
- All themes pass contrast checks (4.5:1 for normal text)
- Screen reader compatibility verified
- Audio feedback opt-in rate >30%

### Phase 4: Advanced Features (Weeks 7-8)

**Deliverables**:
- [ ] Vim modal editing (optional)
- [ ] Custom keybindings
- [ ] Theme editor with live preview
- [ ] Text-to-speech integration
- [ ] Multi-pane layouts (inspired by cmux)
- [ ] Notification panel

**Success Metrics**:
- Vim mode adoption >20%
- Custom keybindings usage >15%
- Multi-pane usage >40%

### Phase 5: Polish & Documentation (Week 9)

**Deliverables**:
- [ ] Comprehensive user guide
- [ ] Video tutorials for key features
- [ ] Migration guide from old TUI
- [ ] Accessibility documentation
- [ ] Theme gallery with screenshots
- [ ] Keybinding reference card

**Success Metrics**:
- Documentation completeness >95%
- User onboarding time <10 minutes
- Feature discovery rate >70%

---

## 9. Mockups & Visual Design

### 9.1 Streaming CLI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Lyra v2.0.0 | Model: claude-opus-4.8 | Session: abc123          │
│ Repo: lyra | Branch: main | PR #446 (approved)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ > Implement voice notification system                            │
│                                                                   │
│ I'll implement a hook-based voice notification system...         │
│                                                                   │
│ [Using Read...] done                                             │
│ [Using Edit...] done                                             │
│ [Using Bash...] done                                             │
│                                                                   │
│ ✓ Voice system implemented with cross-platform support          │
│                                                                   │
│ Tasks: [2/5] ⏳ Installing dependencies...                       │
├─────────────────────────────────────────────────────────────────┤
│ > _                                                              │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Transcript Viewer (Ctrl+O)

```
┌─────────────────────────────────────────────────────────────────┐
│ Transcript Viewer | Press ? for help | q to exit                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ ┌─ Turn 1 ─────────────────────────────────────────────────┐   │
│ │ User: Implement voice notification system                 │   │
│ │                                                            │   │
│ │ Assistant: I'll implement...                              │   │
│ │                                                            │   │
│ │ Tool: Read                                                │   │
│ │   file_path: ~/.lyra/config.toml                          │   │
│ │   → Success (234 bytes)                                   │   │
│ │                                                            │   │
│ │ Tool: Edit                                                │   │
│ │   file_path: src/hooks.py                                 │   │
│ │   → Success (12 lines changed)                            │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│ ┌─ Turn 2 ─────────────────────────────────────────────────┐   │
│ │ User: Add tests                                           │   │
│ │ ...                                                        │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3 Theme Picker

```
┌─────────────────────────────────────────────────────────────────┐
│ Theme Picker | Use ↑↓ to navigate, Enter to select             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ ● Solarized Dark        [Preview: ████████████]                 │
│   Solarized Light       [Preview: ░░░░░░░░░░░░]                 │
│   Dracula               [Preview: ████████████]                 │
│   Nord                  [Preview: ████████████]                 │
│   Gruvbox Dark          [Preview: ████████████]                 │
│   Gruvbox Light         [Preview: ░░░░░░░░░░░░]                 │
│   Tokyo Night           [Preview: ████████████]                 │
│   One Dark              [Preview: ████████████]                 │
│   Ayu Dark              [Preview: ████████████]                 │
│   Ayu Light             [Preview: ░░░░░░░░░░░░]                 │
│                                                                   │
│ [Tab] Preview | [Enter] Select | [Esc] Cancel                   │
└─────────────────────────────────────────────────────────────────┘
```

### 9.4 Notification Panel (⌘I)

```
┌─────────────────────────────────────────────────────────────────┐
│ Notifications | ⌘⇧U Jump to latest unread                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ ● [23:45] researcher#1: Found 12 relevant papers                │
│ ● [23:46] coder#2: Implementation complete, tests passing       │
│   [23:47] writer#3: Draft report ready for review               │
│   [23:48] reviewer#4: Approved with minor suggestions           │
│                                                                   │
│ [Enter] Jump to notification | [x] Clear all | [Esc] Close      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Conclusion & Next Steps

### Key Takeaways

1. **Streaming CLI is the Future**: Claude Code's approach proves that simple, streaming text interfaces outperform heavy TUIs in startup time, portability, and maintainability.

2. **Notifications Solve Context-Switching**: cmux's visual + audio notification system prevents the "too many tabs" problem and reduces cognitive load.

3. **Accessibility is Non-Negotiable**: WCAG 2.1 Level AA compliance (4.5:1 contrast) must be built in from day one, not retrofitted.

4. **Themes Drive Adoption**: Beautiful, accessible themes with dark/light modes are table stakes for developer tools in 2026.

5. **Voice Feedback is Underutilized**: Hook-based audio notifications provide non-intrusive status awareness without requiring visual monitoring.

### Immediate Actions

1. **Start Migration**: Begin Week 1 of streaming CLI migration (core infrastructure)
2. **Audit Themes**: Verify all 10 proposed themes pass WCAG contrast checks
3. **Prototype Voice**: Implement basic hook-based audio feedback for session lifecycle
4. **Document Keybindings**: Create comprehensive keybinding reference card
5. **Test Accessibility**: Verify screen reader compatibility with VoiceOver/NVDA

### Success Metrics (3 Months)

- **Performance**: Startup time <500ms, memory <100MB
- **Adoption**: Theme usage >50%, voice feedback opt-in >30%
- **Accessibility**: 100% WCAG 2.1 Level AA compliance
- **User Satisfaction**: >80% positive feedback on new interface
- **Support Tickets**: <5 critical UI bugs per month

---

## References & Sources

### Research Sources

1. [Claude Code Commands Documentation](https://code.claude.com/docs/en/commands)
2. [Claude Code Interactive Mode](https://code.claude.com/docs/en/interactive-mode)
3. [Claude Code Hooks System](https://code.claude.com/docs/en/hooks)
4. [Hermes Agent Repository](https://github.com/nousresearch/hermes-agent)
5. [Warp Terminal](https://github.com/warpdotdev/warp)
6. [cmux Repository](https://github.com/manaflow-ai/cmux)
7. [rmux Repository](https://github.com/Helvesec/rmux)
8. [AlphaClaw Repository](https://github.com/chrysb/alphaclaw)
9. [tmux Repository](https://github.com/tmux/tmux)

### Color Themes

10. [Gogh Color Schemes](https://github.com/Gogh-Co/Gogh)
11. [Terminal Color Schemes (230+ themes)](https://github.com/ei9h7/Terminal-Color-Schemes)
12. [Dracula Theme](https://draculatheme.com/)
13. [Tokyo Night Theme Setup Guide](https://petronellatech.com/blog/tokyo-night-theme-setup-guide-2026)

### Accessibility

14. [Dark Mode Accessibility Guide](https://www.accessibilitychecker.org/blog/dark-mode-accessibility/)
15. [WCAG Color Contrast Requirements](https://codelucky.com/css-accessibility-wcag-color-contrast/)
16. [Building Self-Correcting Color Systems](https://www.smashingmagazine.com/2026/05/building-self-correcting-color-systems-contrast-color/)

### Terminal UI Best Practices

17. [CLI UX Best Practices - Evil Martians](https://evilmartians.com/chronicles/cli-ux-best-practices-3-patterns-for-improving-progress-displays)
18. [Progress Indicator UX](https://www.eleken.co/blog-posts/progress-indicator-ux)
19. [Practical Interface Patterns for AI Transparency](https://www.smashingmagazine.com/2026/05/practical-interface-patterns-ai-transparency/)

### Voice & TTS

20. [gTTS - Google Text-to-Speech](https://github.com/pndurette/gTTS)
21. [Python Text-to-Speech Guide](https://www.lemonfox.ai/blog/python-text-to-speech)
22. [Sound Effects for Claude Code](https://alexop.dev/posts/how-i-added-sound-effects-to-claude-code-with-hooks/)

### Additional Resources

23. [Awesome TUIs](https://github.com/rothgar/awesome-tuis)
24. [Windows Terminal Color Schemes](https://learn.microsoft.com/en-us/windows/terminal/customize-settings/color-schemes)

---

**End of Report**

*Generated by: Senior UX Architect & Interaction Designer*  
*Date: May 29, 2026*  
*Version: 1.0*
