# rmux Clean-Room Rebuild -- Plan (§5.1)

> Run 2 -- June 7, 2026 (updated with deep-read evidence)

## Plain-Language Summary

Lyra's terminal multiplexer (`lyra-rmux`) provides tmux-like PTY hosting and detach/reattach, with one key innovation: every pane is backed by a git worktree for edit isolation. The ownership split is clean: rmux owns PTY/terminal I/O, the supervisor (§4.13) owns session lifecycle, and worktrees own file isolation.

## Ownership Split

| Component | Owns | Does NOT Own |
|-----------|------|-------------|
| rmux | PTY hosting, terminal I/O, pane layout, detach/reattach | Session lifecycle, file isolation |
| Supervisor (§4.13) | Session lifecycle, state persistence, fleet management | Terminal multiplexing, PTY details |
| Worktrees (§4.13) | Per-session file isolation, .lyrainclude propagation, cleanup | Terminal I/O, session state |

## Key Features

1. **PTY Hosting:** Spawn/manage pseudo-terminals for each session pane
2. **Pane Layout:** Fleet view (top), session terminal (main), status bar (bottom)
3. **Detach/Reattach:** Sessions survive terminal close; reattach restores full state
4. **Worktree Integration:** Each PTY pane backed by a git worktree — edit isolation at the terminal layer
5. **Clean-Room:** MIT-licensed from-scratch rebuild — no code from tmux (BSD) or cmux

## Deep-Read Evidence Base

The following sources were consulted for this plan update:

| Source | ID | Relevance |
|--------|----|-----------|
| Helvesec/rmux (v0.5.0, Rust) | web/Helvesec__rmux | Reference implementation: async/sync split, daemon architecture, PTY backends, IPC protocol |
| tmux (ISC license, C) | web/tmux__tmux | Original multiplexer: client-server via imsg, grid/layout engine, detach/reattach protocol |
| manaflow-ai/cmux (Swift, GPL) | web/manaflow-ai__cmux | AI-agent-native terminal: Agent Hibernation, notification pipeline, session restore |
| Claude Code Worktrees (official docs) | web/docs/.../worktrees | Worktree-per-session isolation: `.worktreeinclude`, cleanup policies, baseRef config |
| Claude Code Terminal Config (official docs) | web/docs/.../terminal_config | Notification tiers, tmux passthrough, theme live-reload, editor modes |
| charmbracelet/crush (Go, FSL-1.1-MIT) | web/charmbracelet__crush | Terminal-native agent: dual-mode workspace, accept-sequence dispatch, SQLite persistence |
| warpdotdev/warp (Rust, AGPL) | web/warpdotdev__warp | Agentic terminal: PTY integration, multi-agent orchestration, diff matching |
| Terminal-Bench 2.0 | 2601.11868v1 | Benchmark: harness quality drives 17pp resolution gap, 62.9% ceiling |
| Harness Engineering: Claude Code, Ch.3-4 | book/harness-engineering...chapters | Query loop architecture, tool permission system, worktree isolation patterns |
| Claude Code Definitive Guide, Practices 5, 6, 11 | book/definitive-guide...playbook | Worktree-per-subagent, terminal-first architecture, context budget governance |
| Safety Survey | 2605.23989v1 | Sandbox tiers, process-level isolation requirements |

## Build Outline (Augmented with Evidence)

### 1. PTY Manager (spawn, resize, signal handling)

**Evidence:**
- **tmux** uses `forkpty()` on Unix with libevent async I/O to manage each pane's child process. The input parser (`input.c`, 86KB) is a custom DEC ANSI state machine. The grid (`grid.c`, 37KB) is a 2D `grid_cell_entry` array split into history + viewable regions. The screen (`screen-write.c`, 72KB) implements all terminal output drawing operations; `screen-redraw.c` (44KB) computes minimal deltas. *Source: tmux deep-read (web/tmux__tmux), §1-2.*
- **Helvesec/rmux** uses a pure in-memory domain model (`rmux-core`, `#![forbid(unsafe_code)]`) with zero OS dependencies. The `rmux-pty` crate provides platform-specific PTY backends: `forkpty`/`openpty` on macOS, `posix_openpt` on Linux, and ConPTY on Windows. Read buffer is 8192 bytes; pane output events are coalesced via `events/coalescing.rs`. Unix daemon uses single-threaded Tokio runtime; Windows requires multi-threaded due to ConPTY blocking I/O. *Source: Helvesec/rmux deep-read (web/Helvesec__rmux), §2-3.*
- **Terminal-Bench 2.0** finds that 37% of realistic CLI tasks remain unsolved by best agents (GPT-5.2 + Codex CLI at 62.9% ceiling), and the same model (Gemini 2.5 Pro) achieves 32.6% with Terminus 2 vs. 15.7% with OpenHands -- a 17pp gap from harness quality alone. Lyra-rmux's PTY layer is part of this harness quality equation: poor PTY management inflates agent latency and failure rates. *Source: Terminal-Bench 2.0 (2601.11868v1), Table 2.*

