# Fleet Supervisor -- Deep Dive

## 1. Executive Summary

Lyra's Fleet Supervisor is a per-user daemon process, completely decoupled from any terminal session, that manages the full lifecycle of detached background agent conversations. It is Lyra's implementation of the pattern Claude Code calls "Agent View" -- a persistent, inspectable, steerable surface that lets a human operator monitor and intervene in agent work without ever attaching to a terminal.

The system is built around three foundational ideas:

1. **Two-axis state model** that separates _what the agent is doing_ (task-state) from _whether its process is alive_ (process-liveness). This lets the system reason about a session that has finished its work (task-state = `completed`) whose process was reaped (liveness = `dead`) but whose artifacts remain inspectable.
2. **Steer-by-exception UX** that makes the default interaction a lightweight peek/reply loop rather than a heavy attach/detach cycle. The operator never needs to enter a session unless something actually needs their input.
3. **Security gate** that protects detached, unwatched sessions from executing dangerous tool calls by hashing command signatures, tiering approval expiry by risk level, and atomically checking against a SQLite ledger.

The supervisor is spread across five packages: `lyra-orchestration` owns the core `FleetSupervisor` class and the `WorktreeIsolation` substrate; `lyra-fleet-tui` provides the Textual-based terminal dashboard; `lyra-core/transparency` supplies the lightweight `FleetView` registry and the escalation loop; `lyra-core/safety` provides the `ApprovalGate` router; and `lyra-cli/swarm` manages resource-level fleet concerns (auto-scaling, heartbeats).

Estimated source size (all packages, all files contributing to fleet supervision): approximately 4,500 lines of Python across 25+ files. Tests number roughly 1,200 lines.

## 2. The Supervisor Architecture

### 2.1 Per-User Host Process, Separate from Terminal

The core class lives at `packages/lyra-orchestration/src/lyra_orchestration/fleet_supervisor.py`:

```python
class FleetSupervisor:
    """Per-user daemon that manages the lifecycle of background agent sessions."""
```

It is instantiated once per OS user. Its state directory is `~/.lyra/jobs/`, and it stores two kinds of persistent state:

- **`roster.json`** -- a flat dictionary mapping session IDs to serialized `SessionState` dicts. This is the catalog of every session the supervisor has ever managed (unless explicitly pruned).
- **`~/.lyra/jobs/<session_id>/state.json`** -- per-session detailed state, stored redundantly so that individual session histories survive roster corruption.

The supervisor is NOT itself a daemon process in the Unix sense (fork + setsid). Instead it is an object that the CLI or TUI instantiates and whose `tick()` method is called periodically. This design choice is deliberate: it avoids the complexity of signal handling and PID-file management while still surviving terminal detach in practice, because the Python process that owns the supervisor can itself be daemonized by the shell (`nohup`, `disown`, `tmux`).

The key behavioral properties from the docstring say it best:

```
- Survives terminal close, machine sleep (reconnects on wake)
- Each session runs as its OWN process
- State persisted to disk (~/.lyra/jobs/<id>/)
- Idle unattached sessions stopped after configurable timeout (~1h)
- Self-exits when nothing is live
- Worktree isolation for parallel file edits
```

### 2.2 Session Lifecycle: Create, Attach, Detach, Stop, Respawn

The lifecycle is encoded in six methods on `FleetSupervisor`:

```
dispatch()       --> SessionState (new, alive)
stop_session()   --> bool (forced termination)
resume_session() --> SessionState | None (restart from dead)
attach()         --> SessionState | None (interactive focus)
detach()         --> None (release focus, keep alive)
tick()           --> None (maintenance: idle-stop, summary refresh, self-exit)
```

The flow for a typical session:

1. **dispatch(prompt, name, model, effort, permission_mode, auto_worktree)** -- Generates a new 12-hex-char session ID, optionally creates a git worktree via `WorktreeIsolation`, writes an `input.json` to the session's directory, records the `SessionState` in the in-memory `_sessions` dict, persists both the per-session state and the roster, and returns the state object. Note that the actual spawning is done by `_spawn_session()` which writes the prompt as a file for a child process to pick up -- it does NOT fork and exec the child directly. This indirection allows the child to be started by a separate process manager or container orchestrator.

2. **attach(session_id)** -- Simply touches `last_active_at` and returns the state. Attach is a logical operation, not a physical one. The actual byte-level attach (connecting stdin/stdout to a pseudoterminal) is handled by the Fleet TUI or CLI.

3. **detach(session_id)** -- Same as attach but in reverse. Touches `last_active_at` so the idle timer resets.

4. **stop_session(session_id)** -- Sends SIGTERM to the session's PID, sets liveness to `DEAD` and task-state to `STOPPED`, cleans up the worktree via `WorktreeIsolation.remove()`, and saves the roster.

