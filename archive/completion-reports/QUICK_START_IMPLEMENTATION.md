# Quick Start: Implementing Missing Widgets

**Version**: 1.0.0  
**Created**: 2026-05-17  
**Audience**: Developers implementing Phase 1 widgets  
**Estimated Time**: 24 hours total (6 hours per widget)  

---

## Overview

This guide walks through implementing the 4 missing widgets required for 100% spec compliance:
1. **WelcomeCard** (FR-001) — 8 hours
2. **CompactionBanner** (FR-010) — 6 hours
3. **BackgroundSwitcher** (FR-012) — 6 hours
4. **TodoPanel** (FR-015) — 4 hours

Each section includes:
- Requirements from spec
- Implementation template
- Test strategy
- Integration steps

---

## Prerequisites

### Environment Setup

```bash
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra

# Ensure dependencies installed
uv sync

# Verify Textual version
python -c "import textual; print(textual.__version__)"
# Should be >=0.86

# Run existing tests to ensure baseline
pytest packages/lyra-cli/tests/test_tui_v2_*.py -v
```

### Read the Specs

Before starting, read:
- `ui-specs/spec.md` — Functional requirements
- `ui-specs/constitution.md` — Design principles
- `ui-specs/plan.md` — Implementation guidance

---

## Widget 1: WelcomeCard (FR-001)

### Requirements

From `ui-specs/spec.md`:
- 2-column grid layout (mascot/title left, tips/news right)
- Collapse to single line on first `Input.Submitted`
- Reactive properties: `model`, `cwd`, `account`
- Truncate long paths with `Text.truncate`
- Stack vertically below 80 cols

### Implementation

**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/widgets/welcome_card.py`

```python
"""Welcome card widget with collapse animation (FR-001)."""

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static, Widget
from textual.containers import Grid
from rich.text import Text


class WelcomeCard(Widget):
    """Collapsible welcome card shown on launch.
    
    Displays greeting, mascot, model info, working directory, and tips.
    Collapses to single line after first user message.
    
    Constitution compliance:
    - I. Truth Over Aesthetics: All info sourced from SessionState
    - III. Progressive Disclosure: Expands/collapses on demand
    - V. Keyboard-First: No mouse-only interactions
    """
    
    DEFAULT_CSS = """
    WelcomeCard {
        height: auto;
        margin: 1;
    }
    
    WelcomeCard.expanded {
        height: auto;
    }
    
    WelcomeCard.collapsed {
        height: 1;
    }
    
    WelcomeCard Grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
    }
    
    @media (max-width: 80) {
        WelcomeCard Grid {
            grid-size: 1;
            grid-columns: 1fr;
        }
    }
    """
    
    # Reactive properties
    model: reactive[str] = reactive("claude-sonnet-4-6")
    cwd: reactive[str] = reactive("")
    account: reactive[str] = reactive("")
    expanded: reactive[bool] = reactive(True)
    
    def compose(self) -> ComposeResult:
        """Compose the welcome card layout."""
        if self.expanded:
            yield Grid(
                Static(self._render_left_column(), id="welcome-left"),
                Static(self._render_right_column(), id="welcome-right"),
            )
        else:
            yield Static(self._render_collapsed(), id="welcome-collapsed")
    
    def _render_left_column(self) -> str:
        """Render mascot and title."""
        mascot = """
    ╭─────────────────╮
    │   🌟 Lyra 🌟   │
    │  Deep Research  │
    │   AI Agent      │
    ╰─────────────────╯
        """
        
        greeting = f"Welcome back, {self.account or 'User'}!"
        
        return f"{mascot}\n\n{greeting}"
    
    def _render_right_column(self) -> str:
        """Render info and tips."""
        # Truncate long paths
        cwd_display = self._truncate_path(self.cwd, max_length=40)
        
        info = f"""
[bold]Current Session[/bold]
• Model: {self.model}
• Directory: {cwd_display}

[bold]Quick Tips[/bold]
• Press [cyan]Ctrl+P[/cyan] for command palette
• Type [cyan]/model[/cyan] to switch models
• Press [cyan]Ctrl+O[/cyan] to expand output
• Press [cyan]Esc[/cyan] to interrupt
        """
        
        return info.strip()
    
    def _render_collapsed(self) -> str:
        """Render single-line collapsed view."""
        cwd_display = self._truncate_path(self.cwd, max_length=30)
        return f"🌟 Lyra | {self.model} | {cwd_display}"
    
    def _truncate_path(self, path: str, max_length: int) -> str:
        """Truncate path intelligently with ellipsis."""
        if len(path) <= max_length:
            return path
        
        # Show start and end of path
        parts = path.split("/")
        if len(parts) <= 2:
            return path[:max_length - 3] + "..."
        
        # Keep first and last parts
        start = parts[0]
        end = parts[-1]
        middle = "..."
        
        result = f"{start}/{middle}/{end}"
        if len(result) > max_length:
            # Still too long, truncate end
            available = max_length - len(start) - len(middle) - 2
            end = end[:available] + "..."
            result = f"{start}/{middle}/{end}"
        
        return result
    
    def on_input_submitted(self) -> None:
        """Collapse card when user submits first message."""
        if self.expanded:
            self.expanded = False
            self.remove_class("expanded")
            self.add_class("collapsed")
    
    def watch_expanded(self, expanded: bool) -> None:
        """React to expanded state changes."""
        # Trigger re-compose
        self.refresh(layout=True)