**Design decision:** Adopt **rmux's pure domain model approach** (OS-free core, platform-specific PTY crate) over tmux's monolithic C approach. The `#![forbid(unsafe_code)]` policy on upper crates eliminates a class of PTY-related memory safety bugs that plague C multiplexers. The async/sync split (rmux-ratatui pattern) keeps TUI rendering deterministic and I/O-free.

**Trade-off:** The rmux approach requires more crates/modules (16 in rmux vs. 1 binary in tmux). Compile time is higher; modularity gains are worth it for Lyra's agent-integrated use case, where individual crates (e.g., `rmux-core`) can be reused by the supervisor without dragging in PTY or TUI dependencies.

### 2. Pane Layout Engine (split, resize, focus)

**Evidence:**
- **tmux** uses a tree of layout cells (`layout.c`, 35KB). Each cell is either a `LAYOUT_WINDOWPANE` leaf or a horizontal/vertical split container. Layout algorithms (`layout-set.c`) include even-horizontal, even-vertical, main-horizontal, main-vertical, tiled. *Source: tmux deep-read (web/tmux__tmux), §1.*
- **Helvesec/rmux** uses a `WindowLayout` in `rmux-core` that implements a tree-based layout model derived from the tmux specification. However, rmux's core is a pure in-memory model: all layout operations are deterministic functions over state, testable without any OS. *Source: Helvesec/rmux deep-read (web/Helvesec__rmux), §2.*
- **Claude Code Definitive Guide** describes the three-pane workspace pattern (fleet view + session terminal + status bar) as the converged UX. *Source: Claude Code Definitive Guide, Practice 11 (book/claude-code-definitive-guide-playbook).*

**Design decision:** Adopt the **rmux pure-state layout model**: layout is a pure function of a tree data structure. The TUI renderer reads a snapshot, not live state. This enables layout testing without spawning PTYs or daemons -- a direct application of Harness Engineering's "test architecture at the state machine level, not the integration level" principle (*Source: Harness Engineering, Ch.3*).

**Benchmark reference:** rmux's renderer computes `PaneRenderDelta` per frame, sending only changed cells/attributes. With the ratatui-rmux async/sync split, rendering is O(window_cells) for snapshot capture but O(changed_cells) for terminal output. *Source: Helvesec/rmux deep-read (web/Helvesec__rmux), §3.*

### 3. Detach/Reattach Protocol (Unix socket)

**Evidence:**
- **tmux** uses OpenBSD `imsg` protocol framework over Unix domain sockets. Protocol version 8 is defined in `tmux-protocol.h`. Messages are framed with type, length, and fd-passing capability. The server listens with `listen(fd, 128)` backlog, accepts via `server_accept()`, and processes command queues in `server_loop()`. Session state is purely in-memory: restarting the server loses all sessions (no native disk persistence). *Source: tmux deep-read (web/tmux__tmux), §1-2, §4.*
- **Helvesec/rmux** uses a detached protocol crate (`rmux-proto`, `#![forbid(unsafe_code)]`) that owns request/response DTOs, framing (length-prefixed with magic number, default max frame 4MB), and wire-safe errors. Versioned as `V1` with a capabilities handshake. The SDK (`rmux-sdk`) wraps client connectivity: `Rmux` builder, `ensure_session`, `PaneHandle` (send_text, wait_for_text, snapshot, split). Unix sockets on macOS/Linux, named pipes on Windows. *Source: Helvesec/rmux deep-read (web/Helvesec__rmux), §2, §5.*
- **charmbracelet/crush** demonstrates the dual-mode workspace pattern: an in-process mode (zero setup, no daemon) and a client/server mode behind `CRUSH_CLIENT_SERVER=1` for shared workspaces, using HTTP over Unix sockets. Crush stores session state in SQLite (embedded, no separate server). *Source: crush deep-read (web/charmbracelet__crush), §2, §5.*
- **tmux loss:** No built-in session persistence to disk. Third-party plugins (tmux-resurrect/tmux-continuum) exist but are not native. Scrollback is purely in-memory. *Source: tmux deep-read (web/tmux__tmux), §4.*

