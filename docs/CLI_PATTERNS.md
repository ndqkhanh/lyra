# Lyra CLI Patterns Library

**Version**: 1.0.0  
**Date**: 2026-05-23  
**Purpose**: Reusable CLI patterns for Lyra implementation

---

## Overview

This document provides a library of reusable CLI patterns based on Claude Code and ECC research. Each pattern includes code examples and usage guidelines.

---

## Pattern 1: Welcome Screen

### Claude Code Style (Rich)

```python
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

def show_welcome(console: Console, user: str, model: str, cwd: str):
    """Display welcome screen with box drawing"""
    logo = """
          ▐▛███▜▌
         ▝▜█████▛▘
           ▘▘ ▝▝
    """
    
    content = Text()
    content.append(f"\n\nWelcome back {user}!\n\n", style="bold cyan")
    content.append(logo, style="magenta")
    content.append(f"\n{model} · Claude Max\n", style="dim")
    content.append(f"  {cwd}\n", style="dim blue")
    
    panel = Panel(
        content,
        title="Lyra v0.1.0",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)
```

**Output**:
```
╭─── Lyra v0.1.0 ───────────────────────────────────────────╮
│                                                            │
│                                                            │
│                 Welcome back Khanh!                        │
│                                                            │
│                       ▐▛███▜▌                              │
│                      ▝▜█████▛▘                             │
│                        ▘▘ ▝▝                               │
│                                                            │
│ Opus 4.7 · Claude Max                                      │
│   ~/research/harness-engineering/projects/lyra             │
│                                                            │
╰────────────────────────────────────────────────────────────╯
```

### ECC Style (Plain Unicode)

```python
def show_simple_welcome():
    """Simple welcome without Rich"""
    print("╭─────────────────────────────────────────╮")
    print("│                                         │")
    print("│  Lyra v0.1.0                            │")
    print("│  AI Research Assistant                  │")
    print("│                                         │")
    print("╰─────────────────────────────────────────╯")
```

**When to use**:
- Application startup
- After clearing screen
- Session start

---

## Pattern 2: Status Messages with Spinners

### Basic Status

```python
from rich.console import Console

console = Console()

# Working status
console.print("⏺ Processing...", style="cyan")

# Success
console.print("✓ Complete!", style="green")

# Error
console.print("✗ Failed!", style="red")

# Warning
console.print("⚠ Warning!", style="yellow")
```

### Live Spinner

```python
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

console = Console()

with console.status("[bold green]⏺ Processing...") as status:
    # Do work
    time.sleep(2)
    status.update("[bold yellow]✻ Building...")
    time.sleep(2)
    status.update("[bold blue]✶ Testing...")
    time.sleep(2)

console.print("✓ Complete!", style="green")
```

**Spinner Characters**:
- `⏺` - Running/Processing (cyan)
- `✻` - Working/Building (yellow)
- `✶` - Thinking/Analyzing (blue)
- `✓` - Success (green)
- `✗` - Failed (red)
- `⚠` - Warning (yellow)
- `ℹ` - Info (blue)
- `⏳` - Pending (dim)

**When to use**:
- Long-running operations
- Agent processing
- Tool execution
- Background tasks

---

## Pattern 3: Background Task Display

### Task Tree

```python
from rich.console import Console
from rich.tree import Tree
from rich.text import Text

console = Console()

def show_background_tasks(tasks: list):
    """Display background tasks as tree"""
    tree = Tree("⏺ Active Background Tasks")
    
    for task in tasks:
        status = "⏺" if task["running"] else "✓"
        style = "cyan" if task["running"] else "green"
        progress = f" ({task['progress']}%)" if task.get("progress") else ""
        
        tree.add(Text(f"{status} {task['name']}{progress}", style=style))
    
    console.print(tree)

# Example usage
tasks = [
    {"name": "Research GitHub repos", "running": True, "progress": 45},
    {"name": "Search academic papers", "running": True, "progress": 30},
    {"name": "Analyze results", "running": False},
]
show_background_tasks(tasks)
```

**Output**:
```
⏺ Active Background Tasks
├── ⏺ Research GitHub repos (45%)
├── ⏺ Search academic papers (30%)
└── ✓ Analyze results
```

### Task List (Claude Code Style)

```python
def show_agent_tasks(agents: list):
    """Display agent tasks"""
    console.print("\n⏺ Running 4 agents...")
    
    for agent in agents:
        console.print(
            f"  ├ {agent['name']} · {agent['tools']} tool uses · {agent['tokens']:,} tokens",
            style="dim"
        )
```

