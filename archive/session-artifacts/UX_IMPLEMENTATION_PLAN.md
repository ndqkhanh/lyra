# Lyra UX Implementation Plan 🚀

**Based on**: Deep research of Claude Code, Hermes-Agent, ECC, CLI-Anything, DeerFlow
**Research Document**: `/packages/lyra-cli/LYRA_UX_AUDIT_AND_ROADMAP.md` (953 lines)
**Status**: Ready to implement

---

## 🎯 Executive Summary

The research revealed **6 critical UX gaps** in Lyra compared to Claude Code and other modern CLI tools:

1. ❌ **Architecture Mismatch** - Lyra uses TUI (alternate screen), Claude Code uses inline streaming
2. ❌ **No Terminal Resize Handling** - Layout breaks on window resize
3. ❌ **Missing Status Bar (HUD)** - No persistent status indicator
4. ❌ **No @ File Mentions** - Can't reference files with `@filename`
5. ❌ **No / Command Palette** - Missing slash commands like `/help`, `/plan`
6. ❌ **Basic Banner** - Welcome screen lacks Claude Code's polish

---

## 🔥 Critical Insight

**Claude Code is NOT a TUI!** It uses:
- ✅ Inline streaming (no alternate screen)
- ✅ Natural terminal scrolling
- ✅ Bottom UI moves down with content
- ✅ Rich formatting with Unicode + ANSI colors

**Current Lyra**: Uses prompt_toolkit TUI with alternate screen ❌

---

## 📋 Implementation Roadmap

### Week 1: Critical Fixes (Priority 1) 🚨

#### 1. Switch from TUI to Inline Streaming ⚠️ BREAKING
**Impact**: Major architectural change
**Benefit**: Matches Claude Code, fixes resize issues, enables scrollback

**Tasks**:
- [ ] Remove alternate screen mode from prompt_toolkit
- [ ] Switch to Rich Console for inline printing
- [ ] Implement scrollback buffer
- [ ] Test terminal resize behavior

**Files**:
- `packages/lyra-cli/src/lyra_cli/repl/session.py`
- `packages/lyra-cli/src/lyra_cli/ui/tui.py`
- Create: `packages/lyra-cli/src/lyra_cli/ui/inline_renderer.py`

#### 2. Terminal Resize Handling
**Impact**: High - fixes layout breaks
**Benefit**: Professional UX, works with tiling WMs

**Tasks**:
- [ ] Add SIGWINCH signal handler
- [ ] Update terminal dimensions dynamically
- [ ] Recalculate layout widths
- [ ] Test with tmux, i3, sway

**Implementation**:
```python
import signal
import shutil

def handle_resize(signum, frame):
    width, height = shutil.get_terminal_size()
    update_layout(width, height)

signal.signal(signal.SIGWINCH, handle_resize)
```

#### 3. Integrate Status Bar (HUD)
**Impact**: High - always-visible context
**Benefit**: Matches Claude Code's HUD

**Tasks**:
- [ ] Wire up existing `status_bar.py` to main REPL
- [ ] Show: permission mode, context %, hints
- [ ] Update on every turn
- [ ] Test with different widths

**Pattern**:
```
────────────────────────────────────────────────────────────────────────────────
❯ [input]
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on · shift+tab to cycle · esc to interrupt · ↓ to manage
```

---

### Week 2: Quick Wins (Priority 2) ⚡

#### 4. Improve Welcome Banner
**Impact**: Medium - first impression
**Benefit**: Professional appearance

**Tasks**:
- [ ] Add rounded box borders (╭─╮╰─╯)
- [ ] Two-column layout (tips sidebar)
- [ ] "What's new" section
- [ ] Responsive breakpoints

**Target**:
```
╭─── Lyra Code v1.0.0 ──────────────────────────────────────────────────────╮
│                                                │ Tips for getting started │
│                 Welcome back!                  │ Run /init to create a …  │
│                   ╦  ╦ ╦╦═╗╔═╗                 │ ───────────────────────  │
│                   ║  ╚╦╝╠╦╝╠═╣                 │ What's new               │
│                   ╩═╝ ╩ ╩╚═╩ ╩                 │ Added color themes…      │
│ Opus 4.7 · Deep Research Mode                  │ /release-notes for more  │
│   ~/Downloads/MyCV/research/harness-engineering│                          │
╰────────────────────────────────────────────────────────────────────────────╯
```

#### 5. Essential Keyboard Shortcuts
**Impact**: Medium - power user efficiency
**Benefit**: Matches Claude Code shortcuts

