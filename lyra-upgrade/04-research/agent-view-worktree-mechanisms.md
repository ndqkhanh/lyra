# Claude Code Agent View & Worktree Mechanisms -- Exact Transferable Design for Lyra

**Research date**: 2026-06-01
**Sources**: Claude Code official documentation (code.claude.com/docs/en/)
**Pages consulted**: agent-view, worktrees, settings, hooks, tools-reference, cli-reference, scheduled-tasks

---

## PART 1: FLEET / SUPERVISOR LAYER

### 1.1 Supervisor Lifecycle

**Start**: Automatic on first use of any background feature (`--bg`, `claude agents`, `/bg` from session). No explicit user command to start the supervisor.

**Process model**: Per-user singleton process. Separate from any terminal. Separate from agent-view TUI. Spawned as a daemon.

**Authentication**: Uses same credentials as interactive sessions. No additional network connections beyond the model API.

**Self-update**: Supervisor watches the installed Claude Code binary on disk via local file watch (not network poll). After auto-updater replaces the binary, supervisor restarts into the new version. Background sessions are detached processes, so they survive the restart; the new supervisor reconnects to them. Idle pinned sessions also get restarted in-place onto the new version.

**Self-exit algorithm**:
```
if (no_live_sessions AND no_terminal_connected):
    supervisor.exit()
```
Starts again next time any background feature is used.

**Recovery from sleep**: Sessions preserved across machine sleep. Processes resume on wake. Supervisor reconnects rather than treating time gap as idle. Shutdown (not sleep) stops sessions; they show as "Failed" on next agent-view open, but attach/peek/reply restarts them from disk.

### 1.2 State Storage

| Path | Contents |
|------|----------|
| `~/.claude/daemon.log` | Supervisor log |
| `~/.claude/daemon/roster.json` | List of running background sessions, used for reconnect after restart |
| `~/.claude/jobs/<id>/state.json` | Per-session state shown in agent view |

If `CLAUDE_CONFIG_DIR` env var is set, supervisor uses that directory instead of `~/.claude` and runs as a separate instance with its own sessions.

**Diagnostics**: `claude daemon status` -- prints supervisor reachability, PID, version, socket directory, worker count. Exits 1 if supervisor not running.

### 1.3 Process Hosting -- "One Process Per Session"

```
┌─────────────────────────────────────────┐
│         Supervisor (per-user daemon)      │
│  watches binary, manages lifecycle        │
│  stores: ~/.claude/daemon/roster.json     │
│  stores: ~/.claude/jobs/<id>/state.json   │
├─────────────────────────────────────────┤
│  Session 1 (own process)   pid=12345     │
│  Session 2 (own process)   pid=12346     │
│  Session 3 (own process)   pid=12347     │
│  ...                                     │
└─────────────────────────────────────────┘
```

Each background session is its own Claude Code process. Not a thread. Not a goroutine. A full OS process.

**What keeps a process alive**:
- Actively working (tool calls, generation)
- Waiting for user input
- Terminal attached
- Running background shell command, subagent, dynamic workflow, or monitor

**What triggers process stop**:
- Idle + unattached for ~1 hour (unless pinned)
- Memory pressure (idle non-pinned first, then idle pinned)
- Explicit `claude stop <id>` or Ctrl+X in agent view

**Process state is disk-persisted**: Transcript and state survive process stop. Next attach/peek/reply spawns a fresh process that resumes from on-disk state.

### 1.4 Idle-Stop Algorithm

```
FOR each session:
    IF session.state == IDLE
       AND session.terminal_attached == FALSE
       AND session.pinned == FALSE
       AND idle_duration > ~1 hour:
        supervisor.stop_process(session)
        # transcript and state remain on disk
```

On next action (peek/reply/attach): supervisor starts fresh process from on-disk state. This takes a moment (the "slow to respond after attaching" symptom).

**Pinned exemption**: Ctrl+T pinned sessions keep their process running indefinitely, even while idle.

### 1.5 Memory-Pressure Shedding

```
ALGORITHM: idle-then-pinned-first
1. Find all idle, non-pinned sessions
2. Stop their processes
3. IF no memory freed:
4.     Find all idle, pinned sessions
5.     Stop their processes
```

Active/working sessions are never stopped by memory pressure.

### 1.6 State Model -- TWO Orthogonal Axes

This is the critical design insight. State is NOT a single enum. It is the cross-product of two independent dimensions.

**Axis 1: Task-state** (WHAT the session is doing -- displayed as icon COLOR/ANIMATION)

| Task-state   | Visual      | Meaning |
|-------------|-------------|---------|
| Working     | Animated    | Actively running tools or generating response |
| Needs-input | Yellow      | Waiting on question or permission decision |
| Idle        | Dimmed      | Nothing to do, ready for next prompt |
| Completed   | Green       | Task finished successfully |
| Failed      | Red         | Task ended with error |
| Stopped     | Grey        | Stopped via Ctrl+X or `claude stop` |

