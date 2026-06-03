# rmux Clean-Room Rebuild — Plan (§5.1)

> Run 1 — June 3, 2026

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

## Build Outline

1. PTY manager (spawn, resize, signal handling)
2. Pane layout engine (split, resize, focus)
3. Detach/reattach protocol (Unix socket)
4. Worktree integration (pane → worktree mapping)
5. TUI rendering (Textual-based)

**Impact:** 3 | **Effort:** 4 | **Tier:** (A) Parity