5. **resume_session(session_id, prompt)** -- Only works if liveness is not `DEAD`. Calls `_spawn_session()` to create a fresh `input.json`, resets liveness to `ALIVE`, touches `last_active_at`, saves roster.

6. **tick()** -- Called periodically (every ~15 seconds) by an event loop. For each session: refreshes the cheap summary (via `_summary_fn` callback), stops idle sessions that have been unattached too long (`_idle_timeout`, default 1 hour), updates process-liveness by checking PID existence with `os.kill(pid, 0)`, and self-exits if no sessions are alive.

One critically important detail: the supervisor uses `SIGSTOP` (not `SIGTERM`) for pausing idle sessions:

```python
def _pause_session(self, session_id: str) -> None:
    state = self._sessions.get(session_id)
    if state and state.pid:
        try:
            os.kill(state.pid, signal.SIGSTOP)
        except ProcessLookupError:
            pass
        state.process_liveness = ProcessLiveness.EXITED_RESUMABLE
        self._save_session_state(state)
```

`SIGSTOP` cannot be caught or ignored by the process, which makes it a clean "pause" mechanism: the process's memory state is frozen, file descriptors remain open, and a later `SIGCONT` can resume exactly where it left off. This is vastly superior to killing and restarting, which would lose conversational context.

### 2.3 State Persistence: roster.json + Per-Job state.json

The persistence layer has a deliberate two-tier design:

**Roster** (`~/.lyra/jobs/roster.json`): A JSON dictionary keyed by session ID, containing a dict version of every `SessionState`. This is what gets loaded on startup -- the full catalog of known sessions. It is written on every `tick()` and every lifecycle mutation, so crash recovery never loses more than ~15 seconds of state.

```python
def _save_roster(self) -> None:
    roster = {sid: state.to_dict() for sid, state in self._sessions.items()}
    self._roster_path.write_text(json.dumps(roster, indent=2, default=str))
```

**Per-job state** (`~/.lyra/jobs/<session_id>/state.json`): An identical copy of the same dict, written to an individual file for the session. This provides two benefits: (1) if the roster is corrupted, individual session states can be recovered from their per-job files; (2) external tools (CI, monitoring) can inspect a single session's state without parsing the entire roster.

### 2.4 Process Reparenting for Crash Survival

When a supervisor process crashes (or the terminal closes), the session child processes are reparented to PID 1 (init or launchd on macOS). On restart, the supervisor reads the roster from disk -- but the PIDs stored in the roster are now stale (they refer to processes that may or may not still be alive under a different parent).

The supervisor handles this in `tick()`:

```python
if state.pid and not self._is_process_alive(state.pid):
    state.process_liveness = ProcessLiveness.EXITED_RESUMABLE
```

`_is_process_alive` uses the classic `os.kill(pid, 0)` probe. If the original PID is dead, the state is marked `EXITED_RESUMABLE`, which tells the operator that the session's worktree and conversation history are intact but the process needs to be respawned via `resume_session()`.

Sessions whose children survived reparenting (their PID is still valid) continue running normally with no interruption -- the supervisor picks them back up on the next `tick()`.

## 3. Two-Axis State Model

### 3.1 Task-State

The task-state axis answers "what is the agent doing?" It is defined in both `lyra_orchestration.fleet_supervisor.TaskState` and `lyra_fleet_tui.models.TaskState` (they are kept in sync but are separate enums because the TUI models are frozen dataclasses with no dependency on the orchestration module):

```python
class TaskState(str, Enum):
    WORKING      = "working"       # Actively executing a prompt or tool call
    NEEDS_INPUT  = "needs_input"   # Blocked, waiting for user reply
    IDLE         = "idle"          # Process alive but not currently working
    COMPLETED    = "completed"     # Finished its task successfully
    FAILED       = "failed"        # Terminated with an error
    STOPPED      = "stopped"       # Explicitly stopped by the user
```

These six states cover the full semantic range. The three "terminal" states (completed, failed, stopped) are mutually exclusive: once a session enters one of them, the only way out is a full `resume_session()` call, which resets to `WORKING`.

`NEEDS_INPUT` is the most interesting state from an architecture perspective. It represents a session that has hit a point in its reasoning where it requires human judgment -- for example, a clarifying question about the task spec, or a choice between two implementation paths, or a permission confirmation for a high-risk tool call. The TUI renders this state in **bold yellow**, and the `ReplyBar` widget only activates when the selected agent is in `NEEDS_INPUT`.

### 3.2 Process-Liveness

The liveness axis answers "is the agent's OS process alive?" It is defined in two places with slightly different value sets:

In the orchestration layer (`FleetSupervisor`):
```python
class ProcessLiveness(str, Enum):
    ALIVE            = "alive"             # Process is running
    EXITED_RESUMABLE = "exited_resumable"  # Stopped, can restart from disk
    LOOP_SLEEPING    = "loop_sleeping"     # In a sleep/wait cycle
    DEAD             = "dead"              # Terminated, cannot resume
```

