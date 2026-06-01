# Ultra Plan: Rebuild Lyra UI to Match Claude Code Patterns

**Date**: 2026-05-23  
**Goal**: Replicate Claude Code's UI patterns using raw terminal control (NO TUI frameworks)

---

## 🎯 Core Insight from Research

Claude Code uses:
- ✅ **crossterm** (Rust) for raw terminal control
- ✅ **rustyline** for REPL input
- ✅ **pulldown-cmark** for markdown parsing
- ✅ **syntect** for syntax highlighting
- ❌ **NO TUI frameworks** (no Textual, Ratatui, Cursive)
- ❌ **NO fixed bottom layout** - prompt appears after response

---

## 📋 Implementation Plan

### Phase 1: Remove TUI Dependencies ✅
**Goal**: Strip out all Textual/TUI code

**Actions**:
1. Remove `tui_v2/` directory completely
2. Remove Textual dependencies
3. Keep only CLI-based chat interface
4. Use simple print() for output

**Files to Remove**:
- `packages/lyra-cli/src/lyra_cli/tui_v2/` (entire directory)
- Any Textual imports

**Files to Keep**:
- `cli/commands/chat.py` (but simplify)
- `cli/agent_handler.py` (but simplify)

---

### Phase 2: Implement Streaming Markdown Renderer 🎨
**Goal**: Incremental markdown rendering like Claude Code

**Python Equivalent Stack**:
- `markdown` or `mistune` (markdown parsing)
- `pygments` (syntax highlighting)
- `colorama` or raw ANSI codes (terminal styling)

**Implementation**:

```python
class StreamingMarkdownRenderer:
    """Incremental markdown renderer"""
    
    def __init__(self):
        self.buffer = ""
        self.lexer = get_lexer_by_name("python")
        self.formatter = Terminal256Formatter()
    
    def push_delta(self, text: str):
        """Add text delta and render complete blocks"""
        self.buffer += text
        
        # Find safe boundary (complete paragraph, code block, etc.)
        if boundary := self._find_safe_boundary():
            ready = self.buffer[:boundary]
            self.buffer = self.buffer[boundary:]
            
            rendered = self._render_markdown(ready)
            print(rendered, end='', flush=True)
    
    def flush(self):
        """Render remaining buffer"""
        if self.buffer:
            rendered = self._render_markdown(self.buffer)
            print(rendered, flush=True)
            self.buffer = ""
    
    def _render_markdown(self, text: str) -> str:
        """Render markdown with syntax highlighting"""
        # Parse markdown
        # Apply ANSI styling
        # Highlight code blocks with pygments
        pass
```

**Files to Create**:
- `cli/markdown_renderer.py` (streaming markdown)
- `cli/syntax_highlighter.py` (code block highlighting)

---

### Phase 3: Implement Spinner with Cursor Control 🔄
**Goal**: Spinner that updates in-place without disrupting output

**Python Implementation**:

```python
import sys
import time
from typing import Optional

class Spinner:
    """Terminal spinner using cursor save/restore"""
    
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    def __init__(self):
        self.frame_index = 0
        self.active = False
    
    def start(self, label: str):
        """Start spinner"""
        self.active = True
        self._render(label)
    
    def tick(self, label: str):
        """Update spinner frame"""
        if not self.active:
            return
        
        frame = self.FRAMES[self.frame_index % len(self.FRAMES)]
        self.frame_index += 1
        
        # ANSI escape codes:
        # \x1b[s - Save cursor position
        # \x1b[u - Restore cursor position
        # \x1b[2K - Clear line
        # \x1b[0G - Move to column 0
        
        sys.stdout.write('\x1b[s')  # Save position
        sys.stdout.write('\x1b[0G')  # Move to start
        sys.stdout.write('\x1b[2K')  # Clear line
        sys.stdout.write(f'\x1b[33m{frame}\x1b[0m {label}')  # Yellow spinner
        sys.stdout.write('\x1b[u')  # Restore position
        sys.stdout.flush()
    
    def finish(self, label: str):
        """Finish spinner with checkmark"""
        self.active = False
        sys.stdout.write('\x1b[0G')  # Move to start
        sys.stdout.write('\x1b[2K')  # Clear line
        sys.stdout.write(f'\x1b[32m✔\x1b[0m {label}\n')  # Green checkmark
        sys.stdout.flush()
    
    def fail(self, label: str):
        """Finish spinner with X"""
        self.active = False
        sys.stdout.write('\x1b[0G')
        sys.stdout.write('\x1b[2K')
        sys.stdout.write(f'\x1b[31m✘\x1b[0m {label}\n')  # Red X
        sys.stdout.flush()
```

