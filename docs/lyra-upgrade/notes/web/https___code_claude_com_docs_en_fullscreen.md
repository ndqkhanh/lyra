# Fullscreen Rendering (code.claude.com / Anthropic)

## Key Technical Claims

1. **Alternate-screen rendering** for Claude Code CLI that eliminates flicker, flat-lines memory usage over long conversations, and adds in-app mouse support.
2. Only **visible messages** are kept in the render tree -- invisible/historical messages are not drawn, so terminal data volume per update drops and memory stays constant regardless of conversation length.
3. Input box stays anchored at the **bottom** of the screen rather than floating with output.
4. Most impactful in terminals where rendering throughput is the bottleneck: VS Code integrated terminal, tmux, iTerm2.
5. If your scroll position jumps to top during work, or screen flashes as tool output streams in, this mode addresses both problems.

## Architecture / Mechanism Details

- Uses the terminal's **alternate screen buffer** (the same technique as `vim`, `htop`) so the conversation is not in the terminal's native scrollback.
- Switch: `/tui fullscreen` (mid-session, saves setting and relaunches with conversation intact) or `CLAUDE_CODE_NO_FLICKER=1` env var before startup.
- The `tui` setting and env var are equivalent; `/tui` clears the env var from the relaunched process so the setting takes effect.
- Mouse capture handles: cursor positioning in input, suggestion/file-list acceptance, click-to-expand collapsed tool results, URL/file-path clicks, text selection (click-drag, double-click word, triple-click line). Selected text copies to clipboard on mouse release automatically.
- Transcript mode (`Ctrl+o`): `less`-style navigation and `/` search; `[` writes conversation back to native scrollback; `v` opens in $EDITOR.
- Focus mode (`/focus`): quieter view showing only last prompt, one-line tool-call summary with diffstats, and final response.
- Auto-follow pauses on manual scroll; `Ctrl+End` or scroll-to-bottom resumes following.
- Scroll speed configurable via `CLAUDE_CODE_SCROLL_SPEED` (1-20) or `/scroll-speed` interactive dialog.
- Mouse capture can be disabled via `CLAUDE_CODE_DISABLE_MOUSE=1` while keeping flicker-free rendering and flat memory.
- Background sessions from `claude attach` always use fullscreen rendering regardless of `tui` setting.
- iTerm2 tmux integration mode (`tmux -CC`) is incompatible; regular tmux inside iTerm2 works.
- Requires Claude Code v2.1.89+ (v2.1.110 for the env-var method).
- Marked as **research preview** -- behavior may change based on feedback.

## Numbers & Benchmarks

- **Scrolling**: `CLAUDE_CODE_SCROLL_SPEED` range 1-20. Value of 3 matches vim default.
- **Clear gesture**: Double `Ctrl+L` within 2 seconds triggers `/clear`.
- **JetBrains** (2025.2) has scroll-wheel bugs producing spurious arrow-keys and wrong-direction events; Claude Code detects and mitigates at runtime. 2025.3+ recommended.

## Transfer to Lyra

**One idea**: *Virtualized render tree / visible-window rendering.*

Fullscreen rendering decouples what is *drawn* from what *exists* in the conversation by only keeping visible messages in the render tree. This keeps memory and update cost flat regardless of total conversation length.

**Transfer**: Lyra should apply the same principle to its **context window and memory management**. Instead of loading the full context into the working window, Lyra should maintain a "visible window" of only the currently relevant context segment. As focus shifts, older context segments are evicted from the active window (not from long-term storage) and new segments are loaded. This keeps the per-turn token budget flat and prevents the context window from gradually filling with stale history.

**Workstream route**: This maps to Lyra's memory/context optimization plans.

- **Memory plan**: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/plans/02-memory.md`
- **Context plan**: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/brainstorm/03-context.md`
