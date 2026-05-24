# Lyra Status Line Enhancement - Context & Mode Display

**Date**: 2026-05-23  
**Purpose**: Add context percentage and permission mode to bottom status line

---

## Current Status Line (Claude Code Style)

```
────────────────────────────────────────────────────────────────────────────────
❯ [user input]
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
```

**Elements**:
- `⏵⏵` - Mode indicator
- `bypass permissions on` - Permission mode
- `(shift+tab to cycle)` - Mode switch hint
- `esc to interrupt` - Keyboard hint
- `↓ to manage` - Background tasks hint

---

## Enhanced Status Line for Lyra

### Design 1: Context Percentage on Left, Mode on Right

```
────────────────────────────────────────────────────────────────────────────────
❯ [user input]
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ 45% context · bypass permissions · esc to exit · ↓ to manage
```

**Elements**:
- `⏵⏵` - Mode indicator
- `45% context` - Context window usage percentage
- `bypass permissions` - Permission mode (bypass/ask/deny)
- `esc to exit` - Keyboard hint
- `↓ to manage` - Background tasks hint

### Design 2: Context Bar with Visual Indicator

```
────────────────────────────────────────────────────────────────────────────────
❯ [user input]
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ [████████░░] 45% · bypass permissions · esc to exit · ↓ to manage
```

**Elements**:
- `[████████░░]` - Visual progress bar (10 chars)
- `45%` - Exact percentage
- Rest same as Design 1

### Design 3: Compact with Color Coding

```
────────────────────────────────────────────────────────────────────────────────
❯ [user input]
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ ctx:45% · mode:bypass · esc to exit · ↓ to manage
```

**Color Coding**:
- `ctx:45%` - Green (<50%), Yellow (50-80%), Red (>80%)
- `mode:bypass` - Yellow (bypass), Green (ask), Red (deny)

---

## Recommended Design: Design 1 (Simple & Clear)

```
  ⏵⏵ 45% context · bypass permissions · esc to exit · ↓ to manage
```

**Why**:
- ✅ Clean and readable
- ✅ Matches Claude Code's style
- ✅ No visual clutter
- ✅ Easy to implement
- ✅ Color coding can be added later

---

## Implementation Plan

### 1. Update StatusLine Class

**File**: `packages/lyra-cli/src/lyra_cli/ui/status_line.py`

```python
"""Status line with context and mode display"""

from typing import List, Optional
from .colors import ColorEngine


class StatusLine:
    """Fixed status line below input"""
    
    def __init__(self):
        self.colors = ColorEngine()
        self.mode = "default"
        self.hints: List[str] = []
        self.context_percentage = 0
        self.permission_mode = "ask"  # ask, bypass, deny
    
    def update(
        self,
        mode: str,
        hints: List[str],
        context_percentage: Optional[int] = None,
        permission_mode: Optional[str] = None
    ):
        """Update status line content
        
        Args:
            mode: Current mode (default, streaming, thinking, etc.)
            hints: Keyboard hints to display
            context_percentage: Context window usage (0-100)
            permission_mode: Permission mode (ask, bypass, deny)
        """
        self.mode = mode
        self.hints = hints
        
        if context_percentage is not None:
            self.context_percentage = context_percentage
        
        if permission_mode is not None:
            self.permission_mode = permission_mode
    
    def render(self) -> str:
        """Render status line"""
        parts = []
        
        # Mode indicator
        parts.append(f"⏵⏵ {self.mode}")
        
        # Context percentage (if available)
        if self.context_percentage > 0:
            ctx_text = f"{self.context_percentage}% context"
            
            # Color code based on usage
            if self.context_percentage < 50:
                ctx_text = self.colors.green(ctx_text)
            elif self.context_percentage < 80:
                ctx_text = self.colors.yellow(ctx_text)
            else:
                ctx_text = self.colors.red(ctx_text)
            
            parts.append(ctx_text)
        
        # Permission mode
        if self.permission_mode:
            mode_text = f"{self.permission_mode} permissions"
            
            # Color code based on mode
            if self.permission_mode == "bypass":
                mode_text = self.colors.yellow(mode_text)
            elif self.permission_mode == "ask":
                mode_text = self.colors.green(mode_text)
            elif self.permission_mode == "deny":
                mode_text = self.colors.red(mode_text)
            
            parts.append(mode_text)
        
        # Keyboard hints
        parts.extend(self.hints)
        
        # Join with separator
        status = "  " + " · ".join(parts)
        
        return status
    
    def render_inline(self):
        """Render status line inline (no newline)"""
        print(self.render(), end="", flush=True)
    
    def get_context_color(self, percentage: int) -> str:
        """Get color for context percentage
        
        Args:
            percentage: Context usage percentage (0-100)
        
        Returns:
            Color name (green, yellow, red)
        """
        if percentage < 50:
            return "green"
        elif percentage < 80:
            return "yellow"
        else:
            return "red"
    
    def get_permission_color(self, mode: str) -> str:
        """Get color for permission mode
        
        Args:
            mode: Permission mode (ask, bypass, deny)
        
        Returns:
            Color name (green, yellow, red)
        """
        if mode == "bypass":
            return "yellow"
        elif mode == "ask":
            return "green"
        elif mode == "deny":
            return "red"
        else:
            return "default"
```