**Axis 2: Process-liveness** (WHETHER the process is running -- displayed as icon SHAPE)

| Liveness         | Shape              | Meaning |
|-----------------|--------------------|---------|
| Alive           | `✻` or animated `✽` | Process running, replies immediately |
| Exited-resumable| `∙`                 | Process exited, resumes from disk on next action |
| Loop-sleeping   | `✢`                 | `/loop` session sleeping between iterations, shows run count + countdown |

**Combining axes**: Every session row has exactly ONE task-state AND exactly ONE process-liveness. The icon displayed is the combination (e.g., yellow `✻` = Needs-input + alive, green `∙` = Completed + exited).

### 1.7 Grouping Logic

**Default grouping: by state**

Group order (top to bottom):
1. **Pinned** -- sessions pinned with Ctrl+T (always at top, regardless of other state)
2. **Ready for review** -- sessions with an open PR (NOT a task-state; this is a separate category)
3. **Needs input** -- everything waiting on user
4. **Working** -- active sessions
5. **Completed** -- finished, failed, AND stopped sessions folded together

**Fold behavior**: Older completed sessions collapse into `… N more` row. Failures and open-PR sessions always stay visible (never folded).

**Alternate grouping**: Ctrl+S switches to directory-based grouping. Preference persists across agent-view sessions.

**Group collapse**: Enter on a group header collapses/expands it.

### 1.8 Visibility Rules

- **Shown**: Background sessions (started via --bg, /bg, or agent-view dispatch)
- **NOT shown**: Interactive sessions in other terminals (until backgrounded)
- **NOT shown**: Subagents spawned by a session
- **NOT shown**: Teammates in agent teams
- **Always shown**: Failed sessions, sessions with open PRs

### 1.9 Filter System

| Filter | Matches |
|--------|---------|
| `a:<name>` | Sessions running named agent/subagent |
| `s:<state>` | Sessions in given task-state. Also `s:blocked` for everything waiting on user |
| `#<number>` or PR URL | Session working on that pull request |

### 1.10 Row Summaries -- The "Haiku Summarizer" Pattern

**Model**: Haiku-class (smallest/fastest model)

**Refresh cadence**:
- At most once every 15 seconds while actively working
- Once when each turn ends

**Billing**: Each refresh = one short Haiku-class request through normal provider. Billed under same data usage terms as the session.

**Content**: One-line summary of current activity, what the session needs, or what it produced. Replaces the need to open transcripts for status checks.

**PR labels**: Shown at right edge of row with color coding:
- Yellow: waiting on checks/review, or checks failed
- Green: checks passed, no review blocking
- Purple: merged
- Grey: draft or closed
- Multiple PRs: shows count like `3 PRs`, colored by the open PR that most needs attention

### 1.11 Steer-by-Exception Interaction Model

The core UX principle: users should NOT need to constantly watch sessions. They intervene only when a session signals it needs them.

**Peek panel** (Space key):
- Shows most recent output OR the question it is waiting on
- Shows any open PRs
- Does NOT show full transcript
- Reply inline without leaving agent view
- MC questions: press number key to select
- Tab: fill input with suggested reply (editable before sending)
- `!`-prefix: send bash command as reply
- Up/Down arrows: browse adjacent sessions without closing panel

**Attach** (Enter or Right arrow):
- Full interactive session takes over terminal
- Shows recap of what happened while away
- All commands/shortcuts work normally
- Left arrow on empty prompt: detach back to agent view
- Ctrl+Z: force-detach (when dialog has focus)
- Double Ctrl+C on empty prompt: detach
- /exit: detach (leaves session running)
- /stop: end session entirely

**Detach never stops** the session. Detaching always leaves it running.

### 1.12 Dispatch Mechanisms

| Method | Command | Notes |
|--------|---------|-------|
| Agent-view input | Type prompt + Enter | New session per prompt (not follow-up) |
| Shell | `claude --bg "<prompt>"` | Prints session ID + management commands |
| Shell | `claude --bg --exec '<cmd>'` | Shell job, no model invoked |
| Shell | `claude --agent <name> --bg "<prompt>"` | Run specific subagent as main agent |
| In-session | `/bg` or `/background` | Backgrounds current session |
| In-session | `/bg <prompt>` | Gives one more instruction, then backgrounds |
| In-session | Left arrow on empty prompt | Backgrounds + opens agent view |
| Agent-view | `! <cmd>` prefix | Shell job as row |
| Agent-view | `<agent-name> <prompt>` | First word matches subagent name → dispatches that subagent |
| Agent-view | `@<agent-name>` | Mention subagent anywhere in prompt |
| Agent-view | `@<repo>` | Target sibling repository under parent directory |
| Agent-view | Shift+Enter | Dispatch + attach immediately |

**Rejection**: Prompts shorter than 4 characters are rejected with "Too short" hint.

### 1.13 Per-Session Configuration Overrides

