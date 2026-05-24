# 🎹 ULTRA KEYBINDINGS PLAN: Claude Code Shortcuts for Lyra

**Date**: 2026-05-23  
**Status**: 🎯 Ready for Implementation  
**Goal**: Implement all Claude Code keybindings and special characters in Lyra

---

## Executive Summary

### What Claude Code Has

**Core Shortcuts (15+)**:
- Shift+Tab - Permission mode cycling
- Esc Esc - Rewind menu
- Ctrl+C - Interrupt
- Ctrl+O - Toggle transcript
- Ctrl+G - External editor
- Option+P / Alt+P - Model picker
- Option+T / Alt+T - Extended thinking
- Ctrl+J - Multiline input

**Special Characters (4)**:
- **@** - File/directory/MCP references with tab completion
- **/** - Slash commands (50+)
- **\\** - Line break escape
- **#** - (Needs verification)

**Permission Modes (6)**:
- Normal, Auto, Plan (Shift+Tab accessible)
- acceptEdits, bypassPermissions, Custom (hidden)

---

## Phase 1: Core Shortcuts (Week 1)

### 1.1 Permission Mode Cycling

**Priority**: 🔴 Critical  
**Effort**: 2 days

**Implementation**:
```python
# packages/lyra-cli/src/lyra_cli/cli/keybindings.py

class PermissionModes:
    NORMAL = "normal"
    AUTO = "auto"
    PLAN = "plan"
    ACCEPT_EDITS = "acceptEdits"
    BYPASS = "bypassPermissions"
    CUSTOM = "custom"

class KeybindingHandler:
    def __init__(self):
        self.current_mode = PermissionModes.NORMAL
        self.modes = [
            PermissionModes.NORMAL,
            PermissionModes.AUTO,
            PermissionModes.PLAN
        ]
        
    def handle_shift_tab(self):
        """Cycle through permission modes"""
        current_idx = self.modes.index(self.current_mode)
        next_idx = (current_idx + 1) % len(self.modes)
        self.current_mode = self.modes[next_idx]
        
        # Update status bar
        self.update_status_bar(self.current_mode)
        
        # Show notification
        self.show_notification(f"Mode: {self.current_mode}")
```

**UI Display**:
```
────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ normal mode (shift+tab to cycle) · esc to interrupt · ↓ to manage
```

**Success Criteria**:
- ✅ Shift+Tab cycles modes
- ✅ Status bar updates
- ✅ Notification shows
- ✅ Mode persists in session

---

### 1.2 Rewind Menu (Esc Esc)

**Priority**: 🔴 Critical  
**Effort**: 3 days

**Implementation**:
```python
class RewindMenu:
    def __init__(self, console: Console):
        self.console = console
        self.history = []
        
    def show(self):
        """Show rewind menu on Esc Esc"""
        menu = [
            "1. Undo last action",
            "2. Rollback to checkpoint",
            "3. Revert file changes",
            "4. Cancel operation",
            "5. Resume from here",
        ]
        
        self.console.print("\n[bold cyan]Rewind Menu[/bold cyan]")
        for item in menu:
            self.console.print(f"  {item}")
        
        choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5"])
        self.handle_choice(choice)
```

**UI Display**:
```
Rewind Menu
  1. Undo last action
  2. Rollback to checkpoint
  3. Revert file changes
  4. Cancel operation
  5. Resume from here

Select option [1/2/3/4/5]:
```

**Success Criteria**:
- ✅ Esc Esc opens menu
- ✅ Options work correctly
- ✅ History tracked
- ✅ Rollback functional

---

### 1.3 Interrupt (Ctrl+C)

**Priority**: 🔴 Critical  
**Effort**: 1 day

**Implementation**:
```python
import signal

class InterruptHandler:
    def __init__(self):
        signal.signal(signal.SIGINT, self.handle_interrupt)
        self.interrupted = False
        
    def handle_interrupt(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        self.interrupted = True
        print("\n[yellow]⚠[/yellow] Interrupted by user")
        print("[dim]Press Ctrl+C again to force quit[/dim]")
        
        # Set timeout for second Ctrl+C
        signal.signal(signal.SIGINT, self.force_quit)
        signal.alarm(3)  # 3 second window
        
    def force_quit(self, signum, frame):
        """Force quit on second Ctrl+C"""
        print("\n[red]✗[/red] Force quit")
        sys.exit(130)
```

**Success Criteria**:
- ✅ Ctrl+C interrupts gracefully
- ✅ Second Ctrl+C force quits
- ✅ Clean shutdown
- ✅ State saved

---

### 1.4 Toggle Transcript (Ctrl+O)

**Priority**: 🟡 High  
**Effort**: 2 days

**Implementation**:
```python
class TranscriptToggle:
    def __init__(self, console: Console):
        self.console = console
        self.visible = False
        self.transcript = []
        
    def toggle(self):
        """Toggle transcript visibility on Ctrl+O"""
        self.visible = not self.visible
        
        if self.visible:
            self.show_transcript()
        else:
            self.hide_transcript()
            
    def show_transcript(self):
        """Show full conversation transcript"""
        self.console.print("\n[bold cyan]Transcript[/bold cyan]")
        self.console.print("[dim]" + "─" * 80 + "[/dim]")
        
        for entry in self.transcript:
            role = entry["role"]
            content = entry["content"]
            
            if role == "user":
                self.console.print(f"\n[bold green]❯[/bold green] {content}")
            else:
                self.console.print(f"\n{content}")
                
        self.console.print("[dim]" + "─" * 80 + "[/dim]")
```

**Success Criteria**:
- ✅ Ctrl+O toggles transcript
- ✅ Full history shown
- ✅ Scrollable
- ✅ Searchable

---

### 1.5 External Editor (Ctrl+G)

**Priority**: 🟡 High  
**Effort**: 2 days

**Implementation**:
```python
import subprocess
import tempfile

class ExternalEditor:
    def __init__(self):
        self.editor = os.getenv("EDITOR", "vim")
        
    def open(self, content: str = "") -> str:
        """Open external editor on Ctrl+G"""
        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.md',
            delete=False
        ) as f:
            f.write(content)
            temp_path = f.name
            
        # Open editor
        subprocess.run([self.editor, temp_path])
        
        # Read result
        with open(temp_path, 'r') as f:
            result = f.read()
            
        # Cleanup
        os.unlink(temp_path)
        
        return result
```

**Success Criteria**:
- ✅ Ctrl+G opens editor
- ✅ Respects $EDITOR
- ✅ Content preserved
- ✅ Changes applied

---

## Phase 2: Special Characters (Week 2)

### 2.1 @ File References

**Priority**: 🔴 Critical  
**Effort**: 4 days

**Implementation**:
```python
from prompt_toolkit.completion import Completer, Completion
import os

class FileCompleter(Completer):
    def get_completions(self, document, complete_event):
        """Tab completion for @file references"""
        text = document.text_before_cursor
        
        # Check if we're in @ context
        if '@' not in text:
            return
            
        # Get partial path after @
        parts = text.split('@')
        partial = parts[-1]
        
        # Get current directory
        if '/' in partial:
            dir_path = os.path.dirname(partial)
            prefix = os.path.basename(partial)
        else:
            dir_path = '.'
            prefix = partial
            
        # List matching files
        try:
            for item in os.listdir(dir_path):
                if item.startswith(prefix):
                    full_path = os.path.join(dir_path, item)
                    
                    # Add / for directories
                    if os.path.isdir(full_path):
                        item += '/'
                        
                    yield Completion(
                        item,
                        start_position=-len(prefix),
                        display=item,
                        display_meta=self.get_meta(full_path)
                    )
        except OSError:
            pass
            
    def get_meta(self, path: str) -> str:
        """Get file metadata for display"""
        if os.path.isdir(path):
            count = len(os.listdir(path))
            return f"{count} items"
        else:
            size = os.path.getsize(path)
            return f"{size} bytes"
```

**UI Display**:
```
❯ Read @src/main.py and explain

Tab completion:
  src/
  ├─ main.py          (1.2 KB)
  ├─ utils.py         (856 bytes)
  └─ config.py        (432 bytes)
```

**Success Criteria**:
- ✅ @ triggers file completion
- ✅ Tab shows suggestions
- ✅ Directories show /
- ✅ Metadata displayed
- ✅ MCP resources supported

---

### 2.2 / Slash Commands

**Priority**: 🔴 Critical  
**Effort**: 3 days

**Implementation**:
```python
class SlashCommandCompleter(Completer):
    def __init__(self, commands: dict):
        self.commands = commands
        
    def get_completions(self, document, complete_event):
        """Tab completion for /commands"""
        text = document.text_before_cursor
        
        # Check if we're in / context
        if not text.startswith('/'):
            return
            
        # Get partial command
        partial = text[1:]  # Remove /
        
        # Find matching commands
        for cmd, info in self.commands.items():
            if cmd.startswith(partial):
                yield Completion(
                    cmd,
                    start_position=-len(partial),
                    display=f"/{cmd}",
                    display_meta=info['description']
                )
```

**UI Display**:
```
❯ /pla

Tab completion:
  /plan              Create implementation plan
  /plan-prd          Generate PRD
  /planner           Launch planner agent
```

**Success Criteria**:
- ✅ / triggers command completion
- ✅ Tab shows suggestions
- ✅ Descriptions shown
- ✅ 155+ commands available

---

### 2.3 \ Line Break Escape

**Priority**: 🟢 Medium  
**Effort**: 1 day

**Implementation**:
```python
class MultilineInput:
    def __init__(self):
        self.buffer = []
        
    def handle_backslash(self, text: str) -> bool:
        """Handle \ for line continuation"""
        if text.endswith('\\'):
            # Remove \ and continue
            self.buffer.append(text[:-1])
            return True  # Continue input
        else:
            # End of input
            self.buffer.append(text)
            return False  # Submit
            
    def get_input(self) -> str:
        """Get complete multiline input"""
        result = '\n'.join(self.buffer)
        self.buffer = []
        return result
```

**UI Display**:
```
❯ This is a long message \
... that continues on the next line \
... and another line
```

**Success Criteria**:
- ✅ \ continues input
- ✅ Multiple lines supported
- ✅ Visual indicator shown
- ✅ Submit on final line

---

## Phase 3: Advanced Shortcuts (Week 3)

### 3.1 Model Picker (Option+P / Alt+P)

**Priority**: 🟡 High  
**Effort**: 2 days

**Implementation**:
```python
class ModelPicker:
    def __init__(self, console: Console):
        self.console = console
        self.models = [
            ("Opus 4.7", "Most capable"),
            ("Sonnet 4.6", "Best for everyday"),
            ("Haiku 4.5", "Fastest"),
        ]
        self.current = 0
        
    def show(self):
        """Show model picker on Option+P"""
        self.console.print("\n[bold cyan]Select Model[/bold cyan]")
        
        for i, (name, desc) in enumerate(self.models):
            arrow = "❯" if i == self.current else " "
            check = "✔" if i == self.current else " "
            self.console.print(
                f"  {arrow} {i+1}. {name} {check}  [dim]{desc}[/dim]"
            )
            
        self.console.print("\n[dim]Enter to confirm · Esc to cancel[/dim]")
```

**Success Criteria**:
- ✅ Option+P opens picker
- ✅ Arrow keys navigate
- ✅ Enter selects
- ✅ Model switches

---

### 3.2 Extended Thinking (Option+T / Alt+T)

**Priority**: 🟡 High  
**Effort**: 2 days

**Implementation**:
```python
class ExtendedThinking:
    def __init__(self):
        self.enabled = False
        self.budget = 10000  # tokens
        
    def toggle(self):
        """Toggle extended thinking on Option+T"""
        self.enabled = not self.enabled
        
        if self.enabled:
            print(f"[green]✓[/green] Extended thinking enabled ({self.budget} tokens)")
        else:
            print("[dim]Extended thinking disabled[/dim]")
            
    def set_budget(self, tokens: int):
        """Set thinking token budget"""
        self.budget = tokens
        print(f"[cyan]ℹ[/cyan] Thinking budget: {tokens} tokens")
```

**Success Criteria**:
- ✅ Option+T toggles thinking
- ✅ Budget configurable
- ✅ Status shown
- ✅ Thinking displayed

---

### 3.3 Multiline Input (Ctrl+J)

**Priority**: 🟢 Medium  
**Effort**: 1 day

**Implementation**:
```python
class MultilineMode:
    def __init__(self):
        self.enabled = False
        
    def toggle(self):
        """Toggle multiline mode on Ctrl+J"""
        self.enabled = not self.enabled
        
        if self.enabled:
            print("[cyan]ℹ[/cyan] Multiline mode (Ctrl+D to submit)")
        else:
            print("[dim]Single line mode[/dim]")
```

**Success Criteria**:
- ✅ Ctrl+J toggles multiline
- ✅ Ctrl+D submits
- ✅ Visual indicator
- ✅ Syntax highlighting

---

## Phase 4: Customization (Week 4)

### 4.1 Keybindings Configuration

**Priority**: 🟢 Medium  
**Effort**: 3 days

**Implementation**:
```json
// ~/.lyra/keybindings.json
{
  "permissionCycle": "shift+tab",
  "rewindMenu": "esc esc",
  "interrupt": "ctrl+c",
  "toggleTranscript": "ctrl+o",
  "externalEditor": "ctrl+g",
  "modelPicker": "alt+p",
  "extendedThinking": "alt+t",
  "multilineInput": "ctrl+j",
  "fileReference": "@",
  "slashCommand": "/",
  "lineBreak": "\\",
  "custom": {
    "quickSave": "ctrl+s",
    "quickLoad": "ctrl+l"
  }
}
```

**Success Criteria**:
- ✅ JSON configuration
- ✅ Custom bindings
- ✅ Validation
- ✅ Hot reload

---

### 4.2 Statusline Customization

**Priority**: 🟢 Medium  
**Effort**: 2 days

**Implementation**:
```python
class Statusline:
    def __init__(self, console: Console):
        self.console = console
        self.segments = [
            "mode",
            "model",
            "tokens",
            "cost",
            "time"
        ]
        
    def render(self):
        """Render customizable statusline"""
        parts = []
        
        for segment in self.segments:
            value = self.get_segment_value(segment)
            if value:
                parts.append(value)
                
        status = " · ".join(parts)
        self.console.print(f"  ⏵⏵ {status}")
```

**Success Criteria**:
- ✅ Customizable segments
- ✅ Dynamic updates
- ✅ Color themes
- ✅ Responsive

---

## Implementation Timeline

### Week 1: Core Shortcuts
- Permission mode cycling
- Rewind menu
- Interrupt handling
- Transcript toggle
- External editor

### Week 2: Special Characters
- @ file references
- / slash commands
- \ line breaks

### Week 3: Advanced Shortcuts
- Model picker
- Extended thinking
- Multiline input

### Week 4: Customization
- Keybindings config
- Statusline customization

---

## Success Metrics

### Quantitative
- ✅ 15+ keyboard shortcuts
- ✅ 4 special characters
- ✅ 6 permission modes
- ✅ 155+ slash commands
- ✅ Tab completion
- ✅ Custom keybindings

### Qualitative
- ✅ Intuitive shortcuts
- ✅ Fast navigation
- ✅ Productive workflow
- ✅ Customizable
- ✅ Well documented

---

## Testing Plan

### Unit Tests
- Keybinding detection
- Mode cycling
- Completion logic
- Configuration loading

### Integration Tests
- End-to-end workflows
- Multi-key sequences
- Custom bindings
- Edge cases

### User Testing
- Usability testing
- Feedback collection
- Iteration

---

## Documentation

### User Guide
- Keyboard shortcuts reference
- Special characters guide
- Customization tutorial
- Tips and tricks

### Developer Guide
- Keybinding architecture
- Adding new shortcuts
- Custom completers
- Testing guide

---

## Conclusion

This plan implements all Claude Code keybindings and special characters in Lyra:
- ✅ 15+ keyboard shortcuts
- ✅ 4 special characters
- ✅ Tab completion
- ✅ Custom keybindings
- ✅ Statusline customization

**Status**: 🎯 Ready for Implementation  
**Timeline**: 4 weeks  
**Team Size**: 2 developers

---

**Created by**: Claude Opus 4.7  
**Date**: 2026-05-23  
**Version**: 1.0
