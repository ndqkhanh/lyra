# manaflow-ai/cmux -- Deep-Read

## 1. Headline Feature & Mechanism

cmux is a **native macOS terminal emulator** (Swift + AppKit, backed by `libghostty` for GPU-accelerated terminal rendering) that wraps AI coding agent terminals -- Claude Code, Codex, OpenCode, Copilot CLI, Grok, Amp, Gemini, Rovo Dev, and 15+ others -- with **vertical sidebar tabs, agent notification rings, composable notification hooks, and an in-app browser**.

The central mechanism is the **unified workspace+notification+event system**:

- **Workspace model** (`Sources/Workspace.swift`, 822 KB) and **TabManager** (`Sources/TabManager.swift`, 420 KB) manage the window/surface/pane hierarchy using the `bonsplit` layout engine. Each workspace is a tab in the vertical sidebar.
- **Notification pipeline** detects terminal sequences (OSC 9, 99, 777) from agent processes. The pipeline routes through `TerminalNotificationStore` (96 KB), `TerminalNotificationPolicy` (32 KB), and `TerminalNotificationQueue` (14 KB). Notifications get a floating blue ring around the pane and a sidebar tab highlight. `Cmd+Shift+U` jumps to the latest unread.
- **Composable notification hooks** (`notifications.hooks` in `cmux.json`) are JSON-in/JSON-out filters that can suppress desktop banners, sounds, workspace reordering, or pane flashes per agent -- user-defined shell commands that transform the notification effect payload.
- **Agent Hibernation** (`Sources/AgentHibernation/`) kills idle background agent processes to free RAM/CPU and auto-resumes each one from saved session state when the tab is revisited, with configurable idle threshold and live-terminal count cap.
- **Dual socket protocol**: a legacy v1 space-delimited protocol and a v2 JSON protocol (both documented in `docs/v2-api-migration.md`). Commands never steal macOS app focus unless explicitly intent-marked (`window.focus`, `workspace.select`, etc.).
- **In-app browser** (`Sources/BrowserWindowPortal.swift`, 173 KB; `Sources/Panels/BrowserPanel*.swift`) embeds WKWebView with accessibility-tree-based agent automation API (ported from `vercel-labs/agent-browser`). Supports snapshots, element refs, click, fill, eval JS, cookies, storage, frame/dialog handling.
- **SSH remote workspaces** (`cmux ssh user@remote`) with daemon bootstrap (`cmuxd-remote`), port mirroring, and browser proxy routing through remote network.
- **Session restore** writes versioned snapshots under `~/Library/Application Support/cmux/` and reinstates window/workspace/pane layout, working directories, terminal scrollback, browser URL and navigation history, and agent-specific resume commands.
- **Swift Package decomposition** in progress: 40+ packages under `Packages/` (CmuxSettings, CmuxSocketControl, CmuxControlSocket, CmuxGit, CmuxFileWatch, CmuxFoundation, CmuxUpdater, etc.), layered in a 5-tier DAG (Core -> Services -> Domain -> UI -> Executable).

## 2. Architecture & Core Modules

**Language**: Swift (primary, ~330k lines), Zig (cmuxd daemon, Go for `daemon/remote/`), TypeScript/React (webview panels), Python (test harness), shell (scripts)

**Entry points**:
- `Sources/cmuxApp.swift` (229 KB) -- `@main` app entry, SwiftUI App + AppKit composition
- `Sources/AppDelegate.swift` (748 KB) -- AppKit lifecycle, menu bar, window management
- `Sources/TerminalController.swift` (943 KB) -- v1/v2 socket command dispatcher, routes all socket operations
- `CLI/cmux.swift` (1.38 MB) -- single-file CLI implementation (hand-rolled parser, migrating to Swift ArgumentParser)
- `CLI/cmux_open.swift` (251 KB) -- file/URL open routing
- `daemon/remote/` -- Zig-based remote SSH daemon (`cmuxd-remote serve --stdio`)

**Core data flow**:
```
Agent Process (terminal) 
  -> GhosttyTerminalView (GPU rendering)
  -> TerminalNotificationQueue/Store (notification pipeline)
  -> TerminalNotificationPolicy (hooks filter chain)
  -> Sidebar highlight + blue ring + desktop notification
  
CLI/Socket commands
  -> TerminalController (v1 text parser + v2 JSON dispatcher)
  -> Workspace/TabManager (layout state)
  -> Bonsplit (pane geometry)
  
Browser automation
  -> cmux CLI browser subcommand
  -> WKWebView via BrowserWindowPortal
  -> Accessibility tree snapshot -> agent reads refs -> actions
```