**Permission mode inheritance**:
- `/bg` or Left-arrow from session: keeps current permission mode
- Agent-view dispatch: uses `defaultMode` from directory settings, OR `permissionMode` from subagent frontmatter
- `claude --bg`: uses `defaultMode` unless `--permission-mode` passed
- Mode persists across supervisor stop/restart cycles (a session launched with bypassPermissions stays in bypassPermissions after restart)

**Agent-view dispatch defaults** (v2.1.142+):
```
claude agents --permission-mode plan --model opus --effort high --agent code-reviewer
```

**Per-session model override**:
- `--model` flag at launch
- `/model` picker + `s` key during attached session (persists across respawn)

**Quota**: Each session consumes subscription quota independently. Running N agents in parallel uses quota ~N times as fast.

### 1.14 Security Gate

**Dangerous-mode gate**:
- `bypassPermissions` or `auto` mode REFUSED until user has accepted that mode interactively at least once
- Applies to both `claude agents --permission-mode bypassPermissions` and `claude --bg --permission-mode bypassPermissions`
- `--allow-dangerously-skip-permissions`: adds bypassPermissions to Shift+Tab cycle WITHOUT starting in it (v2.1.143+)

**Disable agent view entirely**:
- Setting: `disableAgentView: true`
- Env var: `CLAUDE_CODE_DISABLE_AGENT_VIEW=1`
- Administrators enforce via managed settings

### 1.15 Shell Commands Reference

| Command | Purpose |
|---------|---------|
| `claude agents` | Open agent view TUI |
| `claude agents --cwd <path>` | Scoped to sessions under path (v2.1.141+) |
| `claude agents --json` | JSON array output (pid, cwd, kind, startedAt, sessionId, name, status) |
| `claude attach <id>` | Attach terminal to session |
| `claude logs <id>` | Print recent output |
| `claude stop <id>` / `claude kill <id>` | Stop session |
| `claude respawn <id>` | Restart with conversation intact |
| `claude respawn --all` | Restart all running sessions |
| `claude rm <id>` | Remove from list (keeps transcript, keeps dirty worktree) |
| `claude daemon status` | Supervisor diagnostics |

### 1.16 Configuration Flags Passed Through to Dispatched Sessions

When opening `claude agents` with these flags, they apply to agent-view itself AND every session dispatched from it (v2.1.142+):

| Flag | Effect |
|------|--------|
| `--settings <file-or-json>` | Override settings |
| `--add-dir <path>` | Additional directory access |
| `--plugin-dir <path>` | Load plugin |
| `--mcp-config <file-or-json>` | MCP servers |
| `--strict-mcp-config` | Only --mcp-config servers |

Repeat per value. Space-separated multi-value form NOT supported with `claude agents`.

### 1.17 Background Session Isolation -- File Edits

Every background session starts in the working directory. Before editing files, Claude moves the session into an isolated git worktree under `.claude/worktrees/`.

**Skip conditions** (Claude writes directly to working copy instead):
1. Session is already inside a linked git worktree (Claude-created or manual)
2. Working directory is not a git repo AND no `WorktreeCreate` hook configured
3. Write target is outside the working directory

**Opt-out**: `worktree.bgIsolation: "none"` (v2.1.143+) -- bg sessions edit working copy directly.

**Non-git VCS**: Configure `WorktreeCreate` hook; Claude then isolates edits same way as for git.

**Deletion behavior**:
- Agent-view Ctrl+X twice: removes Claude-created worktree INCLUDING uncommitted changes
- `claude rm <id>`: keeps worktree with uncommitted changes, prints path
- Manually-created worktrees always left in place

---

## PART 2: ISOLATION / WORKTREES

### 2.1 Worktree Creation Flow

**CLI invocation**:
```bash
claude --worktree feature-auth    # creates .claude/worktrees/feature-auth/ on branch worktree-feature-auth
claude -w bugfix-123               # shorthand
claude --worktree                  # auto-generated name like "bright-running-fox"
claude -w "#1234"                  # fetch PR from origin, create .claude/worktrees/pr-1234/
```

**Step-by-step algorithm** (default git path):
```
1. User runs: claude --worktree <name>
2. IF workspace-trust NOT yet accepted:
      ERROR: "run claude in this directory first"
      EXIT
3. IF WorktreeCreate hook configured:
      invoke hook (see §2.7)
      SKIP git worktree creation
4. ELSE (default git path):
      resolve baseRef:
          IF worktree.baseRef == "head": use local HEAD
          ELSE (default "fresh"): use origin/HEAD
          IF origin fetch fails: fallback to local HEAD
      IF name starts with "#" or is PR URL:
          fetch pull/<number>/head from origin
          create worktree at .claude/worktrees/pr-<number>/
      ELSE:
          git worktree add .claude/worktrees/<name>/ -b worktree-<name> <baseRef>
5. IF .worktreeinclude exists:
      copy matched+gitignored files into new worktree
6. Start Claude session in worktree directory
```

### 2.2 Auto-Generated Names

