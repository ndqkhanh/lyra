# Implementation Plan: Claude-Code-Parity TUI for Lyra

**Feature**: 001-tui-claude-code-parity
**Status**: Draft → in review
**Owner**: Khanh
**Created**: 2026-05-17

---

## Constitution Check

This plan is constrained by the Lyra TUI Constitution v1.0.0. Compliance
per principle is recorded below; deviations appear in the Complexity
Tracking section.

| Principle | Compliance |
|---|---|
| I. Truth Over Aesthetics | All counters source from `SessionState`. Spinner runs only while worker count > 0. |
| II. Non-Blocking by Default | LLM streaming and tool subprocesses run in `@work(thread=True)` workers; cancellation propagation tested in `tests/tui/test_cancellation.py`. |
| III. Progressive Disclosure | `Collapsible` and a custom `ToolOutputPanel` collapse all panels > 5 lines by default; `Ctrl+O` expands. |
| IV. Streaming as a First-Class Citizen | `Markdown.get_stream()` for assistant turns, `RichLog.write()` for tool stdout, `DataTable` row append for sub-agent rows. |
| V. Keyboard-First | Every action has a `BINDINGS` entry; Footer renders the active set. |
| VI. Single Source of Truth | `SessionState` is the only mutable store; widgets `watch_*` reactives. |
| VII. Observability Over Opacity | Structured logging via `structlog`; rotating file at `~/.lyra/logs/tui.log`; mirror to `textual console` when `LYRA_DEBUG=1`. |

**No deviations required for the MVP.** Any future relaxation will be
recorded in §8 Complexity Tracking.

---

## 1. Technical Context

- **Language / runtime**: Python 3.12 (TaskGroup, `typing.Self`).
- **UI framework**: Textual ≥ 0.86 (MarkdownStream, modern Worker API).
- **Render engine**: Rich ≥ 13.7 (incremental syntax highlighting).
- **CLI host**: Lyra's existing `src/lyra_cli/cli/` entrypoint already
  wires Click/argparse; this plan adds a `--tui` flag that boots the
  Textual app instead of the headless run loop.
- **Async model**: Textual's event loop + Workers. Tool subprocesses
  use `asyncio.create_subprocess_exec`. Long CPU-bound work (none
  expected in the TUI itself) would use thread-mode workers.
- **State store**: a single `SessionState` object (Textual reactive
  dataclass) owned by the root `App`.
- **Inter-process glue with the agent loop**: the agent loop already
  emits structured events on a `asyncio.Queue[AgentEvent]`. The TUI
  subscribes via a single consumer worker that fans events out to the
  appropriate `watch_*` reactives.
- **Persistence**: `~/.lyra/logs/` for logs, `~/.lyra/state/session-*.json`
  for crash-recovery snapshots (write-on-every-N-events, debounced).

## 2. Project Structure