**Tasks**:
- [ ] Ctrl+O - Expand/collapse
- [ ] Shift+Tab - Cycle permissions
- [ ] Esc - Interrupt
- [ ] ↑/↓ - History navigation
- [ ] Ctrl+C - Cancel (graceful)

#### 6. Progress Indicators
**Impact**: Medium - feedback during long operations
**Benefit**: User knows what's happening

**Patterns**:
```
✳ Flowing… (5m 24s · ↑ 9.7k tokens)
⏺ Running 4 agents… (ctrl+o to expand)
   ├ Agent 1 · 10 tool uses · 29.7k tokens
   ├ Agent 2 · 6 tool uses · 29.9k tokens
   └ Agent 3 · 5 tool uses · 25.7k tokens
```

---

### Week 3-4: Major Features (Priority 3) 🎨

#### 7. Command Palette (/ commands)
**Impact**: High - workflow efficiency
**Benefit**: Matches Claude Code, ECC patterns

**Tasks**:
- [ ] Implement `/command` parser
- [ ] Add core commands: `/help`, `/plan`, `/review`, `/test-coverage`
- [ ] Namespace support: `/ecc:plan`, `/oh-my-claudecode:autopilot`
- [ ] Auto-completion
- [ ] Help text for each command

**Commands to implement**:
```
/help              - Show available commands
/plan              - Create implementation plan
/review            - Code review
/test-coverage     - Check test coverage
/init              - Initialize project
/release-notes     - Show what's new
/clear             - Clear screen
/exit              - Exit Lyra
```

#### 8. File/Folder Mentions (@ references)
**Impact**: High - context awareness
**Benefit**: Matches Claude Code, Open-Claw

**Tasks**:
- [ ] Implement `@filename` parser
- [ ] Support `@folder/` for directories
- [ ] Auto-completion for file paths
- [ ] Visual indicators for referenced files
- [ ] Fuzzy matching for file search

**Pattern**:
```
❯ Review @src/components/Header.tsx and @tests/
```

#### 9. Agent Tree Visualization
**Impact**: Medium - transparency
**Benefit**: Shows what's happening

**Tasks**:
- [ ] Hierarchical display with ├│└
- [ ] Collapsed/expanded states
- [ ] Token counts per agent
- [ ] Time tracking
- [ ] Interactive expansion (Ctrl+O)

---

### Week 5+: Polish (Priority 4) ✨

#### 10. Advanced HUD Features
- [ ] Context percentage bar
- [ ] Cost tracking
- [ ] Burn rate indicator
- [ ] Active tools list
- [ ] Todo items

#### 11. Background Task Management
- [ ] Show running background tasks
- [ ] Progress bars
- [ ] Cancel/pause controls
- [ ] Notifications on completion

#### 12. Selection Menus
- [ ] File picker
- [ ] Command picker
- [ ] Model selector
- [ ] Provider selector

---

## 🎨 Design System

