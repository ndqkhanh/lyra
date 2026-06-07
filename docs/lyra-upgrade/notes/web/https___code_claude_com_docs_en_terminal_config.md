# Configure your terminal for Claude Code (code.claude.com — Anthropic)

No publication date or named author on page. Anthropic product documentation.

## Key Technical Claims

1. Claude Code works in any terminal without configuration by default; this page is only for specific behavioral fixes.
2. Multiline prompts: Enter submits, Ctrl+J or backslash+Enter inserts newlines. Shift+Enter support varies by terminal; `/terminal-setup` auto-configures it for VS Code, Cursor, Devin Desktop, Alacritty, and Zed.
3. macOS Option-key shortcuts (e.g. Option+Enter for newline, Option+P for model switch) require "Use Option as Meta Key" in the terminal profile. `/terminal-setup` configures this automatically for Apple Terminal and iTerm2.
4. Notification surface: built-in desktop notification for Ghostty/Kitty/iTerm2; `preferredNotifChannel: "terminal_bell"` for other terminals; custom Notification hook for arbitrary commands.
5. tmux breaks two things by default: Shift+Enter (needs `extended-keys` + `terminal-features`), and notifications (needs `allow-passthrough`).
6. Theme system: `/theme` command or theme picker in `/config`; custom themes are JSON files in `~/.claude/themes/` with `name`, `base` (one of six presets), and `overrides` (map of color tokens). Live-reloads on file change.
7. Fullscreen rendering mode via `/tui fullscreen` or `CLAUDE_CODE_NO_FLICKER=1` env var; fixes flicker/scrollback jitter.
8. Large paste (>10,000 characters) collapses to `[Pasted text]` placeholder in input box; full content still sent on submit.
9. Vim editing mode via `/config` or `editorMode: "vim"` setting; subset of NORMAL/VISUAL motions.

## Architecture/Mechanism Details

- **Notification system** uses a tiered strategy: (1) built-in desktop notification for supported terminals, (2) `preferredNotifChannel` setting to redirect to terminal bell, (3) custom Notification hook that runs alongside the built-in notification. Hooks are JSON-configured commands in `~/.claude/settings.json`, e.g. `afplay /System/Library/Sounds/Glass.aiff` on macOS.
- **Theme system**: directory watch on `~/.claude/themes/` — files are reloaded on change with no session restart required. Three optional fields in JSON: `name`, `base` (preset to extend), `overrides` (color token map). 50+ tokens across text/accent, status, input box, diff rendering, fullscreen mode, usage meter, subagent colors, and rainbow gradient tokens for `ultrathink`/`ultraplan`.
- **Terminal setup command** (`/terminal-setup`) probes the terminal emulator, then writes keybindings to the terminal's own config file. In VS Code/Cursor/Devin it also sets `terminal.integrated.gpuAcceleration: "off"` and `terminal.integrated.mouseWheelScrollSensitivity`.
- **tmux passthrough**: three-line `~/.tmux.conf` config enables `allow-passthrough`, `extended-keys`, and `terminal-features 'xterm*:extkeys'`. Passthrough lets notifications and progress bars reach the outer terminal.

## Numbers & Benchmarks

- Paste collapse threshold: **10,000 characters**
- Custom themes minimum version: **Claude Code v2.1.118+**
- Subagent colors: 8 named colors (red, blue, green, yellow, purple, orange, pink, cyan)
- Rainbow gradient tokens: 7 colors (red, orange, yellow, green, blue, indigo, violet) plus shimmer variants
- Six built-in theme presets: dark, light, dark-daltonized, light-daltonized, dark-ansi, light-ansi

## Transfer to Lyra

**Notification hook pattern with tiered fallback.** Claude Code's notification system uses a layered strategy: desktop notification for supported terminals, then terminal bell, then an arbitrary user-configured hook command. This is directly transferable to Lyra's agent runtime as a `Notification` hook that fires when async tasks complete — subagents finishing long operations, permission prompts blocking, or research tasks landing. Lyra could adopt the same `hooks.Notification` array in its settings, with the same "hooks run alongside built-in notification" semantic so users can layer custom alerts (e.g. Slack webhook + macOS notification + play a sound) without losing the default behavior.

Secondary transfer: the live-reload theme/watch-directory pattern (`~/.claude/themes/` file watcher). Lyra's plugin configuration and user preferences could use the same file-watch approach — write a JSON config file in a watched directory and have the runtime pick it up without a session restart.

**Workstream route:** §4.4 — Developer Experience, hooked into the agent runtime's task lifecycle events.