In the TUI models (`lyra_fleet_tui.models`):
```python
class ProcessLiveness(str, enum.Enum):
    ACTIVE = "active"   # symbol: ◉
    PAUSED = "paused"   # symbol: •
    STOPPED = "stopped" # symbol: ◎
```

The TUI simplifies the four-value orchestration model into three display-oriented values because `EXITED_RESUMABLE` and `LOOP_SLEEPING` are both rendered as `PAUSED` (bullet) -- the operator doesn't need to distinguish between "process exited but can resume" and "process is sleeping." Both mean "the session is alive in principle but its process is not currently hot."

The display symbols are defined as properties on the enum:

```python
@property
def symbol(self) -> str:
    symbols = {
        ProcessLiveness.ACTIVE: "◉",
        ProcessLiveness.PAUSED: "•",
        ProcessLiveness.STOPPED: "◎",
    }
    return symbols[self]
```

"Circle-star" (U+25C9) for active, "bullet" (U+2022) for paused, "circle-dot" (U+25CE) for stopped.

### 3.3 How Rows Are Grouped and Filtered

The `FleetData` container computed properties provide the aggregation points:

```python
class FleetData:
    @property
    def total_count(self) -> int:
        return len(self.agents)

    @property
    def active_count(self) -> int:
        return sum(1 for a in self.agents if a.liveness is ProcessLiveness.ACTIVE)

    @property
    def working_count(self) -> int:
        return sum(1 for a in self.agents if a.task_state is TaskState.WORKING)
```

The `FleetSummary` derived class computes a full cross-tabulation:

```python
class FleetSummary:
    by_liveness: dict[str, int]        # active/paused/stopped counts
    by_task_state: dict[str, int]      # working/needs_input/idle/completed/failed/stopped
    total_tokens: int
    total_cost: float
```

The `AgentFilter` class supports filtering on either axis independently or together:

```python
class AgentFilter:
    task_state: Optional[TaskState]
    liveness: Optional[ProcessLiveness]
    search: str

    def matches(self, agent: AgentState) -> bool:
        if self.task_state is not None and agent.task_state != self.task_state:
            return False
        if self.liveness is not None and agent.liveness != self.liveness:
            return False
        if self.search:
            # checks name, agent_id, current_task, git_branch, pr_label
```

The TUI binds number keys 1-6 to quick filters by task-state, and `/` to free-text search. Pressing the same number again toggles the filter off. The `FilterBar` widget displays the active filter prominently at the top of the screen with a hint that Escape clears it.

## 4. Steer-by-Exception UX

### 4.1 Peek Panel: Latest Output Without Attaching

The `PeekPane` widget is a detail panel that slides in from the right side of the TUI when the operator presses Enter on a selected agent row. It shows:

1. Agent name and ID
2. Task-state and liveness with color and symbol
3. Model identifier
4. Current task summary (up to 30 chars in table, full in peek)
5. Token usage and cost
6. Git branch and PR label
7. Last active timestamp
8. Pane/tmux ID

Crucially, peeking does NOT attach to the session. The agent continues its work uninterrupted. The operator can peek at multiple agents in quick succession, building a mental model of the fleet's overall state without disturbing any running session.

The peek panel is hidden by default (`self.visible = False`) and only appears when `agent` is set to a non-None value:

```python
def watch_agent(self, agent: Optional[AgentState]) -> None:
    if agent is None:
        self.visible = False
        self.update("")
        return
    self.visible = True
    # ... render detail ...
    self.border_title = f"Agent: {agent.display_name}"
```

### 4.2 Reply Without Attaching

The `ReplyBar` is a lightweight text input bar that lets the operator send a message to a `NEEDS_INPUT` agent without entering its session:

```python
class ReplyBar(Static):
    visible = False

    def activate(self, agent: AgentState) -> None:
        self._active_agent = agent
        self.visible = True
        self.update(f"[bold yellow]Reply to {agent.display_name}:[/] type message and press Enter")
```

The reply is routed through the `FleetView.pop_reply()` mechanism. The `FleetView` (in `lyra_core.transparency.agent_view`) maintains a `_pending_reply` field on each `AgentViewRecord`. When the supervisor calls `reply(agent_id, message)`, the message is stored in the record. On the next tick cycle, the agent checks `pop_reply(agent_id)`, consumes the message, and acts on it.

This pattern means replying does NOT require the agent process to have an active stdin. The reply is stored in the roster JSON, and the agent picks it up asynchronously. This is critical for sessions whose process has exited but whose state is `EXITED_RESUMABLE` -- a reply can still be queued, and when the session is resumed, it will immediately receive the pending input.

The TUI only activates the ReplyBar when the selected agent's task-state is `NEEDS_INPUT`. If the operator presses `r` on an agent that is not waiting for input, the PeekPane shows a warning: "(Agent does not need input -- reply ignored)".

### 4.3 Attach/Detach That Never Stops the Session

