# Claude Code-style Rich Status Display — Lyra TUI Implementation Plan

**Goal**: Add Claude Code-style status panel to Lyra TUI:
- Spinner line: `✶ Galloping… (32s · ↓ 20 tokens)`
- Task checklist below spinner: `⎿  ◻ Phase 9: ...`
- Sub-agent panel: `⏺ main / ◯ general-purpose  description  3m 4s · ↓ 63.6k tokens`
- Bottom bar: `⏵⏵ bypass permissions on · 5 background tasks · esc to interrupt`

**Execution order**: Tasks 1 → 2 → 3 → 4 → 5 (Tasks 2, 4, 5 can run in parallel after Task 1)

---

## Task 1 — Add `SubAgentRecord` to `status_source.py`

**File**: `src/lyra_cli/interactive/status_source.py`

Add `SubAgentRecord` dataclass and `sub_agents` list to `StatusSource`.

```python
@dataclass
class SubAgentRecord:
    agent_id: str
    role: str           # e.g. "general-purpose", "executor"
    description: str    # short task description
    started_at: float   # time.monotonic()
    tokens_down: int = 0
    state: str = "running"  # "running" | "done" | "error"
```

Add to `StatusSource`:
```python
sub_agents: list[SubAgentRecord] = field(default_factory=list)

def add_sub_agent(self, record: SubAgentRecord) -> None:
    self.sub_agents = [*self.sub_agents, record]

def update_sub_agent(self, agent_id: str, **kwargs) -> None:
    self.sub_agents = [
        SubAgentRecord(**{**vars(r), **kwargs}) if r.agent_id == agent_id else r
        for r in self.sub_agents
    ]

def remove_sub_agent(self, agent_id: str) -> None:
    self.sub_agents = [r for r in self.sub_agents if r.agent_id != agent_id]

def active_sub_agents(self) -> list[SubAgentRecord]:
    return [r for r in self.sub_agents if r.state == "running"]
```

**Tests**: `tests/test_status_source_tasks.py` — add tests for add/update/remove/active_sub_agents.

---

## Task 2 — New `task_list_renderer.py`

**File**: `src/lyra_cli/interactive/task_list_renderer.py` (new file)

Renders the task checklist in Claude Code style:

```
⎿  ◻ Phase 9: deep analysis
   ◻ Phase 10: synthesis
   ✓ Phase 8: research complete
```

```python
from lyra_cli.interactive.status_source import TaskItem

_ICON_PENDING  = "◻"
_ICON_RUNNING  = "◈"   # or spinner frame
_ICON_DONE     = "✓"

def render_task_checklist(tasks: list[TaskItem], max_items: int = 5) -> list[str]:
    """Return list of display lines, capped at max_items most-recent."""
    lines = []
    visible = tasks[-max_items:] if len(tasks) > max_items else tasks
    for i, t in enumerate(visible):
        prefix = "⎿  " if i == 0 else "   "
        icon = {
            "pending": _ICON_PENDING,
            "running": _ICON_RUNNING,
            "done":    _ICON_DONE,
        }.get(t.state, _ICON_PENDING)
        lines.append(f"{prefix}{icon} {t.description}")
    return lines
```

**Tests**: `tests/test_task_list_renderer.py`
- empty list → `[]`
- pending/running/done icons render correctly
- list capped at `max_items`
- first item gets `⎿  ` prefix, rest get `   `

---

## Task 3 — Extend Spinner with token count + checklist

**File**: `src/lyra_cli/interactive/spinner.py`

### 3a. Token count in spinner line

Modify `_animate()` to produce:
```
✶ Galloping… (32s · ↓ 20 tokens)
```

In `_build_line()` (or wherever the spinner text is assembled):
```python
elapsed = int(time.monotonic() - self._start_time)
toks = self._status_source.tokens_down_turn if self._status_source else 0
suffix = f"({elapsed}s · ↓ {toks} tokens)" if toks else f"({elapsed}s)"
line = f"{frame} {verb}… {suffix}"
```

### 3b. Emit checklist lines after spinner line

After printing the spinner line, print task checklist lines:
```python
from lyra_cli.interactive.task_list_renderer import render_task_checklist

if self._status_source and self._status_source.task_list:
    for row in render_task_checklist(self._status_source.task_list):
        self._print(row)
```

Where `_print` is the existing output mechanism (ANSI-safe via `_print_output`).

**Tests**: `tests/test_spinner_tokens.py`
- spinner line includes elapsed and token count
- token count 0 → omit `↓ 0 tokens`, show only `(Xs)`
- checklist lines emitted when task_list non-empty

---

## Task 4 — New `agent_panel.py`

**File**: `src/lyra_cli/interactive/agent_panel.py` (new file)

Renders sub-agent panel in Claude Code style:
```
⏺ main / ◯ general-purpose  running deep analysis  3m 4s · ↓ 63.6k tokens
```

```python
import time
from lyra_cli.interactive.status_source import SubAgentRecord

_ICON_ACTIVE  = "⏺"
_ICON_IDLE    = "◯"

def _fmt_elapsed(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    return f"{s // 60}m {s % 60}s"

def _fmt_tokens(n: int) -> str:
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)

def render_agent_panel(records: list[SubAgentRecord], now: float | None = None) -> list[str]:
    """Return one display line per active sub-agent."""
    if now is None:
        now = time.monotonic()
    lines = []
    for r in records:
        icon = _ICON_ACTIVE if r.state == "running" else _ICON_IDLE
        elapsed = _fmt_elapsed(now - r.started_at)
        toks = _fmt_tokens(r.tokens_down)
        desc = r.description[:40]  # truncate long descriptions
        line = f"{icon} main / {r.role}  {desc}  {elapsed} · ↓ {toks} tokens"
        lines.append(line)
    return lines
```