### Colors (Already Implemented ✅)
- **Red** (#FF4444) - Security warnings, errors
- **Green** (#50FA7B) - Success, lists, streaming
- **Cyan** (#8BE9FD) - Information, links, tools
- **Purple** (#BD93F9) - Shortcuts, numbers
- **Yellow** (#F1FA8C) - Warnings, code, strings
- **Pink** (#FF79C6) - Keywords, headings
- **Gray** (#6272A4) - Metadata, comments

### Symbols (Unicode)
```python
symbols = {
    'user_prompt': '❯',
    'assistant': '⏺',
    'thinking': '💭',
    'tool': '⚙️',
    'streaming': '✳',
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'branch': '⎿',
    'tree_branch': '├',
    'tree_last': '└',
    'tree_pipe': '│',
    'ellipsis': '…',
    'separator': '·',
}
```

### Indentation Levels
```
Level 0: Main content (no indent)
Level 1: Tool output (2 spaces)
Level 2: Nested content (4 spaces)
Level 3: Deep nesting (6 spaces)
```

---

## 🧪 Testing Strategy

### Visual Tests
1. Terminal resize (narrow/standard/wide)
2. Color rendering (16/256/truecolor)
3. Unicode symbol display
4. Scrollback buffer
5. Status bar updates
6. Banner responsive layout
7. Agent tree expansion

### Functional Tests
1. Command palette (`/help`, `/plan`)
2. File mentions (`@file`, `@folder/`)
3. Keyboard shortcuts (Ctrl+O, Shift+Tab)
4. Permission cycling
5. History navigation
6. Interrupt handling
7. Error recovery

### Integration Tests
1. Multi-agent workflows
2. Long-running operations
3. Background tasks
4. Streaming responses
5. Tool execution
6. File operations

### Terminal Compatibility
Test on:
- iTerm2 (macOS)
- Terminal.app (macOS)
- Alacritty
- Kitty
- WezTerm
- tmux
- screen
- VS Code terminal
- Windows Terminal

---

## 📊 Success Metrics

### Before (Current State)
- ❌ TUI with alternate screen
- ❌ No resize handling
- ❌ No status bar integration
- ❌ No @ mentions
- ❌ No / commands
- ❌ Basic banner

### After (Target State)
- ✅ Inline streaming (like Claude Code)
- ✅ Proper resize handling
- ✅ Always-visible status bar
- ✅ @ file/folder mentions
- ✅ / command palette
- ✅ Beautiful responsive banner
- ✅ Agent tree visualization
- ✅ Progress indicators
- ✅ Keyboard shortcuts
- ✅ Professional polish

---

## 🚨 Risks & Mitigation

### High Risk: TUI to Inline Migration
**Risk**: Breaking change, existing users affected
**Mitigation**:
- Feature flag for gradual rollout
- Comprehensive testing
- Migration guide
- Fallback to old TUI if needed

### Medium Risk: Performance
**Risk**: Inline printing slower than TUI
**Mitigation**:
- Use Rich's buffering
- Batch updates
- Profile and optimize

### Medium Risk: Keyboard Conflicts
**Risk**: Shortcuts conflict with terminal/shell
**Mitigation**:
- Configurable keybindings
- Document conflicts
- Provide alternatives

### Low Risk: Symbol Display
**Risk**: Unicode symbols not supported
**Mitigation**:
- Fallback ASCII symbols
- Auto-detect terminal capabilities
- User configuration

---

## 📚 Resources

### Research Documents
- `/packages/lyra-cli/LYRA_UX_AUDIT_AND_ROADMAP.md` (953 lines)
- Claude Code patterns
- ECC dual-surface architecture
- CLI-Anything ReplSkin
- DeerFlow streaming protocol

### GitHub Repositories
- [claude-hud](https://github.com/jarrodwatts/claude-hud)
- [ccstatusline](https://github.com/sirmalloc/ccstatusline) (3.7k stars)
- [claude-terminal-status-plugin](https://github.com/McGo/claude-terminal-status-plugin)
- [CLI-Anything](https://github.com/HKUDS/CLI-Anything)
- [ECC](https://github.com/affaan-m/ECC)
- [DeerFlow](https://github.com/bytedance/deer-flow)

### Academic Papers
- https://arxiv.org/pdf/2604.25917
- https://arxiv.org/pdf/2605.14038

---

## 🎯 Next Steps

### Immediate Actions (This Week)
1. ✅ Complete color enhancements (DONE)
2. ⏳ Review UX audit document
3. ⏳ Prioritize implementation tasks
4. ⏳ Start Week 1 critical fixes

### Week 1 Focus
1. **TUI to Inline Migration** - Most critical
2. **Terminal Resize Handling** - High impact
3. **Status Bar Integration** - Quick win

### Communication
- Document breaking changes
- Create migration guide
- Update README with new features
- Record demo videos

---

## 💡 Key Takeaways

1. **Claude Code uses inline streaming, not TUI** - This is the biggest architectural insight
2. **Terminal resize is critical** - Must handle SIGWINCH properly
3. **Status bar is always visible** - Not just in TUI mode
4. **@ and / are essential** - Modern CLI UX patterns
5. **Unicode symbols matter** - Professional appearance
6. **Responsive design** - Adapt to terminal width
7. **Keyboard shortcuts** - Power user efficiency
8. **Progress indicators** - User feedback during long operations

---

## 🎉 Expected Outcome

After implementing this roadmap, Lyra will have:
- ✨ **Professional UX** matching Claude Code
- 🎨 **Beautiful color theme** (already done!)
- 📝 **Rich Markdown rendering** (already done!)
- 🔍 **Syntax highlighting** (already done!)
- 🖥️ **Proper terminal handling** (resize, scrollback)
- 🎯 **Modern CLI patterns** (@ mentions, / commands)
- 🚀 **Smooth interactions** (keyboard shortcuts, progress)
- 💎 **Production-ready polish**

**Lyra will be the most beautiful and functional AI coding assistant CLI!** 🎉✨