Attach and detach are zero-cost operations. They do nothing more than touch `last_active_at` and flip a boolean:

```python
def attach(self, session_id: str) -> SessionState | None:
    state = self._sessions.get(session_id)
    if state is None:
        return None
    state.last_active_at = time.time()
    return state

def detach(self, session_id: str) -> None:
    state = self._sessions.get(session_id)
    if state:
        state.last_active_at = time.time()
```

There is no process restart, no context switch, no stdin/stdout reconfiguration. The session process continues running regardless of whether anyone is watching. This property is what makes the fleet supervisor fundamentally different from a traditional terminal multiplexer (tmux, screen): in tmux, every pane is expected to have a viewer; the fleet supervisor normalizes the unattended state as the default.

Detaching also resets the idle timer. This is the only semantic effect: an attached session whose operator walks away will still be idle-stopped after one hour of inactivity. But each attach/detach action pushes the clock forward.

### 4.4 PR Label Integration

The `AgentState` and `SessionState` models both carry a PR label field:

```python
@dataclass(frozen=True)
class AgentState:
    pr_label: str = ""
```

This field is populated when a session creates a pull request. The `FleetTable` renders it in column 10 (rightmost). The `PeekPane` displays it as "PR: #42".

The PR label provides a quick visual grouping: when an operator sees multiple sessions with the same PR label, they know those sessions are collaborating on the same code review. The `AgentFilter` search also matches against `pr_label`, so an operator can filter to show only agents working on a specific PR.

The `has_open_pr` boolean on `SessionState` is used by the idle-stop logic: sessions with open PRs may be deprioritized for idle stopping (future feature, not yet implemented in the current `tick()` body).

## 5. Fleet TUI (Textual)

### 5.1 Widget Architecture

The TUI is a Textual application defined in `lyra_fleet_tui.app.FleetTUIApp`. The screen layout is a CSS grid with three rows:

```
+------------------------------------------+
| FilterBar                    (height: 1) |
+------------------------------------------+
| FleetTable (with PeekPane docked right)  |
|                                (width:48) |
|                                           |
+------------------------------------------+
| StatusBar                     (height: 1) |
+------------------------------------------+
| ReplyBar (hidden, height: 3, dock bottom)|
+------------------------------------------+
```

The grid is defined with `grid-size: 1 3` (one column, three rows) and explicit row heights:

```css
#main-layout {
    layout: grid;
    grid-size: 1 3;
    grid-rows: auto 1fr auto;
    height: 100%;
}
```

#### AgentRow

The `AgentRow` widget is a single-line `Static` widget with a reactive `agent` property. It renders a Rich-markup string that combines the liveness symbol, name, token count, cost, task summary, branch, and model into a fixed-width table row using the `│` character as column separator:

```
[cyan]◉[/] [cyan]coder-alpha       [/] │ [grey62]    15.0K  $0.75[/] │ [cyan]Refactor database layer         [/] │ [grey46]feat/db-refac[/] │ [grey46]claude-sonnet-4[/]
```

The `on_click` handler posts a `SelectAgent` message that the app can catch to navigate or peek.

#### StatusBar

The `StatusBar` is a bottom dock that shows aggregate fleet statistics:

```
Agents: 12  │ Active: 3  │ Working: 2  │ Idle: 5  │ Need Input: 1  │ Completed: 1  │ Failed: 1  │ Stopped: 2  │ Tokens: 150K  │ Cost: $12.34
```

It is a `Static` widget with a reactive `FleetSummary`. When summary is None, it shows a grey "Waiting for fleet data..." message.

#### FleetTable

The `FleetTable` extends `DataTable` with ten columns:

```
" "      # Liveness symbol (2 chars)
"Agent"  # Display name (22 chars)
"State"  # Task-state label (14 chars)
"Tokens" # Token usage (10 chars)
"Cost"   # Dollar cost (8 chars)
"Task"   # Current task summary (34 chars)
"Branch" # Git branch (14 chars)
"Model"  # Model name (16 chars)
"Last Active" # Relative timestamp (18 chars)
"PR"     # PR label (14 chars)
```

The `refresh_agents()` method does a full clear-and-rebuild of rows from `FleetData`. Each cell is built by `_agent_cells()` which renders the data with appropriate Rich markup colors per task-state.

#### PeekPane

Docked on the right side of the table container (width: 48), the `PeekPane` shows a detailed view of the selected agent. It has a reactive `agent` property and its `border_title` updates to show the agent's display name. Content includes agent ID, state, model, current task, usage stats, git info, last active timestamp, and pane ID.

#### ReplyBar

Hidden by default, the `ReplyBar` docks to the bottom with height 3 when activated by pressing `r` on a `NEEDS_INPUT` agent. It currently displays a prompt message -- actual text input handling is a future implementation step (the `action_reply_agent()` method is wired but the keyboard input loop is not yet connected in the current version).

