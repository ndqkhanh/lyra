# Claude Code UI Patterns - Complete Visual Reference for Lyra

**Purpose**: Visual reference showing exactly how Claude Code renders each UI pattern  
**Date**: 2026-05-23

---

## 1. Welcome UI Pattern

### Claude Code
```
╭─── Claude Code v2.1.142 ─────────────────────────────────────────────────────╮
│                                                    │ Tips for getting        │
│                 Welcome back Khanh!                │ started                 │
│                                                    │ Run /init to create a … │
│                       ▐▛███▜▌                      │ ─────────────────────── │
│                      ▝▜█████▛▘                     │ What's new              │
│                        ▘▘ ▝▝                       │ Added new `claude agen… │
│ Sonnet 4.6 · Claude Max · khanhndq2002@gmail.com's │ Fast mode now uses Opu… │
│  Organization                                      │ Plugins with a root-le… │
│   ~/…/research/harness-engineering/projects/lyra   │ /release-notes for more │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### Lyra Target
```
╭─── Lyra v0.1.0 ──────────────────────────────────────────────────────────────╮
│                                                    │ Tips for getting        │
│                 Welcome back Khanh!                │ started                 │
│                                                    │ Run /help for commands  │
│                       ╦  ╦ ╦ ╦═╗ ╔═╗               │ ─────────────────────── │
│                       ║  ╚╦╝ ╠╦╝ ╠═╣               │ What's new              │
│                       ╩═╝ ╩  ╩╚═ ╩ ╩               │ Sequential output UI    │
│ Opus 4.7 · high effort · Anthropic API            │ Claude Code-style REPL  │
│   ~/…/research/harness-engineering/projects/lyra   │ /release-notes for more │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Status**: ✅ Already implemented in `packages/lyra-cli/src/lyra_cli/ui/welcome_banner.py`

---

## 2. Bottom UI Components (CRITICAL)

### Claude Code
```
────────────────────────────────────────────────────────────────────────────────
❯ [user input here]
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
```

### Lyra Target
```
────────────────────────────────────────────────────────────────────────────────
❯ [user input here]
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ default · esc to exit · enter to send
```

**Structure**:
- Line 1: Full-width horizontal divider (`─` × terminal_width)
- Line 2: Prompt symbol `❯` + user input
- Line 3: Full-width horizontal divider
- Line 4: Status line with mode and hints (2-space indent)

**Key Behavior**: These 4 lines are ALWAYS at the bottom of the terminal, never scroll away

**Status**: ⏳ Components exist but not integrated into sequential output REPL

---

## 3. Streaming Response Pattern

### Claude Code
```
⏺ Analyzing your request...

  ⎿ Read src/lyra_cli/cli/agent_integration.py (228 lines)
  ⎿ Referenced file src/lyra_cli/cli/tui.py
  ⎿ Read ../../../../../../../../.claude/rules/python/coding-style.md (43 lines)

⏺ Launching parallel research across all provided repos...

✻ 2.3s · 3 tools · 1,234 tokens
```

### Lyra Target
```
⏺ Analyzing your request...

  ⎿ Read src/lyra_cli/cli/agent_integration.py (228 lines)
  ⎿ Referenced file src/lyra_cli/cli/tui.py
  ⎿ Read ../../../../../../../../.claude/rules/python/coding-style.md (43 lines)

⏺ Launching parallel research across all provided repos...