```
src/lyra_cli/
├── tui/
│   ├── __init__.py
│   ├── app.py                       # LyraApp(App): the root
│   ├── state.py                     # SessionState (reactive dataclass)
│   ├── events.py                    # AgentEvent typed union
│   ├── bus.py                       # consumer worker: queue → state
│   ├── theme.py                     # palette + high-contrast variant
│   ├── screens/
│   │   ├── main.py                  # the primary screen
│   │   ├── model_picker.py          # ModelSelectorModal(ModalScreen)
│   │   ├── command_palette.py       # custom Provider for slash cmds
│   │   ├── background_switcher.py   # Ctrl+T modal
│   │   └── traceback_modal.py       # error detail viewer
│   ├── widgets/
│   │   ├── welcome_card.py          # WelcomeCard(Widget)
│   │   ├── status_line.py           # StatusLine(Widget) (animated verb)
│   │   ├── sub_agent_tree.py        # SubAgentTree(Tree[SubAgentState])
│   │   ├── tool_output_panel.py     # ToolOutputPanel(Collapsible-like)
│   │   ├── compaction_banner.py     # CompactionBanner(Widget)
│   │   ├── todo_panel.py            # TodoPanel(Widget)
│   │   ├── context_row.py           # ContextRow(Widget)
│   │   ├── prompt_input.py          # PromptInput(Input + suggester)
│   │   └── footer_bar.py            # FooterBar(Widget) bypass-mode pill
│   ├── styles/
│   │   ├── app.tcss
│   │   ├── welcome.tcss
│   │   └── ...
│   └── verbs.py                     # the curated verb list
└── ...
tests/
└── tui/
    ├── snapshots/                   # pytest-textual-snapshot baselines
    ├── test_welcome.py
    ├── test_status_line.py
    ├── test_sub_agent_tree.py
    ├── test_tool_output_panel.py
    ├── test_model_picker.py
    ├── test_slash_palette.py
    ├── test_compaction.py
    ├── test_background_switcher.py
    ├── test_todo_panel.py
    ├── test_footer.py
    ├── test_cancellation.py         # Esc → Worker.cancel within 200 ms
    └── test_resize.py               # narrow & wide reflow
specs/001-tui-claude-code-parity/
├── spec.md
├── plan.md                          # this file
├── research.md                      # phase 0 — see §3
├── data-model.md                    # phase 1
├── contracts/
│   └── agent-events.md              # the AgentEvent union spec
├── quickstart.md
└── tasks.md                         # produced by /speckit.tasks
```

## 3. Phase 0 — Research

This is a single-file research note; the heavy decisions are recorded
inline below.

### R1. Why Textual (not prompt_toolkit, urwid, Rich-only)
Textual is the only mainstream Python TUI framework with: (a) a modern
reactive model, (b) first-class async/worker support, (c) a built-in
command palette, (d) CSS-style layout, and (e) snapshot testing
infrastructure (`pytest-textual-snapshot`). Prompt_toolkit's strength
is single-line editing, not full-screen reactive UIs. Urwid is mature
but has no streaming-markdown widget, no built-in command palette, and
no test harness. Rich alone is not interactive.

### R2. How to make Sub-Agent Tree update in place without flicker
Textual's `Tree` widget supports `node.set_label()` and `node.refresh()`
without re-rendering the whole tree. We bind each `SubAgentState` to a
`TreeNode` via `node.data = sub_agent_state`. On a `SubAgentUpdated`
event we mutate the dataclass and call `node.refresh()`. Render
coalescing at the tree level (max ~30 fps) prevents jitter when many
agents update at once.

### R3. Streaming markdown without buffering
`Markdown.get_stream()` returns a `MarkdownStream` that batches appends.
The bus worker calls `stream.write(chunk)` for each token batch. For
runs > 20 chunks/second the stream auto-coalesces; our coalescing
budget is 50 ms (≈ 20 fps).

### R4. Slash commands: command palette vs. custom suggester
Textual's command palette (`Ctrl+P`) is for app-level commands.
Slash commands (`/model`) are *prompt-prefix* commands that the user
types directly. We implement them as a Textual `Suggester` on the
`PromptInput`, which produces an inline dropdown when the input starts
with `/`. This matches Claude Code's behavior. The command palette
remains available via `Ctrl+P` for non-slash actions (Change theme,
Open logs, etc.).

### R5. The verb list and animation
A 50-word verb list lives in `verbs.py`. The `StatusLine` widget uses
a Textual `Timer` ticking at 250 ms; on each tick it advances an
index into the verb list and re-renders. Token-delta and elapsed are
sourced from `SessionState.active_worker_stats` (computed property).

### R6. Cancellation semantics
On `Esc`, `LyraApp.action_interrupt()` calls
`self.workers.cancel_group("agent")`. Each worker catches
`asyncio.CancelledError`, posts a `WorkerCancelled` event to the bus,
and exits. The 200 ms requirement is enforced by a test that asserts
elapsed time between Esc and `WorkerState.CANCELLED`.