```

### Tests

**File**: `packages/lyra-cli/tests/test_tui_v2_welcome_card.py`

```python
"""Tests for WelcomeCard widget."""

import pytest
from textual.pilot import Pilot
from lyra_cli.tui_v2.widgets.welcome_card import WelcomeCard
from lyra_cli.tui_v2.app import LyraHarnessApp


@pytest.mark.asyncio
async def test_welcome_card_renders_expanded():
    """Test welcome card renders in expanded state."""
    app = LyraHarnessApp()
    async with app.run_test() as pilot:
        card = app.query_one(WelcomeCard)
        assert card.expanded is True
        assert "Lyra" in card.query_one("#welcome-left").renderable


@pytest.mark.asyncio
async def test_welcome_card_collapses_on_submit():
    """Test welcome card collapses after first message."""
    app = LyraHarnessApp()
    async with app.run_test() as pilot:
        card = app.query_one(WelcomeCard)
        
        # Simulate input submission
        card.on_input_submitted()
        await pilot.pause()
        
        assert card.expanded is False
        assert card.has_class("collapsed")


@pytest.mark.asyncio
async def test_welcome_card_truncates_long_paths():
    """Test path truncation for long directories."""
    app = LyraHarnessApp()
    async with app.run_test() as pilot:
        card = app.query_one(WelcomeCard)
        
        long_path = "/very/long/path/to/some/deeply/nested/directory/structure"
        card.cwd = long_path
        await pilot.pause()
        
        rendered = card._render_collapsed()
        assert len(rendered) < len(long_path)
        assert "..." in rendered


@pytest.mark.asyncio
async def test_welcome_card_snapshot_120cols(snap_compare):
    """Snapshot test at 120 columns."""
    app = LyraHarnessApp()
    async with app.run_test() as pilot:
        assert snap_compare(app, terminal_size=(120, 40))


@pytest.mark.asyncio
async def test_welcome_card_snapshot_60cols(snap_compare):
    """Snapshot test at 60 columns (stacked layout)."""
    app = LyraHarnessApp()
    async with app.run_test() as pilot:
        assert snap_compare(app, terminal_size=(60, 40))
```

### Integration

**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/app.py`

```python
from .widgets.welcome_card import WelcomeCard

class LyraHarnessApp(HarnessApp):
    def compose(self) -> ComposeResult:
        # Add welcome card at top
        yield WelcomeCard(
            model=self.state.model,
            cwd=self.state.cwd,
            account=self.state.account,
        )
        
        # Rest of composition from harness-tui
        yield from super().compose()
    
    def watch_state_model(self, model: str) -> None:
        """Update welcome card when model changes."""
        card = self.query_one(WelcomeCard)
        card.model = model
```

---

## Widget 2: CompactionBanner (FR-010)

### Requirements

From `ui-specs/spec.md`:
- Render when `compaction_history[-1].triggered_at` within last 30s
- Checklist of restored items with glyphs
- Ctrl+O opens side pane with pre-compaction summary
- Auto-collapse to one-line after 30s

### Implementation

**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/widgets/compaction_banner.py`

```python
"""Compaction banner widget (FR-010)."""