**Files to Create**:
- `cli/spinner.py` (spinner implementation)

---

### Phase 4: Implement Simple REPL Loop 🔁
**Goal**: Simple input loop like Claude Code (NO fixed bottom layout)

**Python Implementation**:

```python
import readline
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

class LyraREPL:
    """Simple REPL loop"""
    
    def __init__(self, model: str):
        self.model = model
        self.session = PromptSession(
            completer=WordCompleter(['/exit', '/quit', '/model', '/clear']),
            multiline=False
        )
    
    def run(self):
        """Main REPL loop"""
        print(self._startup_banner())
        print(f"Connected to {self.model}\n")
        
        while True:
            try:
                # Read input (prompt appears naturally after response)
                user_input = self.session.prompt('❯ ')
                
                if not user_input.strip():
                    continue
                
                # Handle slash commands
                if user_input.startswith('/'):
                    if user_input in ['/exit', '/quit']:
                        break
                    elif user_input == '/model':
                        self._show_model_menu()
                        continue
                    elif user_input == '/clear':
                        print('\x1b[2J\x1b[H')  # Clear screen
                        continue
                
                # Execute turn
                self._run_turn(user_input)
                
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break
    
    def _run_turn(self, user_input: str):
        """Execute a single turn"""
        spinner = Spinner()
        renderer = StreamingMarkdownRenderer()
        
        spinner.start("Thinking...")
        
        try:
            # Stream response from API
            for delta in self._stream_response(user_input):
                spinner.tick("Thinking...")
                renderer.push_delta(delta)
            
            renderer.flush()
            spinner.finish("Done")
            
        except Exception as e:
            spinner.fail(f"Error: {e}")
```

**Files to Create**:
- `cli/repl.py` (main REPL loop)

---

### Phase 5: Integrate with Agent Loop 🤖
**Goal**: Connect streaming renderer to agent loop

**Implementation**:

```python
class StreamingAgentHandler:
    """Agent handler with streaming markdown"""
    
    def __init__(self):
        self.renderer = StreamingMarkdownRenderer()
        self.spinner = Spinner()
    
    def on_turn_start(self, turn_id: str):
        """Turn started"""
        self.spinner.start("Processing...")
    
    def on_stream_chunk(self, chunk: str):
        """Streaming text chunk"""
        self.spinner.tick("Processing...")
        self.renderer.push_delta(chunk)
    
    def on_tool_use(self, tool: str, args: dict):
        """Tool called"""
        print(f"\n  \x1b[2m⎿\x1b[0m  {tool}")
    
    def on_turn_end(self, turn_id: str, result: dict):
        """Turn completed"""
        self.renderer.flush()
        self.spinner.finish("Done")
        
        # Show stats
        if usage := result.get("usage"):
            tokens = usage.get("total_tokens", 0)
            print(f"\n\x1b[2m✻ {tokens:,} tokens\x1b[0m\n")
```

**Files to Modify**:
- `cli/agent_handler.py` (use streaming renderer)

---

### Phase 6: Welcome Banner (Simple Print) 🎨
**Goal**: Simple welcome banner (NO TUI)

**Implementation**:

```python
def print_welcome_banner(version: str, model: str, effort: str, provider: str, cwd: str):
    """Print welcome banner"""
    print(f"""
╭─── Lyra v{version} ─────────────────────────────────────────────────────────
  ╦  ╦ ╦ ╦═╗ ╔═╗   Lyra v{version}
  ║  ╚╦╝ ╠╦╝ ╠═╣   {model} · {effort} effort · {provider}
  ╩═╝ ╩  ╩╚═ ╩ ╩   {cwd}
""")
```

**Files to Modify**:
- `cli/commands/chat.py` (use simple print)

---

### Phase 7: Model Selection Menu (Overlay) 📋
**Goal**: Interactive menu that overlays on terminal

**Implementation**:

