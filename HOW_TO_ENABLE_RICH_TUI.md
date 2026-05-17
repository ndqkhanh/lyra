# How to Enable Rich TUI with Claude Code-Style Formatting

## 🎯 The Issue

You're running Lyra in **"Hermes-style TUI"** mode (line 260 in `__main__.py`), which uses the old `tui.py` file. The features we implemented are in **TUI v2** (`tui_v2/app.py`) which uses harness-tui for rich formatting.

## ✅ Solution: Run with `--tui` Flag

To see the rich formatting with all the new features, run:

```bash
lyra --tui
```

Or set the environment variable:

```bash
export LYRA_TUI=tui
lyra
```

## 📊 Lyra Has 3 Modes

According to `__main__.py` lines 208-267:

1. **Streaming CLI** (`LYRA_TUI=cli`) - Simple streaming output
2. **Hermes-style TUI** (DEFAULT) - Uses old `tui.py` ❌ (what you're seeing now)
3. **TUI v2** (`--tui` or `LYRA_TUI=tui`) - Uses `tui_v2/app.py` ✅ (where we added features)

## 🚀 Quick Test

```bash
# Enable TUI v2
export LYRA_TUI=tui

# Or run with flag
lyra --tui --model deepseek-chat

# Now try:
> What is 2+2?
# Watch for: tips, tool cards, status bar updates

# Try task panel
> Press Ctrl+T
# See: Interactive task list

# Try deep research
> /research "Python async patterns"
# Watch for: agent progress in status bar
```

## 🔧 Make TUI v2 Permanent

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
export LYRA_TUI=tui
```

Then restart your terminal or run:
```bash
source ~/.zshrc  # or ~/.bashrc
```

## 📝 What You'll See in TUI v2

### Status Bar (Bottom)
```
🔬 deepseek-chat │ Tokens: 1.2K │ Cost: $0.0012 │ Ctx: 15% │ Turn: 3
⏺ Running 2 agents · 45.2K tokens  ← NEW!
```

### Context Compaction (Chat Log)
```
✻ Conversation compacted (65% → 35%)
  ⎿  Preserved last 4 turns (20.0K tokens)
  ⎿  Summarized 8 older turns (50.0K → 20.0K tokens)
⎿ Tip: Use /btw to add context for the next turn  ← NEW!
```

### Tool Execution (Chat Log)
```
⚙ bash  running
⚙ read  done  420ms  ← NEW!
⚙ write  done  180ms  ← NEW!
```

### Task Panel (Ctrl+T)
```
┌─ Tasks ─────────────────────────────────────┐
│ ✓ Read authentication module                │
│ ⏺ Implement JWT validation                  │
│ ◯ Write unit tests                          │
└──────────────────────────────────────────────┘
```

## ⚠️ Important Note

The **research pipeline output** you showed (`⏺ Decompose`, `⏺ Search`, etc.) is **separate** from the main TUI. That's the research command's own progress display and will look the same in all modes.

The features we added appear in:
- **Status bar** (bottom of screen)
- **Chat log** (main conversation area)
- **Modals** (Ctrl+T for tasks)

## 🎊 Summary

**Current:** `lyra` → Hermes-style TUI (old)  
**To get new features:** `lyra --tui` → TUI v2 (new) ✅

All the features we implemented are ready and working in TUI v2 mode!
