# Lyra TUI V2 → CLI Migration Map

**Version**: 1.0.0  
**Date**: 2026-05-23  
**Purpose**: Feature mapping from TUI v2 to CLI implementation

---

## Overview

This document maps all TUI v2 features to their CLI equivalents, indicating priority and implementation approach.

---

## Priority Levels

- **MUST** - Critical feature, required for MVP
- **SHOULD** - Important feature, include if time permits
- **NICE** - Enhancement, can be added later
- **SKIP** - Not needed in CLI, TUI-specific

---

## Feature Mapping

### Core Features

| TUI V2 Feature | CLI Equivalent | Priority | Implementation | Notes |
|----------------|----------------|----------|----------------|-------|
| Welcome screen | Rich Panel welcome | MUST | Pattern 1 | Box-drawn welcome with logo |
| Chat log | Scrolling console output | MUST | Rich console | Natural scrolling in terminal |
| Input composer | prompt_toolkit input | MUST | Pattern 7 | Multi-line, history, completion |
| Message streaming | Character streaming | MUST | Pattern 10 | Stream agent responses |
| Status bar | Status messages | MUST | Pattern 2 | Spinners and status text |
| Command palette | Slash commands | MUST | Typer commands | `/help`, `/config`, etc. |
| Model selection | `--model` flag | MUST | Typer option | `lyra --model opus` |
| Session management | `/session` command | SHOULD | Pattern 5 | List/switch/delete sessions |
| Token usage display | Status message | SHOULD | Pattern 11 | Show after each turn |
| Background tasks | Task tree | SHOULD | Pattern 3 | Show running agents |
| Error display | Error messages | MUST | Pattern 8 | Formatted error output |
| Help system | `/help` command | MUST | Pattern 13 | Command help and tips |

### UI Components

| TUI V2 Component | CLI Equivalent | Priority | Implementation | Notes |
|------------------|----------------|----------|----------------|-------|
| Shell widget | Console output | MUST | Rich console | Main output area |
| Composer widget | Prompt input | MUST | prompt_toolkit | Interactive input |
| Sidebar | Not needed | SKIP | N/A | CLI doesn't need sidebar |
| Status bar | Status messages | MUST | Pattern 2 | Inline status |
| Context bar | Token display | SHOULD | Pattern 11 | Show token usage |
| Chat log | Console history | MUST | Rich console | Scrollback buffer |
| Tool output | Formatted output | MUST | Rich panels | Tool results |
| Thinking indicator | Spinner | MUST | Pattern 2 | `✶ Thinking...` |
| Progress bars | Rich progress | SHOULD | Pattern 4 | For long operations |
| Welcome card | Welcome panel | MUST | Pattern 1 | Startup screen |

### Modals

| TUI V2 Modal | CLI Equivalent | Priority | Implementation | Notes |
|--------------|----------------|----------|----------------|-------|
| Command palette | Slash commands | MUST | Typer commands | `/command` syntax |
| Model picker | `--model` flag | MUST | Typer option | Command-line flag |
| Session manager | `/session` command | SHOULD | Pattern 5 | List/switch sessions |
| Skill picker | `/skills` command | SHOULD | Pattern 6 | List/enable skills |
| Theme switcher | `--theme` flag | NICE | Typer option | Rich themes |
| Settings modal | `/config` command | SHOULD | Pattern 12 | Edit config |
| Status dashboard | `/debug status` | NICE | Pattern 6 | System status table |
| Task panel | `/tasks` command | NICE | Pattern 3 | Show active tasks |
| Notification drawer | Not needed | SKIP | N/A | Use inline messages |
| Background switcher | Not needed | SKIP | N/A | Not applicable to CLI |
| MCP modal | `/mcp` command | NICE | Pattern 6 | MCP server management |

### Sidebar Components

| TUI V2 Sidebar | CLI Equivalent | Priority | Implementation | Notes |
|----------------|----------------|----------|----------------|-------|
| Agents tab | `/agents` command | NICE | Pattern 3 | List active agents |
| Process tab | `/debug status` | NICE | Pattern 6 | Process status |
| Agent detail view | `/agent <id>` | NICE | Pattern 5 | Agent details |
| Sidebar tabs | Not needed | SKIP | N/A | CLI doesn't need tabs |

