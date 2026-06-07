# tmux -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline**: tmux is a **terminal multiplexer** -- it enables multiple terminals (sessions, windows, panes) to be created, accessed, and controlled from a single screen. Sessions can be detached from a screen and continue running in the background, then later reattached.

**How the code really works**:

At its core, tmux is a single C binary with a **client-server architecture** communicating over **Unix domain sockets** via a message-based IPC protocol (defined in `tmux-protocol.h`, protocol version 8, using OpenBSD `imsg` framework).

1. **Entry point** (`tmux.c`, `main()`): Sets locale, parses CLI args (`-c`, `-D`, `-C`, `-f`, `-L`, `-S`, etc.), initialises global options (server/session/window), determines socket path (from `-S`, `$TMUX`, or `TMUX_TMPDIR`), and calls `client_main()`.

2. **Client (`client.c`)**: Resolves the server socket, obtains a lock file via `flock()` to serialise server startup, connects to the server via Unix socket, sends identity messages (TERM, TTY name, environment, CWD, features list), then enters an event loop dispatching `imsg` messages from the server. On attach, it renders the grid to the real terminal via `tty.c`.

3. **Server (`server.c`)**: Created via `proc_fork_and_daemon()` when no existing server is found. Creates a Unix domain socket (`server_create_socket`), listens (backlog 128), accepts client connections in `server_accept()`. Runs an event loop based on **libevent** (`proc_loop`). The `server_loop()` function processes command queues for the global server and each client. Manages child process exit signals (`SIGCHLD`) and reclaims pane PTY fds.

4. **Input parser (`input.c`, 86KB)**: A custom VT100/xterm escape sequence parser based on Paul Williams' DEC ANSI parser state machine, extended with UTF-8 support, OSC string handling, DCS passthrough (for sixel), and window rename sequences. Takes raw terminal output from PTY fds and writes to the **grid**.

5. **Grid (`grid.c`, 37KB)**: The fundamental data structure -- a 2D array of `grid_cell_entry` objects representing the character buffer. Splits into **history** (scrollback, lines 0..hsize-1) and **viewable** (lines hsize..hsize+sy-1). Lines are allocated on demand. Supports extended cells for RGB colour, wide characters, hyperlinks, padding cells.

6. **Layout (`layout.c`, 35KB)**: A **tree of layout cells**. Each cell is one of:
   - `LAYOUT_WINDOWPANE` -- a leaf containing a pane
   - A horizontal/vertical split container parenting child cells
   The tree structure allows arbitrary recursive splits. Layout algorithms (`layout-set.c`) include even-horizontal, even-vertical, main-horizontal, main-vertical, tiled.

7. **Screen (`screen.c`, `screen-write.c`, `screen-redraw.c`)**: The "virtual screen" abstraction. `screen-write.c` (72KB) implements all terminal output drawing operations (character writes, scrolling regions, insert/delete lines, etc.). `screen-redraw.c` (44KB) computes the minimal set of drawing operations needed to update the real terminal to match the virtual screen state.

8. **TTY output (`tty.c`, 77KB)**: Renders the grid state to the real terminal via terminfo/termcap capabilities. Manages cursor positioning, colour, attributes, regions, margins, scrolling, and repeated character optimisation. Accesses terminal via `tty_term.c` which wraps terminfo.

9. **Command system**: A yacc grammar (`cmd-parse.y`, 37KB) parses user commands into `struct cmd` objects. ~40 individual `cmd-*.c` files each implement one command. Commands are queued and executed via `cmd-queue.c`. The `cmd-find.c` layer resolves target sessions/windows/panes from command arguments.

10. **Format system (`format.c`, 136KB)**: A template-based rendering engine that expands `#{}` syntax in status line strings. Supports conditionals, arithmetic, loop operators (`W:`, `P:`, `L:`), sorting, and hundreds of format variables.

