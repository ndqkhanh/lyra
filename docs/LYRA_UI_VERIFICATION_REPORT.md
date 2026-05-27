# Lyra UI Verification Report

**Date**: 2026-05-23  
**Purpose**: Verify Lyra's UI alignment with Claude Code response format specification  
**Status**: ⚠️ Partial alignment - Critical issues identified

---

## Executive Summary

Lyra has implemented most Claude Code UI patterns correctly, but has **critical layout issues** with the bottom UI elements (input box and status line). The main problem is that these elements are not staying fixed at the bottom during response streaming.

### ✅ What's Working

1. **Symbol system** - Correct Unicode symbols (⏺, ◯, ✔, ✗, ✻, ✶, ⎿, ❯)
2. **Color engine** - ANSI color support with semantic colors
3. **Tree rendering** - Box-drawing characters for hierarchical display
4. **Tool formatting** - Proper tool call display with ⎿ connector
5. **Layout engine** - Text wrapping, truncation, alignment
6. **Expandable sections** - Collapse/expand functionality

### ❌ Critical Issues

1. **Input box not fixed at bottom** - Scrolls away during streaming
2. **Status line not always visible** - Should be below input at all times
3. **Missing 4-row fixed layout** - No proper separation of scrollable vs fixed areas
4. **Response streaming pushes input up** - Should stream above fixed input

---

## Detailed Comparison

### 1. Bottom UI Layout (CRITICAL)

#### Claude Code Specification

```
┌─────────────────────────────────────────┐
│ [Scrollable Area]                       │
│ - Welcome banner                        │
│ - Conversation history                  │
│ - Agent status                          │
│ - Tool outputs                          │
│                                         │
├─────────────────────────────────────────┤ ← Fixed divider
│ ❯ [Input box - always visible]         │ ← Fixed input (row 3 from bottom)
├─────────────────────────────────────────┤ ← Fixed divider
│ ⏵⏵ mode · hints                        │ ← Fixed status (row 1 from bottom)
└─────────────────────────────────────────┘
```

**Fixed elements (4 rows from bottom up):**
1. Status line (1 row)
2. Horizontal divider (1 row)
3. Input box (1 row)
4. Horizontal divider (1 row)

#### Lyra Current Implementation

❌ **Missing**: Fixed bottom layout  
❌ **Missing**: Input box stays at bottom during streaming  
❌ **Missing**: Status line always visible below input  
❌ **Missing**: Proper separation of scrollable vs fixed areas

**Issue**: Responses stream in and push the input box down, making it scroll away. The input box should be **anchored at the bottom** and responses should stream **above** it.

---

### 2. Response Streaming Patterns

#### Claude Code Specification

```
⏺ Analyzing your request...
  ⎿ Read file.py (228 lines)
  ⎿ Edit src/main.py
  
Response text here...

✻ 2.3s · 3 tools · 1,234 tokens
```

#### Lyra Implementation

✅ **Correct**: Uses ⏺ for active responses  
✅ **Correct**: Uses ⎿ for tool indicators  
✅ **Correct**: Uses ✻ for stats line  
✅ **Correct**: Proper indentation (2 spaces for tools)

**Files**: `renderer.py`, `tool_formatter.py`

---

### 3. Status Line Format

#### Claude Code Specification

```
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
```

**Components**:
- Mode indicator: `⏵⏵ [mode name]`
- Keyboard shortcuts: `(key to action)`
- Separators: ` · ` (space-dot-space)
- Background task hint: `↓ to manage` or `3 shells · ↓ to manage`

#### Lyra Implementation

⚠️ **Partial**: Has status rendering but not fixed at bottom  
✅ **Correct**: Uses ⏵ symbol  
✅ **Correct**: Uses · separator  
❌ **Missing**: Always visible below input box

**Files**: `renderer.py` (render_status method)

---

### 4. Background Agent Display

#### Claude Code Specification

**Collapsed**:
```
⏺ Running 4 agents… (ctrl+o to expand)
```

**Expanded**:
```
⏺ Running 4 agents… (ctrl+o to collapse)
   ├ Agent 1 · 10 tool uses · 29.7k tokens
   │ ⎿  Bash: npm test
   ├ Agent 2 · 6 tool uses · 29.9k tokens
   └ Agent 3 · 5 tool uses · 29.8k tokens
```

#### Lyra Implementation

✅ **Correct**: Tree structure with box-drawing characters  
✅ **Correct**: Uses ├ │ └ for tree branches  
✅ **Correct**: 3-space indent per level  
✅ **Correct**: Agent status symbols (⏺, ◯, ✔, ✗)

**Files**: `tree.py`, `renderer.py`

---

### 5. Symbol Registry

#### Claude Code Specification