```python
def show_model_menu(current_model: str) -> Optional[str]:
    """Show interactive model selection menu"""
    import sys
    import tty
    import termios
    
    models = get_registry().get_all_models()
    selected = 0
    
    # Save terminal settings
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        tty.setraw(fd)
        
        # Print menu
        print("\n" + "─" * 80)
        print("  \x1b[36mSelect model\x1b[0m")
        print("  \x1b[2mSwitch between models from multiple providers.\x1b[0m\n")
        
        while True:
            # Render options
            for i, model in enumerate(models):
                cursor = "\x1b[33m❯\x1b[0m " if i == selected else "  "
                checkmark = " \x1b[32m✔\x1b[0m" if model.id == current_model else ""
                print(f"{cursor}{i+1}. {model.name}{checkmark}")
            
            print("\n  Enter to confirm · Esc to cancel")
            print("─" * 80)
            
            # Read key
            char = sys.stdin.read(1)
            
            if char == '\x1b':  # Escape sequence
                next1 = sys.stdin.read(1)
                if next1 == '[':
                    next2 = sys.stdin.read(1)
                    if next2 == 'A':  # Up arrow
                        selected = max(0, selected - 1)
                    elif next2 == 'B':  # Down arrow
                        selected = min(len(models) - 1, selected + 1)
                else:
                    # Esc pressed
                    return None
            elif char == '\r':  # Enter
                return models[selected].id
            
            # Clear menu for re-render
            lines = len(models) + 5
            for _ in range(lines):
                print('\x1b[1A\x1b[2K', end='')
    
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
```

**Files to Modify**:
- `ui/model_menu.py` (use raw terminal control)

---

## 📊 File Structure After Rebuild

```
packages/lyra-cli/src/lyra_cli/
├── cli/
│   ├── repl.py                    (NEW - main REPL loop)
│   ├── markdown_renderer.py       (NEW - streaming markdown)
│   ├── syntax_highlighter.py      (NEW - code highlighting)
│   ├── spinner.py                 (NEW - terminal spinner)
│   ├── agent_handler.py           (MODIFIED - use streaming)
│   ├── models.py                  (KEEP - model registry)
│   └── commands/
│       └── chat.py                (MODIFIED - simple REPL)
├── ui/
│   ├── welcome_banner.py          (MODIFIED - simple print)
│   └── model_menu.py              (MODIFIED - raw terminal)
└── tui_v2/                        (DELETE - remove TUI)
```

---

## 🎯 Key Principles

1. **NO TUI Frameworks**: Use raw ANSI escape codes
2. **NO Fixed Bottom Layout**: Prompt appears after response
3. **Streaming First**: Incremental markdown rendering
4. **Simple Architecture**: Input loop → Stream → Render → Repeat
5. **Cursor Control**: Save/restore for spinner updates
6. **Direct stdout**: No buffering, immediate output

---

## 🔧 Dependencies

**Remove**:
- `textual` (TUI framework)
- `rich.live` (TUI components)

**Add**:
- `prompt_toolkit` (better than readline)
- `mistune` or `markdown` (markdown parsing)
- `pygments` (syntax highlighting)
- `colorama` (ANSI color support)

**Keep**:
- `anthropic` (API client)
- Standard library (sys, io, termios, tty)

---

## ✅ Success Criteria

- [ ] No TUI framework dependencies
- [ ] Streaming markdown rendering works
- [ ] Spinner updates in-place
- [ ] Simple REPL loop (prompt after response)
- [ ] Code blocks with syntax highlighting
- [ ] Model selection menu with keyboard nav
- [ ] Welcome banner (simple print)
- [ ] Tool calls display with ⎿ connector
- [ ] Stats line with ✻ symbol

---

## 🚀 Implementation Order

1. **Phase 1**: Remove TUI (1 hour)
2. **Phase 2**: Streaming markdown (2 hours)
3. **Phase 3**: Spinner (1 hour)
4. **Phase 4**: REPL loop (1 hour)
5. **Phase 5**: Agent integration (1 hour)
6. **Phase 6**: Welcome banner (30 min)
7. **Phase 7**: Model menu (1 hour)

**Total**: ~7.5 hours

---

## 📝 Notes

- This matches Claude Code's actual implementation
- No complex TUI state management
- Simple, maintainable code
- Fast and responsive
- Works in any terminal

---

**Ready to implement?** Let's start with Phase 1: Remove TUI dependencies.