from datetime import datetime, timedelta
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static, Widget, RichLog
from textual.containers import Vertical
from textual.binding import Binding


class CompactionBanner(Widget):
    """Banner showing context compaction events.
    
    Displays checklist of restored items after compaction.
    Auto-collapses after 30 seconds.
    
    Constitution compliance:
    - I. Truth Over Aesthetics: Shows actual restored items
    - III. Progressive Disclosure: Ctrl+O for detail
    - VII. Observability: Surfaces compaction events
    """
    
    BINDINGS = [
        Binding("ctrl+o", "toggle_expand", "Expand/Collapse"),
    ]
    
    DEFAULT_CSS = """
    CompactionBanner {
        height: auto;
        border: solid $accent;
        margin: 1;
    }
    
    CompactionBanner.collapsed {
        height: 1;
    }
    """
    
    compaction_event: reactive[dict | None] = reactive(None)
    expanded: reactive[bool] = reactive(True)
    
    def compose(self) -> ComposeResult:
        """Compose banner layout."""
        if not self.compaction_event:
            return
        
        if self.expanded:
            yield Vertical(
                Static(self._render_header()),
                RichLog(self._render_checklist(), id="compaction-detail"),
            )
        else:
            yield Static(self._render_collapsed())
    
    def _render_header(self) -> str:
        """Render banner header."""
        return "✻ [bold]Conversation compacted[/bold] (ctrl+o for history)"
    
    def _render_checklist(self) -> str:
        """Render checklist of restored items."""
        if not self.compaction_event:
            return ""
        
        items = self.compaction_event.get("restored", [])
        lines = []
        
        for kind, path, line_count in items:
            if kind == "read":
                glyph = "⎿"
                text = f"Read {path}"
                if line_count:
                    text += f" ({line_count} lines)"
            elif kind == "loaded":
                glyph = "⎿"
                text = f"Loaded {path}"
            elif kind == "skill":
                glyph = "⎿"
                text = f"Skills restored ({path})"
            else:
                glyph = "⎿"
                text = f"{kind}: {path}"
            
            lines.append(f"{glyph}  {text}")
        
        return "\n".join(lines)
    
    def _render_collapsed(self) -> str:
        """Render one-line collapsed view."""
        count = len(self.compaction_event.get("restored", []))
        return f"✻ Compacted ({count} items restored) • ctrl+o to expand"
    
    def action_toggle_expand(self) -> None:
        """Toggle expanded/collapsed state."""
        self.expanded = not self.expanded
        self.refresh(layout=True)
    
    def watch_compaction_event(self, event: dict | None) -> None:
        """React to new compaction events."""
        if event:
            # Auto-collapse after 30 seconds
            self.set_timer(30.0, self._auto_collapse)
    
    def _auto_collapse(self) -> None:
        """Auto-collapse after timeout."""
        if self.expanded:
            self.expanded = False
```

### Tests

**File**: `packages/lyra-cli/tests/test_tui_v2_compaction_banner.py`

```python
"""Tests for CompactionBanner widget."""

import pytest
from textual.pilot import Pilot
from lyra_cli.tui_v2.widgets.compaction_banner import CompactionBanner


@pytest.mark.asyncio
async def test_compaction_banner_renders():
    """Test banner renders with restored items."""
    # Implementation similar to welcome_card tests
    pass


@pytest.mark.asyncio
async def test_compaction_banner_expands_on_ctrl_o():
    """Test Ctrl+O toggles expansion."""
    pass


@pytest.mark.asyncio
async def test_compaction_banner_auto_collapses():
    """Test auto-collapse after 30 seconds."""
    pass
```

---

## Widget 3: BackgroundSwitcher (FR-012)

### Requirements

From `ui-specs/spec.md`:
- Modal `ListView` over `SessionState.background_tasks`
- Show label, elapsed time, last token delta, status glyph
- Enter brings task to foreground
- Esc dismisses modal

### Implementation

**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/modals/background_switcher.py`

