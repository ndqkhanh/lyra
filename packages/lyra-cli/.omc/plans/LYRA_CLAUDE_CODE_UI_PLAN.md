# Lyra Claude Code UI/UX Upgrade Plan

**Goal:** Bring all Claude Code UI patterns to Lyra's prompt_toolkit TUI.  
**Stack:** Python · prompt_toolkit · braille Unicode · ANSI colors  
**Constraint:** No Ink/React — map every pattern to `prompt_toolkit` primitives.

---

## Gap Analysis (Current vs Target)

| Component | Current Lyra | Target (Claude Code) |
|-----------|-------------|----------------------|
| Welcome screen | Single-column block ASCII in box | Two-column: logo+info left, tips+keys right |
| Model picker | Prints text to output | Floating overlay: ❯ cursor, ✔ current, ←→ effort slider |
| Spinner | None — silent during runs | Braille ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏ + rotating verbs + elapsed |
| Tool display | Raw output | ⎿  ToolName args (N lines) with collapse |
| Compaction notice | None | ✻ Conversation compacted (ctrl+h for history) |
| Status bar | 🔬 model│Tokens│Cost│Ctx%│Cache│Turn [v] | + ⏵⏵ mode indicator |
| Mode cycling | None | chat / plan / accept-edits via Shift+Tab |
| Input border | Static ─ rule | Changes color per mode |
| Agent tree | None | ⏺ Running N agents…  ├ agent-1  └ agent-2 |
| Keyboard hints | None | ctrl+o expand · ctrl+h history · ctrl+b background |

---

## Wave 1 — Braille Spinner + Elapsed Time
**Files:** `cli/spinner.py` (new), `cli/tui.py`  
**Risk:** Low — pure display, no architecture change.

### 1.1 `spinner.py`
```python
FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
VERBS = ["Thinking", "Reasoning", "Processing", "Analyzing",
         "Synthesizing", "Reflecting", "Considering", "Computing"]
```
- `BrailleSpinner`: background thread, 80ms frame, updates a shared `_text: str`
- `start(verb=None)` — picks random verb if None, starts thread
- `stop()` — joins thread, clears line
- `elapsed_str` property → "1.2s" / "45s" / "2m 3s"
- `current_line` property → "⠙ Thinking… 3.4s"

### 1.2 `tui.py` integration
- Add `self._spinner: BrailleSpinner` in `__init__`  
- In `_run_agent()`: `self._spinner.start()` before LLM call, `self._spinner.stop()` after
- Spinner line printed via `self._print_output()` using `\r` to overwrite
- Status bar reads `self._spinner.current_line` when `_agent_running=True`

### 1.3 Rotating verbs by content
Map first keyword of user input → verb:
- "research / find / search" → "Researching"
- "write / create / build" → "Building"
- "explain / what / how" → "Analyzing"
- default → random from VERBS

---

## Wave 2 — ⎿ Tool Output Display
**Files:** `cli/tui.py`, `cli/agent_integration.py`  
**Risk:** Low — display change only.

Claude Code format:
```
⎿  Read src/main.py (142 lines)
⎿  Bash ls -la (12 lines)
⎿  Write tests/test_api.py
```

### 2.1 Agent event protocol
`run_agent()` yields event dicts. Add new event type:
```python
{"type": "tool_use", "name": "Read", "args": "src/main.py", "lines": 142}
{"type": "tool_done", "name": "Read", "lines": 142, "truncated": False}
```

### 2.2 TUI rendering in `_stream_to_output()`
```
⎿  Read src/main.py (142 lines)
```
- Color: dim gray `\033[2m` for ⎿ line
- Truncated suffix: " [truncated]" in yellow if `truncated=True`
- Expandable: store last tool output, `ctrl+o` prints full content

### 2.3 ctrl+o keyboard binding
- `@kb.add("c-o")` → if last tool output stored, toggle expand/collapse
- Print "↑ (expanded)" / "↓ (collapsed)" indicator

---

## Wave 3 — ✻ Compaction & Context Notices
**Files:** `cli/tui.py`, `cli/agent_integration.py`  
**Risk:** Low.

### 3.1 Compaction notice
When `ContextManager._summary` is first written (turn crosses compression threshold):
```
✻ Conversation compacted · 47 turns → summary (ctrl+h for history)
```
- `agent_integration.py` emits `{"type": "compaction", "turns": 47, "tokens_saved": 3200}`
- TUI prints notice in dim cyan

