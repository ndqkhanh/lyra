# Lyra UI Sequential Output - Visual Architecture

## Current vs Target Architecture

### Current State (Components Exist, Not Integrated)

```
┌─────────────────────────────────────────────────────────────┐
│ Lyra Components (Isolated)                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ WelcomeBanner          ✅ ResponseFormatter            │
│  ✅ FixedInputBox          ✅ AgentTree                     │
│  ✅ StatusLine             ✅ SelectionMenu                 │
│  ✅ StreamingRenderer      ✅ ScrollManager                 │
│  ✅ EventDispatcher                                         │
│                                                             │
│  ❌ NOT INTEGRATED INTO SEQUENTIAL OUTPUT REPL             │
└─────────────────────────────────────────────────────────────┘
```

### Target State (Sequential Output REPL)

```
┌─────────────────────────────────────────────────────────────┐
│ Terminal Window (80x24)                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ╭─── Lyra v0.1.0 ────────────────────────────────────────╮ │
│ │ Welcome back Khanh!        │ Tips for getting started │ │
│ │   ╦  ╦ ╦ ╦═╗ ╔═╗           │ Run /help for commands   │ │
│ │   ║  ╚╦╝ ╠╦╝ ╠═╣           │ ─────────────────────── │ │
│ │   ╩═╝ ╩  ╩╚═ ╩ ╩           │ What's new              │ │
│ │ Opus 4.7 · Anthropic API   │ Sequential output UI    │ │
│ ╰────────────────────────────────────────────────────────╯ │
│                                                             │
│ ❯ What is Python?                                          │
│                                                             │
│ ⏺ Python is a high-level, interpreted programming          │
│   language created by Guido van Rossum...                  │
│                                                             │
│   ⎿ Read python_docs.md (150 lines)                        │
│   ⎿ Search web for "Python features"                       │
│                                                             │
│ ✻ 2.5s · 2 tools · 1,234 tokens                            │
│                                                             │
│ ────────────────────────────────────────────────────────── │ ← Line 20
│ ❯ [cursor here]                                            │ ← Line 21
│ ────────────────────────────────────────────────────────── │ ← Line 22
│   ⏵⏵ default · esc to exit · enter to send                │ ← Line 23
└─────────────────────────────────────────────────────────────┘
     ↑                                                    ↑
     Bottom UI (4 lines)                    Always at terminal bottom
     NEVER scrolls away                     Re-rendered after each line
```

---

## Sequential Output Flow

### Step-by-Step Rendering

```
Time T0: Welcome Banner
┌─────────────────────────────────────────────────────────────┐
│ ╭─── Lyra v0.1.0 ────────────────────────────────────────╮ │
│ │ Welcome back Khanh!                                    │ │
│ ╰────────────────────────────────────────────────────────╯ │
│                                                             │
│ ────────────────────────────────────────────────────────── │
│ ❯                                                           │
│ ────────────────────────────────────────────────────────── │
│   ⏵⏵ default · esc to exit                                 │
└─────────────────────────────────────────────────────────────┘
```

```
Time T1: User Input
┌─────────────────────────────────────────────────────────────┐
│ ╭─── Lyra v0.1.0 ────────────────────────────────────────╮ │
│ │ Welcome back Khanh!                                    │ │
│ ╰────────────────────────────────────────────────────────╯ │
│                                                             │
│ ❯ What is Python?                                          │
│                                                             │
│ ────────────────────────────────────────────────────────── │
│ ❯                                                           │
│ ────────────────────────────────────────────────────────── │
│   ⏵⏵ default · esc to exit                                 │
└─────────────────────────────────────────────────────────────┘
```

```
Time T2: Streaming Response (Line 1)
┌─────────────────────────────────────────────────────────────┐
│ ╭─── Lyra v0.1.0 ────────────────────────────────────────╮ │
│ │ Welcome back Khanh!                                    │ │
│ ╰────────────────────────────────────────────────────────╯ │
│                                                             │
│ ❯ What is Python?                                          │
│                                                             │
│ ⏺ Python is a high-level                                   │ ← New line
│                                                             │
│ ────────────────────────────────────────────────────────── │
│ ❯                                                           │
│ ────────────────────────────────────────────────────────── │
│   ⏵⏵ streaming · esc to interrupt                          │
└─────────────────────────────────────────────────────────────┘
     ↑ Bottom UI re-rendered after line
```