```python
"""Background task switcher modal (FR-012)."""

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label
from textual.binding import Binding


class BackgroundSwitcherModal(ModalScreen[str | None]):
    """Modal for switching between background tasks.
    
    Constitution compliance:
    - I. Truth Over Aesthetics: Shows actual background tasks
    - V. Keyboard-First: Arrow keys + Enter
    """
    
    BINDINGS = [
        Binding("escape", "dismiss(None)", "Cancel"),
        Binding("enter", "select", "Select"),
    ]
    
    DEFAULT_CSS = """
    BackgroundSwitcherModal {
        align: center middle;
    }
    
    BackgroundSwitcherModal > ListView {
        width: 80;
        height: 20;
        border: solid $accent;
    }
    """
    
    def __init__(self, background_tasks: dict):
        super().__init__()
        self.background_tasks = background_tasks
    
    def compose(self) -> ComposeResult:
        """Compose modal layout."""
        items = []
        for task_id, task in self.background_tasks.items():
            label = self._render_task(task)
            items.append(ListItem(Label(label), id=task_id))
        
        yield ListView(*items)
    
    def _render_task(self, task: dict) -> str:
        """Render single task row."""
        status_glyph = {
            "running": "⏵",
            "done": "✓",
            "failed": "✗",
            "cancelled": "⊗",
        }.get(task["status"], "?")
        
        elapsed = self._format_elapsed(task["started_at"])
        tokens = task.get("last_token_delta", 0)
        
        return f"{status_glyph} {task['label']} • {elapsed} • ↓ {tokens} tokens"
    
    def _format_elapsed(self, started_at: float) -> str:
        """Format elapsed time."""
        import time
        elapsed = time.time() - started_at
        
        if elapsed < 60:
            return f"{int(elapsed)}s"
        elif elapsed < 3600:
            return f"{int(elapsed / 60)}m {int(elapsed % 60)}s"
        else:
            return f"{int(elapsed / 3600)}h {int((elapsed % 3600) / 60)}m"
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle task selection."""
        task_id = event.item.id
        self.dismiss(task_id)
    
    def action_select(self) -> None:
        """Select highlighted task."""
        list_view = self.query_one(ListView)
        if list_view.highlighted_child:
            self.dismiss(list_view.highlighted_child.id)
```

### Integration

**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/app.py`

```python
from .modals.background_switcher import BackgroundSwitcherModal

class LyraHarnessApp(HarnessApp):
    BINDINGS = [
        Binding("ctrl+t", "show_background_switcher", "Background Tasks"),
    ]
    
    async def action_show_background_switcher(self) -> None:
        """Show background task switcher."""
        tasks = self.state.background_tasks
        if not tasks:
            self.notify("No background tasks", severity="information")
            return
        
        result = await self.push_screen(BackgroundSwitcherModal(tasks))
        if result:
            self._bring_to_foreground(result)
    
    def _bring_to_foreground(self, task_id: str) -> None:
        """Bring background task to foreground."""
        # Implementation: re-tag worker group
        pass
```

---

## Widget 4: TodoPanel (FR-015)

### Requirements

From `ui-specs/spec.md`:
- Vertical list of Static rows
- Show 5 items + overflow `… +N pending`
- Glyphs: `◻` pending, `◼` done, `⚠` blocked
- 1-frame highlight animation on transition

### Implementation

**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/widgets/todo_panel.py`

```python
"""To-do panel widget (FR-015)."""

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static, Widget
from textual.containers import Vertical


class TodoPanel(Widget):
    """Live to-do list with checkboxes.
    
    Constitution compliance:
    - I. Truth Over Aesthetics: Shows actual task state
    - IV. Streaming: Updates incrementally
    """
    
    DEFAULT_CSS = """
    TodoPanel {
        height: auto;
        border: solid $accent;
        padding: 1;
    }
    
    TodoPanel .todo-item {
        height: 1;
    }
    
    TodoPanel .todo-item.transition {
        background: $accent 50%;
    }
    """
    
    GLYPH_MAP = {
        "pending": "◻",
        "done": "◼",
        "blocked": "⚠",
    }
    
    todos: reactive[list[dict]] = reactive([])
    
    def compose(self) -> ComposeResult:
        """Compose to-do list."""
        visible = self.todos[:5]
        overflow = len(self.todos) - 5
        
        items = []
        for todo in visible:
            items.append(
                Static(
                    self._render_item(todo),
                    classes="todo-item",
                    id=f"todo-{todo['id']}",
                )
            )
        
        if overflow > 0:
            items.append(Static(f"… +{overflow} pending"))
        
        yield Vertical(*items)
    
    def _render_item(self, todo: dict) -> str:
        """Render single to-do item."""
        glyph = self.GLYPH_MAP.get(todo["status"], "?")
        return f"{glyph} {todo['label']}"
    
    def watch_todos(self, old_todos: list, new_todos: list) -> None:
        """React to to-do list changes."""
        # Detect transitions for animation
        old_ids = {t["id"]: t for t in old_todos}
        new_ids = {t["id"]: t for t in new_todos}
        
        for todo_id, new_todo in new_ids.items():
            old_todo = old_ids.get(todo_id)
            if old_todo and old_todo["status"] != new_todo["status"]:
                # Status changed - animate
                self._animate_transition(todo_id)
        
        # Refresh layout
        self.refresh(layout=True)
    
    def _animate_transition(self, todo_id: str) -> None:
        """Animate status transition."""
        try:
            item = self.query_one(f"#todo-{todo_id}")
            item.add_class("transition")
            self.set_timer(0.3, lambda: item.remove_class("transition"))
        except Exception:
            pass  # Item not in visible range
```