### Widgets

| TUI V2 Widget | CLI Equivalent | Priority | Implementation | Notes |
|---------------|----------------|----------|----------------|-------|
| Message bubble | Formatted text | MUST | Rich markup | Styled messages |
| Expandable tool | Collapsible output | NICE | Rich tree | Expandable sections |
| Progress spinner | Spinner | MUST | Pattern 2 | `⏺ ✻ ✶` |
| Status bar enhanced | Status messages | MUST | Pattern 2 | Inline status |
| Context viz | Token display | SHOULD | Pattern 11 | Token usage |
| Agent dashboard | `/agents` command | NICE | Pattern 6 | Agent list table |
| Memory dashboard | `/memory` command | NICE | Pattern 6 | Memory status |
| Performance dashboard | `/debug perf` | NICE | Pattern 6 | Performance metrics |
| Task checklist | `/tasks` command | NICE | Pattern 3 | Task list |
| Thinking indicator | Spinner | MUST | Pattern 2 | `✶ Thinking...` |
| Welcome card | Welcome panel | MUST | Pattern 1 | Startup screen |
| Ghost text | Not needed | SKIP | N/A | Not applicable |
| Slash dropdown | Auto-completion | SHOULD | prompt_toolkit | Command completion |
| File completion | Auto-completion | NICE | prompt_toolkit | Path completion |

### Commands

| TUI V2 Command | CLI Equivalent | Priority | Implementation | Notes |
|----------------|----------------|----------|----------------|-------|
| `/help` | `/help` | MUST | Typer command | Show help |
| `/exit` | `/exit` or Ctrl+D | MUST | Built-in | Exit application |
| `/clear` | `/clear` | SHOULD | Clear screen | Clear terminal |
| `/model` | `--model` flag | MUST | Typer option | Model selection |
| `/config` | `/config` | SHOULD | Typer command | Config management |
| `/session` | `/session` | SHOULD | Typer command | Session management |
| `/sessions` | `/session list` | SHOULD | Typer subcommand | List sessions |
| `/skills` | `/skills` | SHOULD | Typer command | Skills management |
| `/debug` | `/debug` | NICE | Typer command | Debug commands |
| `/status` | `/debug status` | NICE | Typer subcommand | System status |
| `/history` | Built-in | SHOULD | prompt_toolkit | Command history |
| `/budget` | `/debug tokens` | NICE | Typer subcommand | Token budget |
| `/mode` | Not needed | SKIP | N/A | Not applicable |
| `/escape` | Ctrl+C | MUST | Signal handler | Interrupt |

### Events

| TUI V2 Event | CLI Equivalent | Priority | Implementation | Notes |
|--------------|----------------|----------|----------------|-------|
| TurnStarted | Callback | MUST | AgentOutputCallback | `on_turn_start()` |
| TurnFinished | Callback | MUST | AgentOutputCallback | `on_turn_end()` |
| ToolUse | Callback | MUST | AgentOutputCallback | `on_tool_use()` |
| StreamChunk | Callback | MUST | AgentOutputCallback | `on_stream_chunk()` |
| Error | Callback | MUST | AgentOutputCallback | `on_error()` |
| KeyPress | Not needed | SKIP | N/A | Handled by prompt_toolkit |
| MouseClick | Not needed | SKIP | N/A | Not applicable |
| Resize | Auto-handled | N/A | Rich | Rich handles resize |

### Transport Layer

| TUI V2 Transport | CLI Equivalent | Priority | Implementation | Notes |
|------------------|----------------|----------|----------------|-------|
| LyraTransport | CLIAgentHandler | MUST | Callback pattern | Implements AgentOutputCallback |
| Event bus | Direct callbacks | MUST | Function calls | No event bus needed |
| Message queue | Not needed | SKIP | N/A | Direct communication |
| State management | Simple state | SHOULD | Dict/dataclass | Minimal state tracking |

### Theme System

