# 🎨 Best AI Agent UI Patterns - Research Report

**Date**: 2026-05-23  
**Research Scope**: Top AI Agent Repos (Claude Code, Aider, Continue, Cline, OpenClaw)  
**Status**: ✅ Research Complete

---

## Executive Summary

I researched the **most starred and highest-rated AI agent repositories** to extract the best terminal UI patterns. Here's what the top tools are doing:

### Top Repos Analyzed

1. **OpenClaw** - Breakout star of 2026, fastest-growing open-source project
2. **Claude Code** - 87.6% on SWE-bench, terminal-native leader
3. **Aider** - 44K stars, 6.8M installs, Git-native terminal UI
4. **Continue** - Modular CLI with TUI mode, pink/magenta branding
5. **Cline** - VS Code + CLI, keyboard-driven interactions
6. **Cursor** - IDE-first (not terminal, but studied for patterns)

---

## Key UI Patterns Discovered

### 1. **Color Schemes & Branding**

**Continue**: 
- Primary brand color: `#BE1B55` (pink/magenta)
- Binary feedback: Green = good, Red = issues

**Aider**:
- Terminal-native with minimal colors
- Focus on Git integration visuals

**Claude Code**:
- Minimal, professional
- Status indicators over decoration

**Best Practice**: Use a distinctive brand color (cyan/magenta) with semantic colors (green=success, red=error, yellow=warning, blue=info)

### 2. **Progress Indicators**

**Libraries Used**:
- **Rich** (Python) - 3-6x faster, beautiful progress bars
- **ora** (Node.js) - Elegant spinners
- **indicatif** (Rust) - Progress reporting
- **yaspin** (Python) - Lightweight spinners

**Patterns**:
- Spinners for indeterminate tasks
- Progress bars for known durations
- Real-time token counting
- Step-by-step indicators (1/4, 2/4, etc.)

### 3. **Status Display**

**Claude Code Pattern**:
```
✓ Task completed
⎿ Tool: Read file.py
✻ 2.3s · 3 tools · 1,234 tokens
```

**Aider Pattern**:
```
> Editing file.py
  + Added function
  - Removed old code
✓ Committed: "Add new feature"
```

**Continue Pattern**:
```
Green if code looks good
Red with suggested diff if not
```

### 4. **Interactive Elements**

**Cline Approach**:
- Tab to switch modes
- Keyboard-driven navigation
- Settings panels with keystrokes
- Per-step approval workflow

**Aider Approach**:
- Interactive loop waiting on prompts
- Slash commands (43 total)
- YAML config (100+ keys)
- Multiple modes (chat, architect, etc.)

### 5. **Context Management**

**Visual Patterns**:
- **Repo Map** (Aider) - Condensed repository structure
- **File Trees** - Visual project navigation
- **Diff Previews** - Side-by-side comparisons
- **Review Panes** - Survive terminal clear

**Claude Code**:
- Dynamic agent loop
- Terminal output observation
- Self-correction through iteration

### 6. **Feedback Mechanisms**

**Best Practices**:
- Real-time error diagnosis
- Self-correction loops
- Test execution feedback
- Git commit messages
- Token usage tracking
- Cost estimation

### 7. **Layout Patterns**

**Terminal-First** (Claude Code, Aider):
```
Header: Brand · Model
Path: ~/project

[Content Area]

Status Bar: Model · Tokens · Cost
Prompt: ❯
```

**TUI Mode** (Continue, Cline):
```
┌─ Header ─────────────────┐
│ Brand · Model · Status   │
├─ Main ───────────────────┤
│                          │
│ [Interactive Content]    │
│                          │
├─ Status ─────────────────┤
│ Progress · Tokens · Cost │
└──────────────────────────┘
```

---

## Best UI Libraries

### Python (What Lyra Uses)
1. **Rich** ⭐ Best choice
   - Beautiful formatting
   - Progress bars
   - Tables, trees, panels
   - 3-6x faster
   - Used by: Many top tools

2. **Textual** ⭐ For advanced TUI
   - Full TUI framework
   - Built on Rich
   - Interactive widgets
   - Event-driven

### Other Languages (Reference)
- **Ink** (React/Node.js) - React for CLI
- **BubbleTea** (Go) - Clean architecture
- **Ratatui** (Rust) - Terminal UI

---

## Specific Visual Elements

### 1. **Spinners & Progress**

**Patterns Found**:
```python
# Aider-style
⠋ Processing...
⠙ Analyzing code...
⠹ Running tests...

# Rich-style
[████████░░] 80% Complete
Working... ━━━━━━━━━━━━━━━━ 45%

# Continue-style
✓ Check passed
✗ Check failed (see diff)
```

### 2. **Status Indicators**

**Symbols Used**:
- ✓ ✗ ⚠ ℹ - Status (universal)
- ⎿ - Tool use (Claude Code)
- ✻ - Stats (Claude Code)
- → - Action/flow
- ▶ ▼ - Collapsible sections
- █ ░ - Progress bars

### 3. **Color Semantics**

**Standard Palette**:
- **Cyan** - Brand, commands, links
- **Magenta** - Highlights, model names
- **Green** - Success, completed
- **Red** - Errors, failures
- **Yellow** - Warnings, attention
- **Blue** - Info, paths
- **Dim** - Secondary text

### 4. **Typography**

**Hierarchy**:
```
[bold cyan]Primary Heading[/bold cyan]
[bold]Secondary Heading[/bold]
Regular text
[dim]Secondary text[/dim]
[dim blue]Tertiary text[/dim blue]
```

---

## UX Patterns

### 1. **Onboarding**

**OpenClaw Pattern**:
- Step-by-step wizard
- Progressive disclosure
- Sensible defaults
- Clear progress (1/4, 2/4, etc.)

