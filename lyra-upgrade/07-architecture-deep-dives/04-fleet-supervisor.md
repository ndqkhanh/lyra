# Fleet Supervisor — Deep Dive

**Date**: 2026-06-01 | **Package**: `lyra-orchestration`, `lyra-fleet-tui` | **Tests**: 257+ (orchestration + fleet TUI)

## 1. Executive Summary

The Fleet Supervisor is a per-user daemon process that manages detached background sessions — each a complete Lyra conversation that keeps running with NO terminal attached. Modeled on Claude Code's Agent View (research preview, CC v2.1.139+), it solves the fundamental problem of multi-agent orchestration: how do you run dozens of agents concurrently, monitor their state at a glance, and intervene only when needed — without babysitting each one?

The architecture has three components with clean boundaries: the **Supervisor** owns session lifecycle (create/attach/detach/stop/respawn), the **Fleet TUI** provides a single-screen dashboard for steer-by-exception, and **Worktrees** provide per-session file isolation. No component overlaps — each has exactly one owner, defined interfaces, and specified failure modes.

## 2. The Supervisor Architecture

### 2.1 Process Model

```
┌──────────────────────────────────────────────┐
│           Fleet Supervisor Daemon              │
│                                                │
│  Owns: Session lifecycle, roster, dispatch     │
│  Persists: ~/.lyra/roster.json, jobs/<id>/     │
│  Survives: terminal close, restart, sleep      │
│                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Session A │  │ Session B │  │ Session C │    │
│  │ PGID: 42  │  │ PGID: 43  │  │ PGID: 44  │   │
│  │ State: ✻  │  │ State: ∙  │  │ State: ✢  │   │
│  │ Task: WRK  │  │ Task: NI  │  │ Task: CMP │   │
│  └──────────┘  └──────────┘  └──────────┘     │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │         Roster + State Persistence        │ │
│  │  roster.json → [{id, name, pgid, state}]  │ │
│  │  jobs/<id>/state.json → {messages, cwd}  │ │
│  └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

Each session is spawned as an **independent process group** (`setpgid(0, 0)`), not as a child of the supervisor. This is the critical design decision: when the supervisor exits (for restart, update, or crash), sessions keep running as orphaned process groups. On restart, the new supervisor reads the roster and reconnects via the PTY socket. The roster records the PGID, not the PPID — the supervisor finds sessions by their process group, not their parent.

**State persistence**: `~/.lyra/roster.json` is the source of truth for which sessions exist. It's written atomically (write to `.tmp`, `rename` over the real file) with a WAL (`roster.wal`) for crash recovery. Per-session state lives at `~/.lyra/jobs/<session-id>/state.json` and includes the message history, current working directory, git branch, and open PR information.

### 2.2 Lifecycle Management

**Idle detection**: A session that produces no output for `idleTimeout` (default: 15 minutes for background, 60 minutes for attached) is marked idle. The supervisor stops idle background sessions after `idleStopTimeout` (default: 1 hour) to free resources. The session state is persisted to disk, so it can be respawned on next peek/reply/attach.

**Memory pressure**: Under memory pressure, the supervisor prioritizes stopping idle sessions first, then idle-but-pinned sessions, then the oldest background sessions. Active/attached sessions are never killed.

**Self-exit**: When no sessions are live (all stopped/completed), the supervisor waits `drainTimeout` (default: 5 minutes) then exits. It's a daemon that runs only when needed.

### 2.3 Crash Recovery

1. Supervisor crashes → sessions survive (independent process groups)
2. User restarts supervisor → reads `roster.json`
3. For each session in roster: attempts to reconnect via stored socket path
4. If reconnect fails (session also crashed): marks session as `FAILED`, offers respawn from `state.json`
5. WAL replay: any incomplete roster writes are replayed from the WAL

## 3. Two-Axis State Model

The state model has two orthogonal axes — what the agent is *doing* vs whether its process is *alive*:

### 3.1 Task State (X-axis)

```
WORKING      → Agent is actively processing (model inference, tool execution)
NEEDS_INPUT  → Agent is blocked waiting for user response
IDLE         → Agent is running but has nothing to do (between turns)
COMPLETED    → Agent finished its task successfully
FAILED       → Agent encountered an unrecoverable error
STOPPED      → Agent was explicitly stopped by user
```

### 3.2 Process Liveness (Y-axis)

```
✻ (ACTIVE)   → Process is running, consuming CPU/memory
∙ (PAUSED)    → Process is suspended (SIGSTOP), can be resumed (SIGCONT)
✢ (STOPPED)   → Process has exited, state persists on disk for respawn
```

### 3.3 Row Grouping

```
┌─ Pinned ─────────────────────────────────────┐
│ ✻ auth-fix        WORKING  "Rewriting OAuth…" │
├─ Ready for Review ───────────────────────────┤
│ ✻ pr-342          COMPLETED "Added rate limit" │
│ ∙ api-docs        COMPLETED "Generated OpenAPI"│
├─ Needs Input ────────────────────────────────┤
│ ✻ db-migration    NEEDS_INPUT "Which ORM…"    │
├─ Working ────────────────────────────────────┤
│ ✻ refactor-login  WORKING  "Extracting…"     │
│ ✻ add-tests       WORKING  "Writing unit…"   │
├─ Completed ──────────────────────────────────┤
│ ✢ cleanup-imports COMPLETED "Removed unused…" │
└──────────────────────────────────────────────┘
```

## 4. Steer-by-Exception UX

The key UX insight from Claude Code's Agent View: you shouldn't need to open every session's transcript to know what's happening. A cheap model writes one-line summaries, refreshed ≤ once per 15 seconds and at each turn end.

### 4.1 Peek (without attaching)

Pressing `Enter` on a session row opens the Peek panel showing:
- The last 5 messages of output
- The exact question/task the agent is working on
- Any open PRs with their status
- Multiple-choice hotkeys for common responses ("Looks good", "Fix the tests first", "Add error handling")

### 4.2 Reply (without attaching)

Pressing `r` opens the Reply bar. Type a message and press Enter — the agent receives it as user input. The session was never attached. `Tab` cycles through suggested replies generated by a cheap model.

### 4.3 Attach/Detach

Pressing `a` attaches to the session — full terminal interaction. Pressing `Ctrl+B d` or `←` detaches back to the fleet view. The session **never stops** during attach/detach — it keeps running.

### 4.4 Dispatch

From the fleet view input: `"Fix the auth bug in login.ts"` dispatches a new background session. Flags: `--name`, `--model`, `--effort`, `--permission-mode`. From inside a session: `/bg "Update the API docs"` backgrounds the current task into a new fleet row.

## 5. Fleet TUI (Textual)

The dashboard is built with Python Textual (`packages/lyra-fleet-tui/`). It integrates directly with the supervisor's Python objects — no IPC, no serialization, just method calls.

### 5.1 Widget Architecture

```
┌─ FilterBar ──────────────────────────────────┐
│ [ALL] [WRK] [NI] [IDL] [CMP] [FLD] [STP] 🔍  │
├─ FleetTable ─────────────────────────────────┤
│ # │ State │ Name           │ Task          │ Model  │ Tokens │ Cost   │
│ 1 │  ✻    │ auth-fix       │ Rewriting…    │ Opus   │ 12.3K  │ $0.18  │
│ 2 │  ✻    │ pr-342         │ Added rate…   │ Sonnet │ 8.7K   │ $0.03  │
│ 3 │  ∙    │ api-docs       │ Generated…    │ Haiku  │ 45.2K  │ $0.05  │
│ 4 │  ✻    │ db-migration   │ Which ORM…    │ DS-V3  │ 3.1K   │ $0.00  │
│ 5 │  ✢    │ cleanup-imports│ Removed…      │ Sonnet │ 1.2K   │ $0.00  │
├─ StatusBar ──────────────────────────────────┤
│ ● idle │ ask │ Opus │ 70.5K/200K [███░░░░░░░] 35% │ 3m 42s │ ~/projects/lyra │
└──────────────────────────────────────────────┘
```

### 5.2 Key Bindings

| Key | Action |
|-----|--------|
| `j` / `↓` | Next agent |
| `k` / `↑` | Previous agent |
| `Enter` | Peek selected agent |
| `r` | Reply to selected agent |
| `a` | Attach to selected agent |
| `s` | Stop selected agent |
| `f` | Focus filter bar |
| `1-6` | Filter by task state |
| `/` | Search filter |
| `q` | Quit |
| `Ctrl+O` | Toggle agent tree |

## 6. Security Model

### 6.1 The Unwatched-Session Guard

Claude Code's Agent View has a critical security rule: **unwatched sessions cannot use bypass/auto permission modes without a prior explicit human accept**. Lyra adopts this exactly.

When a background session attempts a tool call that requires `bypass` or `allow` mode:
1. The security gate checks: has the user explicitly accepted this permission class for background sessions?
2. If no → the tool call is BLOCKED with a message: "This session needs permission to run `<tool>`. Approve in the fleet view (press `a` to attach, then accept)."
3. If yes → the approval must not be expired (tiered expiry: 4h/24h/7d depending on tool risk)

### 6.2 Security Gate

`packages/lyra-orchestration/src/lyra_orchestration/security_gate.py`:
- Command hashing: `SHA256(tool_name + args_hash)` — exact match required
- Tiered expiry: LOW risk (Read, Grep) 7d, MEDIUM (Write, Git) 24h, HIGH (Bash, WebFetch) 4h, CRITICAL (rm, curl, pip) per-use
- SQLite-backed approval database with atomic check-and-use
- JSONL audit log with 90-day retention

## 7. Row Summaries

A cheap model (routed via §4.5 router to the fastest available provider) writes one-line summaries:

```
Input (last message + agent state) → Haiku/DeepSeek-Flash → "Rewriting OAuth token refresh to use PKCE"
```

**Cost optimization**: DeepSeek summaries cost $0.0035/refresh vs Haiku's $0.0126 — 72% savings. But quality is validated: first 100 sessions generate summaries with BOTH models; if agreement < 90%, DeepSeek routing is disabled and falls back to Haiku.

**Refresh cadence**: ≤ once per 15 seconds at idle, at every turn end for active sessions. During streaming, the summary updates when the streaming message stabilizes (no change for 3 seconds).

## 8. Lightweight Mode

The supervisor supports a `lightweight` mode for users who don't want a full daemon:

- **Lightweight**: Supervisor runs as a stateless service — row summaries + security gate only. Sessions managed by tmux/screen. No process ownership, no idle-stop, no worktree orchestration.
- **Full daemon**: All features enabled.

This was the Adversarial Skeptic's proposal from `00-architecture/ARCHITECTURE-DEBATE.md` — ship the minimum viable features first, prove value, then upgrade.

## 9. Trade-Off Analysis

| Dimension | Gain | Cost |
|-----------|------|------|
| Session persistence | Survives terminal close, restart, sleep | Daemon process always running (~50MB baseline) |
| Process isolation | One crash doesn't affect others | Memory per process (~200MB per session with LLM runtime) |
| Steer-by-exception | No need to watch every session | Requires trust in automation + row summary accuracy |
| Row summaries | At-a-glance fleet visibility, ~$0.0035/refresh | 72% cost savings only if DeepSeek quality is validated |
| Lightweight mode | Zero-daemon entry point for skeptical users | No process ownership, no idle-stop, no worktree isolation |
| Security gate | Command-hashed approvals, tiered expiry, audit log | User friction: re-approving every 4h for HIGH-risk tools |

## 10. (B) Breakthrough: Multi-Provider Fleet

What Lyra does beyond Claude Code's Agent View:

1. **Provider-aware concurrency caps**: Anthropic 16, DeepSeek 32, OpenAI 10, local unlimited. Claude Code hardcodes 16.

2. **Provider-aware row summaries**: Route summary generation through the model router. Use the cheapest available provider. Quality-gated with dual-model validation.

3. **Lightweight mode**: Entry point for users who don't want a daemon. Claude Code has no equivalent — you either use Agent View or you don't.

4. **Non-destructive worktree cleanup**: Auto-stash to tags, never Claude Code's silent discard. Documented in `10-worktree-isolation.md`.

5. **Open-weight support**: Local models can serve as row summary generators at zero cost, making fleet monitoring free for self-hosted deployments.

## 11. Key Sources

- Claude Code Agent View: https://code.claude.com/docs/en/agent-view
- Claude Code Worktrees: https://code.claude.com/docs/en/worktrees
- Claude Code Sub-agents: https://code.claude.com/docs/en/sub-agents
- Anthropic Multi-Agent Research (+90.2%): https://www.anthropic.com/engineering/built-multi-agent-research-system
- Hermes Agent fleet design: https://github.com/nousresearch/hermes-agent
- AutoScientists self-organizing teams: https://arxiv.org/abs/2605.28655
- Preventing Rogue Agents (arXiv 2502.05986): https://arxiv.org/pdf/2502.05986
- CaMeL prompt injection defense: https://arxiv.org/abs/2503.18813