✻ 2.3s · 3 tools · 1,234 tokens
```

**Symbols**:
- `⏺` (U+23FA) - Active/running indicator (yellow)
- `⎿` (U+23BF) - Tool call indicator (dim, 2-space indent)
- `✻` (U+273B) - Stats line (dim)

**Status**: ✅ Already implemented in `packages/lyra-cli/src/lyra_cli/ui/response_formatter.py`

---

## 4. Agent Tree Pattern (Expanded)

### Claude Code
```
⏺ Running 4 agents… (ctrl+o to expand)
   ├ Research provided GitHub repos on token reduction · 10 tool uses · 29.7k tokens
   │ ⎿  Bash: Fetch RTK README via gh API
   ├ Search GitHub for top token/context compression repos · 6 tool uses · 29.9k tokens
   │ ⎿  Web Search: llmlingua context compression github stars micros…
   ├ Research academic papers on context/token compression · 5 tool uses · 29.8k tokens
   │ ⎿  Web Search: LLMlingua context compression paper arxiv
   └ Research production token reduction tools and techniques · 6 tool uses · 25.7k tokens
     ⎿  Web Search: llama index context management token reduction te…
     (ctrl+b to run in background)
```

### Lyra Target
```
⏺ Running 4 agents… (ctrl+o to expand)
   ├ Research provided GitHub repos on token reduction · 10 tool uses · 29.7k tokens
   │ ⎿  Bash: Fetch RTK README via gh API
   ├ Search GitHub for top token/context compression repos · 6 tool uses · 29.9k tokens
   │ ⎿  Web Search: llmlingua context compression github stars micros…
   ├ Research academic papers on context/token compression · 5 tool uses · 29.8k tokens
   │ ⎿  Web Search: LLMlingua context compression paper arxiv
   └ Research production token reduction tools and techniques · 6 tool uses · 25.7k tokens
     ⎿  Web Search: llama index context management token reduction te…
```

**Box-drawing characters**:
- `├` (U+251C) - T-junction (left)
- `│` (U+2502) - Vertical line
- `└` (U+2514) - Corner (bottom-left)

**Status**: ✅ Already implemented in `packages/lyra-cli/src/lyra_cli/ui/agent_tree.py`

---

## 5. Agent Tree Pattern (Collapsed)

### Claude Code
```
⏺ Running 4 agents… (ctrl+o to expand)
```

### Lyra Target
```
⏺ Running 4 agents… (ctrl+o to expand)
```

**Status**: ✅ Already implemented in `packages/lyra-cli/src/lyra_cli/ui/agent_tree.py`

---

## 6. Thinking Indicator

### Claude Code
```
✶ Roosting… (2m 53s · ↓ 2.6k tokens · almost done thinking)
  ⎿  Tip: Use /btw to ask a quick side question without interrupting Claude's current work
```

### Lyra Target
```
✶ Thinking… (2m 53s · ↓ 2.6k tokens)
```

**Symbol**: `✶` (U+2736) - Star (dim)

**Status**: ✅ Already implemented in `packages/lyra-cli/src/lyra_cli/ui/response_formatter.py`

---

## 7. Selection Menu Pattern

### Claude Code
```
────────────────────────────────────────────────────────────────────────────────
  Select model
  Switch between Claude models. Applies to this session and future Claude Code
   sessions. For other/previous model names, specify with --model.

    1. Default (recommended)  Opus 4.7 with 1M context · Most capable for
                              complex work
  ❯ 2. Sonnet ✔               Sonnet 4.6 · Best for everyday tasks
    3. Haiku                  Haiku 4.5 · Fastest for quick answers

  ● High effort (default) ←/→ to adjust

  Enter to confirm · Esc to cancel
────────────────────────────────────────────────────────────────────────────────
```

### Lyra Target
```
────────────────────────────────────────────────────────────────────────────────
  Select model
  Switch between Claude models.

    1. Default (recommended)  Opus 4.7 · Most capable
  ❯ 2. Sonnet ✔               Sonnet 4.6 · Best for everyday tasks
    3. Haiku                  Haiku 4.5 · Fastest

  Enter to confirm · Esc to cancel