```
Time T3: Streaming Response (Line 2)
┌─────────────────────────────────────────────────────────────┐
│ ╭─── Lyra v0.1.0 ────────────────────────────────────────╮ │
│ │ Welcome back Khanh!                                    │ │
│ ╰────────────────────────────────────────────────────────╯ │
│                                                             │
│ ❯ What is Python?                                          │
│                                                             │
│ ⏺ Python is a high-level                                   │
│   interpreted programming language...                      │ ← New line
│                                                             │
│ ────────────────────────────────────────────────────────── │
│ ❯                                                           │
│ ────────────────────────────────────────────────────────── │
│   ⏵⏵ streaming · esc to interrupt                          │
└─────────────────────────────────────────────────────────────┘
     ↑ Bottom UI re-rendered again
```

```
Time T4: Tool Call
┌─────────────────────────────────────────────────────────────┐
│ ╭─── Lyra v0.1.0 ────────────────────────────────────────╮ │
│ │ Welcome back Khanh!                                    │ │
│ ╰────────────────────────────────────────────────────────╯ │
│                                                             │
│ ❯ What is Python?                                          │
│                                                             │
│ ⏺ Python is a high-level                                   │
│   interpreted programming language...                      │
│                                                             │
│   ⎿ Read python_docs.md (150 lines)                        │ ← Tool call
│                                                             │
│ ────────────────────────────────────────────────────────── │
│ ❯                                                           │
│ ────────────────────────────────────────────────────────── │
│   ⏵⏵ streaming · esc to interrupt                          │
└─────────────────────────────────────────────────────────────┘
```

```
Time T5: Completion
┌─────────────────────────────────────────────────────────────┐
│ ╭─── Lyra v0.1.0 ────────────────────────────────────────╮ │
│ │ Welcome back Khanh!                                    │ │
│ ╰────────────────────────────────────────────────────────╯ │
│                                                             │
│ ❯ What is Python?                                          │
│                                                             │
│ ⏺ Python is a high-level                                   │
│   interpreted programming language...                      │
│                                                             │
│   ⎿ Read python_docs.md (150 lines)                        │
│                                                             │
│ ✻ 2.5s · 1 tool · 234 tokens                               │ ← Stats
│                                                             │
│ ────────────────────────────────────────────────────────── │
│ ❯                                                           │
│ ────────────────────────────────────────────────────────── │
│   ⏵⏵ default · esc to exit · enter to send                │
└─────────────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### ANSI Escape Code Strategy

```python
def render_content_and_bottom_ui(content_line: str):
    """Render content line and update bottom UI"""
    
    # 1. Print content line (grows downward)
    print(content_line)
    
    # 2. Save current cursor position
    print("\033[s", end="")
    
    # 3. Calculate bottom UI position
    terminal_height = get_terminal_height()  # e.g., 24
    bottom_start = terminal_height - 3       # Line 21 (24 - 3)
    
    # 4. Move to bottom UI area
    print(f"\033[{bottom_start};1H", end="")
    
    # 5. Clear bottom 4 lines
    for i in range(4):
        print(f"\033[{bottom_start + i};1H\033[K", end="")
    
    # 6. Render bottom UI components
    print(f"\033[{bottom_start};1H", end="")
    print("─" * terminal_width)
    
    print(f"\033[{bottom_start + 1};1H", end="")
    print("❯ ")
    
    print(f"\033[{bottom_start + 2};1H", end="")
    print("─" * terminal_width)
    
    print(f"\033[{bottom_start + 3};1H", end="")
    print("  ⏵⏵ default · esc to exit")
    
    # 7. Restore cursor position
    print("\033[u", end="", flush=True)