### 3.2 Context budget warning
At 70%: `⚠ Context 70% full · consider /history clear`  (dim yellow)  
At 85%: `⚠ Context 85% full · compaction recommended` (bold yellow)  
At 95%: `⛔ Context 95% full · responses may be cut off` (bold red)

### 3.3 Cache hit notice
When `cache_read_tokens > 1000`:
```
✶ Cache hit · saved 4,200 tokens ($0.0021)
```
Print once per turn, only when savings meaningful (>500 tokens).

---

## Wave 4 — Two-Column Welcome Dashboard
**Files:** `cli/banner.py`, `cli/tui.py`  
**Risk:** Low — startup only.

### 4.1 `banner.py` rewrite
`render_welcome(model, version, cwd, api_provider)` → multiline string:

```
╭──────────────────────────────────╮  ╭──────────────────────────────────╮
│  ██╗  ██╗   ██╗██████╗ █████╗    │  │  Tips                            │
│  ██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗  │  │  ─────────────────────────────  │
│  ██║   ╚████╔╝ ██████╔╝███████║  │  │  ctrl+c   interrupt agent        │
│  ██║    ╚██╔╝  ██╔══██╗██╔══██║  │  │  ctrl+d   exit                   │
│  ███████╗██║   ██║  ██║██║  ██║  │  │  ctrl+o   expand last tool       │
│  ╚══════╝╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝  │  │  ctrl+h   history / context      │
│                                   │  │  ctrl+r   search history         │
│  Deep Research AI Agent           │  │  alt+↵    newline                │
│  v0.x · deepseek/deepseek-chat    │  │  /model   switch model           │
│  ~/projects/lyra                  │  │  /help    all commands           │
╰──────────────────────────────────╯  ╰──────────────────────────────────╯
```

- Each column is `(terminal_width - 4) // 2` wide, minimum 35 chars
- Falls back to compact single-column if terminal < 80 cols
- `api_provider` shown as colored badge: blue=anthropic, cyan=deepseek, green=openai

### 4.2 `tui.py` startup
- Print `render_welcome(...)` via `_print_output()` before entering app loop
- Also print: `\033[2mType /help for commands. Shift+Tab cycles modes.\033[0m`

---

## Wave 5 — Interactive /model Picker Overlay
**Files:** `cli/tui.py`, `cli/model_picker.py` (new)  
**Risk:** Medium — needs prompt_toolkit FloatContainer.

### 5.1 `model_picker.py`
`ModelPicker(models, current)` — a self-contained prompt_toolkit overlay:
```
╭─ Switch Model ──────────────────────────╮
│  ❯ claude-opus-4-7         anthropic    │
│    claude-sonnet-4-6  ✔    anthropic    │
│    claude-haiku-4-5        anthropic    │
│  ─────────────────────────────────────  │
│    deepseek/deepseek-chat  deepseek     │
│    gpt-4o                  openai       │
╰─────────────────────────────────────────╯
  ↑↓ navigate · Enter select · Esc cancel
```
- `❯` marks focused row, `✔` marks current model
- `↑/↓` moves cursor, `Enter` confirms, `Esc` cancels
- Returns selected model name or None

### 5.2 Integration in `_handle_model_command()`
- If no args: open picker via `app.run_in_executor(None, _run_picker_sync)`  
  or use `application.run()` with a mini sub-application
- On selection: update `self.model`, re-init agent on next message
- Print confirmation: `✔ Model switched to claude-opus-4-7`

### 5.3 Effort slider (stretch)
Below model list, for Anthropic models:
```
  Thinking effort: ←──●──────→  normal
```
`←/→` adjusts thinking budget: off / low / normal / high / max

---

## Wave 6 — Mode Indicator + Shift+Tab Cycling
**Files:** `cli/tui.py`  
**Risk:** Low.

### 6.1 Modes
Three modes (like Claude Code):
- `chat` — default conversational mode  
- `plan` — adds "Think step by step, produce a plan first" to system prompt
- `auto` — autonomous accept-edits (currently no file editing, reserve for future)

### 6.2 Status bar `⏵⏵` indicator
Replace static `[verbosity]` suffix with:
```
 chat ●  │  [verbosity]
 plan ◉  │  [verbosity]
```
- `chat`: ● white
- `plan`: ◉ yellow
- `auto`: ◉ red (reserved)

