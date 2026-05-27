# ✅ Lyra CLI - Final Configuration

## Default UI: Hermes-Style TUI Application

Now when you run `lyra`, you get the **full TUI Application** by default!

### Usage

```bash
# Default: Hermes-style TUI Application (NEW DEFAULT!)
lyra

# Streaming CLI (opt-in)
LYRA_USE_STREAMING=true lyra

# Legacy REPL
lyra --legacy

# Textual TUI
lyra --tui
```

### What Changed

**Before:**
- `lyra` → Streaming CLI (default)
- `LYRA_USE_TUI_APP=true lyra` → TUI Application

**After:**
- `lyra` → **TUI Application (default)** ✨
- `LYRA_USE_STREAMING=true lyra` → Streaming CLI

### TUI Application Features

When you run `lyra` now, you get:

```
╭─────────────────────────────────────────────────────────────╮
│                                                             │
│   ██╗  ██╗   ██╗██████╗  █████╗     ██████╗██╗     ██╗    │
│   ██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗   ██╔════╝██║     ██║    │
│   ██║   ╚████╔╝ ██████╔╝███████║   ██║     ██║     ██║    │
│   ██║    ╚██╔╝  ██╔══██╗██╔══██║   ██║     ██║     ██║    │
│   ███████╗██║   ██║  ██║██║  ██║   ╚██████╗███████╗██║    │
│   ╚══════╝╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝    ╚═════╝╚══════╝╚═╝    │
│                                                             │
│              Deep Research AI Agent Framework               │
│                                                             │
╰─────────────────────────────────────────────────────────────╯

Lyra v3.14.0
Model: claude-sonnet-4-6  Repo: harness-engineering  Session: demo-001

Type /help for commands · /status for session info · ⌥? for shortcuts

┌─────────────────────────────────────────────────────────────┐
│ 🔬 claude-sonnet-4-6 │ Tokens: 0 │ Cost: $0.0000 │ Context: 0% │
├─────────────────────────────────────────────────────────────┤
│ > /help[Tab]                                                │
│   /help    Show available commands                          │
│   /history Show command history                             │
├─────────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- ✅ Status bar with live stats (tokens, cost, context %)
- ✅ Dynamic input height (1-8 lines)
- ✅ Slash command autocomplete
- ✅ File path completion
- ✅ Auto-suggestions
- ✅ Command history (Ctrl+R)
- ✅ Multi-line input (Alt+Enter)
- ✅ Background agent execution
- ✅ Decorative input rules

### All Modes Summary

| Command | UI Mode | Description |
|---------|---------|-------------|
| `lyra` | **TUI Application** | Full Hermes-style TUI (DEFAULT) |
| `LYRA_USE_STREAMING=true lyra` | Streaming CLI | Rich CLI with colors |
| `lyra --legacy` | Legacy REPL | Old prompt_toolkit REPL |
| `lyra --tui` | Textual TUI | Original Textual-based TUI |

---

**Now `lyra` gives you the full TUI experience by default!** 🎉