When `--worktree` is called without a name, Claude generates one. Example format from docs: `bright-running-fox` (adjective-adjective-animal triplet pattern).

### 2.3 EnterWorktree Tool -- Agent Self-Isolation

**Tool: EnterWorktree** (no permission required)

Parameters:
- `name` (optional string): Name for a NEW worktree. Creates `.claude/worktrees/<name>/`. Mutually exclusive with `path`.
- `path` (optional string): Path to an EXISTING worktree. Switches into it. Must appear in `git worktree list`.

**Behavior**:
- Agent isolates ITSELF by calling this tool
- Calling with `name`: creates new worktree, switches session's CWD into it
- Calling with `path`: switches into existing worktree, previous one stays on disk untouched
- From within a worktree session or `isolation: worktree` subagent: only `path` form available, target must be under `.claude/worktrees/`

**Use case**: Agent decides mid-session "I should do this in isolation" and calls EnterWorktree. Previous working directory is tracked so ExitWorktree can return to it.

### 2.4 ExitWorktree Tool

**Tool: ExitWorktree** (no permission required)

Parameters:
- `action` (required): `"keep"` or `"remove"`
  - `"keep"`: leave worktree directory and branch on disk
  - `"remove"`: delete worktree directory and its branch
- `discard_changes` (optional boolean, default false): Required to be `true` when `action: "remove"` and worktree has uncommitted files or unmerged commits. Tool REFUSES to remove otherwise.

**Behavior**:
- Restores session CWD to original directory (where it was before EnterWorktree)
- If `action: "remove"` with dirty worktree and `discard_changes: false`: returns error listing changes
- Not available to subagents already in `isolation: worktree` (they have their own lifecycle)

### 2.5 Base-Branch Configuration

**Setting**: `worktree.baseRef`

| Value | Behavior |
|-------|----------|
| `"fresh"` (default) | Branch from `origin/HEAD` (clean, matches remote). Falls back to local HEAD if no remote or fetch fails. |
| `"head"` | Branch from current local HEAD (carries unpushed commits and feature-branch state). Useful for subagents operating on in-progress work. |

Only accepts `"fresh"` or `"head"`, NOT arbitrary git refs.

**PR worktrees**: `claude -w "#1234"` fetches `pull/<number>/head` from origin, creates worktree at `.claude/worktrees/pr-<number>/`.

**Applies to**: `--worktree` CLI flag, `EnterWorktree` tool, subagent isolation.

### 2.6 .worktreeinclude -- Copy Gitignored Files

**File**: `.worktreeinclude` at project root

**Syntax**: `.gitignore` syntax (same patterns)

**Algorithm**:
```
FOR each new worktree:
    IF .worktreeinclude exists at project root:
        FOR each pattern in .worktreeinclude:
            find files matching pattern
            FOR each matched file:
                IF file is also gitignored:
                    copy file into worktree at same relative path
                ELSE (tracked file):
                    SKIP (never duplicate tracked files)
```

**Example**:
```
# .worktreeinclude
.env
.env.local
config/secrets.json
```

Copies `.env`, `.env.local`, and `config/secrets.json` into each new worktree -- but ONLY if they are gitignored.

**Applies to**: `--worktree`, subagent worktrees, desktop app parallel sessions.

**NOT processed when**: `WorktreeCreate` hook is used. The hook replaces the entire creation flow; copy files inside the hook script instead.

### 2.7 WorktreeCreate Hook

**Trigger**: Worktree creation via `--worktree` or `isolation: worktree`

**Matcher**: None. Always fires on every occurrence.

**Exit code behavior** (UNIQUE among hooks):
- ANY non-zero exit code = worktree creation FAILS
- Most other hooks only block on exit code 2; WorktreeCreate blocks on any non-zero

**Decision control pattern: "path return"**:
- **Command hooks**: Print absolute path to stdout. Claude Code reads as plain text.
- **HTTP hooks**: Return `hookSpecificOutput.worktreePath` in JSON response body.
- Missing path or hook failure: worktree creation fails entirely.

**Input** (via stdin JSON):
```json
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "...",
  "hook_event_name": "WorktreeCreate",
  "name": "feature-auth"
}
```

**Example -- SVN**:
```json
{
  "hooks": {
    "WorktreeCreate": [{
      "hooks": [{
        "type": "command",
        "command": "bash -c 'NAME=$(jq -r .name); DIR=\"$HOME/.claude/worktrees/$NAME\"; svn checkout https://svn.example.com/repo/trunk \"$DIR\" >&2 && echo \"$DIR\"'"
      }]
    }]
  }
}
```

Key: `jq -r .name` reads the worktree name from stdin JSON. Script prints the created directory path to stdout. Stderr used for logging (not read by Claude Code).

### 2.8 WorktreeRemove Hook

**Trigger**: Worktree removal at session exit or subagent finish.

**Matcher**: None. Always fires.

**Exit code**: Failures logged in debug mode ONLY. NO blocking capability. Fire-and-forget observability hook.

