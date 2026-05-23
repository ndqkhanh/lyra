# Claude Code UI Format Analysis

## Header Format

```
██╗  ██╗   ██╗██████╗  █████╗    Lyra v1.0.0
██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗   Opus 4.7 (1M context) with xhigh effort · API Usage Billing
███████║ ╚████╔╝ ██████╔╝███████║  ~/Downloads/MyCV/research/harness-engineering
```

**Components:**
- ASCII art logo "LYRA" (left-aligned, 3 lines)
- Version info on line 1
- Model + context + billing on line 2
- Current directory on line 3

## Message Symbols

| Symbol | Meaning | Color | Usage |
|--------|---------|-------|-------|
| `❯` | User input prompt | Bright cyan/blue | User messages |
| `⏺` | Assistant response | White/gray | Assistant text blocks |
| `✳` | Flowing/thinking | Yellow/gold | Extended thinking indicator |
| `◯` | Background task | Gray | Queued/running agents |
| `⏵⏵` | System status | Cyan | Permission/status messages |
| `⎿` | Tool result indent | Gray | Tool execution results |

## Color Scheme

### Primary Colors
- **User prompt (`❯`)**: Bright cyan (`#00D9FF`)
- **Assistant marker (`⏺`)**: White/light gray (`#E0E0E0`)
- **Thinking (`✳`)**: Yellow/gold (`#FFD700`)
- **Background task (`◯`)**: Medium gray (`#808080`)
- **System (`⏵⏵`)**: Cyan (`#00CED1`)

### Tool Execution Colors
- **Tool name**: Bright white/bold
- **File paths**: Cyan
- **Line numbers**: Gray
- **Success indicators**: Green
- **Error indicators**: Red
- **Warnings**: Yellow

### Status Colors
- **Idle**: Gray
- **Thinking**: Yellow
- **Streaming**: Cyan (animated)
- **Error**: Red
- **Success**: Green

## Tool Execution Format

```
⏺ Write(projects/lyra/packages/lyra-cli/src/lyra_cli/hooks/__init__.py)
  ⎿  Wrote 13 lines to projects/lyra/packages/lyra-cli/src/lyra_cli/hooks/__init__.py
       1 """Hook system for Lyra - ECC-inspired event-driven automation"""
       2
       3 from .hook_manager import HookManager, HookType, HookContext
       4 from .hook_registry import HookRegistry
       5 from .builtin_hooks import register_builtin_hooks
       6
       7 __all__ = [
       8     "HookManager",
      … +169 lines (ctrl+o to expand)
  ⎿  Found 3 new diagnostic issues in 1 file (ctrl+o to expand)
```

**Structure:**
1. Tool call line: `⏺ ToolName(arguments)`
2. Result indent: `⎿` (tree branch character)
3. Summary line: Action + file path
4. Code preview: Line numbers + content
5. Collapse indicator: `… +N lines (ctrl+o to expand)`
6. Diagnostics: Issues found (if any)

## Progress Indicators

### Flowing State
```
✳ Flowing… (5m 24s · ↑ 9.7k tokens)
  ⎿  ◻ Phase 3: Rules System with Language Override
```

**Components:**
- `✳` symbol (animated/pulsing)
- Duration counter
- Token usage indicator
- Current phase/task description

### Background Tasks
```
⏺ main                                           ↑/↓ to select · Enter to view
◯ general-purpose  Research provided GitHub repos on token reduction       30s
◯ general-purpose  Search GitHub for top token/context compression repos   26s
◯ general-purpose  Research academic papers on context/token compression   21s
◯ general-purpose  Research production token reduction tools and techniqu… 17s
```

**Structure:**
- Active task: `⏺` (filled circle)
- Queued tasks: `◯` (empty circle)
- Agent name + task description
- Duration/time remaining

## Interactive Elements

### Bottom Status Bar
```
⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
```

**Format:**
- `⏵⏵` prefix
- Current mode/status
- Keyboard shortcuts (separated by `·`)