**Tests**: `tests/test_agent_panel.py`
- active agent → `⏺` icon
- done agent → `◯` icon
- elapsed formatting: <60s → "Xs", ≥60s → "Xm Ys"
- token formatting: <1000 → raw, ≥1000 → "X.Xk"
- long descriptions truncated at 40 chars
- multiple agents → multiple lines

---

## Task 5 — Extend `_bottom_toolbar` + wire into toolbar container

**File**: `src/lyra_cli/interactive/driver.py`

### 5a. Permission badge

```python
_PERM_BADGE = {
    "normal": "",
    "strict": "🔒 strict",
    "yolo":   "⏵⏵ bypass permissions on",
}
```

### 5b. Background task count

```python
bg = status.bg_task_count
bg_str = f" · {bg} background task{'s' if bg != 1 else ''}" if bg else ""
```

### 5c. Sub-agent panel lines

```python
from lyra_cli.interactive.agent_panel import render_agent_panel

agent_lines = render_agent_panel(status.active_sub_agents())
```

### 5d. Full toolbar assembly

Replace the current `_bottom_toolbar` return with:
```python
def _bottom_toolbar(session) -> list:
    from prompt_toolkit.formatted_text import HTML

    status = session.status_source
    perm = _PERM_BADGE.get(getattr(session, "permission_mode", "normal"), "")
    bg = status.bg_task_count
    bg_str = f" · {bg} background task{'s' if bg != 1 else ''}" if bg else ""
    interrupt = " · esc to interrupt" if status.bg_task_count else ""

    bar_parts = [p for p in [perm, bg_str.lstrip(" · "), interrupt.lstrip(" · ")] if p]
    bar_text = " · ".join(bar_parts)

    # Agent panel lines rendered as additional toolbar rows
    agent_lines = render_agent_panel(status.active_sub_agents())

    lines = []
    if agent_lines:
        lines.extend(agent_lines)
    if bar_text:
        lines.append(bar_text)

    return HTML("\n".join(lines)) if lines else HTML("")
```

**Tests**: `tests/test_tui_v2_status_bg_tasks.py`
- no bg tasks → no count in bar
- 1 bg task → "1 background task"
- 2+ bg tasks → "N background tasks"
- yolo mode → "⏵⏵ bypass permissions on" badge
- strict mode → "🔒 strict" badge
- normal mode → no badge

---

## Task 6 — Wire sub-agent tracking in `session.py`

**File**: `src/lyra_cli/interactive/session.py`

Add hooks around `run_agent()` (or wherever sub-agents are invoked) to call:
```python
record = SubAgentRecord(
    agent_id=str(uuid.uuid4()),
    role=agent_role,
    description=task_description[:60],
    started_at=time.monotonic(),
)
self.status_source.add_sub_agent(record)
try:
    result = await run_sub_agent(...)
    self.status_source.update_sub_agent(record.agent_id, state="done")
except Exception:
    self.status_source.update_sub_agent(record.agent_id, state="error")
    raise
```

---

## Task 7 — Wire `StatusSource` into `cli/tui.py` LyraTUI

**File**: `src/lyra_cli/cli/tui.py`

Ensure `LyraTUI` holds a single `StatusSource` instance and passes it to:
- `Spinner` constructor → already accepts `status_source`
- `InteractiveSession` constructor → `session.status_source = self.status_source`
- `_bottom_toolbar` lambda → reads from `session.status_source`

If `StatusSource` is already threaded through, verify the reference is shared (not copied).

---

## Acceptance Criteria

- [ ] Spinner line shows elapsed seconds and token count: `✶ Galloping… (32s · ↓ 20 tokens)`
- [ ] Task checklist appears below spinner when tasks exist
- [ ] Sub-agent panel shows per-agent row with role, description, elapsed, tokens
- [ ] Bottom bar shows permission mode badge when not "normal"
- [ ] Bottom bar shows background task count
- [ ] Bottom bar shows "esc to interrupt" when background tasks active
- [ ] All new unit tests pass
- [ ] `ruff check` clean, `pyright` no new errors

---

## File Change Summary

| File | Status | Description |
|------|--------|-------------|
| `src/lyra_cli/interactive/status_source.py` | Modify | Add `SubAgentRecord`, sub-agent API |
| `src/lyra_cli/interactive/task_list_renderer.py` | New | `render_task_checklist()` |
| `src/lyra_cli/interactive/agent_panel.py` | New | `render_agent_panel()` |
| `src/lyra_cli/interactive/spinner.py` | Modify | Token count in line, checklist emission |
| `src/lyra_cli/interactive/driver.py` | Modify | Permission badge, bg-task count, agent panel in toolbar |
| `src/lyra_cli/interactive/session.py` | Modify | Sub-agent tracking hooks |
| `src/lyra_cli/cli/tui.py` | Modify | Wire `StatusSource` through stack |
| `tests/test_status_source_tasks.py` | Modify | Add sub-agent tests |
| `tests/test_task_list_renderer.py` | New | Checklist renderer tests |
| `tests/test_agent_panel.py` | New | Agent panel tests |
| `tests/test_spinner_tokens.py` | New | Spinner token/checklist tests |
| `tests/test_tui_v2_status_bg_tasks.py` | New | Toolbar permission/bg-task tests |