### 2. Update SequentialREPL to Track Context

**File**: `packages/lyra-cli/src/lyra_cli/repl/sequential_repl.py`

```python
class SequentialREPL:
    """REPL with sequential output and fixed bottom UI"""
    
    def __init__(self):
        # ... existing code ...
        
        # Context tracking
        self.context_budget = 200000  # Total context window
        self.context_used = 0         # Tokens used
        self.permission_mode = "ask"  # ask, bypass, deny
    
    def update_context(self, tokens_used: int):
        """Update context usage
        
        Args:
            tokens_used: Number of tokens used in this turn
        """
        self.context_used += tokens_used
        
        # Calculate percentage
        percentage = int((self.context_used / self.context_budget) * 100)
        
        # Update status line
        self.status_line.update(
            mode=self.current_mode,
            hints=self.current_hints,
            context_percentage=percentage,
            permission_mode=self.permission_mode
        )
    
    def set_permission_mode(self, mode: str):
        """Set permission mode
        
        Args:
            mode: Permission mode (ask, bypass, deny)
        """
        if mode not in ["ask", "bypass", "deny"]:
            raise ValueError(f"Invalid permission mode: {mode}")
        
        self.permission_mode = mode
        
        # Update status line
        self.status_line.update(
            mode=self.current_mode,
            hints=self.current_hints,
            context_percentage=self._get_context_percentage(),
            permission_mode=self.permission_mode
        )
    
    def _get_context_percentage(self) -> int:
        """Get current context usage percentage"""
        return int((self.context_used / self.context_budget) * 100)
    
    def _on_turn_finished(self, event):
        """Handle turn finished"""
        # ... existing code ...
        
        # Update context usage
        total_tokens = event.tokens_in + event.tokens_out
        self.update_context(total_tokens)
        
        # Re-render bottom UI with updated context
        self._render_bottom_ui()
```

### 3. Add Keyboard Shortcut to Cycle Permission Mode

**File**: `packages/lyra-cli/src/lyra_cli/repl/keyboard.py`

```python
class KeyboardHandler:
    """Handle keyboard input with special keys"""
    
    def read_key(self) -> Optional[str]:
        """Read a single key press"""
        # ... existing code ...
        
        # Shift+Tab (cycle permission mode)
        if char == '\x1b[Z':
            return 'shift+tab'
        
        # ... rest of existing code ...
```

**Update SequentialREPL**:

```python
def __init__(self):
    # ... existing code ...
    
    # Setup keyboard shortcuts
    self.keyboard.on_key('shift+tab', self._cycle_permission_mode)

def _cycle_permission_mode(self):
    """Cycle through permission modes"""
    modes = ["ask", "bypass", "deny"]
    current_index = modes.index(self.permission_mode)
    next_index = (current_index + 1) % len(modes)
    
    self.set_permission_mode(modes[next_index])
    
    # Show notification
    print(f"\n  Permission mode: {self.permission_mode}")
    self._render_bottom_ui()
```

---

## Visual Examples

### Low Context Usage (< 50%)

```
────────────────────────────────────────────────────────────────────────────────
❯ What is Python?
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ default · 23% context · ask permissions · esc to exit · ↓ to manage
                  ^^^^^^^^^^^ (green)
```

