# Lyra Audio - Phase 1: Audio System Foundation

## Overview

Phase 1 implements the foundational audio system for Lyra, enabling cross-platform audio playback and event-driven sound effects.

## Features

### 1. Audio Player (`audio_player.py`)

Cross-platform audio playback:

```python
from lyra_audio import AudioPlayer

player = AudioPlayer()

# Play sound (blocking)
player.play("/path/to/sound.mp3")

# Play sound (non-blocking)
player.play_async("/path/to/sound.mp3")

# Play with volume control
player.play("/path/to/sound.mp3", volume=0.8)
```

**Platform Support**:
- macOS: `afplay`
- Linux: `aplay`, `paplay`, `ffplay`
- Windows: `winsound`

### 2. Sound Manager (`sound_manager.py`)

Manage sound effects and themes:

```python
from lyra_audio import SoundManager

manager = SoundManager()

# Play event sound
manager.play_event("task_complete")

# Change theme
manager.set_theme("warcraft")

# List available themes
themes = manager.list_themes()
print(themes)  # ['warcraft', 'glados', 'mario', ...]
```

**Features**:
- Event-to-sound mapping
- Theme switching
- Sound file management
- Volume control

### 3. Event Hook System (`event_hooks.py`)

Hook system for audio events:

```python
from lyra_audio import EventHookSystem

hooks = EventHookSystem()

# Trigger event
hooks.trigger("task_complete")

# Register custom hook
def on_task_complete(context):
    print(f"Task completed: {context}")

hooks.register_hook("task_complete", on_task_complete)
```

**Event Types**:
- Session events: `session_start`, `session_end`
- Task events: `task_start`, `task_complete`, `task_failed`
- User interaction: `prompt_submit`, `prompt_cancel`
- Errors: `error_general`, `error_syntax`, `error_logic`
- System: `context_compact`, `memory_save`
- Achievements: `milestone_10`, `milestone_50`, `milestone_100`

## Architecture

```
┌─────────────────────────────────────────┐
│    Event Hook System                    │
│  (Event-Driven Audio)                   │
│                                         │
│  • Event registration                  │
│  • Hook execution                      │
│  • Custom callbacks                    │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Sound Manager                        │
│  (Sound Effect Management)              │
│                                         │
│  • Event-to-sound mapping              │
│  • Theme management                    │
│  • Sound file loading                  │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Audio Player                         │
│  (Cross-Platform Playback)              │
│                                         │
│  • Platform detection                  │
│  • Async playback                      │
│  • Volume control                      │
└─────────────────────────────────────────┘
```

## Installation

```bash
cd packages/lyra-audio
pip install -e .
```

## Testing

Run tests:
```bash
pytest tests/ -v
```

Tests: 15 tests covering all components

## Usage Examples

### Basic Audio Playback

```python
from lyra_audio import AudioPlayer

player = AudioPlayer()

# Play sound
player.play("sounds/task_complete.mp3")

# Play in background
player.play_async("sounds/notification.mp3")
```

### Event-Driven Sounds

```python
from lyra_audio import EventHookSystem

hooks = EventHookSystem()

# Trigger events
hooks.trigger("session_start")
hooks.trigger("task_complete", {"task": "Build project"})
hooks.trigger("milestone_10")
```

### Theme Management

```python
from lyra_audio import SoundManager

manager = SoundManager()

# Set theme
manager.set_theme("warcraft")

# Play themed sound
manager.play_event("task_complete")  # Plays "Job's done!"

# Change theme
manager.set_theme("glados")
manager.play_event("task_complete")  # Plays "Test complete."
```

## Configuration

Default configuration (`~/.lyra/audio.json`):

```json
{
  "enabled": true,
  "theme": "warcraft",
  "volume": 0.7,
  "soundsDir": "~/.lyra/sounds"
}
```

## Version

Current version: **0.1.0**

## Changes

- Added `AudioPlayer` for cross-platform audio playback
- Added `SoundManager` for sound effect management
- Added `EventHookSystem` for event-driven audio
- Platform detection (macOS, Linux, Windows)
- Async audio playback
- Volume control
- Theme management
- 15 tests with comprehensive coverage

## Next Phase

Phase 2 will implement:
- 8 sound pack library (Warcraft, GLaDOS, Mario, etc.)
- Sound pack manifest format
- Sound file organization
- Pre-configured event mappings

## References

- Lyra Funny Sounds Plan: `.omc/plans/LYRA_FUNNY_SOUNDS_ULTRA_PLAN.md`
- GitHub Repository: https://github.com/ndqkhanh/lyra