**Key architectural patterns**:
- **Coordinator/Service/Repository** decomposition for new/extracted code (5-layer DAG)
- **Dependency inversion**: packages publish protocols, concrete actors conform, executable is single composition root
- **@unchecked Sendable** with explicit lock carve-outs for low-level Process/socket handling
- **Swift 6 concurrency**: actors for shared state, `@Observable` for SwiftUI, `AsyncStream` for cross-actor observation
- **ExtensionKit sidebar extensions** with per-tag bundle ID isolation for dev builds
- **`cmux.json`** project-level config with composable hooks, custom commands, theme control

**Architecture pattern**: Multi-module Swift Package decomposing monolith into DAG of 40+ packages, with Coordinators owning user flows, Services owning I/O, Repositories owning persistence. The remaining god files (ContentView.swift at 823 KB, Workspace.swift at 822 KB, AppDelegate.swift at 748 KB, GhosttyTerminalView.swift at 674 KB, TabManager.swift at 420 KB) are being systematically extracted.

## 3. Performance/Benchmarks

The README and codebase do not publish granular benchmarks, but the trade-off evidence surfaces key performance characteristics:

- **GPU-accelerated rendering** via libghostty (Zig-based terminal renderer); the README claims "fast startup, low memory" compared to Electron/Tauri alternatives.
- **Agent Hibernation** provides RAM/CPU savings: cmux kills idle background agent processes after a configurable window (default 5s idle + ~60s confirmation settle, max 12 live terminals by default). This is the primary memory governor.
- **Memory leak history**: CHANGELOG reports a fixed settings-observation task leak that grew to 4.4 GB over ~23h (v0.64.13), and a browser pane render loop consuming ~39% main-thread CPU (fixed in same release).
- **Process overhead**: AgentForkSupport uses `Process.run()` with custom `ProcessTerminationGate` (NSLock-guarded) and 3-second command output timeout.
- **Notification sound**: Custom NSSound system with background preparation queue and file-system copying to avoid audible lag on first play.
- **500-event ring buffer** in DebugEventLog, dumped to file on demand.
- **Socket command threading**: telemetry hot paths (`report_*`, `ports_kick`) parse/dedupe/coalesce off-main before scheduling minimal UI mutations.
- **Scrollback reads** recently moved off main actor to reduce UI hangs.

No formal latency or throughput benchmarks are published in the repository.

## 4. Trade-offs (wins vs. loses)

**Wins**:
- Native macOS (Swift/AppKit) avoids Electron's memory overhead -- "the performance bugged me" is the author's stated motivation.
- Vertical sidebar with rich metadata (git branch, PR status, listening ports, notification text) is a UX improvement over Ghostty/tmux for multi-agent workflows.
- Composable notification hooks pipeline gives users fine-grained control over notification routing and filtering.
- Dual v1+v2 socket protocol enables backward compatibility while adding JSON protocol for LLM agents.
- Agent Hibernation provides practical resource management for teams running many parallel agent sessions.
- Browser automation API (agent-browser port) reduces context-switching -- agents can inspect dev servers directly.
- SSH remote workspaces with browser proxy routing are a genuine differentiator for remote development.
- Session restore respects layout + terminals + browser state + agent-specific resume commands.

**Loses**:
- **Massive god files**: ContentView.swift (823 KB), Workspace.swift (822 KB), AppDelegate.swift (748 KB), TabManager.swift (420 KB), GhosttyTerminalView.swift (674 KB) -- the CLAUDE.md explicitly calls these "the pattern this rule exists to stop." Extraction into packages is in progress but incomplete.
- **Test quality gap**: The CLAUDE.md test policy states "Never run tests locally" -- all tests run on VM. Unit tests for package code are expected but the monolith god files have minimal unit coverage. "Never run tests locally" is pragmatic but reveals a weak local TDD feedback loop.
- **CLI monolith**: `CLI/cmux.swift` at 1.38 MB is a single-file hand-rolled command parser. The v2-api-migration doc acknowledges migration to Swift ArgumentParser is planned but not done.
- **Localization burden**: Every user-facing string must be localized into 22 languages. Localization audit is required for every UI change. This is a heavy process cost.
- **GPL-3.0-or-later** with dual-license commercial option -- GPL copyleft may be a concern for proprietary integrations.
- **macOS-only**: No Linux/Windows support. Requires Xcode 26.x toolchain.
- **Complex dev setup**: Submodules (ghostty, bonsplit), Zig for GhosttyKit, Zig for cmuxd, Python for tests. Setup is not trivial.
- **Performance issues surface in CHANGELOG**: 4.4 GB memory leak, 39% CPU browser render loop, keyboard events getting swallowed under non-ASCII input sources.
- **Known bugs in TODO.md**: Terminal title updates suppressed when workspace unfocused, sidebar tab reorder can get stuck, drag-and-drop files show URL instead of file path.