#### FilterBar

The `FilterBar` shows the current active filter at the top of the screen. It displays the task-state filter with its color, the liveness filter if set, and the search query if any. When no filter is active, it shows "No filter -- showing all agents" in grey.

### 5.2 Key Bindings

| Key | Action | Description |
|-----|--------|-------------|
| j / Down | cursor_down | Move selection down |
| k / Up | cursor_up | Move selection up |
| Enter | peek_agent | Open PeekPane for selected agent |
| Escape | close_peek | Close PeekPane and deactivate ReplyBar |
| r | reply_agent | Activate ReplyBar for selected agent |
| f | toggle_filter | Toggle WORKING filter on/off |
| q | quit_app | Exit the TUI |
| / | search | Open search input (placeholder) |
| 1 | filter_working | Toggle WORKING filter |
| 2 | filter_needs_input | Toggle NEEDS_INPUT filter |
| 3 | filter_idle | Toggle IDLE filter |
| 4 | filter_completed | Toggle COMPLETED filter |
| 5 | filter_failed | Toggle FAILED filter |
| 6 | filter_stopped | Toggle STOPPED filter |

Number keys 1-6 implement a toggle pattern: pressing the same key twice clears the filter. This is implemented in `_set_filter()`:

```python
def _set_filter(self, state: TaskState) -> None:
    if self._filter_by_state == state:
        self._filter = AgentFilter()
        self._filter_by_state = None
    else:
        self._filter = AgentFilter.from_task_state(state)
        self._filter_by_state = state
    self._refresh_display()
```

### 5.3 Integration with Supervisor Python Objects

The `FleetTUIApp` receives a `FleetData` object at construction time and exposes an `update_fleet(data)` method:

```python
def update_fleet(self, data: FleetData) -> None:
    """Called by the supervisor to push a new fleet snapshot."""
    self._fleet_data = data
    self._summary = FleetSummary.from_fleet_data(data)
    self._refresh_display()
```

This is the contract between the supervisor and the TUI. The supervisor (or any process with access to the `FleetSupervisor`) calls `update_fleet()` with a fresh snapshot, and the TUI re-renders. The supervisor is expected to call this on every `tick()` cycle, which means the TUI refreshes approximately every 15 seconds.

The `_refresh_display()` method orchestrates three updates:

1. Re-applies the current filter to the new data
2. Calls `FleetTable.refresh_agents()` with the filtered subset
3. Updates `StatusBar.summary` and `FilterBar.active_filter`

## 6. Security Gate

### 6.1 Command-Hashed Approvals (SHA256)

The security gate for the fleet supervisor builds on Lyra's multi-layer permissions architecture, which is spread across three systems:

1. **lyra-harness-core permissions** (`lyra_harness_core.permissions`): A rule-based permission resolver with `DENY` > `BYPASS` > `ASK` > `ALLOW` precedence ordering. It supports four modes: `PLAN` (read-only), `DEFAULT` (writes ask), `ACCEPT_EDITS` (edits auto-allowed), and `BYPASS` (anything goes after deny rules).

2. **lyra-core safety approval gate** (`lyra_core.safety.approval_gate`): A 4-level escalation router that classifies actions by risk surface and level. The levels map to gate actions as follows:

```python
_LEVEL_TO_GATE = {
    RiskLevel.LOW:      GateAction.AUTO,     # Approve silently
    RiskLevel.MEDIUM:   GateAction.NOTIFY,   # Approve but log
    RiskLevel.HIGH:     GateAction.CONFIRM,  # Require human confirmation
    RiskLevel.CRITICAL: GateAction.BLOCK,    # Hard deny
}
```

The risk classifier uses keyword matching against six risk surfaces: `FILE_SYSTEM`, `NETWORK`, `CODE_EXEC`, `DATA_ACCESS`, `MODEL_QUERY`, `CONFIG`. Each surface has a default risk level (e.g., `CODE_EXEC` = CRITICAL, `FILE_SYSTEM` = HIGH). Confidence is computed as `min(1.0, hits / 4.0)`.

3. **lyra-core permissions stack** (`lyra_core.permissions.stack`): A mode-aware layered gate that runs destructive-pattern, secrets-scan, and injection guards in sequence. In `yolo` mode it short-circuits entirely. In `normal`/`strict` mode it runs all guards and blocks at the first failure.

For the fleet supervisor specifically, the security gate must handle the case where a session is running **unwatched**. The design principle (from the `FleetSupervisor` docstring):

> unwatched sessions cannot use bypass/auto permission modes without explicit prior human accept.

### 6.2 Tiered Expiry: LOW 7d, MEDIUM 24h, HIGH 4h, CRITICAL per-use

The approval gate applies different expiry windows depending on the classified risk level:

