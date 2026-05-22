# 03. Layouts - Lyra UI/UX Plan

**Version**: 1.0  
**Status**: ✅ Complete  
**Last Updated**: 2026-05-21

---

## Overview

This document defines layout templates and patterns for Lyra's terminal interface. Layouts provide consistent structure across different views and ensure optimal information hierarchy.

---

## Layout Principles

### 1. Consistency
- Same layout patterns across similar views
- Predictable element placement
- Consistent spacing and alignment

### 2. Hierarchy
- Most important content first
- Clear visual hierarchy
- Progressive disclosure

### 3. Responsiveness
- Adapt to terminal width
- Graceful degradation on narrow terminals
- Minimum width: 80 columns

### 4. Efficiency
- Maximize content area
- Minimize chrome and decoration
- Focus on information density

---

## Core Layout Patterns

### 1. Full-Screen Layout

**Use Case**: Main chat interface, agent view

```
╭─────────────────────────────────────────────────────────────╮
│ Header (1 line)                                             │
╰─────────────────────────────────────────────────────────────╯

┌─ Content Area ──────────────────────────────────────────────┐
│                                                              │
│  Main content scrolls here                                  │
│  Takes up most of the screen                                │
│  Dynamically sized based on terminal height                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘

╭─────────────────────────────────────────────────────────────╮
│ Footer (1 line) - Status, tips, shortcuts                  │
╰─────────────────────────────────────────────────────────────╯
```

**Components**:
- Header: App title, mode, status
- Content: Scrollable main area
- Footer: Status bar, tips, shortcuts

**Spacing**:
- Header: 1 line + 1 line padding
- Content: Terminal height - header - footer - 4 lines
- Footer: 1 line + 1 line padding

---

### 2. Split-Pane Layout

**Use Case**: Side-by-side comparison, diff view, multi-agent view

```
╭─────────────────────────────────────────────────────────────╮
│ Header                                                      │
╰─────────────────────────────────────────────────────────────╯

┌─ Left Pane ──────────┬─ Right Pane ──────────────────────────┐
│                      │                                       │
│  Primary content     │  Secondary content                    │
│  50% width           │  50% width                            │
│                      │                                       │
└──────────────────────┴───────────────────────────────────────┘

╭─────────────────────────────────────────────────────────────╮
│ Footer                                                      │
╰─────────────────────────────────────────────────────────────╯
```

**Variants**:
- 50/50 split (equal importance)
- 70/30 split (primary/secondary)
- 60/40 split (main/detail)

**Responsive Behavior**:
- Width < 120 cols: Stack vertically
- Width < 80 cols: Show one pane at a time

---

### 3. Dashboard Layout

**Use Case**: Metrics, status overview, agent dashboard

```
╭─────────────────────────────────────────────────────────────╮
│ Dashboard Title                                             │
╰─────────────────────────────────────────────────────────────╯

┌─ Key Metrics ───────────────────────────────────────────────┐
│  Metric 1: Value    Metric 2: Value    Metric 3: Value     │
└──────────────────────────────────────────────────────────────┘

┌─ Section 1 ──────────┬─ Section 2 ──────────────────────────┐
│                      │                                       │
│  Widget 1            │  Widget 2                             │
│                      │                                       │
├──────────────────────┴───────────────────────────────────────┤
│                                                              │
│  Section 3 (Full Width)                                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Components**:
- Title bar: Dashboard name, refresh time
- Key metrics: 3-5 most important metrics
- Sections: Grouped widgets
- Widgets: Individual data displays

---

### 4. List Layout

**Use Case**: File lists, command history, search results

```
╭─────────────────────────────────────────────────────────────╮
│ List Title                                    Count: 42     │
╰─────────────────────────────────────────────────────────────╯

┌─ Filters/Actions ───────────────────────────────────────────┐
│  [Filter 1] [Filter 2] [Sort ▼]                [Search 🔍] │
└──────────────────────────────────────────────────────────────┘

┌─ Items ─────────────────────────────────────────────────────┐
│  ○ Item 1                                              Meta │
│  ○ Item 2                                              Meta │
│  ● Item 3 (selected)                                   Meta │
│  ○ Item 4                                              Meta │
│  ...                                                        │
└──────────────────────────────────────────────────────────────┘

╭─────────────────────────────────────────────────────────────╮
│ Page 1 of 5                              [Prev] [Next]     │
╰─────────────────────────────────────────────────────────────╯
```

**Features**:
- Title with count
- Filters and search
- Scrollable item list
- Pagination controls

---

### 5. Detail View Layout

**Use Case**: File viewer, message detail, agent detail

```
╭─────────────────────────────────────────────────────────────╮
│ ← Back    Detail Title                                      │
╰─────────────────────────────────────────────────────────────╯

