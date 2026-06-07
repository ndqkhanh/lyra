# Helvesec/rmux -- Deep-Read

**Version**: 0.5.0 | **Language**: Rust (edition 2021) | **License**: MIT OR Apache-2.0 (dual)

**URL**: https://github.com/Helvesec/rmux

## 1. Headline Feature & Mechanism (how the code really works)

RMUX is a modern, async Rust terminal multiplexer engine that is command-compatible with tmux (90+ commands) while adding three capabilities tmux does not have: native Windows support (via ConPTY, no WSL), a public Rust SDK (`rmux-sdk`) for programmatic control of sessions/panes/PTYs, and browser-based web sharing of terminal sessions with hybrid post-quantum end-to-end encryption (E2EE).

The headline feature is the **Web Share** system, which lets you share a live RMUX terminal pane or session in a browser via `rmux web-share`. Execution stays entirely local on the daemon; the browser receives ChaCha20-Poly1305 encrypted terminal frames. The key exchange is a hybrid of ephemeral X25519 and ML-KEM-768 (post-quantum KEM), bound to the handshake transcript via HKDF-SHA256. The frontend is a decoupled static HTML/JS/WASM app served from a CDN or a custom URL. Tunnel providers (e.g., localhost-run, Tailscale) forward only ciphertext -- the "blind relay" model.

The mechanism underlying all features is a **daemon-based client-server architecture**. A Tokio async daemon (`rmux-server`) runs as a background process, managing PTYs, sessions, windows, panes, layouts, hooks, and copy modes. Local clients communicate with it via Unix sockets (Linux/macOS) or named pipes (Windows) using a detached protocol crate (`rmux-proto`) that owns the request/response DTOs, framing, and wire-safe errors. The SDK (`rmux-sdk`) wraps client connectivity with high-level handles (`Rmux`, `OwnedSession`, `PaneHandle`) and async methods for `ensure_session`, `send_text`, `wait_for_text`, `snapshot`, etc.

## 2. Architecture & Core Modules (entry points, data flow, patterns)

**Workspace layout** (16 crates):

| Crate | Role | Safety | Dependencies |
|-------|------|--------|--------------|
| `rmux-core` | Pure in-memory domain model: Session, Window, Pane, layout geometry, VT parser state machine, grid/buffer, options, formats, input dispatch, hooks, key bindings. Zero OS, network, or process integration. | `#![forbid(unsafe_code)]` | none |
| `rmux-pty` | PTY allocation, resize, child process control. Platform backends: Unix PTY (macOS via `forkpty`/`openpty`, Linux via `posix_openpt`) and Windows ConPTY. | 9 files use `unsafe` (syscall boundary) | libc, windows-sys |
| `rmux-proto` | Detached IPC DTOs, codec/framing, request/response types, capabilities handshake, control mode formatting. Wire version `V1`. | `#![forbid(unsafe_code)]` | minimal |
| `rmux-ipc` | Local IPC endpoints, listeners, and streams. Unix sockets on Linux/macOS, named pipes on Windows. | | |
| `rmux-server` | Tokio async daemon: listener infrastructure, request handler dispatch, pane I/O (reader/writer with live rendering), renderer (borders, status bar, clock, overlay, display panes), web-share HTTP server with E2EE. Default web port 9777. | `unsafe` only in unix_socket.rs | Tokio 1.48, rmux-core, rmux-proto |
| `rmux-client` | Local IPC client: connection management, auto-start of hidden daemon, session attach flow (Windows metrics), control mode, command queue. | | |
| `rmux-sdk` | Public daemon-backed Rust SDK: `Rmux` builder, `ensure_session`, `PaneHandle` (send_text, wait_for_text, snapshot, split), event streams, broadcast, diagnostics, web-share handle. | `#![forbid(unsafe_code)]` | rmux-proto (not rmux-core/server) |
| `rmux-web-crypto` | Web Share E2EE core: X25519 ephemeral key agreement, ML-KEM-768 wrappers, HKDF-SHA256 key schedule, ChaCha20-Poly1305 records, kind-byte framing, WASM bindings. | `#![forbid(unsafe_code)]` | zeroize, hkdf, sha2, chacha20poly1305 |
| `ratatui-rmux` | Ratatui widget: `PaneDriver` (async, owns SDK event I/O), `PaneState` (sync, deterministic projection of pane snapshot), `PaneWidget` (sync, referentially transparent renderer). Async/sync split keeps widget safe in any draw loop. | `#![forbid(unsafe_code)]` | ratatui, rmux-sdk |
| `rmux` (root) | CLI binary (`src/main.rs`): clap argument parsing, client dispatch, hidden daemon re-exec path. | | clap, tokio, rmux-server |
| `rmux-types`, `rmux-os`, `rmux-render-core`, `xtask` | Supporting crates: shared types, OS helpers, internal render primitives, build tasks. | | |