| TUI V2 Theme | CLI Equivalent | Priority | Implementation | Notes |
|--------------|----------------|----------|----------------|-------|
| Catppuccin Mocha | Rich theme | NICE | Rich Theme | Color scheme |
| Dracula | Rich theme | NICE | Rich Theme | Color scheme |
| Tokyo Night | Rich theme | NICE | Rich Theme | Color scheme |
| GitHub Light | Rich theme | NICE | Rich Theme | Color scheme |
| Custom themes | Rich theme | NICE | Rich Theme | User themes |
| Theme switcher | `--theme` flag | NICE | Typer option | Theme selection |
| Lyra branding | Logo + colors | MUST | Pattern 1 | Lyra logo and cyan |

### Configuration

| TUI V2 Config | CLI Equivalent | Priority | Implementation | Notes |
|---------------|----------------|----------|----------------|-------|
| ProjectConfig | Config file | MUST | TOML file | `~/.lyra/config.toml` |
| Theme config | Theme setting | NICE | Config option | `theme = "default"` |
| Model config | Model setting | MUST | Config option | `model = "opus"` |
| Keybindings | Not needed | SKIP | N/A | Terminal handles keys |
| Layout config | Not needed | SKIP | N/A | Not applicable |

---

## Implementation Priority

### Phase 2: Core CLI (MUST features)

**Goal**: Basic functional CLI

1. **Welcome screen** - Pattern 1
   - Box-drawn welcome with logo
   - User info, model, cwd
   - Tips display

2. **Interactive prompt** - Pattern 7
   - prompt_toolkit input
   - Command history
   - Slash command completion
   - Multi-line support

3. **Status messages** - Pattern 2
   - Spinners (⏺ ✻ ✶)
   - Success/error/warning
   - Status updates

4. **Message streaming** - Pattern 10
   - Character-by-character streaming
   - Agent response display

5. **Error display** - Pattern 8
   - Formatted error messages
   - Debug mode traceback

6. **Help system** - Pattern 13
   - `/help` command
   - Command list
   - Usage tips

7. **Basic commands**
   - `/help` - Show help
   - `/exit` - Exit application
   - `/clear` - Clear screen

### Phase 3: Agent Integration (MUST features)

**Goal**: Connect CLI to agent loop

1. **Callback protocol** - `agent/callbacks.py`
   - `AgentOutputCallback` protocol
   - Event handlers

2. **CLI agent handler** - `cli/agent_handler.py`
   - Implement callback protocol
   - Format agent output
   - Handle tool use display

3. **Agent loop refactor** - `agent/loop.py`
   - Use callback pattern
   - Remove TUI transport dependency

4. **Tool output display**
   - Format tool results
   - Show tool usage

5. **Token usage display** - Pattern 11
   - Show after each turn
   - Token budget tracking

### Phase 4: Enhanced Features (SHOULD features)

**Goal**: Improve usability

1. **Session management** - `/session` command
   - List sessions
   - Switch sessions
   - Delete sessions

2. **Configuration** - `/config` command
   - Show config
   - Edit config
   - Set values

3. **Skills management** - `/skills` command
   - List skills
   - Show skill details
   - Enable/disable skills

4. **Background tasks** - Pattern 3
   - Show running agents
   - Task tree display

5. **Progress indicators** - Pattern 4
   - Progress bars for long operations

### Phase 5: Polish (NICE features)

**Goal**: Enhanced experience

1. **Debug commands** - `/debug`
   - System status
   - Agent logs
   - Performance metrics

2. **Theme support**
   - Rich themes
   - Custom colors

3. **Advanced features**
   - Agent dashboard
   - Memory dashboard
   - Task management

---

## Removed Features (SKIP)

These TUI v2 features are not needed in CLI:

### UI-Specific
- Sidebar and tabs
- Mouse interaction
- Window resizing
- Layout management
- Modal dialogs (replaced with commands)
- Notification drawer
- Background switcher

### Widgets
- Ghost text
- Accessibility bridge (terminal handles this)
- Async bridge (not needed)
- Widget registrar

### Events
- Mouse events
- Keyboard events (handled by prompt_toolkit)
- Resize events (handled by Rich)