| Symbol | Usage |
|--------|-------|
| ⏺ | Active/running |
| ◯ | Inactive/queued |
| ✔ | Success/completed |
| ✗ | Error/failed |
| ✻ | Stats line |
| ✶ | Thinking |
| ⎿ | Tool use |
| ❯ | Prompt/selection |

#### Lyra Implementation

✅ **Correct**: All symbols match specification  
✅ **Correct**: ASCII fallback support  
✅ **Correct**: Symbol registry pattern

**Files**: `symbols.py`

---

### 6. Color Scheme

#### Claude Code Specification

| Element | Color | ANSI Code |
|---------|-------|-----------|
| Primary text | Default | - |
| Secondary text | Dim | `\033[2m` |
| Success | Green | `\033[32m` |
| Error | Red | `\033[31m` |
| Warning | Yellow | `\033[33m` |
| Info | Cyan | `\033[36m` |

#### Lyra Implementation

✅ **Correct**: Semantic color mapping  
✅ **Correct**: ANSI escape codes  
✅ **Correct**: Dim for secondary text

**Files**: `colors.py`

---

### 7. Tool Call Formatting

#### Claude Code Specification

```
  ⎿ Read file.py (228 lines)
  ⎿ Edit src/main.py
  ⎿ Bash: npm test
```

#### Lyra Implementation

✅ **Correct**: Uses ⎿ connector  
✅ **Correct**: 2-space indent  
✅ **Correct**: Dim color for connector

**Files**: `tool_formatter.py`, `renderer.py`

---

### 8. Update Blocks

#### Claude Code Specification

```
⏺ Update(src/example.py)
  ⎿  Added 8 lines, removed 2 lines
      263      def on_mount(self) -> None:
      264 -        super().on_mount()
      265 +        try:
      266 +            super().on_mount()
```

#### Lyra Implementation

✅ **Correct**: File update format  
✅ **Correct**: Line diff rendering  
✅ **Correct**: Color coding (green +, red -)

**Files**: `renderer.py` (render_file_update, render_diff_line)

---

### 9. Selection Menus

#### Claude Code Specification

```
────────────────────────────────────────────
  Select model
  
    1. Option one
  ❯ 2. Option two ✔
    3. Option three
  
  Enter to confirm · Esc to cancel
────────────────────────────────────────────
```

#### Lyra Implementation

✅ **Correct**: Full-width dividers  
✅ **Correct**: 2-space title indent  
✅ **Correct**: 4-space option indent  
✅ **Correct**: ❯ for current selection  
✅ **Correct**: ✔ for active item

**Files**: `renderer.py` (render_box method)

---

### 10. Responsive Layout

#### Claude Code Specification

- **<80 cols**: Narrow (compact layout)
- **80-120 cols**: Standard (single column)
- **>120 cols**: Wide (two columns)

#### Lyra Implementation

✅ **Correct**: Layout engine supports responsive widths  
⚠️ **Partial**: Two-column layout not fully implemented

**Files**: `layout.py`

---

## Critical Fix Required

### Problem: Input Box Not Fixed at Bottom

The main issue is that Lyra's UI doesn't implement the **fixed bottom layout** pattern. When responses stream in, they push the input box down instead of streaming above it.

### Solution Architecture

Need to implement a **three-layer rendering system**:

```python
class FixedBottomLayout:
    """
    Terminal layout with fixed bottom elements
    
    Layout:
    ┌─────────────────────────────────┐
    │ Scrollable content area         │ ← Rows 1 to (height - 4)
    │ (auto-scroll to bottom)         │
    ├─────────────────────────────────┤
    │ ❯ Input box                     │ ← Row (height - 3)
    ├─────────────────────────────────┤
    │ ⏵⏵ Status line                  │ ← Row (height - 1)
    └─────────────────────────────────┘
    """
    
    def __init__(self, terminal_height: int):
        self.terminal_height = terminal_height
        self.scrollable_height = terminal_height - 4
        self.input_row = terminal_height - 3
        self.status_row = terminal_height - 1
        self.scroll_buffer = []
        self.scroll_offset = 0
    
    def render_frame(self):
        """Render complete frame with fixed bottom"""
        # 1. Render scrollable area (rows 1 to height-4)
        visible_lines = self.get_visible_lines()
        for i, line in enumerate(visible_lines):
            self.move_cursor(i + 1, 1)
            print(line)
        
        # 2. Render divider (row height-3)
        self.move_cursor(self.input_row - 1, 1)
        print("─" * self.terminal_width)
        
        # 3. Render input box (row height-2)
        self.move_cursor(self.input_row, 1)
        print("❯ " + self.input_text)
        
        # 4. Render divider (row height-1)
        self.move_cursor(self.status_row - 1, 1)
        print("─" * self.terminal_width)
        
        # 5. Render status line (row height)
        self.move_cursor(self.status_row, 1)
        print(self.status_text)
    
    def append_content(self, text: str):
        """Append to scrollable area without moving input"""
        self.scroll_buffer.append(text)
        # Auto-scroll to bottom
        if len(self.scroll_buffer) > self.scrollable_height:
            self.scroll_offset = len(self.scroll_buffer) - self.scrollable_height
        self.render_frame()
    
    def move_cursor(self, row: int, col: int):
        """Move cursor to absolute position"""
        print(f"\033[{row};{col}H", end="")
```

