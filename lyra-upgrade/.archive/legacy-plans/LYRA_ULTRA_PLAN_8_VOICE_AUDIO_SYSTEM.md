# LYRA ULTRA PLAN 8: Voice & Audio System — Complete Blueprint

**Version:** 1.0.0 | **Status:** In Progress | **Created:** 2026-05-25
**Parent Plan:** [LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md](LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md)

---

## Overview

Build a world-class voice and audio notification system for Lyra — Warcraft III Peon-style voice packs, cross-platform sound effects via hooks, voice dictation, and MCP-controlled audio. The system has two tiers: Simple (4-hook, minimal) and Full (PeonPing-style 8-event pipeline).

---

## Part 1: Voice Pack System

### 1.1 Pack Architecture

```
~/.lyra/sounds/
├── packs/
│   ├── fantasy/                    # Warcraft III Peon/Peasant voices
│   │   ├── manifest.json
│   │   ├── session_start.wav       # "Ready to work!"
│   │   ├── session_end.wav         # "Job's done!"
│   │   ├── task_start.wav          # "Alright."
│   │   ├── task_complete.wav       # "Work complete!"
│   │   ├── task_error.wav          # "Whaaat?"
│   │   ├── approval_needed.wav     # "Your orders?"
│   │   ├── thinking.wav            # "Hmm..."
│   │   ├── compact.wav             # "I need more gold... er, tokens!"
│   │   ├── permission.wav          # "Who goes there?"
│   │   └── spam.wav                # "Stop poking me!"
│   │
│   ├── sci-fi/                     # Robot/AI voices
│   │   ├── manifest.json
│   │   ├── session_start.wav       # "Systems online. Hello, commander."
│   │   ├── session_end.wav         # "Mission accomplished. Shutting down."
│   │   ├── task_complete.wav       # "Task terminated successfully."
│   │   └── ...
│   │
│   ├── rick-morty/                 # Rick & Morty style
│   │   ├── manifest.json
│   │   ├── session_start.wav       # "Wubba lubba dub dub! Let's do this!"
│   │   ├── task_error.wav          # "And that's the waaaaay the news goes!"
│   │   └── ...
│   │
│   ├── minimal/                    # Subtle chimes (default)
│   │   ├── manifest.json
│   │   ├── session_start.wav       # Gentle ascending chime
│   │   ├── session_end.wav         # Gentle descending chime
│   │   ├── task_complete.wav       # Soft click
│   │   ├── task_error.wav          # Alert tone
│   │   ├── thinking.wav            # Soft pulse
│   │   └── approval_needed.wav     # Inquisitive tone
│   │
│   ├── anime/                      # Anime-style voices
│   │   ├── manifest.json
│   │   └── ...
│   │
│   ├── nature/                     # Nature sounds
│   │   ├── manifest.json
│   │   └── ...
│   │
│   └── custom/                     # User-provided
│       ├── manifest.json
│       └── ...
│
├── config.json                     # Voice pack configuration
└── cache/                          # Cached/converted audio files
```

### 1.2 Manifest Format

```json
{
  "name": "Fantasy (Peon Edition)",
  "id": "fantasy",
  "version": "1.0.0",
  "author": "Lyra Audio Team",
  "description": "Warcraft III Peon voice notifications. 'Ready to work!'",
  "license": "CC-BY-4.0",
  "categories": {
    "session.start": ["session_start.wav", "session_start_alt.wav"],
    "session.end": ["session_end.wav"],
    "task.start": ["task_start.wav"],
    "task.complete": ["task_complete.wav", "task_complete_rare.wav"],
    "task.error": ["task_error.wav", "task_error_alt.wav"],
    "input.required": ["approval_needed.wav"],
    "thinking.start": ["thinking.wav"],
    "thinking.end": [],
    "resource.limit": ["compact.wav"],
    "permission.check": ["permission.wav"],
    "user.spam": ["spam.wav"],
    "goal.complete": ["goal_complete.wav"]
  },
  "no_repeat": true,
  "cooldown_ms": 3000,
  "volume": 0.7
}
```

### 1.3 Pack Selection Hierarchy (6 Layers)

Inspired by PeonPing:

| Priority | Layer | Description |
|----------|-------|-------------|
| 1 | `session_override` | Per-session via `/voice-pack` command or MCP |
| 2 | `path_rules` | Glob match on working directory |
| 3 | `ide_rules` | Match on IDE/source (claude, cursor, lyra, etc.) |
| 4 | `pack_rotation` | Random or round-robin across enabled packs |
| 5 | `default_pack` | Static fallback in `~/.lyra/sounds/config.json` |
| 6 | Hardcoded fallback | `minimal` pack (always available) |

