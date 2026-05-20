# Lyra UI

Beautiful terminal UI for the Lyra AI research agent — built on Rich and Textual.

**Status**: 443 tests passing | 93% coverage | Phases 1–10 complete

## Overview

Lyra UI provides a full terminal-first UI stack: Rich console + Textual TUI
framework, a dual-pane interface, streaming output, context-window visualization,
vim-style keyboard navigation, a multi-agent orchestration dashboard, banners and
themes, collaboration & session sharing, async + performance infrastructure, and
WCAG 2.1 AA accessibility support.

## Phase guides

Deep documentation per phase lives in [`docs/`](docs/README.md). Quick links:

| Phase | Topic | Modules | Guide |
|-------|-------|---------|-------|
| 1 | Rich Console & Progress | `console.py`, `progress.py` | [phase-01](docs/phase-01-console.md) |
| 2 | Dual-Pane TUI | `app.py`, `widgets.py` | [phase-02](docs/phase-02-dual-pane.md) |
| 3 | Streaming & Progress Visualization | `streaming.py`, `progress_viz.py` | [phase-03](docs/phase-03-streaming.md) |
| 4 | Context Window Visualization | `context_viz.py` | [phase-04](docs/phase-04-context.md) |
| 5 | Advanced Keyboard Navigation | `keyboard.py` | [phase-05](docs/phase-05-keyboard.md) |
| 6 | Multi-Agent Dashboard | `agent_dashboard.py`, `dashboard_viz.py` | [phase-06](docs/phase-06-dashboard.md) |
| 7 | Banners, Notifications & Themes | `banner.py`, `notifications.py`, `themes.py` | [phase-07](docs/phase-07-visual-feedback.md) |
| 8 | Sessions, Teams & Integrations | `session.py`, `team.py`, `integration.py` | [phase-08](docs/phase-08-collaboration.md) |
| 9 | Performance & Async Architecture | `performance.py`, `async_arch.py`, `resource_mgmt.py` | [phase-09](docs/phase-09-performance.md) |
| 10 | Accessibility (WCAG 2.1 AA) | `accessibility.py` | [phase-10](docs/phase-10-accessibility.md) |

## Installation

```bash
cd packages/lyra-ui
pip install -e .
```

## Quick start

```python
from lyra_ui import LyraApp, console

# Styled output via the Rich console singleton
console.print_success("Lyra UI loaded")

# Run the dual-pane TUI
LyraApp().run()
```

## Testing

```bash
# All tests
pytest tests/ -v

# Phase-specific
pytest tests/test_agent_dashboard.py tests/test_dashboard_viz.py -v
pytest tests/test_accessibility.py -v
pytest tests/test_async_arch.py -v
```

**Current**: 443 tests passing, 93% line coverage.

## Architecture

```
┌─────────────────────────────────────────┐
│    Lyra Textual App                     │
│  (Main Application)                     │
│                                         │
│  ┌─────────────┬─────────────────────┐ │
│  │ Conversation│  Status Panel       │ │
│  │ Pane (70%)  │  (30%)              │ │
│  │             │                     │ │
│  │ Messages    │  Agent Status       │ │
│  │ History     │  Token Usage        │ │
│  │ Code blocks │  Context Usage      │ │
│  │             │  Progress           │ │
│  └─────────────┴─────────────────────┘ │
│                                         │
│  Keyboard: q, Ctrl+W, Ctrl+N           │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Rich Console (singleton)             │
│  • Theme management                     │
│  • Status / success / warn / error      │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Progress Manager                     │
│  • Multiple progress bars               │
│  • Spinners                             │
│  • Time tracking                        │
└─────────────────────────────────────────┘
```

## Keyboard Shortcuts Cheat Sheet

### Application
| Key | Action |
|-----|--------|
| `q` | Quit |
| `Ctrl+W` | Switch active pane |
| `Ctrl+N` | New chat |
| `Ctrl+C` | Cancel current stream |

### Vim Navigation (`VimNavigator`)
| Key | Action |
|-----|--------|
| `h` `j` `k` `l` | Move left / down / up / right |
| `w` `b` | Forward / back by word |
| `gg` | Go to top |
| `G` | Go to bottom |
| `Ctrl+D` | Page down |
| `Ctrl+U` | Page up |

### Quick Actions
| Key | Action |
|-----|--------|
| `@` | File picker |
| `#` | Skill picker |
| `/` | Command palette |

### Modes (`NavigationMode`)
| Mode | Enter via |
|------|-----------|
| Normal | `Esc` |
| Insert | `i` |
| Visual | `v` |
| Command | `:` |

## Version

Current version: **0.1.0**

## References

- [Rich documentation](https://rich.readthedocs.io/)
- [Textual documentation](https://textual.textualize.io/)
- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- Lyra UI/UX Plan: `.omc/plans/LYRA_UI_UX_ULTIMATE_UPGRADE_PLAN.md`