11. **Options system (`options-table.c`, `options.c`)**: A type-safe options table with default values, range limits, and choice lists. Three scopes: server, session, window. Options are copied from the master table into runtime trees at startup.

## 2. Architecture & Core Modules

### Entry Points

| File | Role |
|------|------|
| `tmux.c` | Main entry: arg parsing, env setup, global options init, dispatches to client |
| `client.c` | Client lifecycle: connect to server, identify, enter event loop |
| `server.c` | Server lifecycle: create socket, accept connections, event loop |

### Data Flow

```
User terminal
    |
    v
[tty.c / tty-keys.c]  <--->  client.c  <---[Unix socket / imsg]--->  server.c
                                                                        |
                                                        +---------------+---------------+
                                                        |               |               |
                                                    [session.c]   [window.c]      [cmd-queue.c]
                                                                        |
                                                                   [layout.c]
                                                                        |
                                                                   [input.c]
                                                                        |
                                                                   [grid.c]
                                                                        |
                                                                 [screen.c]
                                                                        |
                                                              [screen-write.c]
                                                                        |
                                                                  [tty-draw.c]
                                                                        |
                                                            Real PTY child processes
```

### Process Model

- **Single server process** manages all sessions, windows, panes.
- Each pane is a child process with a PTY (`forkpty`).
- The server handles SIGCHLD to detect pane exit.
- Client is a separate process communicating via imsg over Unix domain socket.
- Client can be on a different machine via SSH forwarding the socket.

### Key Design Patterns

1. **Event-driven with libevent**: Server and client both use libevent for async I/O. The server event loop is in `proc.c` using `struct tmuxproc` and `struct tmuxpeer`.

2. **imsg-based IPC**: Borrowed from OpenBSD. Framed messages with type, length, and fd-passing capability. Defined in `tmux-protocol.h`.

3. **RB trees and TAILQ lists**: Heavy use of BSD `sys/tree.h` (red-black trees) and `sys/queue.h` (tail queues). Windows, sessions, panes, clients are all RB trees.

4. **Composited command pattern**: Each command is a separate C file with a `cmd_entry` struct containing name, alias, args template, and execute function. Commands register themselves via a linked list built at compile time.

5. **State machine pattern**: The input parser (`input.c`) is a strict state machine based on the DEC ANSI parser spec. The escape sequence parsing is table-driven with explicit state transitions.

6. **Separated rendering pipeline**: Grid -> Screen -> TTY is a layered pipeline. Changes to the grid (by `input.c`) are applied to the screen, then differences are computed and flushed to the real terminal.

### Dependencies

- `libevent >= 2` (event loop)
- `ncurses` / `tinfo` / `ncursesw` / `curses` (terminal capability database)
- Optional: `utempter`, `utf8proc`, `systemd` (with cgroups), `jemalloc`
- Build: `autoconf`, `automake`, `pkg-config`, `yacc`/`bison`

## 3. Performance / Benchmarks

The tmux repository does not contain explicit benchmarks or performance numbers. Performance characteristics are implicit in the design:

- **Grid memory**: The grid allocates lines on demand. Scrollback history is bounded by `history-limit` option (default 2000 lines per pane). History is retained in memory -- no disk swap.
- **Redraw optimisation**: `screen-redraw.c` computes only changed cells since the last frame, sending minimal escape sequences. `tty.c` uses `tty_large_region()` to batch changes.
- **Event loop**: Single-threaded event model with libevent handles all I/O multiplexing. No threading -- all state is in one process.
- **Backlog**: `listen(fd, 128)` on the server socket.
- **Platform-specific performance tuning**: Uses `malloc_trim(0)` on glibc systems to return memory to the kernel hourly; has a `--enable-jemalloc` option for better memory allocation performance.
- **Timer**: `get_timer()` uses `CLOCK_MONOTONIC` for millisecond-precision time measurement.
- **Blocking I/O mitigation**: 100ms block interval (`TTY_BLOCK_INTERVAL`) for output coalescing to the terminal.
- No synthetic benchmarks, no CI performance regression tracking in the repo.

