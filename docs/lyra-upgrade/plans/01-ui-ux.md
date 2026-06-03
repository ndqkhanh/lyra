# UI/UX — Plan (§4.1)

> Run 1 — June 3, 2026 | Phase 1: 4 color themes, keybindings config, statusline, output styling

## Plain-Language Summary

Lyra currently outputs monochrome terminal text with no user-facing UI customization. This plan implements 4 color themes (Dark, Light, Solarized, Monokai) with hex token definitions, a full keybindings system for navigation/editing/session control, a statusline showing model/effort/session/tokens/cost, styled output for diffs/code blocks/Mermaid diagrams/tables, and a fullscreen fleet view. The UI is terminal-native (via Rich/Textual) with no desktop dependency — Phase 4 will add the Electron desktop (§4.28).

## 1. Problem

BASELINE.md rates UI/UX maturity = `none`: "Basic terminal output; no themes, no keybindings config." Key failures:
- **Monochrome output**: No syntax highlighting, no diff coloring, no visual hierarchy
- **No themes**: Cannot switch between light/dark or customize colors
- **No keybindings**: All interaction is typed commands. No keyboard shortcuts for power users
- **No statusline**: No persistent display of model, effort, session, tokens, or cost
- **No output styling**: Code blocks, diffs, tables all rendered as raw text
- **No fleet view**: No way to see all active sessions at a glance

## 2. Evidence Synthesis

### Claude Code CLI (§3.1)
Full TUI with: color themes (Dark, Light, Solarized, Monokai), keybindings config (`~/.claude/keybindings.json`), statusline (model, session name, effort, mode), output styling (diff highlighting, code blocks with syntax, Mermaid rendering), `/model` and `/effort` commands for live switching. The `claude agents` command opens a fleet view TUI with state-grouped session rows.

### Hermes Desktop (§3.29)
Electron + React + Tailwind CSS desktop client with dark/light themes, IPC streaming, attachment staging, and comprehensive UI state management. Reference for Phase 4 desktop.

### BREAKTHROUGH-ARCHITECTURE.md
CLI/TUI is the primary user surface. Fleet View TUI is specified in the Orchestration Plane. Desktop (Electron + React) is Phase 4.

## 3. Proposed Lyra Design

### 3.1 Color Themes

```python
# Color theme definitions with hex tokens
THEMES = {
    "dark": {
        "name": "Dark (default)",
        "background": "#1e1e2e",       # Main background
        "surface": "#181825",           # Secondary background (status bar)
        "text": "#cdd6f4",             # Primary text
        "text_dim": "#6c7086",         # Dim/muted text
        "accent": "#89b4fa",           # Primary accent (links, active items)
        "accent_alt": "#b4befe",       # Secondary accent
        "success": "#a6e3a1",          # Success/green
        "warning": "#f9e2af",          # Warning/yellow
        "error": "#f38ba8",            # Error/red
        "info": "#89dceb",             # Info/cyan
        "code_bg": "#313244",          # Code block background
        "diff_add": "#a6e3a1",         # Diff added line
        "diff_del": "#f38ba8",         # Diff deleted line
        "diff_header": "#89b4fa",      # Diff header (@@ lines)
        "selection": "#45475a",        # Selection highlight
        "border": "#45475a",           # Border color
        "syntax_keyword": "#cba6f7",   # Syntax: keyword
        "syntax_string": "#a6e3a1",    # Syntax: string
        "syntax_number": "#fab387",    # Syntax: number
        "syntax_comment": "#6c7086",   # Syntax: comment
        "syntax_function": "#89b4fa",  # Syntax: function name
        "syntax_type": "#f9e2af",      # Syntax: type name
    },
    "light": {
        "name": "Light",
        "background": "#eff1f5",
        "surface": "#e6e9ef",
        "text": "#4c4f69",
        "text_dim": "#9ca0b0",
        "accent": "#1e66f5",
        "accent_alt": "#7287fd",
        "success": "#40a02b",
        "warning": "#df8e1d",
        "error": "#d20f39",
        "info": "#04a5e5",
        "code_bg": "#dce0e8",
        "diff_add": "#40a02b",
        "diff_del": "#d20f39",
        "diff_header": "#1e66f5",
        "selection": "#ccd0da",
        "border": "#ccd0da",
        "syntax_keyword": "#8839ef",
        "syntax_string": "#40a02b",
        "syntax_number": "#fe640b",
        "syntax_comment": "#9ca0b0",
        "syntax_function": "#1e66f5",
        "syntax_type": "#df8e1d",
    },
    "solarized": {
        "name": "Solarized",
        "background": "#002b36",
        "surface": "#073642",
        "text": "#839496",
        "text_dim": "#586e75",
        "accent": "#268bd2",
        "accent_alt": "#6c71c4",
        "success": "#859900",
        "warning": "#b58900",
        "error": "#dc322f",
        "info": "#2aa198",
        "code_bg": "#073642",
        "diff_add": "#859900",
        "diff_del": "#dc322f",
        "diff_header": "#268bd2",
        "selection": "#073642",
        "border": "#586e75",
        "syntax_keyword": "#6c71c4",
        "syntax_string": "#2aa198",
        "syntax_number": "#d33682",
        "syntax_comment": "#586e75",
        "syntax_function": "#268bd2",
        "syntax_type": "#b58900",
    },
    "monokai": {
        "name": "Monokai",
        "background": "#272822",
        "surface": "#1e1f1c",
        "text": "#f8f8f2",
        "text_dim": "#75715e",
        "accent": "#a6e22e",
        "accent_alt": "#66d9ef",
        "success": "#a6e22e",
        "warning": "#e6db74",
        "error": "#f92672",
        "info": "#66d9ef",
        "code_bg": "#1e1f1c",
        "diff_add": "#a6e22e",
        "diff_del": "#f92672",
        "diff_header": "#66d9ef",
        "selection": "#49483e",
        "border": "#49483e",
        "syntax_keyword": "#f92672",
        "syntax_string": "#e6db74",
        "syntax_number": "#ae81ff",
        "syntax_comment": "#75715e",
        "syntax_function": "#a6e22e",
        "syntax_type": "#66d9ef",
    },
}
```