---

## Testing Strategy

### Run Tests

```bash
# Run all tui_v2 tests
pytest packages/lyra-cli/tests/test_tui_v2_*.py -v

# Run specific widget tests
pytest packages/lyra-cli/tests/test_tui_v2_welcome_card.py -v

# Update snapshots (after visual review)
pytest packages/lyra-cli/tests/test_tui_v2_*.py --snapshot-update

# Check coverage
pytest packages/lyra-cli/tests/test_tui_v2_*.py --cov=lyra_cli/tui_v2 --cov-report=term-missing
```

### Manual Testing

```bash
# Launch TUI with new widgets
LYRA_TUI=v2 uv run lyra

# Test welcome card collapse
# 1. Launch Lyra
# 2. Type a message and press Enter
# 3. Verify welcome card collapses

# Test compaction banner
# 1. Trigger compaction (long conversation)
# 2. Verify banner appears with checklist
# 3. Press Ctrl+O to expand/collapse
# 4. Wait 30s, verify auto-collapse

# Test background switcher
# 1. Start a long-running task
# 2. Press Ctrl+B to background it
# 3. Press Ctrl+T to open switcher
# 4. Select task and press Enter
# 5. Verify task returns to foreground

# Test to-do panel
# 1. Start a multi-phase task
# 2. Verify to-do panel shows phases
# 3. Watch checkboxes update as phases complete
```

---

## Common Issues & Solutions

### Issue 1: Widget Not Rendering

**Symptom**: Widget doesn't appear in TUI

**Solution**:
1. Check `compose()` is yielding the widget
2. Verify CSS `height` is not 0
3. Check `display` property in CSS
4. Use `self.refresh(layout=True)` after state changes

### Issue 2: Reactive Not Updating

**Symptom**: Widget doesn't update when state changes

**Solution**:
1. Ensure property is declared with `reactive[T] = reactive(default)`
2. Implement `watch_<property>()` method
3. Call `self.refresh()` in watch method
4. Check parent is updating child's reactive properties

### Issue 3: Tests Failing

**Symptom**: Snapshot tests fail with diff

**Solution**:
1. Review snapshot diff carefully
2. If intentional change: `pytest --snapshot-update`
3. If unintentional: fix widget rendering
4. Commit updated snapshots with code changes

### Issue 4: Performance Issues

**Symptom**: UI lags or drops frames

**Solution**:
1. Profile with `textual console` + logging
2. Check for blocking I/O in main thread
3. Move expensive work to `@work` workers
4. Use `call_from_thread` for state updates
5. Implement render coalescing for high-frequency updates

---

## Checklist

Before marking widget complete:

- [ ] Implementation matches spec requirements
- [ ] All reactive properties declared
- [ ] CSS styling applied
- [ ] Unit tests written (≥3 tests per widget)
- [ ] Snapshot tests created (2+ sizes)
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Constitution compliance verified
- [ ] Code reviewed
- [ ] Documentation updated

---

## Next Steps

After completing all 4 widgets:

1. **Integration Testing**: Test all widgets together in full TUI
2. **Performance Benchmarking**: Run 10-minute synthetic session
3. **User Acceptance Testing**: Get feedback from team
4. **Documentation**: Update README and quickstart guide
5. **Make Default**: Proceed to Phase 3 (reverse entry point logic)

---

**End of Quick Start Guide**
