# Lyra UI — Documentation

Per-phase guides for the Lyra UI package. The top-level [`../README.md`](../README.md)
contains the project overview, installation, and testing instructions; this directory
holds the deep documentation for each implementation phase.

| Phase | Module(s) | Guide |
|-------|-----------|-------|
| 1 | `console.py`, `progress.py` | [Rich Console & Progress](phase-01-console.md) |
| 2 | `app.py`, `widgets.py` | [Dual-Pane TUI](phase-02-dual-pane.md) |
| 3 | `streaming.py`, `progress_viz.py` | [Streaming & Progress Visualization](phase-03-streaming.md) |
| 4 | `context_viz.py` | [Context Window Visualization](phase-04-context.md) |
| 5 | `keyboard.py` | [Advanced Keyboard Navigation](phase-05-keyboard.md) |
| 6 | `agent_dashboard.py`, `dashboard_viz.py` | [Multi-Agent Orchestration Dashboard](phase-06-dashboard.md) |
| 7 | `banner.py`, `notifications.py`, `themes.py` | [Banners, Notifications & Themes](phase-07-visual-feedback.md) |
| 8 | `session.py`, `team.py`, `integration.py` | [Sessions, Teams & Integrations](phase-08-collaboration.md) |
| 9 | `performance.py`, `async_arch.py`, `resource_mgmt.py` | [Performance & Async Architecture](phase-09-performance.md) |
| 10 | `accessibility.py` | [Accessibility (WCAG 2.1 AA)](phase-10-accessibility.md) |

## Cross-cutting references

- [Keyboard Shortcuts Cheat Sheet](../README.md#keyboard-shortcuts-cheat-sheet)
- [Architecture diagram](../README.md#architecture)
- [Rich documentation](https://rich.readthedocs.io/)
- [Textual documentation](https://textual.textualize.io/)
- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