┌─ Metadata ──────────────────────────────────────────────────┐
│  Property 1: Value                                          │
│  Property 2: Value                                          │
│  Property 3: Value                                          │
└──────────────────────────────────────────────────────────────┘

┌─ Content ───────────────────────────────────────────────────┐
│                                                              │
│  Main content area                                          │
│  Scrollable                                                 │
│  Full width                                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌─ Actions ───────────────────────────────────────────────────┐
│  [Action 1]  [Action 2]  [Action 3]                        │
└──────────────────────────────────────────────────────────────┘
```

**Sections**:
- Navigation: Back button, title
- Metadata: Key properties
- Content: Main detail area
- Actions: Available operations

---

## Specific View Layouts

### Chat Interface Layout

```
╭─────────────────────────────────────────────────────────────╮
│ 🌟 Lyra v3.14.0                              💬 Chat Mode │
╰─────────────────────────────────────────────────────────────╯

┌─ Conversation ──────────────────────────────────────────────┐
│                                                              │
│  ┌─ 🤖 Assistant ─────────────────────────────────────────┐ │
│  │ Message content...                                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ 👤 You ───────────────────────────────────────────────┐ │
│  │ Message content...                                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ⚡ tool_call(...)                                          │
│  ✅ Result                                                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘

╭─────────────────────────────────────────────────────────────╮
│ 💡 Tip: Use /help for commands    [Ctrl+C] Cancel          │
╰─────────────────────────────────────────────────────────────╯
```

**Layout Rules**:
- Messages stack vertically
- Most recent at bottom
- Auto-scroll to latest
- Tool calls inline between messages
- Footer shows tips and shortcuts

---

### Agent View Layout

```
╭─────────────────────────────────────────────────────────────╮
│ 🤖 Agent Dashboard                          Last: 2s ago   │
╰─────────────────────────────────────────────────────────────╯

┌─ Status ────────────────────────────────────────────────────┐
│  State: 🟢 Active    Task: Processing request               │
│  Cost: $0.42    Tokens: 1.2K    Time: 45s                  │
└──────────────────────────────────────────────────────────────┘

┌─ Current Task ──────┬─ Memory ─────────────────────────────┐
│                     │                                       │
│  Task details       │  Recent memories                      │
│  Progress: 60%      │  Relevant context                     │
│                     │                                       │
├─────────────────────┴───────────────────────────────────────┤
│                                                              │
│  Recent Activity (scrollable)                               │
│  • Action 1                                                 │
│  • Action 2                                                 │
│  • Action 3                                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘

╭─────────────────────────────────────────────────────────────╮
│ [Pause] [Stop] [Details]                    [Refresh: 2s]  │
╰─────────────────────────────────────────────────────────────╯
```

**Sections**:
- Status bar: Current state and metrics
- Split view: Task + Memory
- Activity log: Recent actions
- Controls: Action buttons

---

### Goal Mode Layout

```
╭─────────────────────────────────────────────────────────────╮
│ 🎯 Goal Mode: Fix authentication bug                       │
╰─────────────────────────────────────────────────────────────╯

┌─ Progress ──────────────────────────────────────────────────┐
│  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 40%     │
│  Step 3 of 7: Analyzing code                               │
└──────────────────────────────────────────────────────────────┘

┌─ Current Step ──────────────────────────────────────────────┐
│  📖 Reading src/auth.py                                     │
│  ⏳ In progress... (12s)                                    │
└──────────────────────────────────────────────────────────────┘

┌─ Plan ──────────────────────────────────────────────────────┐
│  ✅ 1. Understand the bug                                   │
│  ✅ 2. Read error logs                                      │
│  🔄 3. Analyze code                                         │
│  ⏳ 4. Identify root cause                                  │
│  ⏳ 5. Implement fix                                        │
│  ⏳ 6. Test fix                                             │
│  ⏳ 7. Verify and commit                                    │
└──────────────────────────────────────────────────────────────┘

╭─────────────────────────────────────────────────────────────╮
│ Budget: $2.50 / $5.00    Time: 2m / 10m    [Pause] [Stop] │
╰─────────────────────────────────────────────────────────────╯
```

**Features**:
- Progress bar with percentage
- Current step highlight
- Full plan with status icons
- Budget and time tracking
- Control buttons

---

## Responsive Behavior

### Terminal Width Breakpoints

**Wide (≥ 120 columns)**:
- Full split-pane layouts
- Side-by-side comparisons
- Maximum information density

**Medium (80-119 columns)**:
- Adjusted split ratios (60/40 or 70/30)
- Some elements stack
- Reduced padding

**Narrow (< 80 columns)**:
- Single column layout
- Vertical stacking
- Minimal padding
- Essential information only

### Adaptive Strategies

**Content Truncation**:
```python
def truncate_for_width(text: str, max_width: int) -> str:
    if len(text) <= max_width:
        return text
    return text[:max_width - 3] + "..."
