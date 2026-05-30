# UI/UX Enhancement: Beautiful CLI Experience

**Version:** 1.0.0
**Date:** 2026-05-30
**Status:** Implementation Design - Ready
**Based on:** Hermes-agent, Claude Code patterns, Textual TUI, Phase 3 Research

---

## Executive Summary

The UI/UX Enhancement delivers a beautiful, modern CLI experience with customizable color themes, full keybinding system, rich interactions (autocomplete, inline suggestions), and Textual TUI framework integration for advanced widgets.

---

## I. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    UI/UX ENHANCEMENT SYSTEM                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. COLOR THEME SYSTEM                                     │   │
│  │ Syntax highlighting | Status indicators | Progress bars    │   │
│  │ Themes: light, dark, high-contrast, custom                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. KEYBINDING SYSTEM                                      │   │
│  │ Customizable shortcuts | Command palette (fuzzy search)    │   │
│  │ Vim/Emacs modes | Chord bindings                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3. RICH INTERACTIONS                                      │   │
│  │ Autocomplete | Inline suggestions (ghost text)             │   │
│  │ Context menus | Drag-drop regions                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 4. TUI FRAMEWORK (Textual)                                │   │
│  │ Rich widgets | Reactive updates | CSS-like styling         │   │
│  │ Multi-panel layouts | Modal dialogs                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## II. Core Components

### 2.1 Color Theme System

```python
class ThemeSystem:
    """Beautiful color themes with syntax highlighting."""

    PRESETS = {
        'dark': Theme(
            name='Dark',
            colors={
                'bg': '#1a1b26',
                'fg': '#a9b1d6',
                'accent': '#7aa2f7',
                'success': '#9ece6a',
                'error': '#f7768e',
                'warning': '#e0af68',
                'info': '#7dcfff',
                'muted': '#565f89',
                'border': '#3b4261',
                'selection': '#364a82',
            },
            syntax={
                'keyword': '#bb9af7',
                'string': '#9ece6a',
                'number': '#ff9e64',
                'comment': '#565f89',
                'function': '#7aa2f7',
                'class': '#e0af68',
                'variable': '#c0caf5',
                'operator': '#89ddff',
                'type': '#2ac3de',
            }
        ),
        'light': Theme(
            name='Light',
            colors={
                'bg': '#ffffff', 'fg': '#1a1b26',
                'accent': '#2e6edf', 'success': '#2ea043',
                'error': '#cf222e', 'warning': '#bf8700',
                'info': '#54aeff', 'muted': '#8b949e',
                'border': '#d0d7de', 'selection': '#b6e3ff',
            },
            syntax={
                'keyword': '#8250df', 'string': '#0a3069',
                'number': '#0550ae', 'comment': '#6e7781',
                'function': '#8250df', 'class': '#953800',
                'variable': '#24292f', 'operator': '#0550ae',
                'type': '#116329',
            }
        ),
        'high_contrast': Theme(
            name='High Contrast',
            colors={
                'bg': '#000000', 'fg': '#ffffff',
                'accent': '#00ffff', 'success': '#00ff00',
                'error': '#ff0000', 'warning': '#ffff00',
                'info': '#00bfff', 'muted': '#808080',
                'border': '#ffffff', 'selection': '#000080',
            }
        ),
    }

    def get_theme(self, name: str) -> Theme:
        return self.PRESETS.get(name, self.PRESETS['dark'])

    def apply(self, theme: Theme):
        """Apply theme to all UI components."""
        for component in self.components:
            component.update_style(theme.colors)
        self.renderer.set_syntax_colors(theme.syntax)
```

### 2.2 Keybinding System

```python
class KeybindingSystem:
    """Customizable keyboard shortcuts with command palette."""

    def __init__(self):
        self.bindings: dict[str, list[Keybinding]] = defaultdict(list)
        self.palette = CommandPalette()
        self._load_defaults()

    DEFAULTS = {
        'core': [
            Keybinding('ctrl+c', 'core.quit', 'Quit'),
            Keybinding('ctrl+s', 'core.save', 'Save'),
            Keybinding('ctrl+z', 'core.undo', 'Undo'),
            Keybinding('ctrl+shift+z', 'core.redo', 'Redo'),
            Keybinding('ctrl+shift+p', 'core.command_palette', 'Command Palette'),
            Keybinding('ctrl+p', 'core.quick_open', 'Quick Open File'),
            Keybinding('ctrl+shift+f', 'core.search_all', 'Search All'),
            Keybinding('ctrl+`', 'core.toggle_terminal', 'Toggle Terminal'),
        ],
        'navigation': [
            Keybinding('ctrl+j', 'nav.down', 'Move Down'),
            Keybinding('ctrl+k', 'nav.up', 'Move Up'),
            Keybinding('ctrl+h', 'nav.left', 'Move Left'),
            Keybinding('ctrl+l', 'nav.right', 'Move Right'),
            Keybinding('ctrl+d', 'nav.page_down', 'Page Down'),
            Keybinding('ctrl+u', 'nav.page_up', 'Page Up'),
        ],
        'agent': [
            Keybinding('ctrl+enter', 'agent.execute', 'Execute'),
            Keybinding('ctrl+shift+enter', 'agent.force_execute', 'Force Execute'),
            Keybinding('ctrl+r', 'agent.retry', 'Retry Last'),
            Keybinding('ctrl+shift+a', 'agent.new_agent', 'New Agent'),
        ],
    }

    def show_command_palette(self) -> CommandPalette:
        """Fuzzy-searchable command palette."""
        return self.palette

    def customize(self, command_id: str, new_binding: Keybinding):
        """User-customizable keybindings."""
        self.bindings[command_id] = [new_binding]
        self._save_customizations()
