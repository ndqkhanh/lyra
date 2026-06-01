# Lyra TUI V2 Removal & CLI Conversion Plan

**Goal**: Remove all TUI v2 components (16,300+ lines) and replace with a clean, Claude Code-style CLI interface

**Status**: Planning
**Created**: 2026-05-23
**Estimated Effort**: 3-5 days
**Risk Level**: High (major architectural change)

---

## Executive Summary

Lyra currently uses a complex Textual-based TUI (90 files, 16,210 lines) built on the harness-tui library. This TUI has proven unstable (immediate exit bugs) and overly complex. This plan removes all TUI v2 components and replaces them with a simple, robust CLI interface matching Claude Code's patterns.

**Key Changes:**
- Remove 91 files (~16,300 lines of TUI code)
- Remove harness-tui dependency
- Implement Rich + Typer based CLI
- Maintain all core functionality (agent loop, commands, status display)

---

## Phase 1: Design Replacement CLI Architecture

**Goal**: Design the new CLI interface before removing TUI v2

### 1.1 Define CLI Patterns (2 hours)

**Patterns to implement** (based on Claude Code):

1. **Welcome Screen** - Box-drawn welcome with model/user info
2. **Status Messages** - Spinners (⏺ ✻ ✶) with hierarchical output
3. **Background Tasks** - Task list with status indicators
4. **Progress Indicators** - Live progress bars for long operations
5. **Interactive Prompts** - Clean input with history
6. **Command Output** - Formatted responses with syntax highlighting

**Technology Stack:**
```python
# Core CLI framework
typer>=0.12.0          # Command routing, subcommands
rich>=13.7.0           # Formatting, panels, progress, live display

# Optional enhancements
prompt_toolkit>=3.0.0  # Advanced input with history/completion
yaspin>=3.0.0          # Lightweight spinners (if Rich spinners insufficient)
```

### 1.2 Design Module Structure (1 hour)

**New CLI module structure:**
```
packages/lyra-cli/src/lyra_cli/
├── cli/
│   ├── __init__.py              # CLI entry point
│   ├── app.py                   # Main Typer app
│   ├── output.py                # Rich output formatting
│   ├── prompts.py               # Interactive prompts
│   ├── status.py                # Status display (spinners, progress)
│   ├── welcome.py               # Welcome screen
│   └── commands/                # Command handlers
│       ├── __init__.py
│       ├── chat.py              # Main chat loop
│       ├── config.py            # Configuration commands
│       ├── session.py           # Session management
│       └── skills.py            # Skills/MCP commands
├── agent/                       # Agent loop (existing, keep)
├── config/                      # Configuration (existing, keep)
└── __main__.py                  # Entry point (simplify)
```

### 1.3 Create Interface Specifications (2 hours)

**Deliverables:**
- [ ] CLI_INTERFACE_SPEC.md - Detailed interface specification
- [ ] CLI_PATTERNS.md - Pattern library with examples
- [ ] CLI_MIGRATION_MAP.md - TUI v2 → CLI feature mapping

---

## Phase 2: Implement Core CLI Framework

**Goal**: Build the new CLI foundation

### 2.1 Setup CLI Infrastructure (3 hours)

**Tasks:**
- [ ] Create `cli/` module structure
- [ ] Setup Typer app with subcommands
- [ ] Implement Rich console singleton
- [ ] Create output formatting utilities
- [ ] Setup logging integration

**Files to create:**
```python
# cli/__init__.py
from .app import app as cli_app

# cli/app.py
import typer
from rich.console import Console

app = typer.Typer(name="lyra", help="Lyra AI Research Assistant")
console = Console()

# cli/output.py
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner

class OutputFormatter:
    """Rich-based output formatting"""
    
    def welcome_screen(self, model: str, user: str) -> None:
        """Display welcome screen with box drawing"""
        
    def status_message(self, message: str, spinner: str = "⏺") -> None:
        """Display status with spinner"""
        
    def background_tasks(self, tasks: list) -> None:
        """Display background task list"""
        
    def progress_bar(self, total: int, description: str) -> Live:
        """Create live progress bar"""
```

### 2.2 Implement Welcome & Status Display (2 hours)

**Tasks:**
- [ ] Welcome screen with box drawing (╭─╮│╰─╯)
- [ ] Status messages with spinners (⏺ ✻ ✶)
- [ ] Hierarchical status output
- [ ] Background task display