### 3.2 Keybindings

```python
KEYBINDINGS = {
    # Navigation
    "ctrl+p": {"action": "navigate.active_sessions", "scope": "global"},
    "ctrl+n": {"action": "navigate.next_session", "scope": "fleet_view"},
    "ctrl+b": {"action": "navigate.prev_session", "scope": "fleet_view"},
    "ctrl+w": {"action": "session.close", "scope": "fleet_view"},
    "ctrl+]": {"action": "fleet_view.activate", "scope": "global"},

    # Session management
    "ctrl+s": {"action": "session.save", "scope": "global"},
    "ctrl+r": {"action": "session.resume", "scope": "global"},
    "ctrl+x": {"action": "session.cancel", "scope": "global"},

    # Editing
    "ctrl+e": {"action": "edit.open_in_editor", "scope": "global"},
    "alt+left": {"action": "edit.go_back", "scope": "global"},
    "alt+right": {"action": "edit.go_forward", "scope": "global"},

    # Model/Effort
    "ctrl+m": {"action": "model.cycle", "scope": "global"},
    "ctrl+t": {"action": "effort.cycle", "scope": "global"},
    "ctrl+/": {"action": "fast_mode.toggle", "scope": "global"},

    # Display
    "ctrl+i": {"action": "theme.cycle", "scope": "global"},
    "ctrl+, ": {"action": "settings.open", "scope": "global"},
    "ctrl+shift+f": {"action": "fullscreen.toggle", "scope": "global"},

    # Voice (Phase 3+)
    "ctrl+shift+v": {"action": "voice.push_to_talk", "scope": "global"},

    # Help
    "ctrl+h": {"action": "help.show", "scope": "global"},
    "ctrl+shift+/": {"action": "keybindings.show", "scope": "global"},
}
```

Keybinding configuration file (`~/.lyra/keybindings.json`):
```json
{
  "ctrl+p": {"action": "navigate.active_sessions", "scope": "global"},
  "ctrl+s": {"action": "session.save", "scope": "global"},
  "ctrl+t": {"action": "effort.cycle", "scope": "global"},
  "custom:ctrl+o": {"action": "model.set", "args": {"model": "opus"}}
}
```

### 3.3 Statusline