## 5. Design Rationale

The README section "Why cmux?" and the CLAUDE.md architecture rules make the design rationale explicit:

- **"Primitive, not a solution"**: cmux is deliberately non-prescriptive. It provides terminals, browser, notifications, workspaces, splits, tabs, and a CLI -- not an opinionated agent orchestrator. "The best developers have always built their own tools."
- **Native over Electron/Tauri**: The author's stated pain point was Electron/Tauri performance. Swift+AppKit + libghostty was chosen for "fast startup, low memory."
- **Ghostty compatibility**: Leverages existing Ghostty investment -- reads `~/.config/ghostty/config` for themes/fonts/colors, uses libghostty for rendering.
- **Gradual modularization**: The 5-layer DAG, Coordinator/Service/Repository pattern, and Swift Package extraction are a deliberate strategy to decompose a monolith that grew too fast. The CLAUDE.md has an unusually rigorous set of rules for new package design (no shared singletons, no namespace enums, no parallel registries, compile-time invariants over runtime traps, one major type per file).
- **Swift 6 purity**: New code requires `actor` isolation, `@Observable` (never `ObservableObject`/`@Published`), `AsyncStream` over callbacks/Combine, structured concurrency. Locks only allowed in documented carve-outs with justification comments.
- **No-focus-steal policy**: Socket/CLI commands must never activate the macOS app or steal keyboard focus. Only explicit focus-intent commands may mutate in-app focus. This is enforced by an audited allowlist documented in `socket-focus-steal-audit.todo.md`.
- **Agent-first design**: The entire notification pipeline, session restore, agent hooks, and browser automation API are designed specifically for AI coding agent workflows. Claude Code integration has special handling (cmux Claude wrapper).

## 6. Transfer to Lyra

**One transferable idea**: **Agent Hibernation** -- cmux's pattern of killing idle background agent processes and auto-resuming them from saved session state. Lyra could implement a managed process pool for multi-agent loops: when an agent subprocess has been idle in the background beyond a configurable threshold, the orchestrator sends SIGSTOP (or kills and saves checkpoint), then SIGCONT or restores on re-activation. The insight is that the user-perceived latency of cold-resume is low (agent reinitializes in seconds) compared to the cumulative memory/CPU cost of keeping N idle agent processes alive. cmux's concrete numbers (default 5s idle + ~60s settle window, max 12 live terminals) provide a starting point for tuning.

**Workstream route**: This maps to **Section 4.x: Multi-Agent Management** (the section covering agent lifecycle, process pools, and resource governance within Lyra's orchestration layer). Specifically, the process pool primitive under Orchestrator/Scheduler.

**Impact**: 5/10 -- Agent Hibernation is a practical resource optimization but not a core differentiator. The real impact is the UX pattern it enables (transparent process lifecycle management), which is valuable for Lyra's multi-agent loops.

**Effort**: 3/10 -- Straightforward to implement with POSIX signals (SIGSTOP/SIGCONT) or process checkpoint/restore. The tricky part is the "confirmation settle window" heuristic and the session save/restore contract with each agent type. The inspection/notification layer (detecting idle, selecting what to hibernate) requires moderate design work.

**Tier**: Cherry-pick -- the idea is self-contained, can be layered on top of existing orchestration infrastructure without core architectural changes, and provides clear benefit for multi-agent deployments.

**LICENSE compatibility**: GPL-3.0-or-later. Lyra must consider: (a) if Lyra is distributed under GPL-compatible terms, code can be ported directly; (b) if Lyra uses a permissive license (MIT/Apache), only the *idea* (Agent Hibernation pattern) should be ported, not the GPL'd implementation. The hibernation algorithm itself (process lifecycle management with idle detection) is not copyrightable -- it is a general computing pattern. Section 4.x would implement the concept from scratch.