```json
// ~/.lyra/sounds/config.json
{
  "default_pack": "fantasy",
  "packs_enabled": ["fantasy", "sci-fi", "minimal"],
  "rotation": "random",
  "path_rules": {
    "**/production/**": "minimal",
    "**/gaming/**": "fantasy",
    "**/research/**": "sci-fi"
  },
  "suppression": {
    "headphones_only": false,
    "suppress_when_tab_focused": false,
    "meeting_detect": true,
    "silent_hours": ["22:00-07:00"],
    "annoyed_threshold": 5,
    "annoyed_window_seconds": 60
  }
}
```

---

## Part 2: Event-to-Sound Mapping

### 2.1 CESP Event Standard

All Lyra events map to the Cross-Environment Sound Protocol (CESP) v1.0:

| Lyra Hook Event | CESP Category | Trigger |
|-----------------|---------------|---------|
| `SessionStart` | `session.start` | New session or `/clear` |
| `SessionEnd` | `session.end` | Session exit |
| `UserPromptSubmit` | `task.start` | User sends message |
| `Stop` | `task.complete` | Agent finishes responding |
| `PostToolUseFailure` | `task.error` | Tool call fails |
| `PermissionRequest` | `input.required` | Permission needed from user |
| `PreCompact` | `resource.limit` | Context compaction triggered |
| `Notification` (idle) | `task.complete` | Idle prompt (deduplicated) |

### 2.2 Five-Phase Pipeline

```
[Hook Event] → [Event Mapping] → [Sound Selection] → [Audio Playback] → [Notification]
```

**Phase 1 — Event Mapping:**
```python
EVENT_MAP = {
    "SessionStart": "session.start",
    "SessionEnd": "session.end",
    "UserPromptSubmit": "task.start",
    "Stop": "task.complete",
    "PostToolUseFailure": "task.error",
    "PermissionRequest": "input.required",
    "PreCompact": "resource.limit",
    "Notification": "task.complete",  # Dedup: skip if <3s since last task.complete
}
```

**Phase 2 — Sound Selection:**
```python
def select_sound(pack: VoicePack, category: str) -> Path:
    candidates = pack.manifest["categories"][category]
    if not candidates:
        return None
    # No-repeat logic: track last played per category
    available = [c for c in candidates if c != pack.last_played.get(category)]
    if not available:
        available = candidates  # Reset if all exhausted
    chosen = random.choice(available)
    pack.last_played[category] = chosen
    return pack.path / chosen
```

**Phase 3 — Audio Playback (Cross-Platform):**
```python
def play_sound(filepath: Path):
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(["afplay", str(filepath)])
    elif system == "Linux":
        for player in ["pw-play", "paplay", "ffplay", "mpv", "play", "aplay"]:
            if shutil.which(player):
                subprocess.Popen([player, str(filepath)])
                break
    elif system == "Windows":
        subprocess.Popen([
            "powershell", "-c",
            f'(New-Object Media.SoundPlayer "{filepath}").PlaySync()'
        ])
    # Always backgrounded — never blocks the agent
```

**Phase 4 — Desktop Notifications:**
- macOS: JXA Cocoa overlay or `terminal-notifier`
- Linux: `notify-send`
- Windows: Toast notifications

**Phase 5 — Remote Routing (SSH/Containers):**
- Detect: `SSH_TTY`, `REMOTE_CONTAINERS`, `CODESPACES` env vars
- Relay: HTTP POST to `http://host.lyra.local:19998/play?category=<cat>`
- Relay server runs on local machine

### 2.3 Simple Mode (4-Hook Minimal)

For users who want simple sound effects without the full pipeline:

```json
// ~/.lyra/settings.json
{
  "hooks": {
    "SessionStart": [
      {"matcher": "startup|clear", "command": "afplay ~/.lyra/sounds/start.wav &"}
    ],
    "UserPromptSubmit": [
      {"matcher": "", "command": "afplay ~/.lyra/sounds/click.wav &"}
    ],
    "Stop": [
      {"matcher": "", "command": "afplay ~/.lyra/sounds/complete.wav &"}
    ],
    "PreCompact": [
      {"matcher": "", "command": "afplay ~/.lyra/sounds/compact.wav &"}
    ]
  }
}
```

**Critical pattern:** Trailing `&` backgrounds audio so it never blocks Lyra.

---

## Part 3: Voice Dictation

### 3.1 Architecture

```
[Microphone] → [Speech-to-Text] → [Text Buffer] → [Lyra Input]
```

### 3.2 Providers

| Provider | Quality | Latency | Cost | Setup |
|----------|---------|---------|------|-------|
| **Whisper API** (OpenAI) | Highest | ~500ms | ~$0.006/min | API key |
| **Whisper Local** (whisper.cpp) | High | ~200ms | Free | Local install |
| **macOS Dictation** | Medium | ~300ms | Free | Built-in |
| **Deepgram** | High | ~100ms | ~$0.005/min | API key |
| **Web Speech API** | Medium | ~200ms | Free | Browser only |

