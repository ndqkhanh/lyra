# Claude Code UI Pattern Examples - Visual Reference

## 1. Welcome UI Pattern

### Claude Code Style
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

**Key Features**:
- Two-column layout (wide terminals >120 cols)
- Left: Greeting + ASCII art + model info + path
- Right: Tips + What's new
- Rounded box borders (╭╮╰╯)
- Title in top border

---

## 2. Streaming Response Pattern

### Claude Code Style
```
⏺ Analyzing your request...

  ⎿ Read src/lyra_cli/cli/agent_integration.py (228 lines)
  ⎿ Referenced file src/lyra_cli/cli/tui.py
  ⎿ Read ../../../../../../../../.claude/rules/python/coding-style.md (43 lines)
  ⎿ Read ../../../../../../../../.claude/rules/python/testing.md (39 lines)
  ⎿ Skills restored (deep-research)

⏺ Launching parallel research across all provided repos...

✻ 2.3s · 3 tools · 1,234 tokens
```

**Key Features**:
- `⏺` for active responses
- `⎿` for tool calls (indented 2 spaces)
- `✻` for stats line at end
- Dim color for tool indicators
- Time · tools · tokens format

---

## 3. Agent Tree Pattern (Collapsed)

### Claude Code Style
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

**Key Features**:
- Box-drawing tree structure (├ │ └)
- Agent name · tool count · token count
- Latest tool call shown under each agent
- Expand/collapse hint
- 3-space indent per level

---

## 4. Agent Tree Pattern (Collapsed)

### Claude Code Style
```
⏺ Running 4 agents… (ctrl+o to expand)
```

**Key Features**:
- Single line when collapsed
- Shows count of running agents
- Keyboard hint for expansion

---

## 5. Status Line Pattern

### Claude Code Style
```
✶ Roosting… (2m 53s · ↓ 2.6k tokens · almost done thinking)
  ⎿  Tip: Use /btw to ask a quick side question without interrupting Claude's current work

────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
```

**Key Features**:
- `✶` for thinking/processing
- Time and token tracking
- Full-width dividers (────)
- `❯` prompt symbol
- `⏵⏵` mode indicator
- Keyboard hints separated by ` · `

---

## 6. Bottom UI Components

### Claude Code Style
```
────────────────────────────────────────────────────────────────────────────────
❯ [user input here]
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
```

**Structure**:
1. Horizontal divider (full width)
2. Input line with `❯` prompt
3. Horizontal divider (full width)
4. Status line with mode and hints

**Always Fixed**: These 4 lines stay at bottom, never scroll away

---

## 7. Selection Menu Pattern

### Claude Code Style
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

**Key Features**:
- Full-width dividers top and bottom
- Title (2-space indent)
- Description (2-space indent, dim)
- Blank line after description
- Options (4-space indent)
- `❯` for current selection
- `✔` for active item
- `●` for settings
- Keyboard hints at bottom

---

## 8. Background Tasks Panel

### Claude Code Style
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

**Key Features**:
- Title and count
- Task list with status
- `❯` for selection
- `(running)` status in dim
- Keyboard hints

---

## 9. File Update Pattern

### Claude Code Style
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
      269 +        except Exception as e:
      270 +            print(f"[APP] super().on_mount() FAILED: {e}", file=sys.stderr, flush=True)
  ⎿  Found 4 new diagnostic issues in 1 file (ctrl+o to expand)
```

**Key Features**:
- `⏺` for active operation
- File path in bold
- `⎿` for summary
- Line numbers right-aligned
- `+` green for additions
- `-` red for deletions
- Context lines in dim

---

## 10. Hierarchical Sub-requests

### Claude Code Style
```
⏺ Main request processing...

  ⏺ Sub-request 1: Analyzing code
    ⎿ Read file.py
    ⎿ Parse AST
    
  ⏺ Sub-request 2: Running tests
    ⎿ Bash: pytest
    
  ✓ Sub-request 1 complete
  ✓ Sub-request 2 complete

✻ 5.2s · 8 tools · 3,456 tokens
```

**Key Features**:
- Nested structure with indentation
- Each level has its own status symbol
- Sub-requests indented 2 spaces
- Completion markers (✓)
- Final stats line for main request

---

## Symbol Reference

| Symbol | Name | Usage | Color |
|--------|------|-------|-------|
| `⏺` | Filled circle | Active/running | Yellow |
| `◯` | Empty circle | Inactive/queued | Dim |
| `✓` | Checkmark | Success/completed | Green |
| `✗` | X mark | Error/failed | Red |
| `⚠` | Warning | Warning | Yellow |
| `✶` | Star | Thinking | Dim |
| `✻` | Asterisk | Stats line | Dim |
| `⎿` | Corner bracket | Tool use | Dim |
| `❯` | Prompt arrow | Input/selection | Default |
| `✔` | Heavy check | Active selection | Green |
| `●` | Bullet | Option/setting | Default |
| `⏵` | Play arrow | Mode indicator | Default |

---

## Box Drawing Characters

| Symbol | Usage |
|--------|-------|
| `╭╮╰╯` | Rounded corners (banners) |
| `─` | Horizontal line |
| `│` | Vertical line |
| `├┤┬┴` | T-junctions |
| `└┘┌┐` | Square corners |

---

## Color Scheme

| Element | Color | ANSI |
|---------|-------|------|
| Primary text | Default | - |
| Secondary text | Dim | `\033[2m` |
| Success | Green | `\033[32m` |
| Error | Red | `\033[31m` |
| Warning | Yellow | `\033[33m` |
| Info | Cyan | `\033[36m` |
| Highlight | Magenta | `\033[35m` |

---

## Spacing Rules

- **Tool calls**: 2-space indent
- **Tree children**: 3-space indent per level
- **Menu options**: 4-space indent
- **Status line**: 2-space indent
- **Separators**: ` · ` (space-dot-space)

---

**This visual reference should be used alongside the implementation plan to ensure exact pattern matching.**