**Continue Pattern**:
- One-line install
- Conversational prompts
- Multiple installation paths

### 2. **Error Handling**

**Best Practices**:
```
✗ Error: API key not configured

Suggested fixes:
  1. Run lyra onboard to set up
  2. Set ANTHROPIC_API_KEY environment variable
  3. Check https://docs.lyra.ai/troubleshooting
```

### 3. **Feedback Loops**

**Aider Pattern**:
- Atomic git commits
- Auto-generated messages
- Easy rollbacks
- Granular history

**Claude Code Pattern**:
- Self-correction
- Test execution
- Error observation
- Iterative refinement

### 4. **Mode Switching**

**Cline Pattern**:
- Tab to switch modes
- Visual mode indicator
- Keyboard shortcuts
- Clear state transitions

---

## Implementation Recommendations for Lyra

### Phase 1: Enhanced Visual Design ✅ (Done)
- ✅ Cyan brand color
- ✅ Magenta model names
- ✅ Status indicators (✓ ✗ ⚠ ℹ)
- ✅ Color hierarchy

### Phase 2: Progress Indicators (Next)
- [ ] Rich progress bars
- [ ] Spinners for long operations
- [ ] Token counting display
- [ ] Step indicators (1/4, 2/4)

### Phase 3: Interactive Elements
- [ ] Collapsible sections (▶/▼)
- [ ] Diff previews
- [ ] File tree navigation
- [ ] Review panes

### Phase 4: Status Bar
- [ ] Bottom status bar
- [ ] Model · Session · Tokens · Cost
- [ ] Real-time updates
- [ ] Inverse colors

### Phase 5: Advanced Features
- [ ] TUI mode (Textual)
- [ ] Multiple panes
- [ ] Keyboard shortcuts
- [ ] Mouse support

---

## Specific Code Patterns

### 1. **Rich Progress Bar**
```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    console=console,
) as progress:
    task = progress.add_task("Processing...", total=None)
    # Do work
    progress.update(task, completed=True)
```

### 2. **Status Display**
```python
# Claude Code style
console.print("[green]✓[/green] Task completed")
console.print("[cyan]⎿[/cyan] [dim]Tool: Read file.py[/dim]")
console.print("[dim]✻ 2.3s · 3 tools · 1,234 tokens[/dim]")
```

### 3. **Collapsible Sections**
```python
# Expandable content
if expanded:
    console.print("[cyan]▼ Details[/cyan]")
    console.print("[dim]Content here...[/dim]")
else:
    console.print("[dim]▶ Details[/dim]")
```

### 4. **Error with Suggestions**
```python
console.print("[red]✗[/red] [bold]Error occurred[/bold]")
console.print()
console.print("[bold]Suggested fixes:[/bold]")
console.print("  1. [cyan]lyra onboard[/cyan]")
console.print("  2. Set ANTHROPIC_API_KEY")
```

---

## Competitive Analysis

| Feature | Claude Code | Aider | Continue | Cline | Lyra (Current) | Lyra (Target) |
|---------|-------------|-------|----------|-------|----------------|---------------|
| Brand Color | Minimal | Minimal | Pink | VS Code | Cyan | Cyan+Magenta |
| Progress Bars | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Spinners | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Status Bar | ✓ | ✗ | ✓ | ✓ | Partial | ✓ |
| Diff Preview | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Token Display | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Cost Tracking | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ |
| Git Integration | ✓ | ✓✓ | ✓ | ✓ | ✗ | ✓ |
| TUI Mode | ✓ | ✗ | ✓ | ✓ | ✗ | Future |

---

## Sources

### Research Sources
1. [AI Coding Agent Comparison](https://codeforgeek.com/ai-coding-agent-comparison/)
2. [8 AI Coding CLIs Compared](https://www.tembo.io/blog/aider-alternatives)
3. [Top 5 CLI Coding Agents 2026](https://pinggy.io/blog/top_cli_based_ai_coding_agents/)
4. [Continue Dev GitHub](https://github.com/continuedev/continue)
5. [Aider Chat](https://aider.chat/)
6. [7 TUI Libraries](https://blog.logrocket.com/7-tui-libraries-interactive-terminal-apps)
7. [Rich Python Library](https://thelinuxcode.com/building-beautiful-command-line-interfaces-with-python-rich/)
8. [CLI UX Best Practices](https://evilmartians.com/chronicles/cli-ux-best-practices-3-patterns-for-improving-progress-displays)
9. [OpenClaw vs Hermes](https://www.glukhov.org/ai-systems/comparisons/openclaw-hermes-alternatives-popularity/)
10. [Agent Friendly Code](https://www.agentfriendlycode.com/)

---

## Next Steps

### Immediate (Phase 2)
1. Add Rich progress bars for long operations
2. Implement spinners for indeterminate tasks
3. Add token counting display
4. Show step indicators

### Short Term (Phase 3)
1. Collapsible tool output
2. Diff preview for file changes
3. File tree navigation
4. Review panes

### Long Term (Phase 4-5)
1. Enhanced status bar
2. Real-time cost tracking
3. TUI mode with Textual
4. Mouse support

---

## Conclusion

The top AI agent tools share common UI patterns:
- **Minimal but colorful** - Not boring, but not overwhelming
- **Real-time feedback** - Progress, tokens, costs
- **Clear status** - Visual indicators for everything
- **Interactive** - Keyboard-driven, responsive
- **Professional** - Polished, production-ready

Lyra should adopt these patterns to compete with the best tools in the space.

---

**Researched by**: Claude Opus 4.7  
**Date**: 2026-05-23  
**Status**: ✅ Research Complete, Ready for Implementation
