# 🔄 Lyra UI Rebuild Summary

## Current State (TUI-based)
- Uses `FixedBottomLayout` class
- Alt screen buffer management
- Fixed input box at bottom
- Complex terminal state management
- Similar to Textual approach

## Target State (Claude Code-style)
- Raw terminal control with ANSI codes
- Simple REPL loop (prompt after response)
- Streaming markdown renderer
- Spinner with cursor save/restore
- NO fixed bottom layout
- NO TUI frameworks

## What Will Change

### Files to DELETE
- `ui/fixed_layout.py` (TUI-style layout)
- Any Textual dependencies

### Files to CREATE
- `cli/repl.py` - Simple REPL loop
- `cli/markdown_renderer.py` - Streaming markdown
- `cli/spinner.py` - Terminal spinner
- `cli/syntax_highlighter.py` - Code highlighting

### Files to MODIFY
- `cli/commands/chat.py` - Use simple REPL
- `cli/agent_handler.py` - Use streaming renderer
- `ui/welcome_banner.py` - Simple print()
- `ui/model_menu.py` - Raw terminal control

## Key Differences

| Feature | Current (TUI) | Target (Claude Code) |
|---------|---------------|---------------------|
| Layout | Fixed bottom | Sequential output |
| Input | Always visible | Appears after response |
| Framework | Custom TUI | Raw ANSI codes |
| Rendering | Buffer-based | Stream-based |
| Complexity | High | Low |

## Benefits of Rebuild

1. ✅ Matches Claude Code exactly
2. ✅ Simpler codebase
3. ✅ Easier to maintain
4. ✅ Better performance
5. ✅ No TUI framework bugs
6. ✅ Works in any terminal

## Estimated Time

- Phase 1: Remove TUI (1 hour)
- Phase 2-7: Implement new patterns (6.5 hours)
- **Total**: ~7.5 hours

## Risk Assessment

**Low Risk** because:
- We keep the agent loop (no changes)
- We keep the API client (no changes)
- Only UI layer changes
- Can test incrementally

## Ready to Proceed?

This will be a complete UI rebuild following Claude Code patterns.
All current TUI code will be replaced with raw terminal control.

**Confirm to proceed with Phase 1: Remove TUI dependencies**
