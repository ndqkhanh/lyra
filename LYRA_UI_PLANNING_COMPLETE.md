# Lyra UI Replication - Complete Planning Package

**Date**: 2026-05-23  
**Status**: ✅ Planning Complete - Ready for Implementation

---

## 📦 Planning Documents Created

### 1. Ultra Implementation Plan (944 lines)
**File**: `LYRA_UI_SEQUENTIAL_OUTPUT_ULTRA_PLAN.md`

Complete 6-phase implementation plan with:
- Detailed code examples for each component
- Phase-by-phase breakdown (16-23 hours total)
- Technical architecture decisions
- Success criteria and testing strategy

### 2. Executive Summary (150 lines)
**File**: `LYRA_UI_SEQUENTIAL_OUTPUT_SUMMARY.md`

High-level overview with:
- Problem statement
- Solution approach
- Timeline and phases
- Files to create/update
- Success criteria

### 3. Visual Architecture (400+ lines)
**File**: `LYRA_UI_SEQUENTIAL_OUTPUT_ARCHITECTURE.md`

Visual diagrams showing:
- Current vs target state
- Step-by-step rendering flow
- Component integration
- ANSI escape code strategy
- Performance considerations

---

## 🎯 The Core Problem

**Current State**: Lyra has all UI components (welcome banner, input box, status line, response formatter, agent tree) but they're **not integrated** into a sequential output REPL.

**Target State**: Claude Code-style sequential output where:
1. Content prints line by line (grows downward)
2. Bottom UI (4 lines) re-renders after each line
3. Bottom UI always stays at terminal bottom
4. Content naturally scrolls up

---

## 🏗️ Architecture Overview

### Sequential Output Pattern

```
[Streaming Content Area - grows downward]
  ⏺ Response text...
  ⎿ Tool calls...
  ✻ Stats...

────────────────────────────────────────────────────────────────────
❯ [user input]
────────────────────────────────────────────────────────────────────
  ⏵⏵ mode · hints
```

**Key Behavior**: Bottom 4 lines are ALWAYS visible - streaming content pushes them down, but they never scroll away.

### Technical Approach

```python
def render_content_and_bottom_ui(content_line: str):
    # 1. Print content line (grows downward)
    print(content_line)
    
    # 2. Save cursor position
    print("\033[s", end="")
    
    # 3. Move to bottom - 4 lines
    print(f"\033[{terminal_height - 3};1H", end="")
    
    # 4. Render bottom UI (4 lines)
    render_bottom_ui()
    
    # 5. Restore cursor position
    print("\033[u", end="", flush=True)
```

---

## 📋 Implementation Phases

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

**Key File**: `packages/lyra-cli/src/lyra_cli/repl/terminal_manager.py`

### Phase 3: Scrollback Buffer (2-3 hours)
- `ScrollbackBuffer` for history
- Max line limit (10,000 default)
- Save to file capability

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

### Phase 6: Testing & Verification (2-3 hours)
- Complete test suite
- Manual testing checklist
- Documentation

---

## 📊 Timeline

**Total Estimated Time**: 16-23 hours (2-3 days of focused work)

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Sequential REPL Core | 4-6 hours | ⏳ Not Started |
| Phase 2: Terminal Management | 2-3 hours | ⏳ Not Started |
| Phase 3: Scrollback Buffer | 2-3 hours | ⏳ Not Started |
| Phase 4: Keyboard Input | 3-4 hours | ⏳ Not Started |
| Phase 5: Integration & Polish | 3-4 hours | ⏳ Not Started |
| Phase 6: Testing & Verification | 2-3 hours | ⏳ Not Started |

---

## ✅ What's Already Done

From previous implementation (Phases 1-7):
- ✅ Event protocol (Pydantic models)
- ✅ StreamingRenderer (append-only)
- ✅ FixedInputBox component
- ✅ StatusLine component
- ✅ ResponseFormatter (all symbols: ⏺ ✻ ✶ ⎿ ❯)
- ✅ AgentTree (collapse/expand)
- ✅ SelectionMenu (interactive)
- ✅ ScrollManager (virtualized)
- ✅ WelcomeBanner (responsive)

**All components exist** - they just need to be integrated into a sequential output REPL.

---

## 📁 Files to Create

### New Files (8)
1. `packages/lyra-cli/src/lyra_cli/repl/sequential_repl.py` - Main REPL (300+ lines)
2. `packages/lyra-cli/src/lyra_cli/repl/terminal_manager.py` - Terminal state (100+ lines)
3. `packages/lyra-cli/src/lyra_cli/repl/scrollback.py` - History buffer (80+ lines)
4. `packages/lyra-cli/src/lyra_cli/repl/keyboard.py` - Keyboard handling (100+ lines)
5. `packages/lyra-cli/src/lyra_cli/repl/input_editor.py` - Line editing (100+ lines)
6. `packages/lyra-cli/src/lyra_cli/repl/__init__.py` - Module exports (20 lines)
7. `test_sequential_repl.py` - Basic test (50 lines)
8. `test_sequential_output_complete.py` - Complete test suite (100+ lines)