```
┌─────────────────────────────────────────────────────────────────┐
│ opus  xhigh  my-session-name   Tok: 12.4K/$0.87    [default]    │
│ ^^^^  ^^^^^  ^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^    ^^^^^^^^     │
│ model effort session name      token usage + cost   perm mode    │
└─────────────────────────────────────────────────────────────────┘
```

Statusline components:
- **Model**: Current model alias (opus, sonnet, haiku, or custom)
- **Effort**: Current effort level (low/medium/high/xhigh/max/ultracode)
- **Session name**: Current session identifier
- **Token usage**: Context window usage (`12.4K/200K`) + cumulative cost
- **Permission mode**: Current permission mode (default/acceptEdits/plan/auto/bypass)
- **Background indicator**: `[BG]` for background sessions (colored yellow)
- **Fleet count**: `[3/8]` when in fleet mode (3 active of 8 total)

### 3.4 Output Styling

```python
class OutputStyler:
    """Apply terminal styling to different output types."""

    def style_diff(self, diff_text: str, theme: Theme) -> str:
        """Colorize unified diff output."""
        lines = []
        for line in diff_text.split("\n"):
            if line.startswith("+++") or line.startswith("---"):
                lines.append(style(line, fg=theme.diff_header, bold=True))
            elif line.startswith("@@ -"):
                lines.append(style(line, fg=theme.diff_header))
            elif line.startswith("+"):
                lines.append(style(line, fg=theme.diff_add))
            elif line.startswith("-"):
                lines.append(style(line, fg=theme.diff_del))
            else:
                lines.append(line)
        return "\n".join(lines)

    def style_code(self, code: str, language: str, theme: Theme) -> str:
        """Syntax-highlight code block."""
        # Use Pygments for syntax highlighting with theme colors
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import Terminal256Formatter
        lexer = get_lexer_by_name(language)
        return highlight(code, lexer, Terminal256Formatter())

    def style_mermaid(self, mermaid_text: str) -> str:
        """Render Mermaid diagram as text (basic ASCII fallback).
        Phase 2: render as SVG in supporting terminals."""
        # Basic: just print the mermaid code block
        # Phase 2: use mermaid-cli for SVG rendering
        return format_code_block(mermaid_text, "mermaid")

    def style_table(self, headers: list[str], rows: list[list[str]]) -> str:
        """Render a table with column alignment."""
        # Use Rich Table for terminal rendering
        from rich.table import Table
        table = Table(*headers)
        for row in rows:
            table.add_row(*row)
        return table
```

### 3.5 Fullscreen Fleet View

```
┌─────────────────────────────────────────────────────────────────┐
│  LYRA FLEET       3 active / 8 total            [F11 to exit]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  NEEDS INPUT (1)                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 1. review-pr-342    [pr-reviewer]   awaiting response    │    │
│  │    "Should we merge the provider abstraction?"           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  WORKING (2)                                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 2. refactor-router [architect]    8 tool calls / 45s    │    │
│  │    "Designing capability matrix schema..."              │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ 3. run-tests       [executor]      23 tool calls / 120s │    │
│  │    "Running test suite: 142/150 passed"                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  COMPLETED (5)                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 4. lint-fix        [executor]     done / 12 tool calls   │    │
│  │ 5. doc-update      [writer]       done / 8 tool calls    │    │
│  │ ...                                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ [↓] next  [↑] prev  [Enter] focus  [d] dispatch  [q] quit       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.6 Implementation Strategy

```
Phase 1 (this plan): Rich-style terminal output with Rich library
  - Rich console for styled output
  - 4 themes via Theme dataclass
  - Basic statusline rendering
  - Code block highlighting via Pygments
  - Diff coloring

Phase 2 (fleet view): Textual TUI
  - Textual app for fleet view dashboard
  - Keyboard-navigable session list
  - Live token/cost display
  - Fleet dispatch surface

Phase 4 (desktop): Electron + React
  - Full GUI with chat, memory, settings screens
  - Rich text editing, image rendering
  - Voice input/output