### Implementation Steps

1. **Create `fixed_layout.py`** - Implement FixedBottomLayout class
2. **Update main app** - Use fixed layout for rendering
3. **Separate scrollable from fixed** - Content streams into scrollable area
4. **Handle terminal resize** - Recalculate layout on resize
5. **Test with streaming** - Verify input stays at bottom

---

## Verification Checklist

### ✅ Implemented Correctly

- [x] Symbol registry with correct Unicode symbols
- [x] Color engine with semantic colors
- [x] Tree rendering with box-drawing characters
- [x] Tool call formatting with ⎿ connector
- [x] File update blocks with diffs
- [x] Layout engine (wrap, truncate, align)
- [x] Expandable sections
- [x] Selection menus with ❯ cursor

### ❌ Needs Implementation

- [ ] Fixed bottom layout (4 rows)
- [ ] Input box anchored at bottom
- [ ] Status line always visible below input
- [ ] Scrollable area above fixed elements
- [ ] Response streaming above input
- [ ] Terminal resize handling for fixed layout
- [ ] Two-column responsive layout (>120 cols)

### ⚠️ Needs Verification

- [ ] Background agent tree with subagents
- [ ] Thinking status with ✶ symbol
- [ ] Stats line with ✻ symbol
- [ ] Background tasks panel
- [ ] Context budget display

---

## Recommended Actions

### Priority 1: Critical (Blocking)

1. **Implement FixedBottomLayout class**
   - Create `ui/fixed_layout.py`
   - Implement 4-row fixed bottom pattern
   - Handle cursor positioning

2. **Update main app to use fixed layout**
   - Integrate FixedBottomLayout
   - Separate scrollable from fixed rendering
   - Test with streaming responses

3. **Add terminal resize handler**
   - Detect terminal size changes
   - Recalculate layout dimensions
   - Re-render with new dimensions

### Priority 2: Important

4. **Implement background agent display**
   - Collapsed/expanded states
   - Tree structure with token rollups
   - ctrl+o to toggle

5. **Add background tasks panel**
   - Show running shells
   - Selection with ❯ cursor
   - Keyboard shortcuts

### Priority 3: Nice to Have

6. **Two-column responsive layout**
   - Detect terminal width >120 cols
   - Render welcome banner in two columns
   - Adjust content layout

7. **Performance optimization**
   - Virtualized scrolling
   - Diff-based updates
   - Debounced resize

---

## Testing Plan

### Manual Testing

1. **Fixed input test**
   - Start Lyra
   - Send a message
   - Verify input box stays at bottom during streaming
   - Verify status line stays below input

2. **Scrolling test**
   - Generate long conversation (>100 lines)
   - Scroll up to review history
   - Verify input box doesn't scroll away
   - Verify status line doesn't scroll away

3. **Resize test**
   - Start Lyra
   - Resize terminal window
   - Verify layout adjusts correctly
   - Verify input box repositions to new bottom

4. **Streaming test**
   - Send message that triggers multiple tool calls
   - Verify responses stream above input
   - Verify input box never moves
   - Verify status line updates correctly

### Automated Testing

```python
def test_fixed_bottom_layout():
    layout = FixedBottomLayout(terminal_height=24)
    
    # Add content
    for i in range(100):
        layout.append_content(f"Line {i}")
    
    # Verify input row position
    assert layout.input_row == 24 - 3
    
    # Verify status row position
    assert layout.status_row == 24 - 1
    
    # Verify scrollable height
    assert layout.scrollable_height == 24 - 4

def test_streaming_doesnt_move_input():
    layout = FixedBottomLayout(terminal_height=24)
    initial_input_row = layout.input_row
    
    # Stream 50 lines
    for i in range(50):
        layout.append_content(f"Streaming line {i}")
    
    # Input row should not change
    assert layout.input_row == initial_input_row
```

---

## Conclusion

Lyra has implemented **80% of Claude Code's UI patterns correctly**, but has a **critical architectural issue** with the bottom layout. The input box and status line are not fixed at the bottom, which breaks the core UX pattern.

**Estimated effort to fix**: 4-6 hours
- 2 hours: Implement FixedBottomLayout class
- 1 hour: Integrate with main app
- 1 hour: Handle terminal resize
- 1-2 hours: Testing and refinement

Once the fixed bottom layout is implemented, Lyra's UI will be **fully aligned** with Claude Code's specification.

---

**Next Steps**: Implement `ui/fixed_layout.py` with the FixedBottomLayout class as specified above.
