# Lyra UI Sequential Output - Executive Summary

**Date**: 2026-05-23  
**Plan**: `LYRA_UI_SEQUENTIAL_OUTPUT_ULTRA_PLAN.md` (944 lines)

---

## The Problem

Current Lyra UI has all the components (welcome banner, input box, status line, response formatter, agent tree) but they're **not integrated** into a sequential output REPL like Claude Code.

### What's Missing

Claude Code's key behavior:
```
[Streaming content grows downward]
  ⏺ Response text...
  ⎿ Tool calls...
  ✻ Stats...

────────────────────────────────────────────────────────────────────
❯ [user input]
────────────────────────────────────────────────────────────────────
  ⏵⏵ mode · hints
```

**The bottom 4 lines are ALWAYS visible** - streaming content pushes them down, but they never scroll away.

---

## The Solution: Sequential Output REPL

### Core Architecture

**NOT** a TUI framework (Textual, Rich) - those use absolute positioning.

**YES** sequential output:
1. Print content line by line (grows downward)
2. After each line, re-render bottom UI at terminal bottom
3. Use ANSI escape codes for positioning
4. Content naturally scrolls up as terminal fills

### Key Technical Approach

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

This ensures bottom UI is **always at the bottom**, even during streaming.

---

## Implementation Phases

### Phase 1: Sequential REPL Core (4-6 hours)
- Create `SequentialREPL` class
- Event-driven streaming with bottom UI re-rendering
- Cursor position tracking
- Terminal size detection

**Key File**: `packages/lyra-cli/src/lyra_cli/repl/sequential_repl.py`

### Phase 2: Terminal Management (2-3 hours)
- `TerminalManager` with resize handling
- SIGWINCH signal handler
- Raw mode support
- Integration with SequentialREPL

**Key File**: `packages/lyra-cli/src/lyra_cli/repl/terminal_manager.py`

### Phase 3: Scrollback Buffer (2-3 hours)
- `ScrollbackBuffer` for history
- Max line limit (10,000 default)
- Save to file capability
- Integration with SequentialREPL

**Key File**: `packages/lyra-cli/src/lyra_cli/repl/scrollback.py`

### Phase 4: Keyboard Input (3-4 hours)
- `KeyboardHandler` with special key detection
- `InputEditor` with history navigation
- Arrow keys (↑↓ for history, ←→ for cursor)
- Ctrl+O for expand/collapse

**Key Files**:
- `packages/lyra-cli/src/lyra_cli/repl/keyboard.py`
- `packages/lyra-cli/src/lyra_cli/repl/input_editor.py`

### Phase 5: Integration & Polish (3-4 hours)
- Complete SequentialREPL with all features
- CLI entry point integration
- Keyboard shortcuts working
- History navigation working

### Phase 6: Testing & Verification (2-3 hours)
- Complete test suite
- Manual testing checklist
- All tests passing
- Documentation updated

---

## Timeline

**Total**: 16-23 hours (2-3 days of focused work)

---

## Success Criteria

### Visual Parity
- ✅ Welcome banner matches layout (already done)
- ⏳ Streaming responses push bottom UI down
- ⏳ Bottom UI always visible (never scrolls away)
- ✅ Response symbols match (⏺ ✻ ✶ ⎿ ❯) (already done)
- ✅ Agent tree rendering matches (already done)
- ✅ Status line matches (already done)

### Functional Requirements
- ⏳ Sequential output (not TUI framework)
- ⏳ Content grows downward
- ⏳ Bottom UI re-rendered after each line
- ⏳ Terminal resize handled
- ⏳ Keyboard shortcuts work
- ⏳ History navigation works
- ⏳ No flicker during streaming

### Performance
- ⏳ < 16ms per line render
- ⏳ < 50ms bottom UI re-render
- ⏳ Smooth scrolling
- ⏳ No memory leaks

---

## What's Already Done

From previous implementation (Phases 1-7):
- ✅ Event protocol (Pydantic models)
- ✅ StreamingRenderer (append-only)
- ✅ FixedInputBox component
- ✅ StatusLine component
- ✅ ResponseFormatter (all symbols)
- ✅ AgentTree (collapse/expand)
- ✅ SelectionMenu (interactive)
- ✅ ScrollManager (virtualized)
- ✅ WelcomeBanner (responsive)

**All components exist** - they just need to be integrated into a sequential output REPL.

---

## Key Insight

The difference between current Lyra and Claude Code is **not the components** (we have those), but the **integration pattern**:

**Current Lyra**: Components exist but not integrated into sequential output flow

**Claude Code**: Sequential output REPL where:
1. Content prints line by line
2. Bottom UI re-renders after each line
3. Bottom UI always at terminal bottom
4. Content scrolls up naturally

---

## Next Steps

1. ✅ Review ultra plan (`LYRA_UI_SEQUENTIAL_OUTPUT_ULTRA_PLAN.md`)
2. ⏳ Get user approval
3. ⏳ Start Phase 1 - Sequential REPL Core
4. ⏳ Implement phases sequentially
5. ⏳ Test after each phase
6. ⏳ Push to main after verification

---

## Files to Create

### New Files (6)
1. `packages/lyra-cli/src/lyra_cli/repl/sequential_repl.py` - Main REPL
2. `packages/lyra-cli/src/lyra_cli/repl/terminal_manager.py` - Terminal state
3. `packages/lyra-cli/src/lyra_cli/repl/scrollback.py` - History buffer
4. `packages/lyra-cli/src/lyra_cli/repl/keyboard.py` - Keyboard handling
5. `packages/lyra-cli/src/lyra_cli/repl/input_editor.py` - Line editing
6. `packages/lyra-cli/src/lyra_cli/repl/__init__.py` - Module exports

### Files to Update (2)
1. `packages/lyra-cli/src/lyra_cli/ui/status_line.py` - Add `render_inline()`
2. `packages/lyra-cli/src/lyra_cli/__main__.py` - Use SequentialREPL

### Test Files (2)
1. `test_sequential_repl.py` - Basic test
2. `test_sequential_output_complete.py` - Complete test suite

---

## Questions?

See the full plan: `LYRA_UI_SEQUENTIAL_OUTPUT_ULTRA_PLAN.md`

**Ready to start implementation?** 🚀