```

### 2.3 Rich Interactions

```python
class RichInteractions:
    """Autocomplete, inline suggestions, context menus."""

    async def autocomplete(self, partial: str, ctx: Context) -> list[Suggestion]:
        """Context-aware autocomplete suggestions."""
        sources = [
            self._command_completions(partial),
            self._file_completions(partial, ctx.cwd),
            self._variable_completions(partial, ctx.variables),
            self._skill_completions(partial),
            self._agent_completions(partial),
        ]
        results = await asyncio.gather(*sources)
        all_suggestions = [s for r in results for s in r]
        return sorted(all_suggestions, key=lambda s: s.relevance, reverse=True)[:10]

    async def inline_suggestion(self, context: str) -> str | None:
        """Ghost text completion for current input."""
        prediction = await self.model.predict_next(context)
        if prediction.confidence > 0.7:
            return prediction.text
        return None

    def context_menu(self, target: UIElement, actions: list[Action]) -> ContextMenu:
        """Right-click context menu."""
        return ContextMenu(target=target, actions=actions)
```

### 2.4 Status Bar & Progress

```python
class StatusBar:
    """Rich status bar with model, cost, progress info."""

    def render(self, session: SessionState) -> str:
        parts = [
            f" [bold]{session.mode}[/bold] ",              # Mode: RALPH/AUTOPILOT
            f" Model: {session.current_model} ",            # Current model
            f" Cost: ${session.total_cost:.4f} ",           # Session cost
            f" Tokens: {session.total_tokens:,} ",          # Token count
            f" Agents: {session.active_agents} ",           # Active agents
        ]
        if session.progress:
            parts.append(
                f" [cyan]{ProgressBar(session.progress).render()}[/cyan] "
            )
        return "│".join(parts)

class RichProgressDisplay:
    """Beautiful progress bars for long-running tasks."""

    def render(self, tasks: list[TaskProgress]) -> str:
        lines = []
        for task in tasks:
            bar_width = 40
            filled = int(task.percent / 100 * bar_width)
            bar = '█' * filled + '░' * (bar_width - filled)

            color = {
                TaskStatus.RUNNING: 'cyan',
                TaskStatus.SUCCESS: 'green',
                TaskStatus.ERROR: 'red',
                TaskStatus.PENDING: 'dim',
            }.get(task.status, 'white')

            lines.append(
                f"  [{color}]{bar}[/{color}] "
                f"{task.percent:3.0f}% {task.label}"
            )
        return '\n'.join(lines)
```

---

## III. Implementation Phases

| Phase | Weeks | Scope | Tests |
|-------|-------|-------|-------|
| 1: Color Themes | 1-2 | Theme engine, syntax highlighting, status indicators, 3 presets | 20 |
| 2: Keybindings | 3-4 | Keybinding registry, command palette, vim/emacs modes, customization | 25 |
| 3: Rich Interactions | 5-6 | Autocomplete, inline suggestions, context menus, progress bars | 25 |
| 4: TUI Integration | 7-8 | Textual framework, rich widgets, multi-panel, modal dialogs | 20 |

---

## IV. Testing Plan

| Test Type | Count | Coverage |
|-----------|-------|----------|
| Theme system | 15 | 95% |
| Keybindings | 20 | 90% |
| Rich interactions | 15 | 85% |
| TUI widgets | 15 | 85% |
| Integration | 15 | N/A |
| Accessibility | 10 | N/A |
| **Total** | **90** | **90%+** |

## V. Success Metrics

- [ ] Beautiful, modern CLI interface
- [ ] 3 theme presets + custom themes
- [ ] Full keybinding customization
- [ ] Autocomplete with <100ms response
- [ ] Command palette with fuzzy search
- [ ] Textual TUI integration working
- [ ] Positive user feedback
- [ ] 90+ tests, 90%+ coverage