**Design decision:** Adopt **rmux's detached protocol crate pattern** (protocol DTOs + codec in a standalone, no-unsafe crate) with rmux-sdk-style high-level handles. Add **SQLite session persistence** (crush pattern) so sessions survive daemon restart -- a strict improvement over both tmux and rmux. This addresses the "session outlives client" requirement directly.

**Trade-off:** Version skew between SDK and daemon is manageable via protocol versioning (rmux-proto pattern), but adds a compatibility surface. In-process mode (crush's default) is unsuitable for Lyra because the supervisor daemon must manage sessions across multiple user terminal connections.

### 4. Worktree Integration (pane -> worktree mapping)

**Evidence:**
- **Claude Code Worktrees (official docs):** Each new session gets a private `git worktree add` at `.claude/worktrees/<name>/` with a branch named `worktree-<value>`. Cleanup is automatic: no changes = silent removal, changes present = user prompt. The `.worktreeinclude` file copies gitignored files (`.env`, etc.) into each new worktree. Subagents can use `isolation: worktree` in frontmatter for per-subagent isolation. Background sessions are cleaned by a periodic sweep based on `cleanupPeriodDays`. *Source: Claude Code Worktrees docs (web/docs/.../worktrees), §1-2.*
- **Harness Engineering, Ch.3:** Worktree isolation is a foundational pattern: "Every agent session gets its own working tree, so edits never collide." The worktree is the mechanism that allows parallel subagents to operate on the same repository without coordination overhead. *Source: Harness Engineering: Claude Code, Ch.3 (book/harness-engineering...chapters).*
- **Claude Code Definitive Guide, Practice 6:** "The spec file survives context compaction, session restarts, and subagent failures" -- persistent state in a worktree-backed filesystem enables recovery across session boundaries. *Source: Claude Code Definitive Guide, Practice 6 (book/claude-code-definitive-guide-playbook).*

**Design decision:** Map each PTY pane to a Claude Code-style worktree. When rmux creates a pane, it calls `git worktree add --detach` (or a non-git VCS equivalent via hooks). When the pane is closed, the worktree is cleaned up (changes committed or stashed per user preference). The `.lyrainclude` file (analogous to `.worktreeinclude`) propagates non-tracked config files.

**Trade-off:** Worktree creation adds latency (2-5s per pane on large repos). This is acceptable for session create/attach but would be prohibitive for lightweight pane operations (e.g., `split-window`). Mitigation: pre-warm a worktree pool (2-3 worktrees ready at session start), or use branch-per-pane within a single worktree for ephemeral panes.

### 5. TUI Rendering (Textual-based)

**Evidence:**
- **Helvesec/rmux ratatui-rmux crate:** Defines `PaneDriver` (async, owns SDK event I/O), `PaneState` (sync, deterministic snapshot), and `PaneWidget` (sync, referentially transparent renderer). The async/sync split ensures the widget is safe in any draw loop (ratatui's `Widget::render` must not block). This is the Elm/Redux architecture pattern: state in, rendering out. *Source: Helvesec/rmux deep-read (web/Helvesec__rmux), §2, §5.*
- **cmux's notification pipeline:** Terminal sequences (OSC 9, 99, 777) from agent processes route through `TerminalNotificationStore`, `TerminalNotificationPolicy`, and `TerminalNotificationQueue`. Notifications get a floating blue ring around the pane and sidebar tab highlight. Composable notification hooks (`notifications.hooks` in `cmux.json`) are JSON-in/JSON-out shell commands. *Source: cmux deep-read (web/manaflow-ai__cmux), §1-2.*
- **Warp's tiered fuzzy diff matching:** For when the agent's edit output goes through the TUI, Warp's diff validator uses a 4-tier cascade: exact > indentation-agnostic > prefix-tail > Jaro-Winkler (threshold 0.9). This recovers from common LLM diff errors. *Source: warp deep-read (web/warpdotdev__warp), §6.*
- **Claude Code Terminal Config (official docs):** Notification system uses three-tiered strategy: (1) built-in desktop notification for supported terminals (Ghostty/Kitty/iTerm2), (2) `preferredNotifChannel: "terminal_bell"` for others, (3) custom Notification hook for arbitrary commands. Paste collapse at 10,000 characters. Six built-in theme presets with live-reload. tmux passthrough requires 3-line config for `allow-passthrough`, `extended-keys`, and `terminal-features`. *Source: Terminal Config docs (web/docs/.../terminal_config), §1-3.*

**Design decision:** Adopt the **rmux ratatui-rmux async/sync split** architecture. Lyra-rmux's TUI widget (state projection) should be a pure synchronous function of a captured snapshot. The async driver folds I/O events into state outside the draw closure. For notifications, adopt the **cmux notification pipeline** architecture (detect agent OSC sequences, route through composable hook filters). Implement the **Claude Code three-tier notification fallback** for cross-terminal compatibility.

**Trade-off:** Textual (Python) vs. ratatui (Rust). If Lyra-rmux ships as a Rust binary (like rmux), ratatui is the natural choice. If Lyra-rmux is a Python subprocess, Textual is available but lacks the strict async/sync enforcement of ratatui's widget contract. Recommendation: adopt the architecture (async/sync split) regardless of toolkit, and enforce it via code review.

## Expert Review

**Mini-Debate Participants:** Senior UX Designer, Senior Backend Engineer, Adversarial Skeptic

**Skeptic's challenge:** "Port Claude Code's implementation directly -- don't invent something new unless the evidence proves it's better."

**Resolution:** Parity port is the (A) tier baseline. Breakthrough enhancements must beat Claude Code's implementation on at least one measurable dimension (latency, token cost, multi-provider compatibility, UX simplicity) with cited evidence. Otherwise ship parity.

**Evidence-informed breakthroughs (gated):**

| Dimension | Breakthrough Claim | Evidence | Gate |
|-----------|-------------------|----------|------|
| Session persistence | Zero-loss restart via SQLite state | crush: SQLite persistence works in production (web/charmbracelet__crush, §2) | Ship if session-loss rate > 1% |
| Agent-triggered notifications | Hook pipeline for agent OSC sequences | cmux: notification pipeline with composable hooks (web/manaflow-ai__cmux, §1) | Ship if users request agent status awareness |
| Worktree pre-warming | Sub-second pane creation | Pre-warmed pool: 2-5s creation cost paid once per session | Ship if pane creation latency exceeds UX budget |
| Cross-platform PTY | Single codebase, all OS | rmux: Unix + ConPTY (web/Helvesec__rmux, §1, §4) | Ship if Windows support required |

## Evidence-Weighted Effort Assessment

| Component | Effort (1-5) | Risk | Dependency | Tier |
|-----------|-------------|------|------------|------|
| PTY manager | 3 | Medium (platform-specific bugs) | None | (A) Parity |
| Pane layout engine | 2 | Low (pure functions) | PTY manager | (A) Parity |
| Detach/reattach | 4 | Medium (IPC correctness) | PTY manager | (A) Parity |
| Worktree integration | 2 | Low (wraps git worktree) | Supervisor (§4.13) | (A) Parity |
| TUI rendering | 3 | Medium (terminal compatibility) | Pane layout | (A) Parity |
| SQLite session persistence | 3 | Low (well-understood pattern) | Detach/reattach | (B) Enhancement |
| Agent notification pipeline | 2 | Low (OSC sequence detection) | TUI rendering | (B) Enhancement |
| Worktree pre-warm pool | 1 | Low (optimization only) | Worktree integration | (C) Optimization |

**Impact:** 3 | **Effort:** 4 | **Tier:** (A) Parity

## Applicable Architectural Principles (from Harness Engineering, Ch.9)

1. **Tools are managed execution interfaces** -- The worktree is a managed file-isolation interface between PTY and agent session. rmux should not decide file policy; the supervisor enforces it via worktree creation parameters.
2. **Error paths are main paths** -- PTY allocation failure, socket disconnection during detach, and worktree cleanup collision are not exceptional; they must have handled code paths with user-visible feedback.
3. **Recovery should optimize for continuation** -- If the daemon crashes, sessions should resume from the last SQLite checkpoint (cf. crush pattern). If a PTY dies, the pane should show a reconnect UI, not terminate the session.
4. **Context is working memory** -- The TUI status bar and notification pipeline should consume minimal LLM context. Agent notifications (OSC sequences) should flow through rmux to the agent's context, not be duplicated in the TUI renderer.

## Changelog

- Run 2 (2026-06-07): Added Deep-Read Evidence Base section with 11 sources, augmented every build outline item with specific evidence citations, added evidence-weighted effort assessment table, added breakthrough gates table with cross-referenced evidence. Source format: `(web/<note-name>)`, `(<paper-ID>)`, or `(book/<book-name>)` throughout.
- Run 1 (2026-06-03): Initial plan with Expert Review section, Changelog
