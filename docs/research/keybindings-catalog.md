# Keybindings Catalog for Terminal/CLI Applications

**Research Date:** 2026-05-26  
**Purpose:** Comprehensive catalog of keybinding systems for implementing in Lyra CLI

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Vim Mode Keybindings](#vim-mode-keybindings)
3. [Emacs Mode Keybindings](#emacs-mode-keybindings)
4. [Readline Keybindings](#readline-keybindings)
5. [Popular CLI Tools](#popular-cli-tools)
6. [Configuration Formats](#configuration-formats)
7. [Conflict Resolution Strategies](#conflict-resolution-strategies)
8. [Discoverability Features](#discoverability-features)
9. [Implementation Guide](#implementation-guide)
10. [Code Examples](#code-examples)
11. [Sources](#sources)

## Executive Summary

This document catalogs comprehensive keybinding systems from popular terminal applications and provides implementation guidance for Lyra CLI. Key findings:

- **Modal editing** (Vim-style) minimizes awkward key combinations while accelerating workflow
- **Chord keybindings** (Emacs-style) use multi-key sequences for complex commands
- **Configuration formats**: JSON for programmatic access, YAML for human readability
- **Priority systems**: User-defined > Plugin-defined > Built-in defaults
- **Discoverability**: Critical for CLI adoption - requires in-context help and hints

## Vim Mode Keybindings

### Core Concepts

**Modal Editing Philosophy:**
- Keyboard-centric approach where most actions require holding at most two keys (usually one)
- Minimizes awkward key combinations (no Control+Shift+Alt+key)
- Accelerates editing workflow through single-key commands

**Modes:**
1. **Normal Mode** - Navigation and commands (default)
2. **Insert Mode** - Text input
3. **Visual Mode** - Text selection
4. **Command Mode** - Ex commands (`:`)

### Complete Vim Keybinding Reference

#### Normal Mode - Navigation

| Key | Action | Description |
|-----|--------|-------------|
| `h` | Left | Move cursor left |
| `j` | Down | Move cursor down |
| `k` | Up | Move cursor up |
| `l` | Right | Move cursor right |
| `w` | Word forward | Jump to start of next word |
| `W` | WORD forward | Jump to start of next WORD (whitespace-separated) |
| `b` | Word backward | Jump to start of previous word |
| `B` | WORD backward | Jump to start of previous WORD |
| `e` | End of word | Jump to end of current/next word |
| `E` | End of WORD | Jump to end of current/next WORD |
| `0` | Line start | Jump to beginning of line |
| `^` | First non-blank | Jump to first non-whitespace character |
| `$` | Line end | Jump to end of line |
| `gg` | File start | Jump to first line |
| `G` | File end | Jump to last line |
| `{number}G` | Go to line | Jump to specific line number |
| `%` | Matching bracket | Jump to matching bracket/paren |

#### Normal Mode - Editing

| Key | Action | Description |
|-----|--------|-------------|
| `i` | Insert before | Enter insert mode before cursor |
| `I` | Insert at line start | Enter insert mode at beginning of line |
| `a` | Append after | Enter insert mode after cursor |
| `A` | Append at line end | Enter insert mode at end of line |
| `o` | Open line below | Insert new line below and enter insert mode |
| `O` | Open line above | Insert new line above and enter insert mode |
| `x` | Delete character | Delete character under cursor |
| `X` | Delete before | Delete character before cursor |
| `dd` | Delete line | Delete entire line |
| `D` | Delete to end | Delete from cursor to end of line |
| `yy` | Yank line | Copy entire line |
| `Y` | Yank to end | Copy from cursor to end of line |
| `p` | Paste after | Paste after cursor |
| `P` | Paste before | Paste before cursor |
| `u` | Undo | Undo last change |
| `Ctrl-r` | Redo | Redo last undone change |
| `.` | Repeat | Repeat last command |

#### Normal Mode - Search

| Key | Action | Description |
|-----|--------|-------------|
| `/pattern` | Search forward | Search for pattern forward |
| `?pattern` | Search backward | Search for pattern backward |
| `n` | Next match | Jump to next search match |
| `N` | Previous match | Jump to previous search match |
| `*` | Search word forward | Search for word under cursor forward |
| `#` | Search word backward | Search for word under cursor backward |

#### Visual Mode

| Key | Action | Description |
|-----|--------|-------------|
| `v` | Visual character | Enter visual mode (character selection) |
| `V` | Visual line | Enter visual line mode |
| `Ctrl-v` | Visual block | Enter visual block mode |
| `d` | Delete selection | Delete selected text |
| `y` | Yank selection | Copy selected text |
| `c` | Change selection | Delete selection and enter insert mode |
| `>` | Indent | Indent selected lines |
| `<` | Unindent | Unindent selected lines |

## Emacs Mode Keybindings

### Core Concepts

**Chord Keybindings Philosophy:**
- Multi-key sequences called "complete keys" or "chords"
- Prefix keys start chord sequences (e.g., `C-x`, `C-c`)
- Powerful command composition through key sequences

**Key Notation:**
- `C-x` = Control + x
- `M-x` = Meta (Alt) + x
- `C-M-a` = Control + Meta + a (simultaneously)
- `S-right` = Shift + right arrow
- `C-x C-f` = Control+x, then Control+f (chord sequence)

### Complete Emacs Keybinding Reference

#### Movement

| Key | Action | Description |
|-----|--------|-------------|
| `C-f` | Forward char | Move forward one character |
| `C-b` | Backward char | Move backward one character |
| `C-n` | Next line | Move to next line |
| `C-p` | Previous line | Move to previous line |
| `M-f` | Forward word | Move forward one word |
| `M-b` | Backward word | Move backward one word |
| `C-a` | Beginning of line | Move to start of line |
| `C-e` | End of line | Move to end of line |
| `M-<` | Beginning of buffer | Move to start of document |
| `M->` | End of buffer | Move to end of document |
| `C-v` | Page down | Scroll down one page |
| `M-v` | Page up | Scroll up one page |

#### Editing

| Key | Action | Description |
|-----|--------|-------------|
| `C-d` | Delete char | Delete character at cursor |
| `M-d` | Delete word | Delete word forward |
| `M-DEL` | Delete word backward | Delete word backward |
| `C-k` | Kill line | Delete from cursor to end of line |
| `C-w` | Kill region | Cut selected region |
| `M-w` | Copy region | Copy selected region |
| `C-y` | Yank | Paste |
| `M-y` | Yank pop | Cycle through kill ring |
| `C-/` or `C-_` | Undo | Undo last change |
| `C-g` | Keyboard quit | Cancel current command |
| `C-x u` | Undo | Alternative undo |

#### Search and Replace

| Key | Action | Description |
|-----|--------|-------------|
| `C-s` | Incremental search | Search forward incrementally |
| `C-r` | Reverse search | Search backward incrementally |
| `M-%` | Query replace | Interactive find and replace |
| `M-x replace-string` | Replace string | Replace all occurrences |

#### Files and Buffers

| Key | Action | Description |
|-----|--------|-------------|
| `C-x C-f` | Find file | Open file |
| `C-x C-s` | Save file | Save current buffer |
| `C-x C-w` | Write file | Save as |
| `C-x C-c` | Exit | Quit Emacs |
| `C-x b` | Switch buffer | Switch to buffer |
| `C-x k` | Kill buffer | Close buffer |
| `C-x C-b` | List buffers | Show buffer list |

#### Windows and Frames

| Key | Action | Description |
|-----|--------|-------------|
| `C-x 2` | Split horizontal | Split window horizontally |
| `C-x 3` | Split vertical | Split window vertically |
| `C-x 1` | Delete other windows | Keep only current window |
| `C-x 0` | Delete window | Close current window |
| `C-x o` | Other window | Switch to next window |

## Readline Keybindings

### Overview

GNU Readline is a library used by many CLI applications (bash, Python REPL, etc.). It provides two modes:

1. **Emacs mode** (default) - Emacs-style keybindings
2. **Vi mode** - Vim-style keybindings

**Switching modes:**
- Enable vi mode: `set -o vi`
- Enable emacs mode: `set -o emacs`
- Configure in `~/.inputrc` for persistence

### Readline Emacs Mode

| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl-a` | Beginning of line | Move to start of line |
| `Ctrl-e` | End of line | Move to end of line |
| `Ctrl-f` | Forward char | Move forward one character |
| `Ctrl-b` | Backward char | Move backward one character |
| `Alt-f` | Forward word | Move forward one word |
| `Alt-b` | Backward word | Move backward one word |
| `Ctrl-d` | Delete char | Delete character at cursor |
| `Ctrl-h` | Delete backward | Delete character before cursor |
| `Ctrl-w` | Kill word backward | Delete word before cursor |
| `Alt-d` | Kill word forward | Delete word after cursor |
| `Ctrl-k` | Kill line | Delete from cursor to end of line |
| `Ctrl-u` | Kill line backward | Delete from cursor to start of line |
| `Ctrl-y` | Yank | Paste killed text |
| `Ctrl-_` | Undo | Undo last edit |
| `Ctrl-r` | Reverse search | Search command history backward |
| `Ctrl-s` | Forward search | Search command history forward |
| `Ctrl-p` | Previous history | Previous command in history |
| `Ctrl-n` | Next history | Next command in history |
| `Ctrl-l` | Clear screen | Clear terminal screen |

### Readline Vi Mode

**Insert Mode:**
- Same as normal typing
- `Esc` to enter command mode

**Command Mode:**
- Standard Vim navigation (`h`, `j`, `k`, `l`)
- Standard Vim editing (`x`, `dd`, `yy`, `p`)
- `/` for history search
- `i`, `a`, `I`, `A` to return to insert mode

## Popular CLI Tools

### tmux Keybindings

**Prefix Key:** `Ctrl-b` (default, often changed to `Ctrl-a`)

**Configuration:** `~/.tmux.conf`

#### Session Management

| Key | Action | Description |
|-----|--------|-------------|
| `Prefix + d` | Detach | Detach from session |
| `Prefix + $` | Rename session | Rename current session |
| `Prefix + s` | List sessions | Show session list |

#### Window Management

| Key | Action | Description |
|-----|--------|-------------|
| `Prefix + c` | Create window | Create new window |
| `Prefix + ,` | Rename window | Rename current window |
| `Prefix + n` | Next window | Switch to next window |
| `Prefix + p` | Previous window | Switch to previous window |
| `Prefix + w` | List windows | Show window list |
| `Prefix + &` | Kill window | Close current window |
| `Prefix + 0-9` | Select window | Switch to window by number |

#### Pane Management

| Key | Action | Description |
|-----|--------|-------------|
| `Prefix + %` | Split vertical | Split pane vertically |
| `Prefix + "` | Split horizontal | Split pane horizontally |
| `Prefix + o` | Next pane | Switch to next pane |
| `Prefix + ;` | Last pane | Switch to last active pane |
| `Prefix + x` | Kill pane | Close current pane |
| `Prefix + {` | Move pane left | Swap pane with previous |
| `Prefix + }` | Move pane right | Swap pane with next |
| `Prefix + z` | Zoom pane | Toggle pane zoom |
| `Prefix + arrow` | Navigate panes | Move between panes |

**Customization Example:**
```bash
# Change prefix to Ctrl-a
unbind C-b
set-option -g prefix C-a
bind-key C-a send-prefix

# Split panes with | and -
bind | split-window -h
bind - split-window -v
```

### Fish Shell Keybindings

**Configuration:** Use `bind` command or add to `~/.config/fish/config.fish`

**Key Notation:**
- `\c` = Control key (e.g., `\cg` = Ctrl-g)
- `\e` = Escape/Alt/Meta key
- Modifiers: `ctrl-`, `alt-`, `shift-`, `super-`

**Examples:**
```fish
# Bind Ctrl-g to accept autosuggestion
bind \cg accept-autosuggestion

# Bind Alt-w to accept word
bind alt-w forward-word

# Bind Ctrl-x Ctrl-e to edit command in editor
bind \cx\ce edit_command_buffer
```

### Zsh Keybindings

**Configuration:** Use `bindkey` command or add to `~/.zshrc`

**Modes:**
- `bindkey -e` - Emacs mode
- `bindkey -v` - Vi mode

**Examples:**
```zsh
# Bind Ctrl-r to history search
bindkey '^R' history-incremental-search-backward

# Bind Up arrow to history search
bindkey '^[[A' history-beginning-search-backward
```

### Warp Terminal Keybindings

**Configuration:** YAML-based preset files

**Features:**
- Custom keyboard shortcut presets
- Vim keybindings support for command editing
- Global hotkeys for terminal access

**Configuration Format:**
```yaml
# default-warp-keybindings.yaml
keybindings:
  - key: "ctrl+t"
    action: "new_tab"
  - key: "ctrl+w"
    action: "close_tab"
  - key: "cmd+k"
    action: "clear_screen"
```

### Claude Code Keybindings

**Configuration:** JSON-based configuration file

**Structure:**
```json
{
  "bindings": [
    {
      "context": "editor",
      "bindings": {
        "ctrl+s": "save",
        "ctrl+shift+p": "command_palette"
      }
    }
  ]
}
```

**Features:**
- Context-based bindings
- Chord sequence support
- Ability to unbind defaults
- Organized by context (editor, terminal, etc.)

## Configuration Formats

### JSON Format

**Advantages:**
- Simple, familiar key-value structure
- Excellent for programmatic access
- Lightweight and fast parsing
- Wide language support
- Ideal for APIs

**Example:**
```json
{
  "keybindings": {
    "ctrl+c": {
      "action": "copy",
      "context": "editor",
      "priority": 100
    },
    "ctrl+v": {
      "action": "paste",
      "context": "editor",
      "priority": 100
    }
  }
}
```

**Use Cases:**
- VS Code keybindings
- Claude Code configuration
- API-driven configurations

### YAML Format

**Advantages:**
- Superior human readability
- Better for complex nested structures
- Supports comments
- Cleaner syntax for hierarchical data

**Example:**
```yaml
keybindings:
  editor:
    ctrl+c:
      action: copy
      priority: 100
      description: "Copy selected text"
    ctrl+v:
      action: paste
      priority: 100
      description: "Paste from clipboard"
  
  terminal:
    ctrl+l:
      action: clear_screen
      priority: 90
```

**Use Cases:**
- Warp terminal presets
- Configuration files requiring comments
- Human-edited configurations

### Hybrid Approach

**Best Practice:** Support both formats
- JSON for programmatic/API access
- YAML for human editing
- Convert between formats as needed

## Conflict Resolution Strategies

### Priority-Based System

**Hierarchy (highest to lowest):**
1. **User-defined bindings** (priority: 100+)
2. **Plugin/extension bindings** (priority: 50-99)
3. **Built-in defaults** (priority: 0-49)

**Implementation:**
```typescript
interface KeyBinding {
  key: string;
  action: string;
  priority: number;
  context?: string;
}

function resolveConflict(bindings: KeyBinding[]): KeyBinding {
  return bindings.reduce((highest, current) => 
    current.priority > highest.priority ? current : highest
  );
}
```

### Context-Aware Resolution

**Concept:** Bindings with same key but different contexts don't conflict

**Example:**
```typescript
const bindings = [
  { key: "ctrl+s", action: "save", context: "editor" },
  { key: "ctrl+s", action: "send", context: "chat" }
];

function getBinding(key: string, context: string): KeyBinding | null {
  return bindings.find(b => b.key === key && b.context === context);
}
```

### Input Sinking

**Concept:** Higher-priority binding consumes input, preventing lower-priority handlers

**Implementation:**
```typescript
function handleKeyPress(key: string, context: string): boolean {
  const binding = getHighestPriorityBinding(key, context);
  if (binding) {
    executeAction(binding.action);
    return true; // Input consumed
  }
  return false; // Allow propagation
}
```

### Conflict Detection

**VS Code Pattern:** Automatic conflict scanner
- Detects conflicts when installing extensions
- Provides resolution UI
- Suggests alternative bindings

**Implementation Strategy:**
```typescript
function detectConflicts(newBinding: KeyBinding, existing: KeyBinding[]): KeyBinding[] {
  return existing.filter(b => 
    b.key === newBinding.key && 
    b.context === newBinding.context &&
    b.priority === newBinding.priority
  );
}
```

## Discoverability Features

### The CLI Discoverability Problem

**Challenge:** CLIs face fundamental discoverability issues compared to GUIs
- New users see blank screen: "what do I even do?"
- High UX barrier without hand-holding
- Must already know conventions (`--help`, `man`) to find help

### Standard Entry Points

1. **`--help` flag** - Command-line help
2. **`man` pages** - Manual pages
3. **Interactive help** - `?` or `help` command

### Best Practices for Discoverability

#### 1. In-Context Help Menus

**Pattern:** Show keybindings where users will find them

```
┌─ Editor ─────────────────────────────┐
│ File  Edit  View  Help               │
│                                       │
│ Ctrl+S  Save                          │
│ Ctrl+O  Open                          │
│ Ctrl+Q  Quit                          │
│                                       │
│ Press ? for help                      │
└───────────────────────────────────────┘
```

#### 2. Keyboard Shortcut Hints

**Pattern:** Display shortcuts alongside menu items

```
File
  New File        Ctrl+N
  Open File...    Ctrl+O
  Save            Ctrl+S
  Save As...      Ctrl+Shift+S
  ───────────────────────
  Exit            Ctrl+Q
```

#### 3. Help Dialog

**Pattern:** Dedicated help screen accessible via keybinding

```
Press Ctrl+? or F1 to show:

┌─ Keyboard Shortcuts ─────────────────┐
│                                       │
│ Navigation                            │
│   ↑/↓/←/→    Move cursor              │
│   Ctrl+Home  Go to start              │
│   Ctrl+End   Go to end                │
│                                       │
│ Editing                               │
│   Ctrl+C     Copy                     │
│   Ctrl+V     Paste                    │
│   Ctrl+Z     Undo                     │
│                                       │
│ Press Esc to close                    │
└───────────────────────────────────────┘
```

#### 4. Status Bar Hints

**Pattern:** Show available actions in status bar

```
┌─────────────────────────────────────┐
│                                     │
│  [Content Area]                     │
│                                     │
├─────────────────────────────────────┤
│ ^S Save  ^O Open  ^Q Quit  ^? Help │
└─────────────────────────────────────┘
```

#### 5. Progressive Disclosure

**Pattern:** Show basic shortcuts first, advanced on demand

```
Basic Mode (default):
  Ctrl+S  Save
  Ctrl+Q  Quit
  
Advanced Mode (press Ctrl+Shift+?):
  Ctrl+Shift+S    Save As
  Ctrl+Alt+S      Save All
  Ctrl+K Ctrl+S   Save Without Formatting
```

#### 6. Command Palette

**Pattern:** Searchable command list with shortcuts

```
> search command...

  Save File                    Ctrl+S
  Save As...                   Ctrl+Shift+S
  Open File                    Ctrl+O
  Close File                   Ctrl+W
  Toggle Sidebar               Ctrl+B
```

## Implementation Guide

### Architecture Overview

```
┌─────────────────────────────────────────┐
│         User Input Layer                │
│  (Captures raw keyboard events)         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Key Sequence Parser                │
│  (Parses key combinations & chords)     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Binding Registry                   │
│  (Stores and resolves keybindings)      │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Action Dispatcher                  │
│  (Executes bound actions)               │
└─────────────────────────────────────────┘
```

### Core Components

#### 1. Key Sequence Parser

**Responsibilities:**
- Parse key notation (e.g., "ctrl+shift+s", "C-x C-f")
- Handle modifier keys (Ctrl, Alt, Shift, Meta)
- Support chord sequences
- Normalize key representations

**Key Notation Standards:**
- **Emacs style:** `C-x` (Control+x), `M-x` (Meta/Alt+x)
- **Modern style:** `ctrl+x`, `alt+x`, `shift+x`
- **Special keys:** `escape`, `space`, `enter`, `tab`, `backspace`
- **Function keys:** `f1`, `f2`, ..., `f12`
- **Arrows:** `up`, `down`, `left`, `right`

#### 2. Binding Registry

**Responsibilities:**
- Store keybinding definitions
- Resolve conflicts using priority system
- Support context-aware bindings
- Enable/disable bindings dynamically

**Data Structure:**
```typescript
interface KeyBinding {
  key: string;              // "ctrl+s" or "C-x C-f"
  action: string;           // Action identifier
  context?: string;         // Optional context
  priority: number;         // Conflict resolution
  description?: string;     // For help display
  when?: string;            // Conditional expression
}
```

#### 3. Action Dispatcher

**Responsibilities:**
- Execute actions based on bindings
- Handle action parameters
- Provide action feedback
- Support undo/redo for actions

### Modal Editing State Machine

**States:**
- `NORMAL` - Command mode (default)
- `INSERT` - Text input mode
- `VISUAL` - Selection mode
- `COMMAND` - Ex command mode

**Transitions:**
```typescript
type Mode = 'NORMAL' | 'INSERT' | 'VISUAL' | 'COMMAND';

interface ModeTransition {
  from: Mode;
  to: Mode;
  trigger: string;
}

const transitions: ModeTransition[] = [
  { from: 'NORMAL', to: 'INSERT', trigger: 'i' },
  { from: 'NORMAL', to: 'VISUAL', trigger: 'v' },
  { from: 'INSERT', to: 'NORMAL', trigger: 'escape' },
  { from: 'VISUAL', to: 'NORMAL', trigger: 'escape' }
];
```

### Configuration Loading

**Priority Order (highest to lowest):**
1. User config (`~/.lyra/keybindings.json`)
2. Project config (`.lyra/keybindings.json`)
3. Plugin configs
4. Built-in defaults

**Loading Strategy:**
```typescript
async function loadKeybindings(): Promise<KeyBinding[]> {
  const defaults = await loadBuiltinBindings();
  const plugins = await loadPluginBindings();
  const project = await loadProjectBindings();
  const user = await loadUserBindings();
  
  return mergeBindings([defaults, plugins, project, user]);
}

function mergeBindings(sources: KeyBinding[][]): KeyBinding[] {
  const registry = new Map<string, KeyBinding>();
  
  for (const bindings of sources) {
    for (const binding of bindings) {
      const key = `${binding.key}:${binding.context || 'global'}`;
      const existing = registry.get(key);
      
      if (!existing || binding.priority > existing.priority) {
        registry.set(key, binding);
      }
    }
  }
  
  return Array.from(registry.values());
}
```

## Code Examples

### TypeScript Implementation

#### Basic Keybinding System

```typescript
// keybinding.ts
export interface KeyBinding {
  key: string;
  action: string;
  context?: string;
  priority: number;
  description?: string;
}

export class KeyBindingRegistry {
  private bindings: Map<string, KeyBinding[]> = new Map();
  
  register(binding: KeyBinding): void {
    const key = this.normalizeKey(binding.key);
    const existing = this.bindings.get(key) || [];
    existing.push(binding);
    existing.sort((a, b) => b.priority - a.priority);
    this.bindings.set(key, existing);
  }
  
  resolve(key: string, context?: string): KeyBinding | null {
    const normalized = this.normalizeKey(key);
    const candidates = this.bindings.get(normalized) || [];
    
    return candidates.find(b => 
      !b.context || b.context === context
    ) || null;
  }
  
  private normalizeKey(key: string): string {
    return key.toLowerCase()
      .replace(/\s+/g, '')
      .replace(/control/g, 'ctrl')
      .replace(/command/g, 'cmd');
  }
}
```

#### Key Sequence Parser

```typescript
// key-parser.ts
export interface ParsedKey {
  key: string;
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
  meta: boolean;
}

export class KeyParser {
  parse(keyString: string): ParsedKey {
    const parts = keyString.toLowerCase().split('+');
    const result: ParsedKey = {
      key: '',
      ctrl: false,
      alt: false,
      shift: false,
      meta: false
    };
    
    for (const part of parts) {
      switch (part) {
        case 'ctrl':
        case 'control':
          result.ctrl = true;
          break;
        case 'alt':
        case 'option':
          result.alt = true;
          break;
        case 'shift':
          result.shift = true;
          break;
        case 'meta':
        case 'cmd':
        case 'command':
          result.meta = true;
          break;
        default:
          result.key = part;
      }
    }
    
    return result;
  }
  
  matches(parsed: ParsedKey, event: KeyboardEvent): boolean {
    return parsed.key === event.key.toLowerCase() &&
           parsed.ctrl === event.ctrlKey &&
           parsed.alt === event.altKey &&
           parsed.shift === event.shiftKey &&
           parsed.meta === event.metaKey;
  }
}
```

#### Chord Sequence Handler

```typescript
// chord-handler.ts
export class ChordHandler {
  private sequence: string[] = [];
  private timeout: NodeJS.Timeout | null = null;
  private readonly CHORD_TIMEOUT = 1000; // ms
  
  handleKey(key: string): string | null {
    this.sequence.push(key);
    
    if (this.timeout) {
      clearTimeout(this.timeout);
    }
    
    this.timeout = setTimeout(() => {
      this.sequence = [];
    }, this.CHORD_TIMEOUT);
    
    const chord = this.sequence.join(' ');
    
    // Check if this could be part of a longer chord
    if (this.hasPartialMatch(chord)) {
      return null; // Wait for more keys
    }
    
    // Complete chord or single key
    this.sequence = [];
    return chord;
  }
  
  private hasPartialMatch(partial: string): boolean {
    // Check against registered chords
    // Return true if any chord starts with this sequence
    return false; // Simplified
  }
}
```

#### Modal Editing State Machine

```typescript
// modal-state.ts
export type Mode = 'NORMAL' | 'INSERT' | 'VISUAL' | 'COMMAND';

export class ModalStateMachine {
  private currentMode: Mode = 'NORMAL';
  private listeners: Map<Mode, Set<(mode: Mode) => void>> = new Map();
  
  getCurrentMode(): Mode {
    return this.currentMode;
  }
  
  transition(to: Mode): void {
    const from = this.currentMode;
    this.currentMode = to;
    this.notifyListeners(from, to);
  }
  
  onModeChange(callback: (mode: Mode) => void): void {
    for (const mode of ['NORMAL', 'INSERT', 'VISUAL', 'COMMAND'] as Mode[]) {
      if (!this.listeners.has(mode)) {
        this.listeners.set(mode, new Set());
      }
      this.listeners.get(mode)!.add(callback);
    }
  }
  
  private notifyListeners(from: Mode, to: Mode): void {
    const listeners = this.listeners.get(to);
    if (listeners) {
      listeners.forEach(cb => cb(to));
    }
  }
}
```

### Python Implementation (using prompt_toolkit)

```python
# keybindings.py
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

kb = KeyBindings()

# Simple binding
@kb.add('c-s')
def save_file(event):
    """Save current file."""
    event.app.current_buffer.save()

# Chord sequence
@kb.add('c-x', 'c-f')
def find_file(event):
    """Open file dialog."""
    event.app.show_file_dialog()

# Conditional binding
@kb.add('c-c', filter=has_selection)
def copy_selection(event):
    """Copy selected text."""
    event.app.clipboard.set_text(event.app.current_buffer.copy_selection())

# Vi mode bindings
@kb.add('i', filter=vi_navigation_mode)
def enter_insert_mode(event):
    """Enter insert mode."""
    event.app.vi_state.input_mode = InputMode.INSERT

@kb.add('escape', filter=vi_insert_mode)
def enter_normal_mode(event):
    """Return to normal mode."""
    event.app.vi_state.input_mode = InputMode.NAVIGATION
```

### Configuration File Examples

#### JSON Configuration

```json
{
  "version": "1.0",
  "modes": {
    "vim": true,
    "emacs": false
  },
  "bindings": [
    {
      "key": "ctrl+s",
      "action": "save",
      "context": "editor",
      "priority": 100,
      "description": "Save current file"
    },
    {
      "key": "ctrl+shift+s",
      "action": "saveAs",
      "context": "editor",
      "priority": 100,
      "description": "Save file as..."
    },
    {
      "key": "ctrl+o",
      "action": "open",
      "context": "editor",
      "priority": 100,
      "description": "Open file"
    }
  ],
  "chords": [
    {
      "sequence": ["ctrl+x", "ctrl+f"],
      "action": "findFile",
      "context": "editor",
      "priority": 90,
      "description": "Find file"
    }
  ]
}
```

#### YAML Configuration

```yaml
version: "1.0"

modes:
  vim: true
  emacs: false

bindings:
  # Editor bindings
  editor:
    - key: ctrl+s
      action: save
      priority: 100
      description: "Save current file"
    
    - key: ctrl+shift+s
      action: saveAs
      priority: 100
      description: "Save file as..."
    
    - key: ctrl+o
      action: open
      priority: 100
      description: "Open file"
  
  # Terminal bindings
  terminal:
    - key: ctrl+l
      action: clearScreen
      priority: 90
      description: "Clear terminal screen"
    
    - key: ctrl+c
      action: interrupt
      priority: 100
      description: "Interrupt current process"

chords:
  - sequence:
      - ctrl+x
      - ctrl+f
    action: findFile
    context: editor
    priority: 90
    description: "Find file"
  
  - sequence:
      - ctrl+x
      - ctrl+s
    action: save
    context: editor
    priority: 90
    description: "Save file (Emacs style)"
```

### Complete Implementation Example

```typescript
// lyra-keybindings.ts
import { KeyBindingRegistry, KeyBinding } from './keybinding';
import { KeyParser } from './key-parser';
import { ChordHandler } from './chord-handler';
import { ModalStateMachine, Mode } from './modal-state';

export class LyraKeybindingSystem {
  private registry: KeyBindingRegistry;
  private parser: KeyParser;
  private chordHandler: ChordHandler;
  private modalState: ModalStateMachine;
  
  constructor() {
    this.registry = new KeyBindingRegistry();
    this.parser = new KeyParser();
    this.chordHandler = new ChordHandler();
    this.modalState = new ModalStateMachine();
    
    this.loadDefaultBindings();
  }
  
  async loadConfig(path: string): Promise<void> {
    const config = await this.readConfigFile(path);
    
    for (const binding of config.bindings) {
      this.registry.register(binding);
    }
  }
  
  handleKeyPress(event: KeyboardEvent): boolean {
    const keyString = this.eventToString(event);
    const chord = this.chordHandler.handleKey(keyString);
    
    if (!chord) {
      return false; // Waiting for more keys in chord
    }
    
    const mode = this.modalState.getCurrentMode();
    const context = this.getContext(mode);
    const binding = this.registry.resolve(chord, context);
    
    if (binding) {
      this.executeAction(binding.action);
      return true;
    }
    
    return false;
  }
  
  private eventToString(event: KeyboardEvent): string {
    const parts: string[] = [];
    
    if (event.ctrlKey) parts.push('ctrl');
    if (event.altKey) parts.push('alt');
    if (event.shiftKey) parts.push('shift');
    if (event.metaKey) parts.push('meta');
    
    parts.push(event.key.toLowerCase());
    
    return parts.join('+');
  }
  
  private getContext(mode: Mode): string {
    return mode.toLowerCase();
  }
  
  private executeAction(action: string): void {
    // Dispatch action to appropriate handler
    console.log(`Executing action: ${action}`);
  }
  
  private loadDefaultBindings(): void {
    // Load built-in defaults
  }
  
  private async readConfigFile(path: string): Promise<any> {
    // Read and parse config file
    return {};
  }
}
```

## Recommendations for Lyra

### 1. Configuration Format

**Recommendation:** Support both JSON and YAML
- JSON for programmatic access and API integration
- YAML for human-friendly editing with comments
- Provide conversion utilities between formats

### 2. Default Mode

**Recommendation:** Start with Emacs mode, offer Vim mode as option
- Emacs mode has lower learning curve for new users
- Vim mode available for power users via config flag
- Allow mode switching at runtime

### 3. Priority System

**Recommendation:** Implement 3-tier priority system
- User bindings: 100-199
- Plugin bindings: 50-99
- Built-in defaults: 0-49

### 4. Conflict Resolution

**Recommendation:** Automatic detection with user notification
- Detect conflicts on config load
- Show warning with conflicting bindings
- Suggest resolution (keep user binding, disable plugin, etc.)

### 5. Discoverability

**Recommendation:** Multi-layered help system
- `?` key for quick help overlay
- `Ctrl+?` or `F1` for full help dialog
- Status bar hints for common actions
- Command palette with searchable shortcuts

### 6. Context System

**Recommendation:** Context-aware bindings
- `editor` - Text editing context
- `terminal` - Terminal/shell context
- `chat` - Chat/conversation context
- `global` - Available everywhere

### 7. Chord Support

**Recommendation:** Support Emacs-style chords with 1-second timeout
- Enable power users to create complex workflows
- Timeout prevents accidental chord activation
- Visual feedback during chord sequence

### 8. Configuration Locations

**Recommendation:** Hierarchical config loading
```
1. ~/.lyra/keybindings.json (user global)
2. ~/.lyra/keybindings.yaml (user global, alternative)
3. .lyra/keybindings.json (project-specific)
4. .lyra/keybindings.yaml (project-specific, alternative)
```

### 9. Implementation Libraries

**TypeScript/JavaScript:**
- **tinykeys** (~650B) - Minimal, modern keybinding library
- **ctrl-keys** - Fast, efficient keybinding handling
- **Keystrokes** - Works in browser and non-browser environments

**Python:**
- **prompt_toolkit** - Full-featured terminal application framework
- Built-in keybinding support with Vi and Emacs modes
- Excellent for building interactive CLI applications

### 10. Testing Strategy

**Recommendation:** Comprehensive keybinding tests
```typescript
describe('KeyBindingSystem', () => {
  it('should resolve single key binding', () => {
    const system = new LyraKeybindingSystem();
    system.registry.register({
      key: 'ctrl+s',
      action: 'save',
      priority: 100
    });
    
    const binding = system.registry.resolve('ctrl+s');
    expect(binding?.action).toBe('save');
  });
  
  it('should resolve chord sequence', () => {
    const system = new LyraKeybindingSystem();
    system.registry.register({
      key: 'ctrl+x ctrl+f',
      action: 'findFile',
      priority: 90
    });
    
    const binding = system.registry.resolve('ctrl+x ctrl+f');
    expect(binding?.action).toBe('findFile');
  });
  
  it('should respect priority in conflicts', () => {
    const system = new LyraKeybindingSystem();
    system.registry.register({
      key: 'ctrl+s',
      action: 'save',
      priority: 50
    });
    system.registry.register({
      key: 'ctrl+s',
      action: 'customSave',
      priority: 100
    });
    
    const binding = system.registry.resolve('ctrl+s');
    expect(binding?.action).toBe('customSave');
  });
});
```

## Sources

### Vim Mode Keybindings
- [Vim Keybindings Guide for Beginners](https://phoenixnap.com/kb/vim-keybindings)
- [Vim Cheat Sheet](https://vim.rtorr.com/)
- [Evil Keybinding Reference](https://practical.li/neovim/reference/modal-editing/key-binding-reference/)
- [Chapter 2: What is Modal Editing, Anyway?](https://lazyvim-ambitious-devs.phillips.codes/course/chapter-2/)

### Emacs Mode Keybindings
- [List of All Emacs Keybinding](http://xahlee.info/emacs/emacs/emacs_keybinding_list.html)
- [Emacs Key Bindings](https://caiorss.github.io/Emacs-Elisp-Programming/Keybindings.html)
- [emacsorphanage/key-chord](https://github.com/emacsorphanage/key-chord)

### Readline
- [How do I switch to vi editing mode in readline?](https://unix.stackexchange.com/questions/112406/how-do-i-switch-to-vi-editing-mode-in-readline)
- [Vim Key Bindings in a Terminal](https://www.baeldung.com/linux/terminal-vim-key-bindings/)
- [What are readline's modes, keymaps and their default bindings?](https://unix.stackexchange.com/questions/303479/what-are-readlines-modes-keymaps-and-their-default-bindings)

### Popular CLI Tools
- [How to customize tmux keybindings?](https://tmuxai.dev/tmux-keybindings/)
- [Make tmux Pretty and Usable](https://hamvocke.com/blog/a-guide-to-customizing-your-tmux-conf/)
- [handle fish key bindings](https://fishshell.com/docs/current/cmds/bind.html)
- [Warp Keyboard Shortcuts](https://docs.warp.dev/getting-started/keyboard-shortcuts/)
- [warpdotdev/keysets](https://github.com/warpdotdev/keysets)
- [Customize keyboard shortcuts - Claude Code](https://claude-code.mintlify.app/en/keybindings)

### Configuration & Design Patterns
- [Terminal.Gui Keyboard Documentation](https://github.com/gui-cs/Terminal.Gui/blob/v2_develop/docfx/docs/keyboard.md)
- [Advanced Key Binding - Atuin](https://docs.atuin.sh/cli/configuration/advanced-key-binding/)
- [How can I change keyboard shortcut bindings in Visual Studio Code?](https://stackoverflow.com/questions/33791097/how-can-i-change-keyboard-shortcut-bindings-in-visual-studio-code)

### Conflict Resolution
- [NAP-7 — Key Binding Dispatch](https://napari.org/dev/naps/7-key-binding-dispatch.html)
- [Priority of keymapping commands](https://emacs.stackexchange.com/questions/37277/priority-of-keymapping-commands)
- [Keybinding Conflict Scanner](https://marketplace.visualstudio.com/items?itemName=rhslvkf.keybinding-conflict-scanner)

### Implementation Libraries
- [webNeat/ctrl-keys](https://github.com/webNeat/ctrl-keys)
- [jamiebuilds/tinykeys](https://github.com/jamiebuilds/tinykeys)
- [RobertWHurst/Keystrokes](https://github.com/RobertWHurst/Keystrokes)
- [Python Prompt Toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/)
- [More about key bindings — prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/advanced_topics/key_bindings.html)

### Discoverability
- [How to design great keyboard shortcuts](https://knock.app/blog/how-to-design-great-keyboard-shortcuts)
- [CLI user experience case study](https://news.ycombinator.com/item?id=38966601)

### State Machines
- [Building Predictable and Robust UI Components with State Machines](https://leapcell.io/blog/building-predictable-and-robust-ui-components-with-state-machines)
- [The Rise Of The State Machines](https://www.smashingmagazine.com/2018/01/rise-state-machines/)

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-26  
**Maintained by:** Lyra Research Team