### Files to Update (2)
1. `packages/lyra-cli/src/lyra_cli/ui/status_line.py` - Add `render_inline()` method
2. `packages/lyra-cli/src/lyra_cli/__main__.py` - Use SequentialREPL

---

## 🎯 Success Criteria

### Visual Parity with Claude Code
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
- ⏳ Keyboard shortcuts work (↑↓ ←→ Ctrl+O)
- ⏳ History navigation works
- ⏳ No flicker during streaming

### Performance
- ⏳ < 16ms per line render
- ⏳ < 50ms bottom UI re-render
- ⏳ Smooth scrolling
- ⏳ No memory leaks

---

## 🔑 Key Technical Decisions

### Why Sequential Output (Not TUI Framework)?

**TUI frameworks** (Textual, Rich, urwid):
- ❌ Use absolute positioning
- ❌ Require full screen management
- ❌ Complex layout engines
- ❌ Harder to integrate with streaming

**Sequential output**:
- ✅ Natural terminal behavior
- ✅ Content grows downward
- ✅ Simple ANSI escape codes
- ✅ Easy to integrate with streaming
- ✅ Matches Claude Code's approach

### Bottom UI Rendering Strategy

**Approach**: Re-render after each content line

This ensures bottom UI is ALWAYS at the bottom, even as content streams.

---

## 📚 Documentation Structure

```
LYRA_UI_SEQUENTIAL_OUTPUT_ULTRA_PLAN.md (944 lines)
├── Problem Statement
├── Current State Analysis
├── Architecture: Sequential Output REPL
├── Phase 1: Sequential REPL Core (4-6 hours)
├── Phase 2: Terminal Management (2-3 hours)
├── Phase 3: Scrollback Buffer (2-3 hours)
├── Phase 4: Keyboard Input (3-4 hours)
├── Phase 5: Integration & Polish (3-4 hours)
├── Phase 6: Testing & Verification (2-3 hours)
├── Success Criteria
├── Implementation Timeline
└── Key Technical Decisions

LYRA_UI_SEQUENTIAL_OUTPUT_SUMMARY.md (150 lines)
├── The Problem
├── The Solution
├── Implementation Phases
├── Timeline
├── Success Criteria
├── What's Already Done
├── Files to Create
└── Next Steps

LYRA_UI_SEQUENTIAL_OUTPUT_ARCHITECTURE.md (400+ lines)
├── Current vs Target Architecture
├── Sequential Output Flow (Step-by-Step)
├── Technical Implementation (ANSI codes)
├── Component Integration
├── Performance Considerations
└── Comparison: TUI Framework vs Sequential Output
```

---

## 🚀 Next Steps

1. ✅ **Review planning documents**
   - Ultra plan: `LYRA_UI_SEQUENTIAL_OUTPUT_ULTRA_PLAN.md`
   - Summary: `LYRA_UI_SEQUENTIAL_OUTPUT_SUMMARY.md`
   - Architecture: `LYRA_UI_SEQUENTIAL_OUTPUT_ARCHITECTURE.md`

2. ⏳ **Get user approval** to proceed with implementation

3. ⏳ **Start Phase 1** - Sequential REPL Core
   - Create `SequentialREPL` class
   - Implement event-driven streaming
   - Add bottom UI re-rendering
   - Test basic functionality

4. ⏳ **Implement remaining phases** sequentially
   - Phase 2: Terminal Management
   - Phase 3: Scrollback Buffer
   - Phase 4: Keyboard Input
   - Phase 5: Integration & Polish
   - Phase 6: Testing & Verification

5. ⏳ **Test after each phase**
   - Unit tests
   - Integration tests
   - Manual testing

6. ⏳ **Push to main** after verification
   - Commit each phase separately
   - Update documentation
   - Create release notes

---

## 💡 Key Insights

### The Core Difference

**Current Lyra**: Components exist but not integrated into sequential output flow

**Claude Code**: Sequential output REPL where:
1. Content prints line by line
2. Bottom UI re-renders after each line
3. Bottom UI always at terminal bottom
4. Content scrolls up naturally

### The Solution

Integrate existing components into a **SequentialREPL** that:
- Prints content sequentially (grows downward)
- Re-renders bottom UI after each line using ANSI escape codes
- Keeps bottom UI always visible at terminal bottom
- Handles terminal resize and keyboard input

---

## 📞 Questions?

- **Full implementation details**: See `LYRA_UI_SEQUENTIAL_OUTPUT_ULTRA_PLAN.md`
- **High-level overview**: See `LYRA_UI_SEQUENTIAL_OUTPUT_SUMMARY.md`
- **Visual diagrams**: See `LYRA_UI_SEQUENTIAL_OUTPUT_ARCHITECTURE.md`

---

## ✨ Ready to Implement?

All planning is complete. The path forward is clear:

1. ✅ Planning documents created (3 files, 1,500+ lines)
2. ✅ Architecture designed
3. ✅ Implementation phases defined
4. ✅ Success criteria established
5. ✅ Timeline estimated (16-23 hours)

**Next**: Get user approval and start Phase 1! 🚀

---

**Created**: 2026-05-23  
**Status**: ✅ Planning Complete  
**Ready for**: Implementation
