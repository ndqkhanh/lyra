# Lyra CLI Interface Specification

**Version**: 1.0.0  
**Date**: 2026-05-23  
**Status**: Design Phase

---

## Overview

This document specifies the command-line interface for Lyra after removing TUI v2. The CLI follows Claude Code patterns for a clean, professional user experience using Rich and Typer libraries.

---

## Technology Stack

### Core Dependencies
```toml
typer = "^0.12.0"           # CLI framework with type hints
rich = "^13.7.0"            # Terminal formatting and output
prompt-toolkit = "^3.0.0"  # Interactive prompts with history
```

### Optional Dependencies
```toml
yaspin = "^3.0.0"          # Lightweight spinners (if Rich insufficient)
```

---

## CLI Architecture

### Module Structure
```
packages/lyra-cli/src/lyra_cli/
├── cli/
│   ├── __init__.py              # Exports: cli_app, console
│   ├── app.py                   # Main Typer application
│   ├── output.py                # Rich output formatting utilities
│   ├── prompts.py               # Interactive prompt handling
│   ├── status.py                # Status display (spinners, progress)
│   ├── welcome.py               # Welcome screen rendering
│   └── commands/                # Command handlers
│       ├── __init__.py
│       ├── chat.py              # Main chat loop command
│       ├── config.py            # Configuration commands
│       ├── session.py           # Session management
│       ├── skills.py            # Skills/MCP commands
│       └── debug.py             # Debug/diagnostic commands
├── agent/                       # Agent loop (existing, refactored)
│   ├── loop.py                  # Main agent loop
│   ├── callbacks.py             # NEW: Callback protocol for CLI
│   └── ...
├── config/                      # Configuration (existing)
└── __main__.py                  # Entry point (simplified)
```

---

## Entry Point

### `__main__.py`
```python
#!/usr/bin/env python3
"""Lyra CLI entry point"""

import sys
from lyra_cli.cli import cli_app

def main():
    """Main entry point"""
    try:
        cli_app()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## Core CLI Application

### `cli/app.py`
```python
"""Main Typer CLI application"""

import typer
from rich.console import Console
from typing import Optional

app = typer.Typer(
    name="lyra",
    help="Lyra - AI Research Assistant",
    add_completion=False,
    rich_markup_mode="rich",
)

# Global console instance
console = Console()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
):
    """Lyra - AI Research Assistant"""
    if version:
        console.print("Lyra v0.1.0", style="cyan")
        raise typer.Exit()
    
    # If no command provided, start interactive chat
    if ctx.invoked_subcommand is None:
        from lyra_cli.cli.commands.chat import interactive_chat
        interactive_chat()

# Import and register commands
from lyra_cli.cli.commands import chat, config, session, skills, debug