**Decision control**: NONE. Side effects only (logging, cleanup, notifications).

**Input** (via stdin JSON): Includes `worktree_path` and removal reason.

**Example**:
```bash
#!/bin/bash
WORKTREE_PATH=$(jq -r '.worktree_path')
rm -rf "/tmp/build-cache-${WORKTREE_PATH##*/}"
echo "Cleaned up build cache for $WORKTREE_PATH" >> /tmp/claude-worktree-cleanup.log
exit 0
```

### 2.9 Cleanup Behavior -- Full Decision Tree

```
ON WORKTREE SESSION EXIT:

IF session was non-interactive (-p flag):
    DO NOTHING (no cleanup prompt available)
    User must manually: git worktree remove <path>

ELSE IF no uncommitted changes AND no untracked files AND no new commits:
    IF session has a name (via --name or /rename):
        PROMPT: keep or remove? (named = user might want to return)
    ELSE:
        AUTO-REMOVE worktree directory + branch

ELSE (dirty: uncommitted/untracked/new commits):
    PROMPT: keep or remove?
    IF user chooses "remove":
        DELETE worktree directory + branch
        SILENTLY DISCARDS all uncommitted changes, untracked files, local commits
        THIS IS A FOOTGUN -- no recovery possible
    ELSE:
        KEEP directory + branch intact for later return
```

**cleanupPeriodDays sweep** (runs at startup):
```
FOR each worktree under .claude/worktrees/:
    IF worktree created by --worktree CLI flag:
        SKIP (never auto-removed by sweep)
    IF worktree is CLEAN (no uncommitted, no untracked, no unpushed commits)
       AND worktree age > cleanupPeriodDays:
        REMOVE worktree
```

Default `cleanupPeriodDays`: 30. Minimum: 1. Setting to 0 is rejected.

**Session deletion in agent view**:
- Ctrl+X twice: removes Claude-created worktree INCLUDING uncommitted changes
- `claude rm <id>`: keeps worktree with uncommitted changes, prints path

### 2.10 Subagent Worktree Isolation

**Frontmatter**: `isolation: worktree` in subagent definition.

**Behavior**:
- Each subagent invocation creates a temporary worktree
- Uses same base-branch rules as `--worktree` (`worktree.baseRef`)
- Auto-removed when subagent finishes WITHOUT changes
- Subagent cannot call `ExitWorktree` (not available to `isolation: worktree` subagents)
- Subagent can call `EnterWorktree` with `path` only (to switch between worktrees under `.claude/worktrees/`)

### 2.11 Workspace-Trust Gate

Before `--worktree` works in a directory:
1. User must run plain `claude` in that directory at least once
2. Accept the workspace trust dialog
3. Without trust: `--worktree` exits with error, prompts to run `claude` first

This applies even when combined with `-p` (non-interactive mode).

### 2.12 bgIsolation Setting

**Key**: `worktree.bgIsolation` (v2.1.143+)

| Value | Behavior |
|-------|----------|
| `"worktree"` (default) | Blocks `Edit`/`Write` in main checkout until `EnterWorktree` is called. Agent MUST isolate before editing. |
| `"none"` | Background sessions edit working copy directly. Use when git worktrees are impractical for a repo. |

Set in project's `.claude/settings.json`:
```json
{
  "worktree": {
    "bgIsolation": "none"
  }
}
```

### 2.13 Additional Worktree Settings

| Key | Default | Description |
|-----|---------|-------------|
| `worktree.symlinkDirectories` | `[]` | Directories to symlink from main repo into each worktree (avoids duplicating large dirs). Example: `["node_modules", ".cache"]` |
| `worktree.sparsePaths` | `[]` | Directories to check out via git sparse-checkout. Only listed dirs + root files are written. Faster in large monorepos. Example: `["packages/my-app", "shared/utils"]` |

---

## PART 3: /LOOP SESSION TYPE (for Loop-Sleeping State)

### 3.1 /loop Overview

Scheduled tasks run prompts on an interval within a session. The `✢` icon in agent view represents a `/loop` session sleeping between iterations.

### 3.2 Three Scheduling Modes

| Mode | Example | Behavior |
|------|---------|----------|
| Fixed interval + prompt | `/loop 5m check the deploy` | Runs on cron schedule |
| Prompt only (dynamic) | `/loop check the deploy` | Claude chooses interval each iteration (1 min -- 1 hour), calls `ScheduleWakeup` |
| No prompt (maintenance) | `/loop` | Uses built-in maintenance prompt or `loop.md` |

### 3.3 Loop Session Display

In agent view: `✢` icon. Row shows run count + countdown to next iteration. Example: `✢ playtest level 3  run 12 · all checkpoints cleared  in 4m`.

### 3.4 Dynamic Interval (Self-Paced)

When prompt is given without an interval:
- Claude calls `ScheduleWakeup` at end of each iteration
- Picks delay between 1 minute and 1 hour
- Short waits while build finishing / PR active, longer when nothing pending
- Jitter rules do NOT apply
- 7-day expiry still applies
- Not available on Bedrock/Vertex/Foundry (falls back to fixed 10-min schedule)