### R7. Background tasks
A foreground worker is registered with `group="foreground"`. On
`Ctrl+B` we re-tag the worker by removing it from the foreground
group, adding it to `group="background"`, and inserting a
`BackgroundTask` row into `SessionState`. The Footer's
`background_count` reactive watches `SessionState.background_tasks`.

### R8. Snapshot testing
`pytest-textual-snapshot` captures SVG snapshots of any pilot-driven
session. We commit baseline SVGs under `tests/tui/snapshots/`; CI fails
on diff. For non-deterministic content (timers, verb animation), we
freeze the clock in tests via `App._test_clock` and use a fixed seed
for verb-index advancement.

## 4. Phase 1 — Data Model & Contracts

### 4.1 SessionState (data-model.md will hold full schema)

```python
# src/lyra_cli/tui/state.py (excerpt)
from dataclasses import dataclass, field
from textual.reactive import reactive
from typing import Literal

PermissionMode = Literal["read_only", "ask", "bypass"]

@dataclass(slots=True)
class SubAgentState:
    id: str
    name: str
    label: str
    task_summary: str
    status: Literal["pending", "running", "done", "failed"]
    tool_uses: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    started_at: float = 0.0
    last_log_line: str = ""
    expanded: bool = False
    error: str | None = None

@dataclass(slots=True)
class BackgroundTask:
    id: str
    label: str
    worker_id: str
    started_at: float
    last_token_delta: int
    status: Literal["running", "done", "failed", "cancelled"]

@dataclass(slots=True)
class TodoItem:
    id: str
    label: str
    status: Literal["pending", "done", "blocked"]

@dataclass(slots=True)
class CompactionEvent:
    triggered_at: float
    restored: list[tuple[Literal["read", "loaded", "skill"], str, int | None]]

class SessionState:
    """Owned by LyraApp; widgets subscribe via reactives."""
    model: reactive[str] = reactive("claude-sonnet-4-6")
    permission_mode: reactive[PermissionMode] = reactive("ask")
    cwd: reactive[str] = reactive("")
    sub_agents: reactive[dict[str, SubAgentState]] = reactive({}, always_update=True)
    background_tasks: reactive[dict[str, BackgroundTask]] = reactive({}, always_update=True)
    todos: reactive[list[TodoItem]] = reactive([], always_update=True)
    compaction_history: reactive[list[CompactionEvent]] = reactive([], always_update=True)
    active_worker_count: reactive[int] = reactive(0)
    last_token_delta: reactive[int] = reactive(0)
    elapsed_seconds: reactive[float] = reactive(0.0)
```

### 4.2 AgentEvent contract (contracts/agent-events.md)

```python
# Tagged union — the agent loop and TUI both depend on this.
from typing import Literal, TypedDict

class _Base(TypedDict):
    ts: float           # unix seconds, monotonic
    session_id: str

class TokenDelta(_Base):
    kind: Literal["token_delta"]
    delta_in: int
    delta_out: int

class ThoughtUpdate(_Base):
    kind: Literal["thought_update"]
    summary: str

class SubAgentSpawned(_Base):
    kind: Literal["sub_agent_spawned"]
    sub_agent_id: str
    name: str            # e.g. "oh-my-claudecode:executor"
    label: str           # short task summary

class SubAgentProgress(_Base):
    kind: Literal["sub_agent_progress"]
    sub_agent_id: str
    tool_uses: int
    tokens_in: int
    tokens_out: int
    last_log_line: str

class SubAgentDone(_Base):
    kind: Literal["sub_agent_done"]
    sub_agent_id: str
    success: bool
    error: str | None

class ToolCallStart(_Base):
    kind: Literal["tool_call_start"]
    call_id: str
    tool_name: str
    args_preview: str

class ToolCallChunk(_Base):
    kind: Literal["tool_call_chunk"]
    call_id: str
    chunk: str
    is_stderr: bool

class ToolCallEnd(_Base):
    kind: Literal["tool_call_end"]
    call_id: str
    success: bool
    error: str | None

class CompactionStart(_Base):
    kind: Literal["compaction_start"]

class CompactionRestored(_Base):
    kind: Literal["compaction_restored"]
    items: list[tuple[Literal["read", "loaded", "skill"], str, int | None]]

class TodoUpdate(_Base):
    kind: Literal["todo_update"]
    items: list[dict]  # serialized TodoItem

class ModelChanged(_Base):
    kind: Literal["model_changed"]
    new_model: str

class PermissionModeChanged(_Base):
    kind: Literal["permission_mode_changed"]
    mode: Literal["read_only", "ask", "bypass"]

AgentEvent = (
    TokenDelta | ThoughtUpdate | SubAgentSpawned | SubAgentProgress
    | SubAgentDone | ToolCallStart | ToolCallChunk | ToolCallEnd
    | CompactionStart | CompactionRestored | TodoUpdate
    | ModelChanged | PermissionModeChanged
)
```

