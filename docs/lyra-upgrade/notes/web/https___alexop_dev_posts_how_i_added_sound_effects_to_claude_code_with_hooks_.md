# How I Added Sound Effects to Claude Code with Hooks (alexop.dev)

**Author:** Alexander Opalic (alexop.dev)
**Date:** February 11, 2026
**URL:** https://alexop.dev/posts/how-i-added-sound-effects-to-claude-code-with-hooks/

---

## Key Technical Claims

1. Claude Code's hooks system (four lifecycle events: SessionStart, UserPromptSubmit, Stop, PreCompact) can be used for non-urgent UX enhancement -- not just safety/validation gating.
2. The `&` suffix on hook shell commands backgrounds the audio player, preventing the sound from blocking Claude Code's execution flow.
3. The PreCompact hook (fires before context compaction) is the most creative hook point: mapping an abstract, invisible system event to a recognizable audio cue (Age of Empires "wololo" priest conversion sound) makes the internal process perceptible to the user.
4. Hook commands can create marker files via `touch` (e.g., `touch ~/.claude/.claude-done`) for cross-process signaling -- a terminal status-line script reads these to display state.

## Architecture/Mechanism Details

- **Config location:** `~/.claude/settings.json` -- hooks are JSON objects inside the `hooks` key.
- **Four lifecycle events:**
  - `SessionStart` -- fires on startup or `/clear` (uses `matcher: "startup|clear"` to scope).
  - `UserPromptSubmit` -- fires on every user prompt submission (unconditional).
  - `Stop` -- fires when Claude Code stops (unconditional).
  - `PreCompact` -- fires before context compaction (unconditional).
- **macOS audio player:** `afplay` (built-in, no dependency).
- **Linux alternatives:** `aplay` or `paplay`.
- **Windows WSL alternative:** `powershell.exe -c (New-Object Media.SoundPlayer "path").PlaySync()`.
- **Sound storage:** `~/.claude/sounds/` directory, MP3 files.
- **Setup time claimed:** 5 minutes.
- **Sound-to-event mapping:**
  | Event | File | Meaning |
  |---|---|---|
  | SessionStart | horn.mp3 | Battle horn -- work begins |
  | UserPromptSubmit | yes.mp3 | Villager acknowledgment |
  | Stop | allhail.mp3 | Victory/king tribute |
  | PreCompact | wololo.mp3 | Priest conversion -- context gets "converted" |

## Numbers & Benchmarks

- No latency benchmarks, cost figures, or performance measurements reported.
- 4 sound files, 4 hook events configured.
- Claimed setup time: 5 minutes.
- The `&` backgrounding pattern is the critical detail for non-blocking operation -- without it, audio playback would block the Claude Code process until the sound file finished playing.

## Transfer to Lyra

**One idea: Non-blocking ambient lifecycle audio for the Supervisor Daemon.**

In Lyra's fleet-centric architecture, the Supervisor Daemon manages multiple concurrent sessions. Each session has lifecycle events (spawned, running, completed, failed, compacted). Adding ambient audio cues to these events would solve a real problem: users running background fleet sessions cannot easily tell when a task finishes or fails without constantly checking the TUI. A short non-blocking `afplay` (or platform-appropriate player) triggered on lifecycle transitions would provide peripheral awareness without adding latency to the primary agent loop.

**Why this maps well:**
- The Supervisor Daemon already has a well-defined event system (session lifecycle: running/done/failed).
- Non-blocking backgrounding (`&` or equivalent async spawn) is architecturally trivial -- the supervisor just forks a subprocess.
- Cross-platform audio players (`afplay`/`aplay`/`paplay`) require zero dependencies.
- The pattern extends beyond audio: the same lifecycle hooks could fire desktop notifications (`osascript -e 'display notification'` on macOS, `notify-send` on Linux) or update a status bar via file touch.

**Workstream route:** Observability Plane (ambient UX affordances on Supervisor Daemon lifecycle events). This is a Phase 3 (fleet) ancillary feature with zero dependency chain -- could be shipped as a quick UX win alongside the Supervisor Daemon or even added as an early Phase 1-2 enhancement to the existing single-session event loop.