### 3.5 loop.md Customization

| Path | Scope |
|------|-------|
| `.claude/loop.md` | Project-level (takes precedence) |
| `~/.claude/loop.md` | User-level (applies in any project without its own) |

Plain markdown. Content beyond 25,000 bytes truncated. Edits take effect next iteration.

### 3.6 Cron Toolset

| Tool | Purpose |
|------|---------|
| `CronCreate` | Schedule task: 5-field cron, prompt, recurring flag |
| `CronList` | List all scheduled tasks with IDs |
| `CronDelete` | Cancel task by ID |

Max 50 scheduled tasks per session.

### 3.7 Runtime Behavior

- Scheduler checks every second for due tasks
- Enqueued at low priority
- Fires between turns (not mid-response)
- If Claude busy when task due: waits until current turn ends
- All times in local timezone (not UTC)

### 3.8 Jitter Rules

- Recurring: up to 30 min after scheduled time (or up to half the interval for sub-hourly)
- One-shot at :00 or :30: up to 90 seconds early
- Offset derived from task ID (deterministic -- same task always gets same offset)
- Workaround for exact timing: pick off-peak minutes like `3 9 * * *`

### 3.9 Seven-Day Expiry

Recurring tasks auto-expire after 7 days. Fire one final time, then self-delete. Bounds how long forgotten loops run.

### 3.10 Disable

`CLAUDE_CODE_DISABLE_CRON=1` disables the scheduler entirely. Cron tools and `/loop` become unavailable.

---

## PART 4: TRADE-OFF ANALYSIS

### 4.1 What the Fleet/Supervisor Architecture Costs

| Cost | Detail |
|------|--------|
| **Disk I/O per state change** | Every session writes state.json on each transition. Good for crash recovery, bad for high-frequency state changes. |
| **Haiku-class API calls for row summaries** | Each active session burns 1 Haiku call every ~15 seconds + per turn-end. With 10 active sessions, that is ~40-60 Haiku calls/minute just for status text. |
| **Process-per-session memory** | Each background session is an OS process. Node.js processes are ~50-100MB baseline. 20 idle sessions = ~1-2GB RAM. Mitigated by idle-stop. |
| **Startup latency on attach** | Stopped session takes a moment to respawn from disk. Pinned sessions avoid this. |
| **No multi-machine** | Sessions are local. Shutdown kills them. No cloud execution option in the base feature. |
| **Quota multiplication** | N parallel sessions = Nx quota consumption. No built-in budget pooling. |

### 4.2 What the Fleet/Supervisor Architecture Gains

| Gain | Detail |
|------|--------|
| **Zero-config parallelism** | No Docker, no Kubernetes, no queue system. Just `claude --bg`. |
| **Crash-only design** | State on disk at all times. Supervisor can die and restart; sessions survive. |
| **Steer-by-exception** | User attention is the bottleneck. Haiku summaries eliminate transcript-reading. Peek panel eliminates full-attach for most interactions. |
| **Per-session isolation** | Each session in its own worktree. Parallel edits cannot conflict. |
| **Graceful degradation** | Memory pressure sheds idle processes. Sessions restore from disk. |
| **Binary hot-reload** | Supervisor restarts on binary update. Sessions reconnect. Zero-downtime updates. |

### 4.3 What the Worktree Architecture Costs