### Keyboard Shortcuts Display
- `ctrl+o` - Expand collapsed content
- `shift+tab` - Cycle options
- `esc` - Interrupt
- `↑/↓` - Navigate
- `Enter` - Select/view

## Text Formatting

### Code Blocks
- Line numbers: Right-aligned, gray
- Code content: Syntax highlighted
- Indentation: Preserved with spaces

### File Paths
- Relative paths: Cyan color
- Absolute paths: Cyan color
- Truncated with `…` if too long

### Timestamps
- Format: `5m 24s` (minutes and seconds)
- Format: `30s` (seconds only)
- Color: Gray

### Token Counts
- Format: `↑ 9.7k tokens` (with arrow)
- Color: Gray/white

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Header (logo + version + model + directory)                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ❯ User message                                              │
│                                                              │
│ ⏺ Assistant response                                        │
│                                                              │
│ ⏺ Tool execution                                            │
│   ⎿ Tool result                                             │
│      Code preview                                           │
│      … +N lines                                             │
│                                                              │
│ ✳ Flowing… (duration · tokens)                             │
│   ⎿ Current task                                            │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ ❯ Next user input                                           │
├─────────────────────────────────────────────────────────────┤
│ ⏵⏵ Status bar with shortcuts                               │
└─────────────────────────────────────────────────────────────┘
```

## Spacing Rules

- **Between messages**: 1 blank line
- **Between tool calls**: No blank line
- **Tool result indent**: 2 spaces + `⎿` + 2 spaces
- **Code preview indent**: 5 spaces (for line numbers)
- **Collapsed content**: `… +N lines` on same indent level

## Animation States

### Streaming Indicator
- Character: `⏺` (pulsing)
- Animation: Fade in/out or color shift
- Duration: While streaming

### Thinking Indicator
- Character: `✳` (rotating or pulsing)
- Text: "Flowing…"
- Shows: Duration + token count

### Background Task Spinner
- Character: `◯` → `◐` → `◓` → `◑` (rotating)
- Updates: Every 100ms

## Special Characters Used

- `██╗  ██╗   ██╗██████╗  █████╗` - Logo line 1 (LYRA)
- `██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗` - Logo line 2 (LYRA)
- `███████║ ╚████╔╝ ██████╔╝███████║` - Logo line 3 (LYRA)
- `❯` - User prompt
- `⏺` - Response marker
- `✳` - Thinking/flowing
- `◯` - Background task
- `⏵⏵` - System status
- `⎿` - Tree branch (result indent)
- `◻` - Empty checkbox
- `↑` - Up arrow (tokens)
- `↓` - Down arrow (navigate)
- `·` - Separator dot
- `…` - Ellipsis (collapsed)

## Color Palette (Hex Codes)

```
User prompt:       #00D9FF (bright cyan)
Assistant:         #E0E0E0 (light gray)
Thinking:          #FFD700 (gold)
Background task:   #808080 (gray)
System:            #00CED1 (cyan)
Success:           #00FF00 (green)
Error:             #FF0000 (red)
Warning:           #FFA500 (orange)
File path:         #00CED1 (cyan)
Line numbers:      #666666 (dark gray)
Code:              #FFFFFF (white)
Timestamp:         #999999 (medium gray)
```

## Implementation Notes

1. **Use Rich library** for Python terminal formatting
2. **ANSI color codes** for basic colors
3. **Unicode characters** for symbols (ensure terminal support)
4. **Monospace font** required for alignment
5. **Terminal width detection** for responsive layout
6. **Collapsible sections** with expand/collapse state
7. **Real-time updates** for streaming and progress

## Key Features to Implement

1. ✅ Header with logo and metadata
2. ✅ Message symbols (❯, ⏺, ✳, ◯)
3. ✅ Color-coded output
4. ✅ Tool execution formatting
5. ✅ Collapsible code blocks
6. ✅ Progress indicators
7. ✅ Background task list
8. ✅ Interactive status bar
9. ✅ Keyboard shortcuts display
10. ✅ Streaming animations

---

**Reference**: Claude Code v2.1.148 UI format
**Date**: 2026-05-24