**Data flow**:
1. `rmux` binary parses CLI args via clap -> `Command` enum
2. Client connects to daemon via `rmux-client` over Unix socket/named pipe
3. Requests encoded via `rmux-proto` frames (length-prefixed, magic-numbered)
4. Daemon dispatches via `RequestHandler` -> mutates `SessionStore` in `rmux-core`
5. Pane I/O runs concurrently: `pane_io::reader` reads PTY output, `pane_io::live_render` computes diffs, `pane_io::attach_transport` streams to attached clients
6. For Web Share: daemon spawns TCP listener, performs hybrid PQ handshake, wraps socket in EncryptedWebSocketReader/Writer

**Architecture pattern**: Client-Server (detached daemon) with framed IPC. Pure domain model (rmux-core) is fully testable without OS. Protocol crate (rmux-proto) enables independent evolution of client and server.

**Safety policy**: Upper-level crates (rmux-core, rmux-proto, rmux-sdk, rmux-web-crypto, ratatui-rmux) use `#![forbid(unsafe_code)]`. Lower-level OS/terminal boundary code (rmux-pty, rmux-server unix_socket) isolates `unsafe` to minimal platform-specific modules.

## 3. Performance/Benchmarks

The repository has no integrated benchmark suite. The `benches/` directory is empty (contains only `.gitkeep`). There are no Criterion, Iai, or Divan benchmarks in the source tree.

Performance characteristics inferred from architecture:
- **Rendering**: The renderer computes pane deltas (`PaneRenderDelta`) to minimize terminal output, only sending changed cells/attributes.
- **PTY I/O**: Read buffer is 8192 bytes (`READ_BUFFER_SIZE`). Pane output events are coalesced in `rmux-core` via `events/coalescing.rs`.
- **Runtime**: Unix daemon uses `Builder::new_current_thread()` (single-threaded async runtime, efficient for I/O-bound work). Windows daemon uses multi-thread with 4+ worker threads (ConPTY requires blocking I/O on separate threads).
- **Release profile**: `codegen-units=1`, `lto="fat"`, `strip="symbols"` -- optimizes for binary size and runtime speed at cost of compile time.
- **ratatui-rmux budget**: Explicit source/dependency budget enforced by integration test (`budget.rs`) and CI script (`scripts/ratatui-rmux-budget.sh`).
- **Protocol**: Frames use length-prefixed encoding with magic number. Default max frame 4MB (`DEFAULT_MAX_FRAME_LENGTH`). Control mode uses write buffering with `CONTROL_BUFFER_HIGH`/`CONTROL_BUFFER_LOW` watermarks.

## 4. Trade-offs (wins vs loses from issues, design decisions, complexity)

**Wins**:
- **Cross-platform**: Single codebase runs on Linux, macOS, and Windows with native PTY backends (no WSL). This is a significant advantage over tmux (Unix-only) and most alternatives.
- **SDK as first-class citizen**: `rmux-sdk` is published to crates.io as a public crate, enabling programmatic terminal automation in Rust. The SDK is deliberately decoupled from internal crates (`rmux-core`, `rmux-server`) -- it depends only on `rmux-proto`, so version skew between SDK and daemon is manageable.
- **Web Share E2EE**: Hybrid post-quantum key exchange (X25519 + ML-KEM-768) with forward secrecy and blind relay model. No other terminal multiplexer offers this combination (see comparison table in web-share docs).
- **tmux migration path**: Automatic `tmux.conf` fallback loading (filtered: imports supported static options and key unbindings, skips commands, plugins, conditionals, etc.). Environment variable `RMUX_DISABLE_TMUX_FALLBACK=1` to opt out.
- **Async/sync split in ratatui-rmux**: Widget is pure sync with no I/O, safe to call from any draw loop. Driver is async and owns the SDK connection. Well-designed boundary.