The bus worker (`bus.py`) consumes this queue and dispatches each event
type to a `_handle_<kind>` method that mutates `SessionState`.

## 5. Phase 1 — Quickstart

```bash
# Setup
uv sync                 # installs textual, rich, pytest-textual-snapshot
uv run lyra --tui       # boots LyraApp; falls back to headless without --tui

# Dev console (in a second terminal)
uv run textual console

# Run tests
uv run pytest tests/tui/ -q
uv run pytest tests/tui/ --snapshot-update     # regen baselines on intent
```

## 6. Phase 1 — Screens & Widgets (specifications)

### 6.1 Welcome Card (`widgets/welcome_card.py`)
- Layout: 2-column `Grid` (mascot/title left, tips/news right) above
  80 cols; stacks vertically below.
- Reactives: `model`, `cwd`, `account`. On change, re-render only the
  affected sub-Static.
- Collapse: on first `Input.Submitted` from `PromptInput`, the widget
  removes its `expanded` class and reduces to a single `Static` line.
- Truncation: paths truncated mid-string (`/home/.../lyra`) using
  Rich's `Text.truncate`.

### 6.2 Status Line (`widgets/status_line.py`)
- Internal `Timer` at 250 ms advances `_verb_index`.
- `compose()` yields one `Static` with markup.
- `render()` returns
  `f"{glyph} {verb}… ({elapsed_human} · ↓ {tokens_human} tokens · {thought})"`.
- Reactives watched: `active_worker_count` (hide when 0),
  `last_token_delta`, `elapsed_seconds`, `current_thought`.
- Stalled-state hint: if `elapsed_since_last_token > 30`, append
  `(no tokens for 30s — Esc to interrupt)`.

### 6.3 Sub-Agent Tree (`widgets/sub_agent_tree.py`)
- Subclass `Tree[SubAgentState]`.
- Root: `Running {len(running)} {name_summary} agents…`.
- On `SubAgentSpawned`: `root.add(label, data=state)`.
- On `SubAgentProgress`: locate node by `data.id`, mutate, `node.refresh()`.
- On `SubAgentDone`: mutate `status`, prepend `⎿ Done` or `⎿ Failed`.
- Bindings: `Ctrl+O` expands the focused node's inline `last_log_line`
  preview (uses `node.add_leaf(state.last_log_line)`).
- Bindings: `Ctrl+B` posts `BackgroundRequested(sub_agent_id=...)`.

### 6.4 Tool Output Panel (`widgets/tool_output_panel.py`)
- Subclass `Collapsible` with custom `_title` showing
  `[icon] [tool_name] (ctrl+o to expand)` / `(ctrl+o to collapse)`.
- Body: a `RichLog` with `highlight=True`, `markup=True`,
  `auto_scroll=True`.
- Bindings: `ctrl+o` toggles `collapsed`.
- On error: header turns red; body shows truncated stack trace; full
  trace accessible via `traceback_modal`.

### 6.5 Slash-Command Picker (`widgets/prompt_input.py`)
- Subclass `Input`; attach a custom `Suggester` that only activates
  when `value.startswith("/")` AND cursor is at end.
