# Lyra UI Replication - Executive Summary

## 📋 Overview

**Goal**: Replicate Claude Code's complete terminal UI response format patterns in Lyra

**Status**: ✅ Research Complete | 📝 Plan Ready | ⏳ Implementation Pending

**Estimated Time**: 25-30 hours (3-4 days focused work)

---

## 🎯 What We're Building

### Current Lyra UI
```
❯ lyra
╭─── Lyra v0.1.0 ───────────────────────────────────
  ╦  ╦ ╦ ╦═╗ ╔═╗   Lyra v0.1.0
  ║  ╚╦╝ ╠╦╝ ╠═╣   Claude Opus 4.7 (1M context)
  ╩═╝ ╩  ╩╚═ ╩ ╩   ~/path

❯ [cursor here - but scrolls away during responses]
```

### Target Claude Code UI
```
╭─── Claude Code v2.1.142 ─────────────────────────╮
│ Welcome back Khanh!        │ Tips               │
│                            │ Run /help          │
│   ▐▛███▜▌                  │ ───────────        │
│  ▝▜█████▛▘                 │ What's new         │
│    ▘▘ ▝▝                   │ Fast mode now...   │
│ Opus 4.7 · ~/path          │ /release-notes     │
╰──────────────────────────────────────────────────╯

⏺ Analyzing your request...
  ⎿ Read file.py (228 lines)
  ⎿ Edit src/main.py

Response text here...

⏺ Running 4 agents… (ctrl+o to expand)
   ├ Agent 1 · 10 tool uses · 29.7k tokens
   │ ⎿  Bash: npm test
   ├ Agent 2 · 6 tool uses · 29.9k tokens
   └ Agent 3 · 5 tool uses · 29.8k tokens

✻ 2.3s · 3 tools · 1,234 tokens

────────────────────────────────────────────────────
❯ [cursor here - ALWAYS VISIBLE]
────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on · esc to interrupt · ↓ to manage
```

---

## 🔑 Key Differences

| Feature | Current Lyra | Target Claude Code |
|---------|--------------|-------------------|
| **Input Box** | Scrolls away | Fixed at bottom |
| **Status Line** | None | Always visible below input |
| **Response Symbols** | Basic | ⏺ ✻ ✶ ⎿ ❯ |
| **Agent Display** | None | Hierarchical tree with collapse |
| **Tool Calls** | Basic | Formatted with ⎿ symbol |
| **Stats Line** | None | ✻ time · tools · tokens |
| **Welcome Banner** | Single column | Two-column responsive |
| **Streaming** | Basic | Flicker-free append-only |
| **Selection Menus** | None | Interactive with ❯ |
| **Scrolling** | Basic | Virtualized with fixed UI |

---

## 📦 10 Implementation Phases

### Phase 1: Event Protocol & Streaming (2-3h)
- Pydantic event models (TurnStarted, TextDelta, etc.)
- Append-only streaming renderer
- Event dispatcher/consumer

### Phase 2: Fixed Bottom UI (3-4h)
- Input box with ANSI positioning
- Status line with mode/hints
- Keyboard shortcut display

### Phase 3: Response Format Patterns (4-5h)
- Active response indicator (⏺)
- Stats line formatter (✻)
- Tool call display (⎿)
- Thinking indicator (✶)

### Phase 4: Agent Tree Display (3-4h)
- Hierarchical agent tree
- Collapse/expand with ctrl+o
- Box-drawing connectors
- Token rollup display

### Phase 5: Interactive Selection Menus (3-4h)
- Selection menu widget
- Keyboard navigation (↑↓)
- Model picker
- Background tasks panel

### Phase 6: Scrollable Area Management (2-3h)
- Scroll manager with offset tracking
- Auto-scroll to bottom
- Virtualized rendering

### Phase 7: Welcome Banner Enhancement (2h)
- Two-column layout (wide terminals)
- Single-column (narrow terminals)
- Responsive breakpoints

### Phase 8: Integration & Testing (3-4h)
- Main REPL integration
- Event flow testing
- UI component testing

### Phase 9: Performance Optimization (2h)
- Virtualized scrolling
- Diff-based updates
- Buffer limits

### Phase 10: Documentation (2h)
- API documentation
- Integration guide
- Examples

---

## ✅ Success Criteria

### Visual Parity
- ✓ Welcome banner matches Claude Code layout
- ✓ Response symbols match (⏺ ✻ ✶ ⎿ ❯)
- ✓ Agent tree rendering matches
- ✓ Selection menus match
- ✓ Status line matches
- ✓ Color scheme matches

### Functional Parity
- ✓ Streaming without flicker
- ✓ Fixed input at bottom
- ✓ Scrollable content area
- ✓ Agent tree collapse/expand
- ✓ Selection menu navigation
- ✓ Terminal resize handling

### Performance
- ✓ First paint < 50ms
- ✓ Token-to-screen < 16ms
- ✓ Smooth scrolling
- ✓ No memory leaks

---

## 📚 Reference Documents

1. **CLAUDE_CODE_RESPONSE_FORMAT_SPECIFICATION.md** (752 lines)
   - Complete technical specification
   - Event protocol details
   - Symbol reference
   - Layout algorithms

2. **CLAUDE_CODE_UI_QUICK_REFERENCE.md** (184 lines)
   - Quick lookup guide
   - Common patterns
   - Implementation checklist

3. **LYRA_UI_REPLICATION_ULTRA_PLAN.md** (this document)
   - Detailed implementation plan
   - Code examples for each phase
   - Testing checklist

---

## 🚀 Next Steps

1. **Review** this plan
2. **Approve** to proceed
3. **Start** with Phase 1 (Event Protocol)
4. **Implement** phases sequentially
5. **Test** after each phase
6. **Push** to main after each phase completion

---

## 💡 Key Implementation Notes

### Event-Driven Architecture
```
Backend → Events → TUI → Terminal
         (Pydantic)  (Textual/Rich)
```

### Fixed UI Layout
```
┌─────────────────────────────┐
│ [Scrollable Area]           │ ← Conversation history
│ - Welcome banner            │
│ - Responses                 │
│ - Agent status              │
│                             │
├─────────────────────────────┤ ← Fixed divider
│ ❯ [Input - always visible] │ ← Fixed input
├─────────────────────────────┤ ← Fixed divider
│ ⏵⏵ mode · hints            │ ← Fixed status
└─────────────────────────────┘
```

### Streaming Pattern
```python
# Append-only (no flicker)
for delta in stream:
    renderer.append_delta(delta.text)
    # Only prints new text, doesn't re-render buffer
```

### Symbol Usage
- `⏺` Active/running
- `◯` Inactive/queued
- `✓` Success
- `✗` Error
- `✶` Thinking
- `✻` Stats line
- `⎿` Tool use
- `❯` Prompt/selection

---

**Ready to implement? Let's start with Phase 1!** 🚀