**Output**:
```
⏺ Running 4 agents...
  ├ Research GitHub repos · 10 tool uses · 29,700 tokens
  ├ Search for compression · 6 tool uses · 29,900 tokens
  ├ Research papers · 5 tool uses · 29,800 tokens
  └ Production tools · 6 tool uses · 25,700 tokens
```

**When to use**:
- Multiple concurrent operations
- Agent orchestration
- Parallel task execution

---

## Pattern 4: Progress Indicators

### Progress Bar

```python
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn
)

with Progress(
    SpinnerColumn(spinner_name="dots"),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    TimeRemainingColumn(),
) as progress:
    
    task = progress.add_task("⏺ Downloading...", total=100)
    
    for i in range(100):
        time.sleep(0.05)
        progress.update(task, advance=1)
```

**Output**:
```
⠋ ⏺ Downloading... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45% 0:00:05
```

### Simple Progress

```python
def show_progress(current: int, total: int, description: str):
    """Simple progress indicator"""
    percent = int((current / total) * 100)
    bar_length = 40
    filled = int((bar_length * current) / total)
    bar = "━" * filled + "─" * (bar_length - filled)
    
    console.print(f"⏺ {description} {bar} {percent}%", end="\r")
```

**When to use**:
- File downloads
- Data processing
- Long computations
- Batch operations

---

## Pattern 5: Hierarchical Status Output

### ECC Style

```python
def show_hierarchical_status():
    """Hierarchical status like ECC"""
    console.print("\n[bold]System Status:[/bold]")
    console.print("Active sessions: 3")
    console.print("  - session-abc123 [active]")
    console.print("    Status: OK")
    console.print("    Repo: /Users/user/project")
    console.print("    Workers: 2")
    console.print("  - session-def456 [idle]")
    console.print("    Status: WARNING")
    console.print("    Repo: /Users/user/other")
    console.print("    Workers: 1")
    console.print()
    console.print("Summary: ok=2, warnings=1, errors=0")
```

**Output**:
```
System Status:
Active sessions: 3
  - session-abc123 [active]
    Status: OK
    Repo: /Users/user/project
    Workers: 2
  - session-def456 [idle]
    Status: WARNING
    Repo: /Users/user/other
    Workers: 1

Summary: ok=2, warnings=1, errors=0
```

### Tree Style

```python
from rich.tree import Tree

def show_tree_status():
    """Tree-based status"""
    tree = Tree("⏺ System Status")
    
    sessions = tree.add("📁 Active Sessions (3)")
    sessions.add("✓ session-abc123 [active]")
    sessions.add("⚠ session-def456 [degraded]")
    sessions.add("⏺ session-ghi789 [running]")
    
    services = tree.add("🔧 Services")
    services.add("✓ Agent Loop: Running")
    services.add("✓ API: Connected")
    services.add("⚠ Cache: Degraded")
    
    console.print(tree)
```

**When to use**:
- System status display
- Session management
- Service health checks
- Diagnostic output

---

## Pattern 6: Status Tables

### Basic Table

```python
from rich.table import Table

def show_status_table():
    """Display status as table"""
    table = Table(title="Service Status", show_header=True, header_style="bold cyan")
    
    table.add_column("Service", style="cyan", width=20)
    table.add_column("Status", width=15)
    table.add_column("Uptime", justify="right")
    
    table.add_row("Agent Loop", "[green]✓ Running[/green]", "2h 15m")
    table.add_row("API Client", "[green]✓ Connected[/green]", "2h 15m")
    table.add_row("Cache", "[yellow]⚠ Degraded[/yellow]", "45m")
    table.add_row("Database", "[red]✗ Failed[/red]", "0m")
    
    console.print(table)
```

**Output**:
```
                    Service Status                    
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Service            ┃ Status        ┃ Uptime ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ Agent Loop         │ ✓ Running     │  2h 15m│
│ API Client         │ ✓ Connected   │  2h 15m│
│ Cache              │ ⚠ Degraded    │    45m │
│ Database           │ ✗ Failed      │     0m │
└────────────────────┴───────────────┴────────┘
```

**When to use**:
- Service status
- Session list
- Configuration display
- Comparison views

---

## Pattern 7: Interactive Prompts

### Basic Input

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

session = PromptSession(
    history=FileHistory("~/.lyra/history")
)

user_input = session.prompt("❯ ")
```

### With Completion

```python
from prompt_toolkit.completion import WordCompleter

completer = WordCompleter(
    ["/help", "/exit", "/config", "/session"],
    ignore_case=True
)