**Example output:**
```
╭─── Lyra v0.1.0 ───────────────────────────────────────────────────────╮
│                                                                        │
│                 Welcome back Khanh!                                    │
│                                                                        │
│                       ▐▛███▜▌                                          │
│                      ▝▜█████▛▘                                         │
│                        ▘▘ ▝▝                                           │
│ Opus 4.7 · Claude Max · khanhndq2002@gmail.com                        │
│   ~/research/harness-engineering/projects/lyra                         │
╰────────────────────────────────────────────────────────────────────────╯

⏺ Launching parallel research...
  ├ Research GitHub repos · 10 tool uses · 29.7k tokens
  ├ Search for compression repos · 6 tool uses · 29.9k tokens
  └ Research academic papers · 5 tool uses · 29.8k tokens

✻ Worked for 20s · 3 agents running
```

### 2.3 Implement Interactive Prompt (3 hours)

**Tasks:**
- [ ] Setup prompt_toolkit integration
- [ ] Command history
- [ ] Auto-completion for slash commands
- [ ] Multi-line input support
- [ ] Ctrl+C handling

**Example:**
```python
# cli/prompts.py
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

class LyraPrompt:
    def __init__(self):
        self.session = PromptSession(
            history=FileHistory("~/.lyra/history"),
            auto_suggest=AutoSuggestFromHistory(),
        )
    
    def get_input(self) -> str:
        """Get user input with history and completion"""
        return self.session.prompt("❯ ")
```

---

## Phase 3: Migrate Agent Loop Integration

**Goal**: Connect new CLI to existing agent loop

### 3.1 Refactor Agent Loop Interface (4 hours)

**Current state:**
- Agent loop in `agent/loop.py` expects TUI transport
- TUI transport handles events, streaming, status updates

**New approach:**
- Agent loop outputs to callback interface
- CLI implements callback interface with Rich display
- No TUI transport dependency

**Tasks:**
- [ ] Define `AgentOutputCallback` protocol
- [ ] Refactor agent loop to use callbacks
- [ ] Implement CLI callback handler
- [ ] Test agent loop with CLI output

**Example:**
```python
# agent/callbacks.py
from typing import Protocol

class AgentOutputCallback(Protocol):
    """Protocol for agent output handling"""
    
    def on_turn_start(self, turn_id: str) -> None:
        """Called when agent turn starts"""
        
    def on_tool_use(self, tool: str, args: dict) -> None:
        """Called when agent uses a tool"""
        
    def on_stream_chunk(self, chunk: str) -> None:
        """Called for streaming text chunks"""
        
    def on_turn_end(self, turn_id: str, result: dict) -> None:
        """Called when agent turn ends"""

# cli/agent_handler.py
from rich.live import Live
from rich.spinner import Spinner

class CLIAgentHandler:
    """CLI implementation of AgentOutputCallback"""
    
    def __init__(self, console: Console):
        self.console = console
        self.live = None
    
    def on_turn_start(self, turn_id: str) -> None:
        self.console.print("⏺ Processing...", style="cyan")
        
    def on_tool_use(self, tool: str, args: dict) -> None:
        self.console.print(f"  ⎿ {tool}", style="dim")
```

### 3.2 Implement Command Handlers (3 hours)

**Tasks:**
- [ ] Migrate slash commands from TUI v2
- [ ] Implement as Typer commands
- [ ] Connect to agent loop
- [ ] Add command help text

**Commands to migrate:**
```python
# cli/commands/chat.py
@app.command()
def chat(
    message: str = typer.Argument(None, help="Message to send"),
    model: str = typer.Option("opus", help="Model to use"),
):
    """Start interactive chat or send single message"""

# cli/commands/session.py
@app.command()
def sessions():
    """List and manage sessions"""

# cli/commands/skills.py
@app.command()
def skills():
    """List available skills"""
```

### 3.3 Implement Status Display (2 hours)

**Tasks:**
- [ ] Live status updates during agent execution
- [ ] Background task tracking
- [ ] Token usage display
- [ ] Error handling and display

---

## Phase 4: Remove TUI V2 Components

**Goal**: Delete all TUI v2 code and dependencies

### 4.1 Remove TUI V2 Files (1 hour)