### 6.3 Shift+Tab binding
```python
@kb.add("s-tab")
def cycle_mode(event):
    modes = ["chat", "plan"]
    idx = (modes.index(self._mode) + 1) % len(modes)
    self._mode = modes[idx]
    self._print_output(f"\n\033[2m◌ Mode: {self._mode}\033[0m\n\n")
    self._invalidate_status()
```

### 6.4 Input border color per mode
Change `input-rule` style dynamically:
- `chat`: `#CD7F32` (bronze — current)
- `plan`: `#FFD700` (gold)
- `auto`: `#FF4444` (red)

---

## Wave 7 — Agent/Task Tree Panel
**Files:** `cli/tui.py`, `cli/agent_integration.py`  
**Risk:** Medium — new UI region.

### 7.1 Tree structure (Claude Code style)
```
⏺ Running 3 agents…
├ 🔬 researcher    searching "quantum computing"    12s
├ ✔ planner       plan drafted                      8s
└ ⚙  writer        idle
```

### 7.2 When shown
- Only during `/research` or `/team run` — never during single-turn chat
- Rendered as `_print_output()` lines that update in-place (use `\r` + ANSI clear-to-EOL)
- On completion: collapse to single summary line

### 7.3 Event protocol
`agent_integration.py` emits:
```python
{"type": "agent_start",  "agent_id": "researcher", "task": "searching…"}
{"type": "agent_update", "agent_id": "researcher", "status": "found 5 sources"}
{"type": "agent_done",   "agent_id": "researcher", "elapsed": 12.3}
```
TUI maintains `_agent_tree: dict[str, AgentStatus]` and redraws on each event.

---

## Wave 8 — Keyboard Hints Footer
**Files:** `cli/tui.py`  
**Risk:** Low.

### 8.1 Context-sensitive hint line
Add a second status bar row (height=1) below input:
```
ctrl+c interrupt · ctrl+o expand · ctrl+h history · ctrl+r search · shift+tab mode
```
- Shown in very dim style `#444444`
- Hidden if terminal height < 20 rows
- Changes when agent is running:
```
ctrl+c interrupt agent · ctrl+b run in background
```

### 8.2 Implementation
Add `hint_bar = Window(height=1, content=FormattedTextControl(self._get_hint_bar))` to HSplit below input_rule_bot.

---

## Implementation Order

```
Wave 1 — Spinner           (2-3h) ← highest user-visible impact, lowest risk
Wave 2 — ⎿ tool display    (1-2h)
Wave 3 — ✻ notices         (1h)
Wave 4 — Welcome dashboard (2h)
Wave 5 — /model picker     (3-4h) ← most complex
Wave 6 — Mode + Shift+Tab  (1-2h)
Wave 7 — Agent tree        (2-3h)
Wave 8 — Hint footer       (1h)
```

Total estimated: **~14-18 hours** of coding.

---

## Files to Create / Modify

| File | Action | Waves |
|------|--------|-------|
| `cli/spinner.py` | CREATE | 1 |
| `cli/model_picker.py` | CREATE | 5 |
| `cli/banner.py` | REWRITE | 4 |
| `cli/tui.py` | MODIFY (many places) | 1,2,3,4,5,6,7,8 |
| `cli/agent_integration.py` | ADD events | 2,3,7 |

---

## Unicode Symbol Reference

| Symbol | Code | Usage |
|--------|------|-------|
| ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏ | U+2800-28FF | Braille spinner frames |
| ✻ | U+273B | Compaction notice prefix |
| ✶ | U+2736 | Cache hit notice |
| ⎿ | U+23BF | Tool use display |
| ⏺ | U+23FA | Agent tree root |
| ├ └ | U+251C U+2514 | Agent tree branches |
| ❯ | U+276F | Picker cursor |
| ✔ | U+2714 | Current/done marker |
| ● ◯ ◉ | U+25CF U+25EF U+25C9 | Mode indicators |
| ╭╮╰╯ | U+256D-256F | Box corners |
| ─ │ | U+2500 U+2502 | Box edges |
| ⏵⏵ | U+23F5 | Mode double-arrow |
| ⚠ ⛔ | U+26A0 U+26D4 | Context warnings |