app.add_typer(config.app, name="config", help="Configuration management")
app.add_typer(session.app, name="session", help="Session management")
app.add_typer(skills.app, name="skills", help="Skills and MCP management")
app.add_typer(debug.app, name="debug", help="Debug and diagnostics")
```

---

## Output Formatting

### `cli/output.py`
```python
"""Rich-based output formatting utilities"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from typing import List, Dict, Any

class OutputFormatter:
    """Handles all Rich-based output formatting"""
    
    def __init__(self, console: Console):
        self.console = console
    
    def welcome_screen(
        self,
        user: str,
        model: str,
        cwd: str,
        organization: str = "Claude Max"
    ) -> None:
        """Display welcome screen with box drawing"""
        logo = """
              ▐▛███▜▌
             ▝▜█████▛▘
               ▘▘ ▝▝
        """
        
        content = Text()
        content.append(f"\n\nWelcome back {user}!\n\n", style="bold cyan")
        content.append(logo, style="magenta")
        content.append(f"\n{model} · {organization}\n", style="dim")
        content.append(f"  {cwd}\n", style="dim blue")
        
        panel = Panel(
            content,
            title="Lyra v0.1.0",
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)
    
    def status_message(
        self,
        message: str,
        spinner: str = "⏺",
        style: str = "cyan"
    ) -> None:
        """Display status message with spinner"""
        self.console.print(f"{spinner} {message}", style=style)
    
    def success_message(self, message: str) -> None:
        """Display success message"""
        self.console.print(f"✓ {message}", style="green")
    
    def error_message(self, message: str) -> None:
        """Display error message"""
        self.console.print(f"✗ {message}", style="red")
    
    def warning_message(self, message: str) -> None:
        """Display warning message"""
        self.console.print(f"⚠ {message}", style="yellow")
    
    def info_message(self, message: str) -> None:
        """Display info message"""
        self.console.print(f"ℹ {message}", style="blue")
    
    def background_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Display background task list"""
        if not tasks:
            return
        
        self.console.print("\n[bold]Background Tasks:[/bold]")
        tree = Tree("⏺ Active Tasks")
        
        for task in tasks:
            status = task.get("status", "running")
            name = task.get("name", "Unknown")
            progress = task.get("progress", 0)
            
            if status == "running":
                icon = "⏺"
                style = "cyan"
            elif status == "completed":
                icon = "✓"
                style = "green"
            elif status == "failed":
                icon = "✗"
                style = "red"
            else:
                icon = "⏳"
                style = "yellow"
            
            task_text = f"{icon} {name}"
            if progress > 0:
                task_text += f" ({progress}%)"
            
            tree.add(Text(task_text, style=style))
        
        self.console.print(tree)
    
    def agent_output(
        self,
        agent_name: str,
        tool_uses: int,
        tokens: int,
        duration: str
    ) -> None:
        """Display agent execution summary"""
        self.console.print(
            f"  ├ {agent_name} · {tool_uses} tool uses · {tokens:,} tokens · {duration}",
            style="dim"
        )
    
    def hierarchical_status(self, items: List[str], indent: int = 0) -> None:
        """Display hierarchical status output"""
        prefix = "  " * indent
        for item in items:
            self.console.print(f"{prefix}{item}")
    
    def status_table(
        self,
        title: str,
        headers: List[str],
        rows: List[List[str]]
    ) -> None:
        """Display status table"""
        table = Table(title=title, show_header=True, header_style="bold cyan")
        
        for header in headers:
            table.add_column(header)
        
        for row in rows:
            table.add_row(*row)
        
        self.console.print(table)
    
    def divider(self, char: str = "─", width: int = 80) -> None:
        """Display horizontal divider"""
        self.console.print(char * width, style="dim")
```

---

## Interactive Prompts

### `cli/prompts.py`
```python
"""Interactive prompt handling with prompt_toolkit"""

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from pathlib import Path
import os

class LyraPrompt:
    """Interactive prompt with history and completion"""
    
    def __init__(self):
        # Setup history file
        history_dir = Path.home() / ".lyra"
        history_dir.mkdir(exist_ok=True)
        history_file = history_dir / "history"
        
        # Slash commands for completion
        slash_commands = [
            "/help", "/exit", "/quit", "/clear",
            "/model", "/config", "/session", "/sessions",
            "/skills", "/debug", "/status", "/history"
        ]
        
        completer = WordCompleter(
            slash_commands,
            ignore_case=True,
            sentence=True
        )
        
        # Key bindings
        kb = KeyBindings()
        
        @kb.add('c-c')
        def _(event):
            """Handle Ctrl+C"""
            event.app.exit(exception=KeyboardInterrupt)
        
        @kb.add('c-d')
        def _(event):
            """Handle Ctrl+D (EOF)"""
            event.app.exit(exception=EOFError)
        
        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=completer,
            complete_while_typing=True,
            key_bindings=kb,
        )
    
    def get_input(self, prompt: str = "❯ ") -> str:
        """Get user input with history and completion"""
        try:
            return self.session.prompt(prompt)
        except (KeyboardInterrupt, EOFError):
            raise
    
    def get_multiline_input(self, prompt: str = "❯ ") -> str:
        """Get multi-line input"""
        try:
            return self.session.prompt(
                prompt,
                multiline=True,
                prompt_continuation="... "
            )
        except (KeyboardInterrupt, EOFError):
            raise
```

---

## Status Display

### `cli/status.py`
```python
"""Status display with spinners and progress bars"""

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn
)
from contextlib import contextmanager
from typing import Optional

class StatusDisplay:
    """Handles status display during operations"""
    
    def __init__(self, console: Console):
        self.console = console
        self._live: Optional[Live] = None
        self._progress: Optional[Progress] = None
    
    @contextmanager
    def spinner(self, message: str, spinner_style: str = "dots"):
        """Context manager for spinner display"""
        spinner = Spinner(spinner_style, text=message)
        with Live(spinner, console=self.console, refresh_per_second=10):
            yield
    
    @contextmanager
    def progress_bar(self):
        """Context manager for progress bar"""
        progress = Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
        
        with progress:
            yield progress
    
    def show_working(self, message: str = "Working...") -> None:
        """Show working indicator"""
        self.console.print(f"⏺ {message}", style="cyan")
    
    def show_thinking(self, message: str = "Thinking...") -> None:
        """Show thinking indicator"""
        self.console.print(f"✶ {message}", style="blue")
    
    def show_processing(self, message: str = "Processing...") -> None:
        """Show processing indicator"""
        self.console.print(f"✻ {message}", style="yellow")