────────────────────────────────────────────────────────────────────────────────
```

**Symbols**:
- `❯` (U+276F) - Current selection
- `✔` (U+2714) - Active item
- `●` (U+25CF) - Setting indicator

**Status**: ✅ Already implemented in `packages/lyra-cli/src/lyra_cli/ui/selection_menu.py`

---

## 8. Background Tasks Panel

### Claude Code
```
────────────────────────────────────────────────────────────────────────────────
  Background tasks
  3 active shells

  ❯ .venv/bin/python test_textual_driver.py 2>&1 (running)
    chmod +x test_catch_exception.py && .venv/bin/python test_catch_exception.py 2>&1 | head -100 (running)
    chmod +x test_tui_debug.py && .venv/bin/python test_tui_debug.py 2>&1 | head -100 (running)

  ↑/↓ to select · Enter to view · x to stop · ←/Esc to close
────────────────────────────────────────────────────────────────────────────────
```

### Lyra Target
```
────────────────────────────────────────────────────────────────────────────────
  Background tasks
  2 active shells

  ❯ python test_sequential_repl.py (running)
    python test_integration.py (running)

  ↑/↓ to select · Enter to view · x to stop · ←/Esc to close
────────────────────────────────────────────────────────────────────────────────
```

**Status**: ⏳ To be implemented in Phase 5

---

## 9. File Update Pattern

### Claude Code
```
⏺ Update(packages/lyra-cli/src/lyra_cli/tui_v2/app.py)
  ⎿  Added 8 lines, removed 2 lines
      263      def on_mount(self) -> None:
      264          import sys
      265          print("[APP] LyraHarnessApp.on_mount() called", file=sys.stderr, flush=True)
      266 -        super().on_mount()
      267 -        print("[APP] super().on_mount() completed", file=sys.stderr, flush=True)
      266 +        try:
      267 +            super().on_mount()
      268 +            print("[APP] super().on_mount() completed", file=sys.stderr, flush=True)
  ⎿  Found 4 new diagnostic issues in 1 file (ctrl+o to expand)
```

### Lyra Target
```
⏺ Update(packages/lyra-cli/src/lyra_cli/repl/sequential_repl.py)
  ⎿  Added 8 lines, removed 2 lines
      263      def render_bottom_ui(self):
      264          # Save cursor
      265          print("\033[s", end="")
      266 -        # Old implementation
      267 -        print("Bottom UI")
      266 +        # New implementation
      267 +        print(f"\033[{self.terminal_height - 3};1H", end="")
      268 +        self._render_components()
```

**Status**: ✅ Already implemented in `packages/lyra-cli/src/lyra_cli/ui/tool_formatter.py`

---

## 10. Complete Flow Example

### Claude Code
```
╭─── Claude Code v2.1.142 ─────────────────────────────────────────────────────╮
│                 Welcome back Khanh!                │ Tips for getting        │
╰──────────────────────────────────────────────────────────────────────────────╯

❯ What is Python?

⏺ Python is a high-level, interpreted programming language created by Guido van Rossum...

  ⎿ Read python_docs.md (150 lines)
  ⎿ Search web for "Python features"

✻ 2.5s · 2 tools · 1,234 tokens

────────────────────────────────────────────────────────────────────────────────
❯ 
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ default · esc to exit · enter to send
```

### Lyra Target (EXACT SAME)
```
╭─── Lyra v0.1.0 ──────────────────────────────────────────────────────────────╮
│                 Welcome back Khanh!                │ Tips for getting        │
╰──────────────────────────────────────────────────────────────────────────────╯

❯ What is Python?

⏺ Python is a high-level, interpreted programming language created by Guido van Rossum...

  ⎿ Read python_docs.md (150 lines)
  ⎿ Search web for "Python features"

✻ 2.5s · 2 tools · 1,234 tokens