**Files to delete:**
```bash
# Remove entire tui_v2 directory (90 files, 16,210 lines)
rm -rf packages/lyra-cli/src/lyra_cli/tui_v2/

# Remove TUI command
rm packages/lyra-cli/src/lyra_cli/commands/tui.py

# Remove TUI tests
rm -rf packages/lyra-cli/tests/tui_v2/
```

### 4.2 Update Entry Point (30 minutes)

**File**: `packages/lyra-cli/src/lyra_cli/__main__.py`

**Changes:**
```python
# BEFORE (lines 115-130)
if os.getenv("LYRA_TUI") == "1":
    from lyra_cli.tui_v2 import launch_tui_v2
    launch_tui_v2()
    return

# AFTER
from lyra_cli.cli import cli_app
cli_app()
```

### 4.3 Remove Dependencies (15 minutes)

**File**: `packages/lyra-cli/pyproject.toml`

**Remove:**
```toml
[tool.poetry.dependencies]
# Remove these
textual = "^0.85.0"
harness-tui = { path = "../../../packages/harness-tui", develop = true }
```

**Add:**
```toml
[tool.poetry.dependencies]
typer = "^0.12.0"
rich = "^13.7.0"
prompt-toolkit = "^3.0.0"
```

### 4.4 Update Configuration (30 minutes)

**Tasks:**
- [ ] Remove LYRA_TUI environment variable handling
- [ ] Remove TUI-specific config options
- [ ] Update CLI config options
- [ ] Update documentation

---

## Phase 5: Testing & Validation

**Goal**: Ensure new CLI works correctly

### 5.1 Manual Testing (2 hours)

**Test scenarios:**
- [ ] Welcome screen displays correctly
- [ ] Interactive prompt accepts input
- [ ] Agent loop executes and displays output
- [ ] Slash commands work
- [ ] Background tasks display correctly
- [ ] Error handling works
- [ ] Ctrl+C interrupts gracefully
- [ ] Session management works
- [ ] Token usage displays correctly

### 5.2 Integration Testing (2 hours)

**Tasks:**
- [ ] Test with real agent loop
- [ ] Test with multiple concurrent agents
- [ ] Test with long-running operations
- [ ] Test with streaming output
- [ ] Test with various terminal sizes
- [ ] Test on macOS, Linux, Windows

### 5.3 Performance Testing (1 hour)

**Metrics:**
- [ ] Startup time < 1 second
- [ ] Memory usage < 100MB baseline
- [ ] No memory leaks during long sessions
- [ ] Responsive during agent execution

---

## Phase 6: Documentation & Cleanup

**Goal**: Update documentation and clean up

### 6.1 Update Documentation (2 hours)

**Files to update:**
- [ ] README.md - Remove TUI references, add CLI usage
- [ ] CONTRIBUTING.md - Update development setup
- [ ] docs/CLI.md - New CLI documentation
- [ ] docs/MIGRATION.md - TUI v2 → CLI migration guide

### 6.2 Code Cleanup (1 hour)

**Tasks:**
- [ ] Remove unused imports
- [ ] Remove TUI-related comments
- [ ] Update type hints
- [ ] Run linters and formatters
- [ ] Fix any remaining references

### 6.3 Final Validation (1 hour)

**Checklist:**
- [ ] All tests pass
- [ ] No TUI v2 references remain
- [ ] No harness-tui imports
- [ ] No textual imports
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

---

## Rollout Strategy

### Option A: Big Bang (Recommended)

**Approach**: Complete all phases, then merge in one PR

**Pros:**
- Clean cutover
- No hybrid state
- Easier to review

**Cons:**
- Large PR
- Higher risk
- Longer development time

**Timeline**: 3-5 days

### Option B: Incremental

**Approach**: Build CLI alongside TUI v2, then switch

**Pros:**
- Lower risk
- Can test CLI before removing TUI
- Smaller PRs

**Cons:**
- Maintains both systems temporarily
- More complex
- Longer overall timeline

**Timeline**: 5-7 days

---

## Risk Mitigation

### Risk 1: Feature Loss

**Risk**: Some TUI v2 features might not have CLI equivalents

**Mitigation:**
- Create feature mapping document (Phase 1.3)
- Identify critical features early
- Design CLI equivalents before removal
- User acceptance testing