| Cost | Detail |
|------|--------|
| **Disk space per worktree** | Each worktree is a full checkout (mitigated by git's hard-link optimization and sparsePaths). |
| **Setup overhead per worktree** | Dependencies must be installed in each worktree (node_modules, venv, etc.). SymlinkDirectories mitigates. |
| **Dirty-removal footgun** | Choosing "remove" on a dirty worktree silently discards uncommitted work. No trash/recovery. |
| **Non-git VCS requires hook coding** | SVN/Perforce/Mercurial users must write WorktreeCreate/Remove hooks. |
| **Workspace-trust gate friction** | Must accept trust dialog before --worktree works. Extra step for new repos. |

### 4.4 What the Worktree Architecture Gains

| Gain | Detail |
|------|--------|
| **True filesystem isolation** | No overlays, no FUSE, no copy-on-write tricks. Standard git worktrees. Every tool works. |
| **Branch-per-task** | Each session has its own branch. Can push independently. No merge conflicts between sessions. |
| **Clean removal** | Standard `git worktree remove`. No custom cleanup scripts needed (for git). |
| **.worktreeinclude** | Solves the "missing .env files" problem elegantly. gitignore syntax is familiar. |
| **Hook extensibility** | WorktreeCreate/Remove hooks support any VCS. Not locked to git. |
| **Subagent auto-isolation** | `isolation: worktree` in frontmatter. Subagent gets temp worktree, auto-cleaned when done. |

---

## PART 5: PROVIDER-AGNOSTIC VS ANTHROPIC-ONLY

### 5.1 Provider-Agnostic Mechanisms (Transferable)

These mechanisms have NO dependency on Anthropic infrastructure:

| Mechanism | Why Agnostic |
|-----------|-------------|
| Supervisor process model | Standard daemon architecture. Any language, any OS. |
| Process-per-session hosting | OS-level process management. Universal. |
| Disk-persisted state (roster.json, state.json) | JSON files. Any filesystem. |
| Idle-stop + respawn-from-disk | Standard process lifecycle management. |
| Memory-pressure shedding | OS memory monitoring. |
| State model (task-state x process-liveness) | Pure data model. No API dependency. |
| Agent-view TUI | Terminal UI. Framework-agnostic. |
| Filter/group/pin UX | Pure UI patterns. |
| Peek panel + inline reply | Terminal UI patterns. |
| Git worktree creation/cleanup | Standard git. |
| .worktreeinclude | File I/O + gitignore parser. |
| WorktreeCreate/Remove hooks | Standard hook/plugin pattern. |
| Workspace-trust gate | Filesystem flag + user prompt. |
| Cron scheduling (fixed interval) | Standard cron library. |
| /loop session type | Pure orchestration pattern. |

### 5.2 Anthropic-Only Mechanisms (Require Adaptation)

| Mechanism | Why Anthropic-Only | Adaptation for Lyra |
|-----------|-------------------|---------------------|
| Haiku-class row summaries | Uses Anthropic's Haiku model for cheap summarization | Use any small/fast model (GPT-4o-mini, Gemini Flash, local model). Or use local heuristic (last tool call name + target file). |
| Model picker (/model) | Anthropic model catalog | Map to Lyra's provider-agnostic model registry. |
| Subscription quota | Anthropic billing | Map to Lyra's token tracking / cost accounting. |
| `PushNotification` tool | Anthropic-hosted push infrastructure | Use OS-native notifications or webhook-based push. |
| `ScheduleWakeup` (dynamic interval) | Anthropic-only; not on Bedrock/Vertex/Foundry | Implement as pure orchestration logic. Agent decides next interval, scheduler honors it. |
| Claude API authentication | Anthropic accounts | Map to Lyra's provider credential system. |

---

## PART 6: EXACT TRANSFERABLE DESIGN FOR LYRA

### 6.1 Fleet/Supervisor Layer

```
DESIGN BLUEPRINT: Lyra Fleet Manager

1. SUPERVISOR DAEMON
   - Per-user singleton process
   - Auto-starts on first `lyra fleet` or `lyra --bg`
   - Stores state at: ~/.lyra/daemon/roster.json, ~/.lyra/jobs/<id>/state.json
   - Watches Lyra binary for self-update
   - Self-exits when no sessions + no terminal connected

2. STATE MODEL (two orthogonal axes)
   TaskState: Working | NeedsInput | Idle | Completed | Failed | Stopped
   ProcessLiveness: Alive | ExitedResumable | LoopSleeping
   Display icon = combine(TaskState, ProcessLiveness)

3. PROCESS HOSTING
   - Each session = own process (not thread, not goroutine)
   - Session state checkpoints to disk on every state transition
   - Idle-stop: ~1h idle + unattached + not pinned → stop process
   - Respawn: on next peek/reply/attach, start fresh process from disk state

4. MEMORY PRESSURE
   - Monitor system memory
   - Shed: idle non-pinned → idle pinned (never active)

5. ROW SUMMARIES
   - Small model call (configurable provider, not locked to Haiku)
   - Max refresh: every 15s + turn-end
   - Fallback: heuristic summary (last tool name + target + time)

6. TUI (agent-view equivalent)
   - Groups: Pinned | NeedsReview | NeedsInput | Working | Completed
   - Fold older Completed into "... N more"
   - Peek panel: Space key, shows recent output + questions
   - Inline reply: Tab suggested reply, number keys for MC, !-prefix bash
   - Attach: Enter key, full session, Left-arrow detach

7. DISPATCH
   - TUI input: type prompt + Enter = new session
   - CLI: lyra --bg "<prompt>"
   - In-session: /bg command
   - Shell job: lyra --bg --exec '<cmd>'

8. SHELL COMMANDS
   - lyra fleet              → open TUI
   - lyra fleet --cwd <path> → scoped
   - lyra fleet --json        → JSON output
   - lyra attach <id>         → attach
   - lyra logs <id>           → recent output
   - lyra stop <id>           → stop session
   - lyra respawn <id>        → restart with conversation intact
   - lyra rm <id>             → remove from list
   - lyra daemon status       → supervisor diagnostics

9. SECURITY GATE
   - Dangerous permission modes require one-time interactive acceptance
   - disableAgentView setting + env var for admin lockdown
```

### 6.2 Worktree/Isolation Layer

```
DESIGN BLUEPRINT: Lyra Worktree Isolation

1. CREATION
   - lyra --worktree <name>  → .lyra/worktrees/<name>/ on branch worktree-<name>
   - lyra -w                 → auto-generated name (adjective-adjective-animal)
   - lyra -w "#1234"         → fetch PR, create worktree

2. AGENT SELF-ISOLATION TOOL
   - EnterWorktree(name?, path?) → agent isolates itself
   - ExitWorktree(action: keep|remove, discard_changes?) → return to original dir

3. BASE BRANCH
   - worktree.baseRef: "fresh" (origin/HEAD) | "head" (local HEAD)
   - Only these two values, not arbitrary refs

4. .worktreeinclude
   - File at project root, .gitignore syntax
   - Copies matched+gitignored files into each new worktree
   - Skipped when WorktreeCreate hook used

5. CLEANUP
   - Clean worktree: auto-remove (prompt if named session)
   - Dirty worktree: prompt keep-or-remove (WARN on remove = data loss)
   - -p non-interactive: no auto-cleanup
   - cleanupPeriodDays sweep: only clean auto-created worktrees
   - Never auto-remove --worktree CLI created ones

6. HOOKS
   - WorktreeCreate: replaces default creation. Stdin JSON with "name". Prints path to stdout.
   - WorktreeRemove: fire-and-forget cleanup. Stdin JSON with "worktree_path".

7. SUBAGENT ISOLATION
   - isolation: worktree in subagent frontmatter
   - Temp worktree, auto-removed when done without changes
   - Uses same baseRef rules

8. SETTINGS
   - worktree.baseRef: "fresh" | "head"
   - worktree.symlinkDirectories: string[]
   - worktree.sparsePaths: string[]
   - worktree.bgIsolation: "worktree" | "none"
   - cleanupPeriodDays: number (default 30, min 1)

9. WORKSPACE TRUST
   - First run in directory requires trust acceptance
   - --worktree refused until trust accepted
```

### 6.3 /loop Session Type

```
DESIGN BLUEPRINT: Lyra Scheduled Loop Sessions

1. SCHEDULING
   - /loop <interval> <prompt> → fixed cron schedule
   - /loop <prompt>            → dynamic (agent chooses interval)
   - /loop                     → maintenance prompt (from loop.md)

2. TOOLS
   - CronCreate: 5-field cron + prompt + recurring flag
   - CronList: all tasks with IDs
   - CronDelete: cancel by ID
   - ScheduleWakeup: dynamic interval (1min-1hr)

3. RUNTIME
   - Check every second for due tasks
   - Fire between turns (not mid-response)
   - Local timezone (not UTC)
   - Jitter: deterministic offset from task ID
   - 7-day expiry on recurring tasks

4. DISPLAY
   - Agent-view icon: ✢ (loop-sleeping)
   - Shows run count + countdown to next iteration

5. CUSTOMIZATION
   - .lyra/loop.md (project-level)
   - ~/.lyra/loop.md (user-level)
   - Plain markdown, ≤25KB

6. DISABLE
   - LYRA_DISABLE_CRON=1 env var
```

### 6.4 Key Design Principles to Copy

1. **State is a cross-product, not an enum**. Task-state and process-liveness are independent axes. This is the single most important design insight.

2. **Crash-only software**. State always on disk. Processes can die at any time; the supervisor respawns from disk. No in-memory-only state.

3. **Steer-by-exception**. Users intervene only when a session needs input. Haiku summaries + peek panel eliminate constant monitoring.

4. **Process-per-session, not thread-per-session**. Full OS process isolation. No shared memory between sessions. The supervisor is a thin process manager, not a runtime.

5. **Worktree-as-default, not worktree-as-option**. Background sessions auto-isolate into worktrees. Users opt OUT (`bgIsolation: "none"`), not opt IN.

6. **Hooks for non-git VCS**. WorktreeCreate/Remove hooks make the isolation layer provider-agnostic. The default implementation is git, but the architecture is VCS-neutral.

7. **Dangerous-mode gate**. High-risk permission modes require one-time interactive acceptance. This is a UX pattern, not a security mechanism -- it prevents accidents, not attacks.

8. **Named sessions survive auto-cleanup**. Named sessions prompt before cleanup. Anonymous sessions auto-clean. This is a simple heuristic that matches user intent well.

---

## APPENDIX: Version Gates Summary

| Feature | Minimum Version |
|---------|----------------|
| Agent view (research preview) | v2.1.139 |
| `claude agents --cwd` | v2.1.141 |
| `--permission-mode`, `--model`, `--effort`, `--dangerously-skip-permissions` for agent view | v2.1.142 |
| `--allow-dangerously-skip-permissions` for agent view | v2.1.143 |
| `worktree.bgIsolation` | v2.1.143 |
| `--agent` for agent view, honoring `agent` setting | v2.1.157 |
| Monitor tool | v2.1.98 |
| Scheduled tasks (/loop, CronCreate) | v2.1.72 |
| `disableRemoteControl` | v2.1.128 |
| `auto` mode restricted in project/local settings | v2.1.142 |