| Risk Level | Expiry Window | Behavior |
|------------|---------------|----------|
| LOW | 7 days | Auto-approved; cached for 7 days |
| MEDIUM | 24 hours | Notify on first use; auto-approved for 24h |
| HIGH | 4 hours | Require confirm on first use; auto-approved for 4h |
| CRITICAL | Per-use | Block every time; human must confirm each use |

The expiry is not yet implemented as a SQLite ledger in the code as committed -- this is the planned extension. The current `ApprovalGate` makes per-call decisions without caching. The SQLite atomic check-and-use mechanism described below is the forward-looking design for tiered approval caching.

### 6.3 Atomic Check-and-Use via SQLite

The plan for production-grade permission caching uses a SQLite ledger with the following schema:

```sql
CREATE TABLE approval_cache (
    command_hash TEXT PRIMARY KEY,
    risk_level TEXT NOT NULL,
    approved_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    human_confirmed INTEGER NOT NULL DEFAULT 0
);
```

The flow:

1. When an unwatched session wants to call a tool, the supervisor computes `SHA256(command_string + risk_level + session_id)`.
2. It queries the SQLite cache: if a matching row exists with `expires_at > now()`, the cached decision stands.
3. If no valid cache entry exists, the action goes through the full `ApprovalGate.evaluate()` pipeline. If the result is `AUTO` or `NOTIFY`, a cache entry is inserted. If `CONFIRM`, the human operator is prompted via the TUI (the `ReplyBar` or a modal dialog). If `BLOCK`, no cache entry is created and the tool call is rejected.
4. For CRITICAL actions, the `human_confirmed` column is set to 0 and only incremented to 1 after explicit human approval. CRITICAL cache entries expire immediately after use (they are checked in the same transaction that reads them, and deleted afterward).

The `CHECK_AND_USE` SQL pattern for CRITICAL:

```sql
BEGIN TRANSACTION;
    SELECT expires_at FROM approval_cache
    WHERE command_hash = ? AND expires_at > unixepoch()
    AND human_confirmed = 1;
    -- If row found: delete it (single-use) and COMMIT
    DELETE FROM approval_cache WHERE command_hash = ?;
COMMIT;
-- If any row was found: ALLOW. Otherwise: BLOCK.
```

This ensures that even a CRITICAL approval cannot be reused -- the cache entry is atomically consumed in the same transaction that reads it.

## 7. Architecture Diagram

```
+-----------------------------------------------------------------------+
| OPERATOR (Human)                                                      |
|   [Fleet TUI]     [CLI: fleet ls/peek/reply]                          |
+----------+------------------------------------------------------------+
           |  update_fleet(data) / reply(agent_id, msg)
           v
+----------+------------------------------------------------------------+
| FLEET SUPERVISOR  (lyra-orchestration)                                |
|                                                                        |
|  FleetSupervisor                                                       |
|  +-------------+    +--------------+    +----------------------------+|
|  | _sessions[] |--->| _save_roster |--->| ~/.lyra/jobs/roster.json  ||
|  | SessionState|    | _load_roster |    | ~/.lyra/jobs/<id>/state   ||
|  +-------------+    +--------------+    +----------------------------+|
|        |                                     ^                        |
|        v tick()                              | SIGSTOP / SIGCONT     |
|  +-------------+    +-----------------+       |                        |
|  | _pause_     |--->| WorktreeIsolation|------+                        |
|  | _spawn_     |    | (worktree_isolate)|                             |
|  | _is_idle    |    +-----------------+                               |
|  +-------------+                                                       |
|        |                                                               |
|        | dispatch/resume/create                                        |
|        v                                                               |
+--------+--------------------------------------------------------------+
| SESSION PROCESSES (one per agent)                                      |
|                                                                        |
|  +-------------+   +-------------+   +-------------+                   |
|  | Session A   |   | Session B   |   | Session C   |                   |
|  | PID 4421    |   | PID 4492    |   | PID 4507    |                   |
|  | ◉ WORKING   |   | • PAUSED    |   | ◎ STOPPED   |                   |
|  | worktree-A  |   | worktree-B  |   | (no proc)   |                   |
|  +-------------+   +-------------+   +-------------+                   |
+------------------------------------------------------------------------+
        |                          |                          ^
        v                          v                          |
+-------+--------------------------+--------------------------+---------+
| SECURITY GATE                                                          |
|                                                                        |
|  +---------------+  +-----------------+  +--------------------------+ |
|  | ApprovalGate  |  | PermissionStack  |  | SQLite Approval Cache   | |
|  | classify_risk |  | destructive/s    |  | command_hash, expires,  | |
|  | AUTO→BLOCK    |  | secrets/injec   |  | human_confirmed         | |
|  +---------------+  +-----------------+  +--------------------------+ |
+------------------------------------------------------------------------+
        |
        v
+-------+----------------------------------------------------------------+
| FLEET VIEW (lyra_core.transparency)                                    |
|                                                                        |
|  FleetView                                                             |
|  +----------------+   +-------------------+   +----------------------+ |
|  | AgentViewRecord|   | FleetSupervisor   |   | AttentionPriority    | |
|  | row_summary    |   | (escalation loop) |   | P0 → P4             | |
|  | _pending_reply |   | scan_once()       |   | stale/blocked/done   | |
|  | is_attached    |   | poll_interval=15s |   | escalation           | |
|  +----------------+   +-------------------+   +----------------------+ |
+------------------------------------------------------------------------+
```