### Risk 2: Agent Loop Integration Issues

**Risk**: Agent loop might be tightly coupled to TUI transport

**Mitigation:**
- Refactor agent loop to use callbacks (Phase 3.1)
- Test agent loop independently
- Create integration tests
- Gradual migration of agent loop

### Risk 3: User Experience Degradation

**Risk**: CLI might be less usable than TUI

**Mitigation:**
- Follow Claude Code patterns (proven UX)
- Use Rich for formatting (professional output)
- Add prompt_toolkit for advanced input
- User testing before final release

### Risk 4: Regression Bugs

**Risk**: Removing 16,300 lines might introduce bugs

**Mitigation:**
- Comprehensive testing (Phase 5)
- Manual testing of all features
- Integration testing with real agent loop
- Beta testing period

---

## Success Criteria

### Must Have
- [ ] CLI launches without errors
- [ ] Interactive prompt works
- [ ] Agent loop executes correctly
- [ ] All slash commands work
- [ ] Status display shows progress
- [ ] Error handling works
- [ ] No TUI v2 code remains
- [ ] No harness-tui dependency

### Should Have
- [ ] Welcome screen matches Claude Code style
- [ ] Background task display
- [ ] Token usage display
- [ ] Command history
- [ ] Auto-completion
- [ ] Syntax highlighting

### Nice to Have
- [ ] Multi-line input with editor
- [ ] Session management UI
- [ ] Configuration wizard
- [ ] Keyboard shortcuts

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Design | 5 hours | None |
| Phase 2: Core CLI | 8 hours | Phase 1 |
| Phase 3: Agent Integration | 9 hours | Phase 2 |
| Phase 4: Remove TUI v2 | 2 hours | Phase 3 |
| Phase 5: Testing | 5 hours | Phase 4 |
| Phase 6: Documentation | 4 hours | Phase 5 |
| **Total** | **33 hours** | **~4-5 days** |

---

## Next Steps

1. **Review this plan** - Get stakeholder approval
2. **Create feature mapping** - Document TUI v2 → CLI feature equivalents
3. **Setup development branch** - `feature/cli-migration`
4. **Start Phase 1** - Design CLI architecture
5. **Daily standups** - Track progress and blockers

---

## Appendix A: TUI V2 Component Inventory

### Files to Remove (91 total)

**Main TUI v2 directory** (90 files):
```
packages/lyra-cli/src/lyra_cli/tui_v2/
├── __init__.py
├── app.py                           # 500+ lines
├── transport.py                     # 300+ lines
├── brand.py
├── events.py
├── expandable.py
├── hierarchical.py
├── lyra_composer.py
├── progress.py
├── safe_render.py
├── spinner_states.py
├── status.py
├── task_progress.py
├── theme_manager.py
├── tips.py
├── commands/                        # 9 files
│   ├── __init__.py
│   ├── budget.py
│   ├── claude_compat.py
│   ├── escape.py
│   ├── meta.py
│   ├── mode.py
│   ├── sessions.py
│   └── skills_mcp.py
├── modals/                          # 14 files
│   ├── __init__.py
│   ├── background_switcher.py
│   ├── base.py
│   ├── command_palette.py
│   ├── mcp.py
│   ├── model_picker.py
│   ├── model.py
│   ├── notification_drawer.py
│   ├── session_manager.py
│   ├── skill_picker.py
│   ├── skill.py
│   ├── status_dashboard.py
│   ├── task_panel.py
│   └── theme_switcher.py
├── sidebar/                         # 6 files
│   ├── __init__.py
│   ├── agent_detail.py
│   ├── agents_tab.py
│   ├── data.py
│   ├── process_tab.py
│   └── tabs.py
└── widgets/                         # 49 files
    ├── __init__.py
    ├── accessibility_bridge.py
    ├── agent_dashboard.py
    ├── agent_panel.py
    ├── async_bridge.py
    ├── background_panel.py
    ├── chat_tools_panel.py
    ├── ci_suggestions.py
    ├── claude_banner.py
    ├── compaction_banner.py
    ├── connect_status.py
    ├── context_engineering.py
    ├── context_viz.py
    ├── cron_dashboard.py
    ├── deepsearch_panel.py
    ├── ecc_panel.py
    ├── effort_app_panel.py
    ├── enhanced_features.py
    ├── evolution_status.py
    ├── expandable_tool.py
    ├── file_completion.py
    ├── ghost_text.py
    ├── memory_dashboard.py
    ├── message_bubble.py
    ├── metrics_tracker.py
    ├── model_router_panel.py
    ├── monitor_panel.py
    ├── onboarding_panel.py
    ├── performance_dashboard.py
    ├── phase_progress.py
    ├── progress_spinner.py
    ├── progress_viz.py
    ├── research_flow.py
    ├── resource_monitor.py
    ├── rich_repl.py
    ├── skills_lifecycle_panel.py
    ├── slash_dropdown.py
    ├── spec_drawer.py
    ├── spec_drawer.tcss
    ├── status_bar_enhanced.py
    ├── stream_handler.py
    ├── task_checklist.py
    ├── thinking_indicator.py
    ├── todo_panel.py
    ├── trace_panel.py
    ├── ultrareview_panel.py
    ├── welcome_card.py
    └── widget_registrar.py
```