- Use `textual-autocomplete` library OR implement a tiny dropdown via
  `OptionList` overlaying the input. The library is preferred for
  fewer custom code paths.
- On `Enter` with a `/cmd` selected, dispatch `SlashCommandInvoked(cmd)`
  which the main screen routes to the registered handler.

### 6.6 Model Selector Modal (`screens/model_picker.py`)
- Subclass `ModalScreen[str | None]`.
- Composes a `Vertical` with: a title, a `ListView` of models, a
  `RadioSet` for effort, and `Footer`-style instructions.
- Bindings: `up`/`down` move selection, `left`/`right` cycle effort,
  `enter` dismiss with model id, `escape` dismiss with `None`.
- Result piped to `LyraApp.action_apply_model(result)`.

### 6.7 Compaction Banner (`widgets/compaction_banner.py`)
- A `Static` + nested `RichLog`.
- Rendered when `compaction_history[-1].triggered_at` changes within
  the last 30 s, then collapses to a one-line summary that opens a
  side pane on `Ctrl+O`.

### 6.8 Background Switcher (`screens/background_switcher.py`)
- Modal `ListView` over `SessionState.background_tasks.values()`.
- `Enter` brings the selected task to the foreground (re-tag its
  worker group) and pops the modal.

### 6.9 To-Do Panel (`widgets/todo_panel.py`)
- A `Vertical` of `Static` rows showing 5 at a time + overflow.
- Glyphs from a lookup dict (no if/else chains): `{"pending": "◻",
  "done": "◼", "blocked": "⚠"}`.
- Animation on transition: 1-frame `tcss` class added then removed
  300 ms later.

### 6.10 Footer (`widgets/footer_bar.py`)
- Three sections, `Horizontal`:
  - left: bypass-mode pill (`⏵⏵ bypass permissions on`)
  - middle: `N shells · N background tasks` (computed from state)
  - right: active bindings (sourced from the focused widget)

## 7. Testing Strategy

- **Snapshot tests** for every widget at default and resized widths.
  Stable verbs and timestamps via `App._test_clock` and a deterministic
  verb seed.
- **Pilot interaction tests**: `await pilot.press("ctrl+o")` etc.
- **Bus integration test**: feed a recorded `AgentEvent` stream from a
  JSONL fixture into the bus worker; assert resulting `SessionState`.
- **Cancellation timing test**: assert `Esc` → `Worker.state == CANCELLED`
  within 200 ms.
- **Resize test**: `pilot.app.console.size = (40, 24)` then snapshot.
- **Worker error test**: a worker raises; assert a `Toast` is shown and
  the app does not crash.

## 8. Complexity Tracking

| Item | Why simple alternative fails | Decision |
|---|---|---|
| Custom suggester for slash commands instead of the built-in command palette | Slash commands are *prompt-prefix* commands typed inline; the command palette opens a separate modal which breaks the typing flow. | Custom suggester. |
| Tree widget for sub-agents instead of a flat list | The agent hierarchy is a real tree (orchestrator → executors). Future deeper nesting becomes free. | Tree. |
| `pytest-textual-snapshot` baselines committed to git | Visual regressions are otherwise invisible until a user reports them. | Commit baselines; review SVG diffs in PRs. |

No constitution deviations needed.

## 9. Roll-out Plan

1. Land scaffolding (state, bus, root app shell) behind `--tui` flag.
2. Ship widgets in the order Welcome → Status Line → Sub-Agent Tree →
   Tool Output Panel → Slash Picker → Model Picker → Compaction →
   Background Switcher → To-Do → Footer.
3. After all snapshot tests pass and one user-study session with Khanh,
   promote `--tui` to the default and add `--no-tui` as the escape
   hatch.
4. Tag `v0.x.0` and write a one-page CHANGELOG section listing every
   key binding.

---

*End of plan. Tasks are produced by `/speckit.tasks` and live in
`tasks.md`.*