### Medium Context Usage (50-80%)

```
────────────────────────────────────────────────────────────────────────────────
❯ Explain machine learning
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ streaming · 67% context · bypass permissions · esc to interrupt
                   ^^^^^^^^^^^ (yellow)  ^^^^^^^^^^^^^^^^^ (yellow)
```

### High Context Usage (> 80%)

```
────────────────────────────────────────────────────────────────────────────────
❯ Continue the conversation
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ default · 92% context · ask permissions · esc to exit · ↓ to manage
                 ^^^^^^^^^^^ (red)
```

### Bypass Mode Active

```
────────────────────────────────────────────────────────────────────────────────
❯ Run dangerous command
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ default · 45% context · bypass permissions · shift+tab to cycle
                               ^^^^^^^^^^^^^^^^^ (yellow - warning)
```

### Deny Mode Active

```
────────────────────────────────────────────────────────────────────────────────
❯ Try to execute
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ default · 45% context · deny permissions · shift+tab to cycle
                               ^^^^^^^^^^^^^^^ (red - blocked)
```

---

## Context Percentage Calculation

### Method 1: Token Counting (Recommended)

```python
def calculate_context_percentage(
    tokens_used: int,
    context_budget: int = 200000
) -> int:
    """Calculate context usage percentage
    
    Args:
        tokens_used: Total tokens used in conversation
        context_budget: Total context window size
    
    Returns:
        Percentage (0-100)
    """
    return int((tokens_used / context_budget) * 100)
```

### Method 2: Message Counting (Alternative)

```python
def calculate_context_percentage_by_messages(
    message_count: int,
    max_messages: int = 50
) -> int:
    """Calculate context usage by message count
    
    Args:
        message_count: Number of messages in conversation
        max_messages: Maximum messages before compaction
    
    Returns:
        Percentage (0-100)
    """
    return int((message_count / max_messages) * 100)
```

### Method 3: Hybrid (Most Accurate)

```python
def calculate_context_percentage_hybrid(
    tokens_used: int,
    message_count: int,
    context_budget: int = 200000,
    max_messages: int = 50
) -> int:
    """Calculate context usage using both tokens and messages
    
    Args:
        tokens_used: Total tokens used
        message_count: Number of messages
        context_budget: Total context window
        max_messages: Maximum messages
    
    Returns:
        Percentage (0-100) - uses the higher of the two
    """
    token_percentage = int((tokens_used / context_budget) * 100)
    message_percentage = int((message_count / max_messages) * 100)
    
    return max(token_percentage, message_percentage)
```

---

## Permission Modes

### 1. Ask Mode (Default)

```python
permission_mode = "ask"
```

**Behavior**:
- Prompt user for each tool call
- Show permission dialog
- User can approve/deny/always allow

**Status Line**: `ask permissions` (green)

### 2. Bypass Mode

```python
permission_mode = "bypass"
```

**Behavior**:
- Auto-approve all tool calls
- No permission prompts
- Dangerous operations still require confirmation

**Status Line**: `bypass permissions` (yellow - warning)

**Keyboard Shortcut**: Shift+Tab to cycle

### 3. Deny Mode

```python
permission_mode = "deny"
```

**Behavior**:
- Auto-deny all tool calls
- Read-only mode
- No file modifications allowed

**Status Line**: `deny permissions` (red - blocked)

---

## Integration with Phase 1

### Update Phase 1 Deliverables

**Original Phase 1**:
- [x] SequentialREPL class with bottom UI rendering
- [x] Event-driven streaming that re-renders bottom UI
- [x] Cursor position tracking
- [x] Terminal size detection
- [x] Test script

**Enhanced Phase 1** (add these):
- [ ] Context percentage tracking
- [ ] Permission mode management
- [ ] Keyboard shortcut for mode cycling (Shift+Tab)
- [ ] Color-coded status line
- [ ] Context budget configuration

### Updated SequentialREPL Constructor