### 3.3 Keybindings

| Key | Action |
|-----|--------|
| `Ctrl+Shift+V` | Start/stop voice dictation |
| `Ctrl+Shift+V` (again) | Stop and submit |
| `Esc` | Cancel dictation |

### 3.4 Voice Command Mode

Voice commands for hands-free operation:
- "Lyra, run the tests" → `lyra run "run the tests"`
- "Lyra, what's the status?" → `lyra status`
- "Lyra, switch to Opus" → `/model opus`
- "Lyra, approve" → Approve pending permission
- "Lyra, clear" → `/clear`

---

## Part 4: MCP Audio Server

### 4.1 MCP Tools

```json
{
  "tools": [
    {
      "name": "play_sound",
      "description": "Play a sound by category key",
      "parameters": {
        "category": {"type": "string", "enum": ["session.start", "task.complete", "task.error", "input.required", "resource.limit"]},
        "pack": {"type": "string", "optional": true},
        "volume": {"type": "number", "minimum": 0, "maximum": 1, "optional": true}
      }
    },
    {
      "name": "set_voice_pack",
      "description": "Switch active voice pack",
      "parameters": {
        "pack_id": {"type": "string"},
        "persist": {"type": "boolean", "default": false}
      }
    },
    {
      "name": "list_voice_packs",
      "description": "List available voice packs"
    },
    {
      "name": "preview_sound",
      "description": "Preview a specific sound from a pack",
      "parameters": {
        "pack_id": {"type": "string"},
        "category": {"type": "string"}
      }
    },
    {
      "name": "speak",
      "description": "Text-to-speech output",
      "parameters": {
        "text": {"type": "string"},
        "voice": {"type": "string", "optional": true},
        "speed": {"type": "number", "optional": true}
      }
    }
  ]
}
```

### 4.2 MCP Resources

```
lyra-audio://packs                    # Full pack catalog
lyra-audio://packs/{id}/manifest      # Individual pack details
lyra-audio://config                   # Current audio configuration
lyra-audio://history                  # Recent playback history
```

---

## Part 5: Implementation Roadmap

### Phase 8.1: Core Audio Engine (Weeks 1-2)
- [ ] Cross-platform audio player (afplay/paplay/powershell chain)
- [ ] Hook event → CESP event mapping
- [ ] Simple 4-hook mode with backgrounded audio
- [ ] `~/.lyra/sounds/` directory structure

### Phase 8.2: Voice Packs (Weeks 3-4)
- [ ] Fantasy (Peon) pack — 10 sounds
- [ ] Minimal pack — 6 sounds
- [ ] Sci-Fi pack — 6 sounds
- [ ] Pack manifest format + validation
- [ ] No-repeat sound selection logic

### Phase 8.3: Advanced Pipeline (Weeks 5-6)
- [ ] Full 5-phase pipeline
- [ ] Desktop notifications
- [ ] Terminal focus detection
- [ ] Pack selection hierarchy (6 layers)
- [ ] Suppression settings (silent hours, meeting detect, spam protection)

### Phase 8.4: MCP & Remote (Weeks 7-8)
- [ ] MCP audio server (play_sound, set_voice_pack, list_voice_packs, speak)
- [ ] SSH/container relay server
- [ ] TTS integration (system say command, OpenAI TTS)

### Phase 8.5: Voice Dictation (Weeks 9-10)
- [ ] Voice dictation keybinding (Ctrl+Shift+V)
- [ ] Whisper API integration
- [ ] macOS Dictation integration
- [ ] Voice command mode
- [ ] Additional voice packs (Rick & Morty, Anime, Nature)

---

## Part 6: Reference & Inspiration

| Source | Key Ideas Adopted |
|--------|------------------|
| [PeonPing](https://github.com/PeonPing/peon-ping) | 8-event hook model, 5-phase pipeline, CESP standard, pack hierarchy, cross-platform playback, SSH relay, MCP server |
| [Alexop Sound Effects](https://alexop.dev/posts/how-i-added-sound-effects-to-claude-code-with-hooks/) | 4-hook simple model, `afplay` + `&` pattern, marker files |
| [Warcraft III Peon Voice](https://freedium-mirror.cfd/https://medium.com/@gentechimports/warcraft-iii-peon-voice-notifications-for-claude-code-a-developers-story-dd6842deb852) | Voice pack concept, Peon lines as notification sounds |
| [Claude Code Voice Dictation](https://code.claude.com/docs/en/voice-dictation) | Voice dictation keybinding, system STT integration |
| [Claude Code Hooks](https://code.claude.com/docs/en/hooks) | Hook events, matcher patterns, command-type handlers |