```

### Key ANSI Codes

| Code | Description |
|------|-------------|
| `\033[s` | Save cursor position |
| `\033[u` | Restore cursor position |
| `\033[{row};{col}H` | Move cursor to row, col |
| `\033[K` | Clear line from cursor to end |
| `\033[2J` | Clear entire screen |
| `\033[H` | Move cursor to home (1,1) |

---

## Component Integration

### Event Flow

```
User Input
    ↓
EventDispatcher
    ↓
┌───────────────────────────────────────────────────────────┐
│ Event Handlers                                            │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  on_text_delta()                                          │
│    → StreamingRenderer.append_delta()                     │
│    → print(text)                                          │
│    → render_bottom_ui()                                   │
│                                                           │
│  on_tool_started()                                        │
│    → ResponseFormatter.format_tool_call()                 │
│    → print(tool_line)                                     │
│    → render_bottom_ui()                                   │
│                                                           │
│  on_turn_finished()                                       │
│    → ResponseFormatter.format_stats_line()                │
│    → print(stats)                                         │
│    → render_bottom_ui()                                   │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Component Responsibilities

```
┌─────────────────────────────────────────────────────────────┐
│ SequentialREPL (Orchestrator)                               │
├─────────────────────────────────────────────────────────────┤
│ - Main loop                                                 │
│ - Event dispatching                                         │
│ - Bottom UI rendering                                       │
│ - Terminal state management                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                                   ↓
┌──────────────────┐              ┌──────────────────┐
│ EventDispatcher  │              │ TerminalManager  │
├──────────────────┤              ├──────────────────┤
│ - Event routing  │              │ - Size tracking  │
│ - Callbacks      │              │ - Resize events  │
└──────────────────┘              │ - Raw mode       │
        ↓                         └──────────────────┘
┌──────────────────┐
│ StreamingRenderer│
├──────────────────┤
│ - Append buffer  │
│ - Line tracking  │
└──────────────────┘
        ↓
┌──────────────────────────────────────────────────────────┐
│ UI Components                                            │
├──────────────────────────────────────────────────────────┤
│ ResponseFormatter  AgentTree  FixedInputBox  StatusLine │
└──────────────────────────────────────────────────────────┘
```

---

## Performance Considerations

### Rendering Budget

| Operation | Target | Actual |
|-----------|--------|--------|
| Print content line | < 1ms | TBD |
| Re-render bottom UI | < 50ms | TBD |
| Total per line | < 16ms | TBD |
| Terminal resize | < 100ms | TBD |

### Optimization Strategies

1. **Minimize ANSI codes**: Batch cursor movements
2. **Buffer output**: Use `flush=True` strategically
3. **Debounce resize**: Wait 100ms before re-rendering
4. **Virtualize scrollback**: Only keep last 10,000 lines
5. **Lazy rendering**: Only render visible area

---

## Comparison: TUI Framework vs Sequential Output

### TUI Framework Approach (NOT USED)

```python
# Textual/Rich approach
class LyraApp(App):
    def compose(self):
        yield Header()
        yield ContentArea()
        yield Footer()
    
    # Absolute positioning, full screen management
    # Complex layout engine
    # Harder to integrate with streaming
```

### Sequential Output Approach (USED)

```python
# Sequential approach
def main_loop():
    print_welcome()
    
    while True:
        user_input = get_input()
        
        for line in stream_response(user_input):
            print(line)              # Content grows downward
            render_bottom_ui()       # Always at bottom
        
        print_stats()
        render_bottom_ui()
```

**Why Sequential?**
- ✅ Natural terminal behavior
- ✅ Simple ANSI escape codes
- ✅ Easy streaming integration
- ✅ Matches Claude Code's approach
- ✅ No complex layout engine needed

---

## Next Steps

1. ✅ Review architecture diagrams
2. ⏳ Approve implementation plan
3. ⏳ Start Phase 1: Sequential REPL Core
4. ⏳ Implement remaining phases
5. ⏳ Test and verify
6. ⏳ Push to main

---

**See full plan**: `LYRA_UI_SEQUENTIAL_OUTPUT_ULTRA_PLAN.md` (944 lines)  
**See summary**: `LYRA_UI_SEQUENTIAL_OUTPUT_SUMMARY.md`

**Ready to implement?** 🚀