```python
def __init__(
    self,
    context_budget: int = 200000,
    permission_mode: str = "ask"
):
    """Initialize Sequential REPL
    
    Args:
        context_budget: Total context window size (default: 200k)
        permission_mode: Initial permission mode (ask/bypass/deny)
    """
    # Components
    self.dispatcher = EventDispatcher()
    self.streaming = StreamingRenderer()
    self.input_box = FixedInputBox()
    self.status_line = StatusLine()
    self.formatter = ResponseFormatter()
    self.agent_tree = AgentTree()
    
    # Context tracking
    self.context_budget = context_budget
    self.context_used = 0
    self.permission_mode = permission_mode
    
    # ... rest of initialization ...
```

---

## Testing

### Test Context Percentage Display

```python
def test_context_percentage():
    """Test context percentage display"""
    repl = SequentialREPL(context_budget=200000)
    
    # Simulate token usage
    repl.update_context(10000)  # 5%
    assert repl._get_context_percentage() == 5
    
    repl.update_context(90000)  # 50%
    assert repl._get_context_percentage() == 50
    
    repl.update_context(100000)  # 100%
    assert repl._get_context_percentage() == 100
    
    print("✓ Context percentage tracking works")
```

### Test Permission Mode Cycling

```python
def test_permission_mode_cycling():
    """Test permission mode cycling"""
    repl = SequentialREPL()
    
    assert repl.permission_mode == "ask"
    
    repl._cycle_permission_mode()
    assert repl.permission_mode == "bypass"
    
    repl._cycle_permission_mode()
    assert repl.permission_mode == "deny"
    
    repl._cycle_permission_mode()
    assert repl.permission_mode == "ask"
    
    print("✓ Permission mode cycling works")
```

### Test Status Line Rendering

```python
def test_status_line_with_context():
    """Test status line with context and mode"""
    status = StatusLine()
    
    status.update(
        mode="default",
        hints=["esc to exit"],
        context_percentage=45,
        permission_mode="bypass"
    )
    
    rendered = status.render()
    
    assert "45% context" in rendered
    assert "bypass permissions" in rendered
    assert "esc to exit" in rendered
    
    print("✓ Status line rendering works")
```

---

## Configuration

### Environment Variables

```bash
# Context budget (default: 200000)
export LYRA_CONTEXT_BUDGET=200000

# Initial permission mode (default: ask)
export LYRA_PERMISSION_MODE=ask

# Show context percentage (default: true)
export LYRA_SHOW_CONTEXT=true
```

### Config File

**File**: `~/.lyra/config.json`

```json
{
  "context": {
    "budget": 200000,
    "show_percentage": true,
    "warning_threshold": 80
  },
  "permissions": {
    "default_mode": "ask",
    "allow_bypass": true,
    "dangerous_operations_require_confirm": true
  },
  "status_line": {
    "show_context": true,
    "show_permission_mode": true,
    "show_keyboard_hints": true
  }
}
```

---

## Summary

### What's Added

1. **Context Percentage Display**
   - Real-time token usage tracking
   - Color-coded (green/yellow/red)
   - Updates after each turn

2. **Permission Mode Display**
   - Shows current mode (ask/bypass/deny)
   - Color-coded for visibility
   - Keyboard shortcut to cycle (Shift+Tab)

3. **Enhanced Status Line**
   - `⏵⏵ 45% context · bypass permissions · esc to exit · ↓ to manage`
   - Clean, readable format
   - Matches Claude Code style

### Files to Update

1. `packages/lyra-cli/src/lyra_cli/ui/status_line.py`
   - Add context_percentage parameter
   - Add permission_mode parameter
   - Add color coding logic

2. `packages/lyra-cli/src/lyra_cli/repl/sequential_repl.py`
   - Add context tracking
   - Add permission mode management
   - Add keyboard shortcut handler

3. `packages/lyra-cli/src/lyra_cli/repl/keyboard.py`
   - Add Shift+Tab detection

### Timeline Impact

**Original Phase 1**: 4-6 hours  
**Enhanced Phase 1**: 5-7 hours (+1 hour for context/mode tracking)

**Total Timeline**: 17-24 hours (still 2-3 days)

---

## Ready to Implement?

This enhancement is now integrated into the main implementation plan. When we start Phase 1, the status line will include:

✅ Context percentage (color-coded)  
✅ Permission mode (ask/bypass/deny)  
✅ Keyboard shortcuts  
✅ Real-time updates

**Shall we proceed with Phase 1 implementation including these enhancements?** 🚀