## 4. Trade-offs

### Wins

1. **Detachable persistence**: Sessions outlive the client connection. This is the killer feature over a plain terminal -- disconnect and reconnect without losing state.
2. **Client-server separation**: The server runs as a daemon, clients connect/disconnect freely. No global lock-in to a single terminal emulator.
3. **Lightweight panes with PTY isolation**: Each pane is a real child process with its own PTY. Full job control, signals, and TTY behaviour.
4. **Single process model**: Simpler than multi-process (per-pane daemon like GNU Screen's `screen -X`). All state in one process address space -- no inter-process coordination for shared state.
5. **Unix domain socket IPC**: Fast, secure (file permissions on socket), fd-passing support, well-understood.
6. **BSD-heritage code quality**: OpenBSD-style kernel normal form, pledge() sandboxing, careful bounds checking, compatibility shims for 15+ platforms.
7. **Custom VT parser**: Full control over terminal emulation. Supports all common escape sequences, sixel images, DCS passthrough, OSC 4/10/11/12 palette control, DECRQSS, and more.
8. **Huge format system**: The 136KB `format.c` is one of the most powerful template/formatting engines in any terminal tool. Supports arbitrary text transformations, conditionals, loops, filtering.

### Losses

1. **Single-server bottleneck**: All panes feed through one server process. A buggy pane that floods output can stall the entire server event loop.
2. **C language ergonomics**: No RAII, no standard collections, manual memory management. Large monolithic header (`tmux.h` at 3882 lines) includes everything. No module encapsulation.
3. **No built-in session persistence to disk**: Restarting the server loses all sessions. There is `tmux resurrect`/`tmux continuum` as third-party plugins, but no native checkpointing.
4. **Scrollback in memory only**: History is stored entirely in process heap. Very large history limits consume proportional RAM. No mmap-backed history.
5. **No native clustering/distribution**: Sessions are bound to one machine. No built-in way to share sessions across hosts (can be tunneled via SSH but not native).
6. **Steep configuration language**: The tmux command language is terse and idiosyncratic. The `bind-key`, `set-option`, `run-shell` syntax has a learning curve. No TOML/YAML/JSON config alternative.
7. **Input parser complexity**: The custom VT parser in `input.c` is 86KB of intricate state machine logic. Every new terminal feature requires deep understanding of escape sequence esoterica -- very hard to contribute to.
8. **No multi-threading**: Everything is single-threaded. CPU-intensive operations (e.g., regex search in large scrollback) block the event loop.

### Known Limitations from CHANGES

- macOS library support for Unicode is described as "very poor, particularly for complex codepoints like emojis" -- `configure.ac` requires `--enable-utf8proc` or `--disable-utf8proc` on macOS.
- Format processing had a buffer overread and infinite loop bug (3.6a fix).
- Various edge cases with mouse handling when status bar is at the top.
- Sixel image save/restore across alternate screen was only added in 3.5.
- Some platforms have broken `CMSG_FIRSTHDR`, `wcwidth`, `daemon()`, `reallocarray` -- all handled by compatibility shims.

## 5. Design Rationale

Why this approach was chosen:

1. **Client-server over process-per-pane**: tmux chose a single-server architecture (influenced by OpenBSD's design philosophy of simplicity and correctness) over GNU Screen's more complex per-pane process model. This makes state management simpler (everything in one address space) at the cost of isolation.

2. **imsg-based IPC over raw sockets**: Adopted from OpenBSD's privilege separation framework. Provides structured message passing with automatic fd-passing, queue management, and message type safety -- simpler and more robust than implementing a custom protocol over raw sockets.

3. **Custom VT parser rather than libtermkey/libvterm**: By implementing their own DEC ANSI parser, tmux gains full control over terminal emulation without depending on external terminal emulation libraries. This is a double-edged sword -- it works brilliantly for the 95% case but requires significant maintenance for new terminal features.

4. **Autotools rather than CMake/meson**: tmux targets a broad range of Unix platforms (OpenBSD, FreeBSD, NetBSD, Linux, macOS, Solaris, AIX, HP-UX, Cygwin, Haiku). Autotools provides the widest compatibility for portable C code targeting POSIX-like systems.

5. **Single monolithic header**: The 3882-line `tmux.h` is an OpenBSD convention. Every .c file includes only `"tmux.h"`. This avoids include-ordering bugs and makes the full API surface visible from one place, at the cost of recompilation overhead.

6. **No plugin system**: tmux intentionally does not have a native plugin/extension mechanism. Instead, it provides `run-shell` and a control mode protocol (`-C` flag) that external tools can script against. This keeps the core simple and avoids versioning ABI compatibility constraints.

7. **Memory management**: Uses custom `xmalloc`, `xcalloc`, `xreallocarray`, `xstrdup`, `xasprintf` wrappers that abort on allocation failure. No attempt at graceful OOM recovery -- allocation failure is treated as fatal. This is consistent with OpenBSD's "fail closed" philosophy.

8. **Shell as default command, not a custom terminal**: tmux deliberately does not implement a terminal emulator with full graphics rendering. It delegates to the host terminal for font rendering, window management, and colour capabilities. This keeps tmux small and portable.

## 6. Transfer to Lyra

### Transferable Idea

**Detachable agent sessions using a client-server persistence model analogous to tmux's socket-based IPC.** Lyra's agent sessions could adopt the core tmux pattern: a background server process holds the agent's runtime state (memory, context, call stack), while zero or more client processes connect/disconnect to interact with the session. This enables:

- Agent sessions that persist across client disconnections (network drops, IDE restarts, machine sleep).
- Multiple clients observing or interacting with the same agent session (collaboration, monitoring).
- Programmatic control mode (like tmux `-C`) for headless agent operation from CI/CD or orchestration scripts.

The specific mechanism to borrow: **imsg-style structured IPC** over Unix domain sockets with fd-passing -- not for terminal data but for structured agent protocol messages (state deltas, observation requests, tool results). The tmux protocol (`tmux-protocol.h`) with `MSG_IDENTIFY_*`, `MSG_COMMAND`, and asynchronous I/O maps well to agent lifecycle phases.

### Workstream Route

This maps to **SS4.x (Agent Runtime Architecture) + SS6.5 (Long-lived Agent Sessions)** of the Lyra upgrade plan. Specifically:

- The client-server socket model addresses the "agent session lifecycle" section in 4.x -- how an agent's state outlives the tool/IDE process.
- The imsg-based protocol design applies to 6.5's requirement for "session serialisation and resumption across host restarts."
- The control mode (`-C`) pattern informs Lyra's programmatic API layer for external orchestration.

### Impact / Effort / Tier

| Dimension | Rating | Rationale |
|-----------|--------|-----------|
| **Impact** | 8/10 | This is a foundational architectural change. Detachable sessions affect every layer: state management, IPC protocol, lifecycle, observability. High leverage but also high blast radius. |
| **Effort** | 7/10 | Requires designing a new IPC protocol akin to tmux-protocol.h, a server daemon pattern, state serialisation for session resume, and coordination with the existing plugin/extension architecture. Many weeks of work. |
| **Tier** | Tier-1 (Core) | This is not an incremental bolt-on. The session architecture is a Tier-1 concern -- it defines how all other subsystems (memory, context, tools, plugins) interact with the runtime. |

### LICENSE

tmux is licensed under the **ISC license** (equivalent to MIT/BSD-2-Clause). The full text in `COPYING` reads:

> Permission to use, copy, modify, and distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

This is a maximally permissive license. Code from tmux (or the imsg framework) can be incorporated into Lyra without license compatibility concerns. Attribution is required only in source file headers (the notice must appear "in all copies").