────────────────────────────────────────────────────────────────────────────────
❯ 
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ default · esc to exit · enter to send
```

---

## Symbol Reference

| Symbol | Unicode | Name | Usage | Color |
|--------|---------|------|-------|-------|
| `⏺` | U+23FA | Filled circle | Active/running | Yellow |
| `◯` | U+25EF | Empty circle | Inactive/queued | Dim |
| `✓` | U+2713 | Checkmark | Success/completed | Green |
| `✗` | U+2717 | X mark | Error/failed | Red |
| `⚠` | U+26A0 | Warning | Warning | Yellow |
| `✶` | U+2736 | Star | Thinking | Dim |
| `✻` | U+273B | Asterisk | Stats line | Dim |
| `⎿` | U+23BF | Corner bracket | Tool use | Dim |
| `❯` | U+276F | Prompt arrow | Input/selection | Default |
| `✔` | U+2714 | Heavy check | Active selection | Green |
| `●` | U+25CF | Bullet | Option/setting | Default |
| `⏵` | U+23F5 | Play arrow | Mode indicator | Default |

---

## Box Drawing Characters

| Symbol | Unicode | Usage |
|--------|---------|-------|
| `╭` | U+256D | Top-left rounded corner |
| `╮` | U+256E | Top-right rounded corner |
| `╰` | U+2570 | Bottom-left rounded corner |
| `╯` | U+256F | Bottom-right rounded corner |
| `─` | U+2500 | Horizontal line |
| `│` | U+2502 | Vertical line |
| `├` | U+251C | T-junction (left) |
| `┤` | U+2524 | T-junction (right) |
| `┬` | U+252C | T-junction (top) |
| `┴` | U+2534 | T-junction (bottom) |
| `└` | U+2514 | Bottom-left corner |
| `┘` | U+2518 | Bottom-right corner |
| `┌` | U+250C | Top-left corner |
| `┐` | U+2510 | Top-right corner |

---

## Color Scheme (ANSI)

| Element | Color | ANSI Code |
|---------|-------|-----------|
| Primary text | Default | - |
| Secondary text | Dim | `\033[2m` |
| Success | Green | `\033[32m` |
| Error | Red | `\033[31m` |
| Warning | Yellow | `\033[33m` |
| Info | Cyan | `\033[36m` |
| Highlight | Magenta | `\033[35m` |

---

## Spacing Rules

- **Tool calls**: 2-space indent (`  ⎿`)
- **Tree children**: 3-space indent per level (`   ├`)
- **Menu options**: 4-space indent (`    1.`)
- **Status line**: 2-space indent (`  ⏵⏵`)
- **Separators**: ` · ` (space-dot-space)

---

## Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Welcome Banner | ✅ Done | `ui/welcome_banner.py` |
| Response Formatter | ✅ Done | `ui/response_formatter.py` |
| Agent Tree | ✅ Done | `ui/agent_tree.py` |
| Selection Menu | ✅ Done | `ui/selection_menu.py` |
| Fixed Input Box | ✅ Done | `ui/fixed_input.py` |
| Status Line | ✅ Done | `ui/status_line.py` |
| Event Protocol | ✅ Done | `events/protocol.py` |
| Streaming Renderer | ✅ Done | `events/streaming.py` |
| **Sequential REPL** | ⏳ **To Do** | `repl/sequential_repl.py` |
| Terminal Manager | ⏳ To Do | `repl/terminal_manager.py` |
| Scrollback Buffer | ⏳ To Do | `repl/scrollback.py` |
| Keyboard Handler | ⏳ To Do | `repl/keyboard.py` |
| Input Editor | ⏳ To Do | `repl/input_editor.py` |

---

## Key Insight

**All UI components are already implemented!**

What's missing is the **Sequential Output REPL** that:
1. Prints content line by line (grows downward)
2. Re-renders bottom UI after each line
3. Keeps bottom UI always at terminal bottom
4. Handles keyboard input and terminal resize

---

**See implementation plan**: `LYRA_UI_SEQUENTIAL_OUTPUT_ULTRA_PLAN.md`  
**See architecture**: `LYRA_UI_SEQUENTIAL_OUTPUT_ARCHITECTURE.md`  
**See summary**: `LYRA_UI_SEQUENTIAL_OUTPUT_SUMMARY.md`

**Ready to implement!** 🚀