```

**Dynamic Columns**:
```python
def calculate_columns(terminal_width: int) -> int:
    if terminal_width >= 120:
        return 2  # Split pane
    return 1  # Single column
```

**Responsive Padding**:
```python
def get_padding(terminal_width: int) -> int:
    if terminal_width >= 120:
        return 4  # Spacious
    elif terminal_width >= 80:
        return 2  # Compact
    return 1  # Minimal
```

---

## Layout Components

### Header Component

```python
class Header:
    def __init__(self, title: str, subtitle: str = "", right_text: str = ""):
        self.title = title
        self.subtitle = subtitle
        self.right_text = right_text
    
    def render(self, width: int) -> str:
        left = f"{self.title}"
        if self.subtitle:
            left += f" {self.subtitle}"
        
        # Calculate spacing
        padding = width - len(left) - len(self.right_text)
        
        return f"╭{'─' * (width - 2)}╮\n│ {left}{' ' * padding}{self.right_text} │\n╰{'─' * (width - 2)}╯"
```

### Footer Component

```python
class Footer:
    def __init__(self, left_text: str = "", right_text: str = ""):
        self.left_text = left_text
        self.right_text = right_text
    
    def render(self, width: int) -> str:
        padding = width - len(self.left_text) - len(self.right_text) - 4
        return f"╭{'─' * (width - 2)}╮\n│ {self.left_text}{' ' * padding}{self.right_text} │\n╰{'─' * (width - 2)}╯"
```

### Panel Component

```python
class Panel:
    def __init__(self, title: str, content: str, border_color: str = ""):
        self.title = title
        self.content = content
        self.border_color = border_color
    
    def render(self, width: int) -> str:
        lines = [
            f"┌─ {self.title} {'─' * (width - len(self.title) - 5)}┐"
        ]
        
        for line in self.content.split('\n'):
            lines.append(f"│ {line.ljust(width - 4)} │")
        
        lines.append(f"└{'─' * (width - 2)}┘")
        
        return '\n'.join(lines)
```

---

## Layout Best Practices

### 1. Consistent Spacing
- Use design system spacing units (4px base)
- Maintain consistent padding within sections
- Align elements to grid

### 2. Clear Hierarchy
- Most important content at top
- Group related information
- Use visual weight (size, color, borders)

### 3. Efficient Use of Space
- Maximize content area
- Minimize chrome
- Use progressive disclosure for details

### 4. Accessibility
- Maintain minimum contrast ratios
- Support keyboard navigation
- Provide text alternatives for symbols

### 5. Performance
- Lazy render off-screen content
- Cache rendered layouts
- Minimize redraws

---

## Implementation Notes

### Layout Manager

```python
class LayoutManager:
    def __init__(self, terminal_width: int, terminal_height: int):
        self.width = terminal_width
        self.height = terminal_height
    
    def get_content_area(self) -> tuple[int, int]:
        """Returns (width, height) of content area after header/footer"""
        return (self.width, self.height - 4)  # 2 lines header, 2 lines footer
    
    def should_split_pane(self) -> bool:
        """Determine if split pane layout is appropriate"""
        return self.width >= 120
    
    def get_split_ratio(self) -> tuple[int, int]:
        """Returns (left_width, right_width) for split pane"""
        if self.width >= 140:
            return (self.width // 2, self.width // 2)
        return (int(self.width * 0.6), int(self.width * 0.4))
```

---

## Testing Layouts

### Test Cases

1. **Terminal Sizes**:
   - 80x24 (minimum)
   - 120x40 (medium)
   - 160x60 (large)

2. **Content Overflow**:
   - Long lines
   - Many items
   - Deep nesting

3. **Dynamic Resizing**:
   - Expand terminal
   - Shrink terminal
   - Maintain state

4. **Edge Cases**:
   - Empty content
   - Single item
   - Maximum items

---

## Summary

This layout system provides:
- ✅ 5 core layout patterns
- ✅ Responsive behavior (3 breakpoints)
- ✅ Specific view layouts (chat, agent, goal)
- ✅ Reusable components (header, footer, panel)
- ✅ Best practices and guidelines
- ✅ Implementation examples

**Next**: See 04-ANIMATIONS.md for animation and transition patterns.
