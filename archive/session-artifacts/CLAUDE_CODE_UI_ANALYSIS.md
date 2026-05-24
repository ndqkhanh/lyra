# 🎨 Claude Code UI Pattern Analysis

**Source**: Real Claude Code terminal output  
**Date**: 2026-05-23

---

## Visual Elements Observed

### 1. **Welcome Banner**
```
╭─── Claude Code v2.1.142 ─────────────────────────────────────────────────────╮
│                                                    │ Tips for getting        │
│                 Welcome back Khanh!                │ started                 │
│                                                    │ Run /init to create a … │
│                       ▐▛███▜▌                      │ ─────────────────────── │
│                      ▝▜█████▛▘                     │ What's new              │
│                        ▘▘ ▝▝                       │ Added new `claude agen… │
│ Sonnet 4.6 · Claude Max · khanhndq2002@gmail.com's │ Fast mode now uses Opu… │
│  Organization                                      │ Plugins with a root-le… │
│   ~/…/research/harness-engineering/projects/lyra   │ /release-notes for more │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Features**:
- Two-column layout (main + tips sidebar)
- ASCII art logo centered
- User greeting
- Model · Organization · Email
- Path with ellipsis for long paths
- Tips and "What's new" section
- Full-width box with title

### 2. **Status Indicators**
```
⏺ Status message (filled circle)
⏵⏵ Mode indicator (double arrows)
✶ Roosting/thinking (star)
✻ Stats line (asterisk)
⎿ Tool use (corner bracket)
```

### 3. **Progress Display**
```
⏺ Running 4 agents… (ctrl+o to expand)
   ├ Agent 1 · 10 tool uses · 29.7k tokens
   │ ⎿  Bash: Command
   ├ Agent 2 · 6 tool uses · 29.9k tokens
   │ ⎿  Web Search: Query
   ├ Agent 3 · 5 tool uses · 29.8k tokens
   │ ⎿  Web Search: Query
   └ Agent 4 · 6 tool uses · 25.7k tokens
     ⎿  Web Search: Query
```

**Features**:
- Tree structure with box-drawing characters
- Real-time token counts
- Tool use indicators
- Keyboard hints (ctrl+o, ctrl+b)

### 4. **Interactive Menus**
```
────────────────────────────────────────────────────────────────────────────────
  Select model
  Switch between Claude models...

    1. Default (recommended)  Opus 4.7 with 1M context · Most capable
  ❯ 2. Sonnet ✔               Sonnet 4.6 · Best for everyday tasks
    3. Haiku                  Haiku 4.5 · Fastest for quick answers

  ● High effort (default) ←/→ to adjust

  Enter to confirm · Esc to cancel
```

**Features**:
- Numbered options
- Current selection with ❯
- Checkmark ✔ for active
- Descriptions inline
- Keyboard hints at bottom
- Horizontal dividers

### 5. **Status Bar**
```
────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to man…
```

**Features**:
- Full-width dividers
- Mode indicator
- Keyboard shortcuts
- Contextual help

### 6. **Background Tasks Panel**
```
────────────────────────────────────────────────────────────────────────────────
  Background tasks
  3 active shells

  ❯ .venv/bin/python test_textual_driver.py 2>&1 (running)
    chmod +x test_catch_exception.py && ... (running)
    chmod +x test_tui_debug.py && ... (running)

  ↑/↓ to select · Enter to view · x to stop · ←/Esc to close
```

**Features**:
- Task list with status
- Selection indicator
- Keyboard shortcuts
- Status labels (running)

### 7. **Collapsible Sections**
```
✻ Conversation compacted (ctrl+o for history)

  ⎿  Read src/lyra_cli/cli/agent_integration.py (228 lines)
  ⎿  Referenced file src/lyra_cli/cli/tui.py
  ⎿  Skills restored (deep-research)
```

**Features**:
- Expandable with keyboard shortcut
- Indented tool list
- File paths and line counts
- Dim/secondary styling

### 8. **Agent Status Display**
```
⏺ main                                           ↑/↓ to select · Enter to view
◯ general-purpose  Research provided GitHub repos...   30s
◯ general-purpose  Search GitHub for top repos...      26s
◯ general-purpose  Research academic papers...         21s
```

**Features**:
- Filled/unfilled circles for status
- Agent type labels
- Time indicators
- Truncated descriptions

---

## Color Scheme

- **Cyan** - Borders, headers, highlights
- **Dim/Gray** - Secondary text, hints
- **Green** - Success, checkmarks
- **Yellow** - Warnings, attention
- **White/Default** - Primary text

---

## Box Drawing Characters

```
╭ ╮ ╰ ╯  - Rounded corners
─ │      - Lines
├ ┤ ┬ ┴  - T-junctions
└ ┘ ┌ ┐  - Square corners
```

---

## Symbols Used

```
⏺ - Filled circle (active)
◯ - Empty circle (inactive)
⏵ - Play/forward arrow
✶ - Star (thinking)
✻ - Asterisk (stats)
⎿ - Tool indicator
❯ - Selection arrow
✔ - Checkmark
● - Bullet point
```

---

## Layout Patterns

### Two-Column Welcome
```
╭─── Title ───────────────────────────╮
│ Main Content    │ Sidebar           │
│                 │ - Tips            │
│                 │ - What's new      │
╰─────────────────────────────────────╯
```

### Tree Structure
```
⏺ Parent
   ├ Child 1
   │ └ Detail
   ├ Child 2
   └ Child 3
```

### Menu with Selection
```
  1. Option one
❯ 2. Option two ✔
  3. Option three
```

---

## Implementation for Lyra

### Priority 1: Welcome Banner
- Two-column layout
- ASCII art logo
- User greeting
- Tips sidebar
- What's new section

### Priority 2: Status Indicators
- ⏺ for active status
- ⏵⏵ for mode
- ✶ for thinking
- Tree structure for agents

### Priority 3: Interactive Menus
- Numbered options
- Selection arrow ❯
- Checkmarks ✔
- Keyboard hints

### Priority 4: Progress Display
- Real-time token counts
- Tool use tree
- Time indicators
- Collapsible sections

---

## Key Takeaways

1. **Rich box drawing** - Extensive use of Unicode box characters
2. **Two-column layouts** - Main + sidebar pattern
3. **Tree structures** - For hierarchical data
4. **Real-time updates** - Token counts, timers
5. **Keyboard hints** - Always visible
6. **Status symbols** - Consistent icon language
7. **Collapsible sections** - Reduce clutter
8. **Full-width dividers** - Clear visual separation

---

**Status**: ✅ Analysis Complete