**TUI command** (1 file):
```
packages/lyra-cli/src/lyra_cli/commands/tui.py
```

**Total**: 91 files, ~16,300 lines of code

---

## Appendix B: CLI Pattern Examples

### Welcome Screen
```python
from rich.panel import Panel
from rich.text import Text

def show_welcome(console: Console, user: str, model: str, cwd: str):
    logo = """
          ▐▛███▜▌
         ▝▜█████▛▘
           ▘▘ ▝▝
    """
    
    content = Text()
    content.append(f"\n\nWelcome back {user}!\n\n", style="bold cyan")
    content.append(logo, style="magenta")
    content.append(f"\n{model} · Claude Max · {user}@gmail.com\n", style="dim")
    content.append(f"  {cwd}\n", style="dim blue")
    
    panel = Panel(
        content,
        title="Lyra v0.1.0",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)
```

### Status Messages
```python
from rich.spinner import Spinner
from rich.live import Live

def show_status(console: Console, message: str):
    with Live(Spinner("dots", text=message), console=console):
        # Do work
        pass
    console.print(f"✓ {message}", style="green")
```

### Background Tasks
```python
from rich.table import Table

def show_background_tasks(console: Console, tasks: list):
    table = Table(title="Background Tasks", show_header=False)
    table.add_column("Status", style="cyan")
    table.add_column("Task")
    
    for task in tasks:
        status = "⏺" if task.running else "✓"
        table.add_row(status, task.description)
    
    console.print(table)
```

---

## Appendix C: Feature Mapping

| TUI V2 Feature | CLI Equivalent | Priority | Notes |
|----------------|----------------|----------|-------|
| Welcome screen | Rich Panel | Must | Box-drawn welcome |
| Chat log | Scrolling output | Must | Use Rich console |
| Input composer | prompt_toolkit | Must | Multi-line, history |
| Status bar | Status messages | Must | Spinners, progress |
| Command palette | Slash commands | Must | Typer commands |
| Model picker | --model flag | Must | CLI option |
| Session manager | /sessions command | Should | List/switch sessions |
| Theme switcher | --theme flag | Nice | Rich themes |
| Sidebar | Not needed | Skip | CLI doesn't need sidebar |
| Modals | Interactive prompts | Should | Use prompt_toolkit |
| Widgets | Rich components | Must | Tables, panels, etc. |
| Background tasks | Task list | Should | Show running tasks |
| Token usage | Status display | Should | Show in status |
| Context viz | Not needed | Skip | CLI doesn't need viz |
| Agent dashboard | /agents command | Nice | List agents |
| Memory dashboard | /memory command | Nice | Show memory |
| Skill picker | /skills command | Should | List skills |

---

## Appendix D: Dependencies

### Remove
```toml
textual = "^0.85.0"
harness-tui = { path = "../../../packages/harness-tui", develop = true }
```

### Add
```toml
typer = "^0.12.0"           # CLI framework
rich = "^13.7.0"            # Output formatting
prompt-toolkit = "^3.0.0"  # Interactive prompts
```

### Keep (existing)
```toml
anthropic = "^0.40.0"       # Claude API
pydantic = "^2.0.0"         # Data validation
httpx = "^0.27.0"           # HTTP client
```

---

**Plan Status**: Ready for review and approval
**Next Action**: Review with stakeholders, then start Phase 1