```

## 4. Build Outline

### Phase 1a — Theme System (Week 1)
- [ ] Define Theme dataclass with all color tokens in `src/ui/theme.py`
- [ ] Implement Dark, Light, Solarized, Monokai themes
- [ ] Implement `get_theme(name)` and `cycle_theme()` functions
- [ ] Theme persistence in settings.json (`ui.theme` key)
- [ ] Unit tests: theme token values, theme switching
- [ ] **Dependency:** None

### Phase 1b — Output Styling (Week 1-2)
- [ ] Implement `OutputStyler` with diff, code, table, and mermaid rendering
- [ ] Integrate Pygments for syntax highlighting
- [ ] Add Rich console formatting to all output paths
- [ ] Add `--no-color` flag for CI/pipe mode
- [ ] Integrate with tools: Bash output, Read output, file diffs
- [ ] **Dependency:** Phase 1a

### Phase 1c — Statusline (Week 2)
- [ ] Implement statusline rendering with Rich Layout
- [ ] Model, effort, session name display
- [ ] Token usage + cumulative cost display
- [ ] Permission mode indicator
- [ ] Background/fleet indicators
- [ ] **Dependency:** Phase 1a

### Phase 1d — Keybindings (Week 3-4)
- [ ] Implement keybinding registry (default + config overrides)
- [ ] Config file parsing (`~/.lyra/keybindings.json`, `.lyra/keybindings.json`)
- [ ] Action dispatcher (map keys to registered actions)
- [ ] Default keybindings for navigation, session control, model/effort
- [ ] `keybindings` CLI command for viewing/listing bindings
- [ ] **Dependency:** None

### Phase 1e — Fullscreen Fleet View (Week 4, TUI)
- [ ] Implement Textual TUI app for fleet view
- [ ] Session list grouped by state (needs-input/working/completed)
- [ ] Keyboard navigation (arrows, Enter, Escape)
- [ ] Dispatch surface for new sessions
- [ ] Live status updates via WebSocket
- [ ] **Dependency:** Phase 1a, 1c, Fleet/Swarm (§4.13)

## 5. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Rich/Textual terminal incompatibility (old terminals) | Medium | Low | `--no-color` fallback; plain text mode |
| Keybinding conflicts with terminal emulator | High | Medium | Documented defaults; user-configurable overrides |
| Statusline too wide for narrow terminals | Medium | Low | Collapsible statusline (short mode) |
| Fleet view TUI complexity | Medium | Medium | Phase 2 feature; Textual provides built-in key handling |
| Theme rendering differences across terminals | Low | Low | ANSI color mapping; 256-color palette fallback |

## 6. Multi-Provider Note

UI/UX is provider-agnostic by design. The statusline model indicator shows the model alias (sonnet/opus/haiku) not the provider ID. The theme system is purely terminal rendering. The only provider-aware element: the token/cost display normalizes across providers using the unified TokenUsage format.

## 7. References

1. Claude Code CLI Reference — code.claude.com/docs/en/cli-reference. Themes, keybindings, statusline.
2. Claude Code Agent View — code.claude.com/docs/en/agent-view. Fleet view TUI, session state model.
3. Claude Code Keybindings — code.claude.com/docs/en/keybindings. Config format, chord bindings.
4. Hermes Desktop — https://github.com/fathah/hermes-desktop. Electron + React reference for Phase 4.
5. Rich — https://rich.readthedocs.io. Terminal rendering library.
6. Textual — https://textual.textualize.io. TUI framework for Python.
7. BREAKTHROUGH-ARCHITECTURE.md — CLI/TUI primary surface, fleet view in Orchestration Plane.
8. BASELINE.md — Lyra current state: `none` for UI/UX.

## 8. Changelog
- Run 1: Initial plan — themes, keybindings, statusline, output styling, fleet view TUI

## Expert Review

**Mini-Debate Participants:** Senior UX Designer, Senior Backend Engineer, Adversarial Skeptic

**Skeptic's challenge:** "Port Claude Code's implementation directly — don't invent something new unless the evidence proves it's better."

**Resolution:** Parity port is the (A) tier baseline. Breakthrough enhancements must beat Claude Code's implementation on at least one measurable dimension (latency, token cost, multi-provider compatibility, UX simplicity) with cited evidence. Otherwise ship parity.

**Sign-off:** Plan is feasible. Parity implementation is well-documented in Claude Code docs (§3.1). Breakthrough tier gated on evidence from batch research findings.

## Changelog

- Run 4 (2026-06-03): Added Expert Review section, Changelog