### Configuration
- Keybindings (terminal handles)
- Layout config
- Widget positions

---

## Migration Strategy

### Step 1: Core CLI (Phase 2)
Implement MUST features:
- Welcome screen
- Interactive prompt
- Status messages
- Message streaming
- Error display
- Help system

**Deliverable**: Functional CLI that can display output

### Step 2: Agent Integration (Phase 3)
Connect to agent loop:
- Callback protocol
- CLI agent handler
- Agent loop refactor
- Tool output display
- Token usage

**Deliverable**: CLI that can run agent loop

### Step 3: Remove TUI V2 (Phase 4)
Delete TUI code:
- Remove `tui_v2/` directory
- Remove `commands/tui.py`
- Update `__main__.py`
- Remove dependencies

**Deliverable**: Clean codebase without TUI

### Step 4: Enhanced Features (Phase 4)
Add SHOULD features:
- Session management
- Configuration
- Skills management
- Background tasks
- Progress indicators

**Deliverable**: Feature-complete CLI

### Step 5: Polish (Phase 5)
Add NICE features:
- Debug commands
- Theme support
- Advanced features

**Deliverable**: Polished CLI

---

## Testing Checklist

### Core Functionality
- [ ] Welcome screen displays correctly
- [ ] Interactive prompt accepts input
- [ ] Command history works (↑/↓ arrows)
- [ ] Slash command completion works
- [ ] Multi-line input works
- [ ] Status messages display correctly
- [ ] Spinners animate correctly
- [ ] Message streaming works
- [ ] Error messages display correctly
- [ ] Help command works

### Agent Integration
- [ ] Agent loop executes
- [ ] Tool use displays correctly
- [ ] Token usage displays
- [ ] Streaming responses work
- [ ] Multiple agents display correctly
- [ ] Background tasks display
- [ ] Error handling works

### Commands
- [ ] `/help` shows help
- [ ] `/exit` exits cleanly
- [ ] `/clear` clears screen
- [ ] `/config` shows config
- [ ] `/session` manages sessions
- [ ] `/skills` lists skills
- [ ] `/debug` shows debug info

### User Experience
- [ ] Ctrl+C interrupts gracefully
- [ ] Ctrl+D exits cleanly
- [ ] Terminal resize handled
- [ ] Colors display correctly
- [ ] Unicode symbols display correctly
- [ ] Long output scrolls correctly
- [ ] Performance is acceptable

### Edge Cases
- [ ] Empty input handled
- [ ] Invalid commands handled
- [ ] Network errors handled
- [ ] Long-running operations interruptible
- [ ] Memory usage acceptable
- [ ] No memory leaks

---

## Success Metrics

### Functionality
- ✓ All MUST features implemented
- ✓ All SHOULD features implemented (if time permits)
- ✓ Agent loop works correctly
- ✓ No TUI v2 code remains

### Performance
- ✓ Startup time < 1 second
- ✓ Memory usage < 100MB baseline
- ✓ No memory leaks
- ✓ Responsive during agent execution

### User Experience
- ✓ Clean, professional output
- ✓ Intuitive commands
- ✓ Good error messages
- ✓ Helpful documentation

### Code Quality
- ✓ Clean architecture
- ✓ Well-documented
- ✓ Tested
- ✓ Maintainable

---

## Appendix: Feature Comparison

### TUI V2 (Before)
- 91 files, 16,300 lines
- Complex Textual framework
- Heavy dependencies (textual, harness-tui)
- Full TUI with widgets, modals, sidebar
- Mouse interaction
- Custom event system
- Complex state management

### CLI (After)
- ~15 files, ~2,000 lines
- Simple Rich + Typer
- Lightweight dependencies
- Clean terminal output
- Keyboard-only
- Direct callbacks
- Minimal state

### Benefits
- ✓ 87% less code
- ✓ Simpler architecture
- ✓ Easier to maintain
- ✓ Faster startup
- ✓ Lower memory usage
- ✓ More stable
- ✓ Better performance

---

**Status**: Migration Map Complete  
**Next**: Begin Phase 2 implementation