session = PromptSession(
    history=FileHistory("~/.lyra/history"),
    completer=completer,
    complete_while_typing=True
)

user_input = session.prompt("❯ ")
```

### Multi-line Input

```python
user_input = session.prompt(
    "❯ ",
    multiline=True,
    prompt_continuation="... "
)
```

**When to use**:
- Interactive chat
- Command input
- Configuration editing
- Multi-line messages

---

## Pattern 8: Error Display

### Error Messages

```python
# Simple error
console.print("✗ Error: Connection failed", style="red")

# Error with details
console.print("[red]✗ Error:[/red] Connection failed")
console.print("[dim]  Reason: Timeout after 30s[/dim]")
console.print("[dim]  Suggestion: Check network connection[/dim]")

# Error with traceback (debug mode)
if os.getenv("DEBUG"):
    import traceback
    console.print("\n[dim]Traceback:[/dim]")
    console.print(traceback.format_exc(), style="dim red")
```

### Warning Messages

```python
console.print("⚠ Warning: Low disk space", style="yellow")
console.print("[dim]  Available: 2.5 GB[/dim]")
console.print("[dim]  Recommended: 10 GB[/dim]")
```

### Info Messages

```python
console.print("ℹ Info: Session saved", style="blue")
console.print("[dim]  Location: ~/.lyra/sessions/abc123[/dim]")
```

**When to use**:
- Error handling
- Validation failures
- Warning conditions
- Informational messages

---

## Pattern 9: Dividers and Separators

### Horizontal Divider

```python
# Simple divider
console.print("─" * 80, style="dim")

# With Rich rule
from rich.rule import Rule
console.print(Rule(style="dim"))

# Titled divider
console.print(Rule("Section Title", style="cyan"))
```

### Section Headers

```python
console.print("\n[bold cyan]Configuration[/bold cyan]")
console.print("─" * 40, style="dim")
```

**When to use**:
- Section separation
- Visual organization
- Output grouping

---

## Pattern 10: Streaming Output

### Character-by-character

```python
def stream_text(text: str, delay: float = 0.01):
    """Stream text character by character"""
    for char in text:
        console.print(char, end="", markup=False)
        time.sleep(delay)
    console.print()
```

### Chunk-by-chunk

```python
def stream_chunks(chunks: list):
    """Stream text chunks"""
    for chunk in chunks:
        console.print(chunk, end="", markup=False)
    console.print()
```

**When to use**:
- Agent responses
- Real-time output
- Streaming API responses

---

## Pattern 11: Context Display

### Token Usage

```python
def show_token_usage(tokens: int, max_tokens: int):
    """Display token usage"""
    percent = int((tokens / max_tokens) * 100)
    
    if percent < 50:
        style = "green"
    elif percent < 80:
        style = "yellow"
    else:
        style = "red"
    
    console.print(
        f"[dim]Tokens: {tokens:,} / {max_tokens:,} ({percent}%)[/dim]",
        style=style
    )
```

### Timing Information

```python
def show_timing(duration: float):
    """Display timing information"""
    if duration < 1:
        time_str = f"{duration*1000:.0f}ms"
    elif duration < 60:
        time_str = f"{duration:.1f}s"
    else:
        minutes = int(duration / 60)
        seconds = int(duration % 60)
        time_str = f"{minutes}m {seconds}s"
    
    console.print(f"[dim]Time: {time_str}[/dim]")
```

**When to use**:
- Performance metrics
- Resource usage
- Timing information

---

## Pattern 12: Confirmation Prompts

### Yes/No Confirmation

```python
import typer

def confirm_action(message: str) -> bool:
    """Ask for confirmation"""
    return typer.confirm(message)

# Usage
if confirm_action("Delete session?"):
    delete_session()
```

### Choice Selection

```python
from rich.prompt import Prompt

def select_option(options: list) -> str:
    """Select from options"""
    console.print("\n[bold]Select an option:[/bold]")
    for i, option in enumerate(options, 1):
        console.print(f"  {i}. {option}")
    
    choice = Prompt.ask(
        "Choice",
        choices=[str(i) for i in range(1, len(options) + 1)]
    )
    
    return options[int(choice) - 1]
```

**When to use**:
- Destructive operations
- Configuration changes
- User decisions

---

## Pattern 13: Help Display

### Command Help

```python
def show_command_help():
    """Display command help"""
    console.print("\n[bold cyan]Available Commands:[/bold cyan]\n")
    
    commands = [
        ("/help", "Show this help message"),
        ("/exit", "Exit the application"),
        ("/config", "Show configuration"),
        ("/session", "Manage sessions"),
        ("/skills", "List available skills"),
    ]
    
    for cmd, desc in commands:
        console.print(f"  [cyan]{cmd:15}[/cyan] {desc}")