**Loses / Complexity**:
- **Not a byte-for-byte tmux clone**: Some tmux features are not supported (e.g., `refresh-client control-mode flags` -- explicitly noted as "not yet available" in handler code). Some tmux config features are silently skipped during migration fallback.
- **No benchmark suite**: Performance claims are architectural only, no published benchmarks or regression measurements.
- **Single visible commit in cloned repo**: The cloned repository only has one commit (`90e7ca0 ci: protect release publishing environment`) and no CHANGELOG. This is likely a CI-published snapshot, so the issue tracker and commit history were not available for deeper analysis of design rationale.
- **Windows runtime complexity**: Windows requires a multi-threaded Tokio runtime (due to ConPTY blocking I/O), while Unix uses a simpler current-thread runtime. This adds a platform-specific code path in the daemon entry point.
- **Web Share is new**: Web Share feature ships in v0.5.0. It is marked as "moving fast" and the README explicitly invites feature requests and issue reports. Some aspects (e.g., tunnel providers, frontend hosting) require external infrastructure.
- **Graphics passthrough**: Kitty graphics and SIXEL passthrough are opt-in (`set -g allow-passthrough on`). SIXEL on Windows depends on outer terminal support; ConPTY passthrough can be disabled via `RMUX_CONPTY_NO_PASSTHROUGH=1`.

## 5. Design Rationale (why this approach)

1. **Pure domain model first**: `rmux-core` is deliberately free of OS, network, and process dependencies. This makes the entire session/window/pane/layout state machine testable via ordinary `#[test]` functions without mocks or daemons. The VT input parser, format renderer, layout engine, and options system are all pure functions over in-memory state.

2. **Detached protocol layer**: `rmux-proto` owns the IPC contract as its own crate with `#![forbid(unsafe_code)]` and minimal dependencies. This allows client and server to be versioned independently and enables third-party clients to speak the protocol.

3. **Defense in depth for Web Share**: The web-crypto crate deliberately knows nothing about network transports, JSON, or HTTP. It is a pure crypto library that happens to also compile to WASM. The key schedule uses HKDF-SHA256 with domain-separated labels (baked as constants in the code), transcript binding, and constant-time rejection of zero shared secrets. This isolation prevents whole classes of implementation bugs.

4. **Async/sync boundary for TUI**: The ratatui-rmux widget is pure sync because ratatui's `Widget::render` is called inside a draw closure that must not block. State is captured ahead of time by the async driver. This is identical to the Elm/Redux architecture pattern: state in, rendering out.

5. **tmux compatibility as migration path, not straitjacket**: The `tmux.conf` fallback is explicitly filtered to avoid executing arbitrary shell commands or loading plugins. This prevents security issues (malicious `tmux.conf` from dotfiles) while making migration effortless for most users. The RMUX config format is separate.

6. **Platform-specific PTY abstraction**: Rather than trying to unify Unix PTY and Windows ConPTY under a single API, the PTY crate uses `#[cfg(unix)]` / `#[cfg(windows)]` conditional compilation extensively. This keeps each backend's specialized behavior (e.g., Windows `application.manifest`, ConPTY passthrough detection, Unix `TIOCSWINSZ` for resize) explicit rather than abstracted behind traits that would leak platform details.

## 6. Transfer to Lyra (one idea + workstream route + Impact/Effort/Tier + LICENSE)

**Transferable idea**: The **ratatui-rmux async/sync split pattern** (pure sync `Widget` with captured state vs async `Driver` that folds events into state) is directly applicable to Lyra's TUI rendering pipeline. Lyra could adopt the same architecture: a deterministic, referentially transparent widget that renders a snapshot of agent/session state, driven by an async state collector. This keeps TUI rendering fast, testable, and free of I/O issues.

**LICENSE consideration**: MIT OR Apache-2.0 -- compatible with Lyra's license. Code can be adapted or patterns adopted without licensing conflict.

**Workstream route**: **§4.3 -- UI/UX** (TUI rendering pipeline improvement).

**Impact**: **7** -- A pure sync widget architecture eliminates a class of TUI rendering bugs (flickering, stale state, I/O-in-draw-loop panics) and makes the render path trivially testable.

**Effort**: **3** -- Low effort. The pattern is well-understood (Elm/Redux architecture). Implementation requires refactoring the existing TUI renderer to capture state before draw time, but does not require new infrastructure.

**Tier**: **T2** -- High value, low risk, achievable in one focused sprint.