```

---

## Welcome Screen

### `cli/welcome.py`
```python
"""Welcome screen rendering"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from pathlib import Path
import os

def show_welcome(console: Console) -> None:
    """Display welcome screen"""
    # Get user info
    user = os.getenv("USER", "User")
    cwd = Path.cwd()
    model = "Opus 4.7"  # TODO: Get from config
    
    # Lyra logo
    logo = """
          ▐▛███▜▌
         ▝▜█████▛▘
           ▘▘ ▝▝
    """
    
    # Build content
    content = Text()
    content.append(f"\n\nWelcome back {user}!\n\n", style="bold cyan")
    content.append(logo, style="magenta")
    content.append(f"\n{model} · Claude Max\n", style="dim")
    content.append(f"  {cwd}\n", style="dim blue")
    
    # Create panel
    panel = Panel(
        content,
        title="Lyra v0.1.0",
        border_style="cyan",
        padding=(1, 2),
    )
    
    console.print(panel)
    
    # Show tips
    console.print("\n[dim]Tips:[/dim]")
    console.print("  • Type your message to start chatting")
    console.print("  • Use /help for available commands")
    console.print("  • Press Ctrl+C to interrupt, Ctrl+D to exit")
    console.print()
```

---

## Command Specifications

### Chat Command (`cli/commands/chat.py`)

**Purpose**: Main interactive chat loop

**Usage**:
```bash
# Start interactive chat (default)
lyra

# Send single message
lyra chat "Explain quantum computing"

# Specify model
lyra chat --model sonnet "Quick question"
```

**Implementation**:
```python
import typer
from rich.console import Console
from lyra_cli.cli.prompts import LyraPrompt
from lyra_cli.cli.welcome import show_welcome
from lyra_cli.agent.loop import AgentLoop
from lyra_cli.cli.agent_handler import CLIAgentHandler

app = typer.Typer()
console = Console()

@app.command()
def chat(
    message: str = typer.Argument(None, help="Message to send"),
    model: str = typer.Option("opus", help="Model to use"),
):
    """Start interactive chat or send single message"""
    if message:
        # Single message mode
        send_message(message, model)
    else:
        # Interactive mode
        interactive_chat()

def interactive_chat():
    """Interactive chat loop"""
    show_welcome(console)
    
    prompt = LyraPrompt()
    agent_handler = CLIAgentHandler(console)
    agent_loop = AgentLoop(callback=agent_handler)
    
    while True:
        try:
            user_input = prompt.get_input()
            
            if not user_input.strip():
                continue
            
            # Handle slash commands
            if user_input.startswith("/"):
                handle_slash_command(user_input)
                continue
            
            # Send to agent
            agent_loop.process_message(user_input)
            
        except (KeyboardInterrupt, EOFError):
            console.print("\n\nGoodbye!", style="cyan")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")

def send_message(message: str, model: str):
    """Send single message"""
    agent_handler = CLIAgentHandler(console)
    agent_loop = AgentLoop(callback=agent_handler, model=model)
    agent_loop.process_message(message)
```

### Config Command (`cli/commands/config.py`)

**Purpose**: Configuration management

**Usage**:
```bash
# Show current config
lyra config show

# Set config value
lyra config set model opus

# Get config value
lyra config get model

# Edit config file
lyra config edit
```

### Session Command (`cli/commands/session.py`)

**Purpose**: Session management

**Usage**:
```bash
# List sessions
lyra session list

# Switch session
lyra session switch <session-id>

# Create new session
lyra session new

# Delete session
lyra session delete <session-id>
```

### Skills Command (`cli/commands/skills.py`)

**Purpose**: Skills and MCP management

**Usage**:
```bash
# List available skills
lyra skills list

# Show skill details
lyra skills show <skill-name>

# Enable skill
lyra skills enable <skill-name>

# Disable skill
lyra skills disable <skill-name>
```

### Debug Command (`cli/commands/debug.py`)

**Purpose**: Debug and diagnostics

**Usage**:
```bash
# Show system status
lyra debug status

# Show agent logs
lyra debug logs

# Show token usage
lyra debug tokens

# Test agent connection
lyra debug test
```

---

## Agent Integration

### Callback Protocol (`agent/callbacks.py`)

```python
"""Callback protocol for agent output"""

from typing import Protocol, Dict, Any

class AgentOutputCallback(Protocol):
    """Protocol for handling agent output"""
    
    def on_turn_start(self, turn_id: str) -> None:
        """Called when agent turn starts"""
        ...
    
    def on_tool_use(self, tool: str, args: Dict[str, Any]) -> None:
        """Called when agent uses a tool"""
        ...
    
    def on_stream_chunk(self, chunk: str) -> None:
        """Called for streaming text chunks"""
        ...
    
    def on_turn_end(self, turn_id: str, result: Dict[str, Any]) -> None:
        """Called when agent turn ends"""
        ...
    
    def on_error(self, error: Exception) -> None:
        """Called when error occurs"""
        ...
```

### CLI Agent Handler (`cli/agent_handler.py`)

```python
"""CLI implementation of AgentOutputCallback"""

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from lyra_cli.agent.callbacks import AgentOutputCallback
from typing import Dict, Any

class CLIAgentHandler:
    """CLI implementation of agent output handling"""
    
    def __init__(self, console: Console):
        self.console = console
        self.live = None
        self.current_turn = None
    
    def on_turn_start(self, turn_id: str) -> None:
        """Called when agent turn starts"""
        self.current_turn = turn_id
        self.console.print("⏺ Processing...", style="cyan")
    
    def on_tool_use(self, tool: str, args: Dict[str, Any]) -> None:
        """Called when agent uses a tool"""
        self.console.print(f"  ⎿ {tool}", style="dim")
    
    def on_stream_chunk(self, chunk: str) -> None:
        """Called for streaming text chunks"""
        self.console.print(chunk, end="", markup=False)
    
    def on_turn_end(self, turn_id: str, result: Dict[str, Any]) -> None:
        """Called when agent turn ends"""
        self.console.print()
        
        # Show token usage if available
        if "usage" in result:
            tokens = result["usage"].get("total_tokens", 0)
            self.console.print(
                f"\n[dim]Tokens: {tokens:,}[/dim]"
            )
        
        self.current_turn = None
    
    def on_error(self, error: Exception) -> None:
        """Called when error occurs"""
        self.console.print(f"\n[red]✗ Error: {error}[/red]")
        self.current_turn = None
```

---

## Error Handling

### Global Error Handler

```python
"""Global error handling"""

import sys
from rich.console import Console

console = Console()

def handle_error(error: Exception) -> None:
    """Handle errors gracefully"""
    if isinstance(error, KeyboardInterrupt):
        console.print("\n\nInterrupted by user", style="yellow")
        sys.exit(130)
    elif isinstance(error, EOFError):
        console.print("\n\nGoodbye!", style="cyan")
        sys.exit(0)
    else:
        console.print(f"\n[red]✗ Error: {error}[/red]")
        if os.getenv("DEBUG"):
            import traceback
            traceback.print_exc()
        sys.exit(1)
```

---

## Configuration

### Config File Location

```
~/.lyra/config.toml
```

### Config Schema

```toml
[general]
model = "opus"
organization = "Claude Max"

[display]
theme = "default"
show_tokens = true
show_timing = true

[history]
max_entries = 1000
save_location = "~/.lyra/history"

[agent]
max_turns = 10
timeout = 300
```

---

## Testing Requirements

### Unit Tests
- [ ] Test output formatting functions
- [ ] Test prompt handling
- [ ] Test status display
- [ ] Test command parsing

### Integration Tests
- [ ] Test interactive chat loop
- [ ] Test agent callback integration
- [ ] Test slash command handling
- [ ] Test error handling

### Manual Tests
- [ ] Welcome screen displays correctly
- [ ] Interactive prompt accepts input
- [ ] Agent output displays correctly
- [ ] Background tasks display correctly
- [ ] Error messages display correctly
- [ ] Ctrl+C interrupts gracefully
- [ ] Ctrl+D exits gracefully

---

## Performance Requirements

- **Startup time**: < 1 second
- **Memory usage**: < 100MB baseline
- **Response time**: < 100ms for UI updates
- **No memory leaks**: During long sessions

---

## Accessibility

- Support terminal screen readers
- Provide text-only output mode
- Support high contrast themes
- Keyboard-only navigation

---

## Future Enhancements

- [ ] Multi-line input with editor
- [ ] Syntax highlighting for code blocks
- [ ] Image display in terminal (iTerm2, Kitty)
- [ ] Mouse support for clickable links
- [ ] Custom themes
- [ ] Plugin system for commands

---

**Status**: Design Complete  
**Next Phase**: Implementation (Phase 2)