```

### Tips Display

```python
def show_tips():
    """Display usage tips"""
    console.print("\n[dim]Tips:[/dim]")
    tips = [
        "Type your message to start chatting",
        "Use /help for available commands",
        "Press Ctrl+C to interrupt, Ctrl+D to exit",
        "Use ↑/↓ arrows for command history",
    ]
    
    for tip in tips:
        console.print(f"  • {tip}", style="dim")
```

**When to use**:
- First-time users
- Help commands
- Onboarding
- Feature discovery

---

## Pattern 14: Live Updates

### Live Status

```python
from rich.live import Live
from rich.table import Table

def show_live_status():
    """Live updating status"""
    with Live(refresh_per_second=4) as live:
        for i in range(100):
            table = Table(title="Live Status")
            table.add_column("Metric")
            table.add_column("Value")
            
            table.add_row("Progress", f"{i}%")
            table.add_row("Time", f"{i}s")
            
            live.update(table)
            time.sleep(0.1)
```

**When to use**:
- Real-time monitoring
- Live metrics
- Dynamic updates

---

## Pattern 15: Exit Handling

### Graceful Exit

```python
import signal
import sys

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    console.print("\n\n[yellow]Interrupted by user[/yellow]")
    console.print("[dim]Cleaning up...[/dim]")
    # Cleanup code here
    sys.exit(130)

signal.signal(signal.SIGINT, signal_handler)
```

### Exit Messages

```python
def exit_application():
    """Exit with message"""
    console.print("\n[cyan]Goodbye![/cyan]")
    console.print("[dim]Session saved to ~/.lyra/sessions/[/dim]")
    sys.exit(0)
```

**When to use**:
- Application exit
- Interrupt handling
- Cleanup operations

---

## Unicode Symbol Reference

### Status Symbols
- `⏺` - Running/Active (U+23FA)
- `✓` - Success/Complete (U+2713)
- `✗` - Failed/Error (U+2717)
- `⚠` - Warning (U+26A0)
- `ℹ` - Information (U+2139)
- `⏳` - Pending/Waiting (U+23F3)

### Spinner Symbols
- `⏺` - Record button (U+23FA)
- `✻` - Eight-spoked asterisk (U+273B)
- `✶` - Six-pointed star (U+2736)
- `◐` - Circle half black (U+25D0)
- `◓` - Circle quarter (U+25D3)

### Tree Symbols
- `├──` - Branch (U+251C U+2500 U+2500)
- `│` - Vertical line (U+2502)
- `└──` - Last branch (U+2514 U+2500 U+2500)
- `─` - Horizontal line (U+2500)

### Box Drawing (Rounded)
- `╭` - Top left (U+256D)
- `╮` - Top right (U+256E)
- `╰` - Bottom left (U+2570)
- `╯` - Bottom right (U+256F)
- `─` - Horizontal (U+2500)
- `│` - Vertical (U+2502)

### Box Drawing (Square)
- `┌` - Top left (U+250C)
- `┐` - Top right (U+2510)
- `└` - Bottom left (U+2514)
- `┘` - Bottom right (U+2518)
- `─` - Horizontal (U+2500)
- `│` - Vertical (U+2502)

### Arrows
- `→` - Right arrow (U+2192)
- `←` - Left arrow (U+2190)
- `↑` - Up arrow (U+2191)
- `↓` - Down arrow (U+2193)
- `⇒` - Double right arrow (U+21D2)

---

## Best Practices

### 1. Consistent Styling
- Use same spinner characters throughout
- Consistent color scheme (cyan for info, green for success, red for error, yellow for warning)
- Consistent indentation (2 spaces per level)

### 2. Performance
- Use Live() for frequently updating displays
- Avoid excessive console.print() calls in loops
- Buffer output when possible

### 3. Accessibility
- Provide text-only mode option
- Don't rely solely on color
- Use symbols + text labels
- Support screen readers

### 4. Error Handling
- Always show user-friendly error messages
- Provide suggestions for fixing errors
- Show detailed errors only in debug mode
- Handle Ctrl+C gracefully

### 5. User Experience
- Show progress for long operations
- Provide feedback for all actions
- Use appropriate spinner/status indicators
- Clear success/failure states

---

**Status**: Pattern Library Complete  
**Next**: Use these patterns in Phase 2 implementation
