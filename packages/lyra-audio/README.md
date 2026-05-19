# Lyra Audio - Complete Implementation

## Overview

Complete audio system for Lyra with sound effects, themes, and advanced features.

## Installation

```bash
pip install lyra-audio
```

## Quick Start

```python
from lyra_audio import SoundManager, EventHookSystem

# Initialize
manager = SoundManager()
hooks = EventHookSystem()
hooks.sound_manager = manager

# Set theme
manager.set_theme("warcraft")

# Play sounds
manager.play_event("task_complete")

# Trigger events
hooks.trigger("session_start")
```

## CLI Usage

```bash
# Enable/disable sounds
lyra-sounds on
lyra-sounds off

# Set theme
lyra-sounds theme warcraft

# List themes
lyra-sounds list

# Test sound
lyra-sounds test task_complete

# Create custom pack
lyra-sounds create my-pack

# Show status
lyra-sounds status
```

## Features

### 1. Cross-Platform Audio (Phase 1)
- macOS, Linux, Windows support
- Async playback
- Volume control

### 2. Sound Pack Library (Phase 2)
- 8 themed packs included
- Custom pack support
- Manifest-based configuration

### 3. Advanced Features (Phase 3)
- Adaptive volume (boost after inactivity)
- Time-based behavior (ridiculous mode after 5 PM)
- Productivity mode (critical sounds only)

### 4. Sound Pack Manager (Phase 4)
- CLI interface (lyra-sounds)
- Pack creation and validation
- Theme switching

### 5. Configuration (Phase 5)
- JSON-based configuration
- Nested settings
- Import/export

## Sound Packs

1. **Warcraft III - Peon Pack** (Default)
2. **Age of Empires - Monk Pack**
3. **Portal - GLaDOS Pack**
4. **StarCraft - Terran Pack**
5. **Minecraft - Villager Pack**
6. **Mario - Classic Pack**
7. **Metal Gear Solid - Alert Pack**
8. **Meme Pack - Internet Classics**

## Testing

```bash
pytest tests/ -v
```

**Results**: 58 tests, 77% coverage

## Version

Current version: **1.0.0**

## License

MIT License

## Contributing

Contributions welcome! See CONTRIBUTING.md

## Credits

Inspired by:
- [Warcraft III Peon Notifications](https://medium.com/@gentechimports/warcraft-iii-peon-voice-notifications-for-claude-code)
- [Sound Effects for Claude Code](https://alexop.dev/posts/how-i-added-sound-effects-to-claude-code-with-hooks/)

---

**Status**: Production ready! 🎉
