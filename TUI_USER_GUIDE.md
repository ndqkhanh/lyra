# Lyra TUI - Quick User Guide

## 🚪 How to Exit Lyra TUI

### Method 1: Type `/exit` or `/quit`
```
> /exit
```

### Method 2: Press Ctrl+C
```
Ctrl+C (twice if needed)
```

### Method 3: Type `/help` to see all commands
```
> /help
```

---

## 💡 Current Autocomplete Features

### ✅ What Works Now (Phase 1)

**Command Palette (Ctrl-K):**
- Press `Ctrl+K` to open the command palette
- Type to search commands (fuzzy search)
- Use ↑↓ to navigate
- Press Enter to insert command
- Press Esc to cancel

**Example:**
```
1. Press Ctrl+K
2. Type "mod"
3. See "model" and "mode" commands
4. Press Enter to insert
```

---

## ❌ What Doesn't Work Yet

### Inline Slash Dropdown (Not Implemented)

**Current behavior when you type `/`:**
- ❌ No dropdown appears automatically
- ❌ No inline suggestions

**Why?**
- Phase 1 only implemented the Command Palette (Ctrl-K)
- Inline dropdown is Phase 2 (not yet implemented)

**Workaround:**
- Use `Ctrl+K` instead of typing `/`
- Or type the full command manually: `/model`, `/mode`, etc.

---

## 🎯 Available Commands

### Essential Commands
```
/help       - Show all commands
/exit       - Exit Lyra
/quit       - Exit Lyra
/model      - Switch model
/mode       - Switch mode (plan/build/run)
/status     - Show session status
```

### How to Discover Commands
1. **Press Ctrl+K** - Opens command palette with all commands
2. **Type `/help`** - Shows command list
3. **Check docs** - See MODEL_SELECTION_GUIDE.md

---

## 🐛 Known Issues

### Issue 1: No inline dropdown when typing `/`
**Status:** Not implemented yet (Phase 2)
**Workaround:** Use Ctrl+K command palette
**ETA:** 1-2 weeks if implemented

### Issue 2: Exit not obvious
**Status:** UX improvement needed
**Workaround:** Type `/exit` or `/quit`
**Fix:** Add to welcome message and placeholder

---

## 🔧 Quick Fixes Needed

### 1. Update Placeholder Text
**Current:**
```
"Ask anything · / for commands · Shift+Enter for newline"
```

**Should be:**
```
"Ask anything · Ctrl-K for commands · /exit to quit · Shift+Enter for newline"
```

### 2. Add Exit Hint to Welcome Message
**Add to welcome screen:**
```
💡 Quick tips:
   • Ctrl-K - Open command palette
   • /exit or /quit - Exit Lyra
   • /help - Show all commands
```

### 3. Implement Phase 2 (Inline Dropdown)
**Status:** Planned but not implemented
**Effort:** 1-2 weeks
**See:** docs/TUI_AUTOCOMPLETE_IMPLEMENTATION_GUIDE.md

---

## 📝 Summary

**What works:**
- ✅ Ctrl-K command palette (fuzzy search)
- ✅ All slash commands work if typed manually
- ✅ /exit and /quit work

**What doesn't work:**
- ❌ Inline dropdown when typing `/`
- ❌ Auto-suggestions as you type
- ❌ Clear exit instructions in UI

**Immediate workarounds:**
1. Use `Ctrl-K` instead of typing `/`
2. Type `/exit` to quit
3. Type `/help` to see commands

---

## 🚀 Next Steps

### Immediate (This Session)
1. Update placeholder text to mention Ctrl-K and /exit
2. Add welcome message with quick tips
3. Test and commit

### Short-term (Next Sprint)
1. Implement Phase 2 (inline dropdown)
2. Add better UX hints
3. Improve discoverability

---

**Last Updated:** 2026-05-15
**Status:** Phase 1 complete, Phase 2 needed for inline dropdown