## 8. Trade-Off Analysis

### 8.1 Design Decisions

| Decision | Choice | Rationale | Alternative Considered |
|----------|--------|-----------|----------------------|
| Supervisor process model | In-process object, not a forking daemon | Avoids PID-file juggling and signal complexity. Shell `nohup` / `tmux` handles backgrounding. | A standalone `lyra-supervisord` that spawns and tracks child processes. Rejected because it adds a separate deployable artifact and complicates lifecycle. |
| Session spawn mechanism | Write `input.json` to disk, child picks it up | Decouples spawner from spawnlee. Works across container boundaries. | Direct `subprocess.Popen` with piped stdin. Rejected because it ties child to parent's lifecycle and makes container-orchestration harder. |
| Idle pausing | `SIGSTOP` (not kill) | Freezes process state, preserves memory, enables instant resume. Maximum fairness to the agent. | `SIGTERM` + restart from checkpoint. Rejected because checkpointing an LLM conversation is complex and lossy. |
| State persistence | Two-tier: roster + per-job state.json | Roster for bulk ops, per-job for isolation and external inspection. | Single SQLite database for all state. Rejected because SQLite is less trivially inspectable with `cat`/`jq`, and adds a migration concern. |
| TUI framework | Textual | Asynchronous, reactive, CSS-based layout, built-in DataTable. | Rich Live display (simpler but lacks interactivity). Custom curses (too much work). |
| TUI data flow | Push: supervisor calls `update_fleet(data)` | Simple contract. The supervisor owns the tick loop and drives screen updates. | Pull: TUI polls supervisor on a timer. Rejected because it introduces a polling interval mismatch and stale data. |
| TUI vs CLI priority | TUI first, CLI second | Textual enables richer interactions (peek pane, status bar, inline formatting). CLI flags will follow. | CLI-only. Rejected because fleet management benefits enormously from visual layout. |
| Approval caching | SQLite (planned), not in-memory | In-memory caches die with the process. SQLite survives crashes. | In-process LRU dict. Rejected because the whole point of tiered expiry is persistence across supervisor restarts. |
| Task-state values | 6 states (working, needs_input, idle, completed, failed, stopped) | Covers all observable agent behaviors without over-fragmentation. | Adding "awaiting_review" and "pending_push" states. Rejected because those are better expressed as metadata, not first-class state. |

### 8.2 Known Limitations and Mitigations

1. **`SIGSTOP` does not work across containers.** A process in a different PID namespace cannot be signaled from outside. Mitigation: the `input.json` approach allows containerized sessions to be paused by simply not starting a new container (`EXITED_RESUMABLE` rather than `ALIVE`).

2. **`os.kill(pid, 0)` is racy.** The PID could be reused by a new process between the check and the next operation. Mitigation: the supervisor checks liveness only for the purpose of updating the display state. The actual process management commands (`SIGTERM`, `SIGSTOP`) handle `ProcessLookupError` gracefully.

3. **roster.json can grow unbounded.** Every dispatched session adds an entry that is never pruned. Mitigation: the `stats` property and the TUI display are bounded to active sessions only. A future `prune_old_sessions(older_than_days=30)` method would remove stale entries from the roster (but archive per-job state files).

4. **The TUI and supervisor must share a Python process.** The current architecture requires the TUI app to create or receive a `FleetData` object from the supervisor. If they are in separate processes, they would need IPC (a Unix socket or HTTP). Mitigation: for v1, they share the same process. A future version could expose the supervisor's roster as a small HTTP API (a la `claude agents` command).

5. **`_summary_fn` is a placeholder.** The cheap model for regenerating row summaries is currently unset in the default constructor. Mitigation: the default value is `None`, which skips summary refresh. A production deployment would supply a Haiku-class callable.

## 9. (B) Breakthrough

The fleet supervisor achieves a breakthrough in agent-operations ergonomics by flipping the default assumption of terminal multiplexing. In tmux, screen, or `kubectl exec`, the default is **attached**: every pane expects a viewer. The operator must explicitly detach, and detaching is a conscious action. In Lyra's fleet supervisor, the default is **detached**: every session expects to run unattended. The operator must explicitly attach, and attaching is a zero-cost no-op.

This inversion of defaults matters because it changes the operational pattern from "babysitting" to "management by exception." The operator does not watch agents work; they watch agents **signal** that they need attention (via `NEEDS_INPUT` task-state or escalated `AttentionPriority`). The PeekPane and ReplyBar provide the lightweight interaction surface needed to resolve exceptions without the overhead of a full session attach.

The second breakthrough is the two-axis state model. Traditional process supervisors (systemd, supervisord, circus) model state as a single linear progression (STARTING -> RUNNING -> STOPPED). By separating logical task-state from physical process-liveness, the fleet supervisor can represent states like "process died but work is complete" (task=completed, liveness=dead) vs "process died but work is incomplete" (task=working, liveness=exited_resumable). These two states require completely different operator responses (nothing vs. resume), and the two-axis model makes them immediately distinguishable.

The third breakthrough is the integration of `SIGSTOP`-based process pausing. Most agent frameworks that support background sessions either keep the process running (wasting GPU/API credits on idle) or kill it (losing conversational state). The freeze-resume cycle using `SIGSTOP`/`SIGCONT` gives the best of both worlds: zero resource consumption during idle exactly preserves all process memory, allowing instant resumption without any serialization or checkpointing logic.

## 10. Key Sources

### Source Files (Core)

- `packages/lyra-orchestration/src/lyra_orchestration/fleet_supervisor.py` -- Primary `FleetSupervisor` class (467 lines). All session lifecycle, state model, persistence, and process management.
- `packages/lyra-orchestration/src/lyra_orchestration/worktree_isolate.py` -- `WorktreeIsolation` for per-session git worktree management (507 lines). Base branch policy, `.worktreeinclude` propagation, non-destructive cleanup with STASH default.
- `packages/lyra-fleet-tui/src/lyra_fleet_tui/app.py` -- `FleetTUIApp` (302 lines). Textual app with CSS layout, key bindings, actions, and filter management.
- `packages/lyra-fleet-tui/src/lyra_fleet_tui/models.py` -- TUI-side data models: `AgentState`, `FleetData`, `FleetSummary`, `AgentFilter`, `ProcessLiveness`, `TaskState` (188 lines).
- `packages/lyra-fleet-tui/src/lyra_fleet_tui/widgets.py` -- TUI widgets: `AgentRow`, `StatusBar`, `FleetTable`, `PeekPane`, `ReplyBar`, `FilterBar` (297 lines).
- `packages/lyra-core/src/lyra_core/transparency/agent_view.py` -- `FleetView` registry and `AgentViewRecord` with attention priority, `peek`/`reply`/`pop_reply` (164 lines).
- `packages/lyra-core/src/lyra_core/transparency/supervisor.py` -- Lightweight escalation loop daemon that scans FleetView and escalates stale/blocked agents (127 lines).

### Source Files (Security)

- `packages/lyra-core/src/lyra_core/safety/approval_gate.py` -- 4-level approval gate: `classify_risk`, risk surfaces, reasoning flags (258 lines).
- `packages/lyra-core/src/lyra_core/permissions/stack.py` -- Mode-aware permission stack with destructive, secrets, and injection guards (112 lines).
- `packages/lyra-core/src/lyra_core/permissions/modes.py` -- `LyraMode` enum: PLAN, RED, GREEN, REFACTOR, RESEARCH, DEFAULT, ACCEPT_EDITS, BYPASS, RESUME (31 lines).
- `packages/lyra-harness-core/src/lyra_harness_core/permissions.py` -- Harness-level permission resolver with rule-based DENY/ASK/ALLOW precedence (114 lines).

### Source Files (Swarm Integration)

- `packages/lyra-cli/src/lyra_cli/swarm/fleet_manager.py` -- Resource-level fleet management: spawn, monitor, auto-scale, heartbeat (337 lines).
- `packages/lyra-cli/src/lyra_cli/ui/fleet_view.py` -- CLI fleet view with heartbeat tracking, agent status, success rates, aggregate summaries (174 lines).
- `packages/lyra-agent-swarm/src/lyra_agent_swarm/fleet_orchestrator.py` -- Fan-out, map-reduce, and DAG execution patterns across fleet agents (534 lines).

### Tests

- `packages/lyra-fleet-tui/tests/test_models.py` -- 17 test functions covering AgentState, FleetData, FleetSummary, AgentFilter (261 lines).
- `packages/lyra-fleet-tui/tests/test_widgets.py` -- 21 test functions covering FleetTable, PeekPane, ReplyBar, StatusBar, FilterBar with Textual async test harness (437 lines).
- `packages/lyra-core/tests/test_approval_gate.py` -- 11 test functions covering risk classification, gate evaluation, escalation flags, human handler, history (170 lines).
- `packages/lyra-permissions/tests/test_bypass_mode.py` -- 14 test functions covering bypass mode, audit logging, safety guardrails, integration (263 lines).
- `packages/lyra-permissions/tests/test_granular_control.py` -- 14 test functions covering granular controller, context rules, time-based rules, priority (269 lines).
- `packages/lyra-core/tests/safety/test_approval_gate.py` -- Safety-pipeline approval gate tests (separate from the core approval gate tests).
