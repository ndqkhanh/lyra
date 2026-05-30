# Voice System: Session Sounds & Audio Feedback

**Version:** 1.0.0
**Date:** 2026-05-30
**Status:** Implementation Design - Ready
**Based on:** Warcraft III peon voice article, Claude Code hooks sound article, Phase 3 Research

---

## Executive Summary

The Voice System adds non-intrusive audio feedback to Lyra sessions using Warcraft III-inspired voice notifications, session lifecycle sounds, and customizable sound themes. Designed for cross-platform compatibility with minimal dependencies.

---

## I. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                       VOICE SYSTEM                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. AUDIO ENGINE                                           │   │
│  │ Cross-platform playback (sounddevice/pygame)               │   │
│  │ Sound file management | Volume control                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. SESSION LIFECYCLE SOUNDS                               │   │
│  │ Start (funny voice) | Pause | Resume | Complete | Error    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3. WORKFLOW SOUNDS                                        │   │
│  │ Agent start/finish | Success/error | Notification          │   │
│  │ Progress updates | Milestone reached                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 4. SOUND THEME MANAGER                                    │   │
│  │ Multiple sound packs | User customization                  │   │
│  │ Enable/disable | Per-event configuration                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## II. Core Components

### 2.1 Audio Engine

```python
class AudioEngine:
    """Cross-platform audio playback with fallback support."""

    def __init__(self, backend: str = 'auto'):
        self.backend = self._select_backend(backend)
        self.sounds: dict[str, Sound] = {}
        self.volume: float = 0.7
        self.enabled: bool = True
        self._load_default_sounds()

    def _select_backend(self, preference: str):
        """Auto-select best available audio backend."""
        backends = []
        try:
            import sounddevice
            backends.append(SoundDeviceBackend())
        except ImportError:
            pass
        try:
            import pygame
            pygame.mixer.init()
            backends.append(PygameBackend())
        except (ImportError, Exception):
            pass
        try:
            import playsound
            backends.append(PlaySoundBackend())
        except ImportError:
            pass
        if not backends:
            raise NoAudioBackendError(
                "Install sounddevice, pygame, or playsound"
            )
        return backends[0]

    async def play(self, sound_id: str, volume: float = None):
        if not self.enabled:
            return
        sound = self.sounds.get(sound_id)
        if not sound:
            return
        vol = volume if volume is not None else self.volume
        await self.backend.play(sound.file_path, volume=vol)

    async def play_async(self, sound_id: str):
        asyncio.create_task(self.play(sound_id))
```

### 2.2 Session Lifecycle Sounds

```python
class SessionSounds:
    """Sound notifications for session lifecycle events."""

    FUNNY_VOICES = {
        'startup': [
            'peon_ready_to_work.wav',    # "Ready to work!"
            'peon_yes_milord.wav',        # "Yes, milord?"
            'peon_more_work.wav',         # "More work?"
        ],
        'complete': [
            'peon_job_done.wav',          # "Job's done!"
            'peon_work_complete.wav',     # "Work complete!"
        ],
        'error': [
            'peon_cant_do_that.wav',      # "I can't do that!"
            'peon_not_enough.wav',        # "Not enough gold!"
        ],
    }

    def __init__(self, engine: AudioEngine):
        self.engine = engine

    async def on_session_start(self):
        sound = random.choice(self.FUNNY_VOICES['startup'])
        await self.engine.play_async(sound)

    async def on_session_complete(self):
        sound = random.choice(self.FUNNY_VOICES['complete'])
        await self.engine.play_async(sound)

    async def on_error(self):
        sound = random.choice(self.FUNNY_VOICES['error'])
        await self.engine.play_async(sound)
```

### 2.3 Workflow & Agent Sounds

```python
class WorkflowSounds:
    """Sound notifications for workflow and agent events."""

    SOUNDS = {
        'agent_spawned': 'agent_appear.wav',
        'agent_completed': 'agent_done.wav',
        'agent_error': 'agent_fail.wav',
        'tool_executing': 'tool_use.wav',
        'tool_success': 'tool_success.wav',
        'tool_error': 'tool_error.wav',
        'debate_started': 'debate_bell.wav',
        'consensus_reached': 'agreement_chime.wav',
        'milestone_hit': 'milestone.wav',
        'research_finding': 'discovery.wav',
        'warning': 'warning_alert.wav',
        'escalation': 'escalation_alert.wav',
    }

    def __init__(self, engine: AudioEngine):
        self.engine = engine

    async def on_agent_event(self, event: AgentEvent):
        sound_id = self.SOUNDS.get(event.type)
        if sound_id:
            await self.engine.play_async(sound_id)
```

### 2.4 Sound Theme Manager

```python
class SoundThemeManager:
    """Manage sound themes and user preferences."""

    THEMES = {
        'warcraft3': {
            'name': 'Warcraft III Peon',
            'description': 'Classic Warcraft III peon voice lines',
            'sounds': {
                'startup': 'peon_ready_to_work.wav',
                'complete': 'peon_job_done.wav',
                'error': 'peon_cant_do_that.wav',
            }
        },
        'minimal': {
            'name': 'Minimal Chimes',
            'description': 'Subtle chime notifications only',
            'sounds': {
                'startup': 'soft_start.wav',
                'complete': 'soft_complete.wav',
                'error': 'soft_error.wav',
            }
        },
        'scifi': {
            'name': 'Sci-Fi Computer',
            'description': 'Futuristic computer sounds',
            'sounds': {
                'startup': 'computer_boot.wav',
                'complete': 'task_complete.wav',
                'error': 'system_error.wav',
            }
        },
    }

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.active_theme = self._load_preference('theme', 'warcraft3')
        self.volume = self._load_preference('volume', 0.7)
        self.enabled_events = self._load_preference('enabled_events', [
            'session_start', 'session_complete', 'error'
        ])

    def set_theme(self, theme_id: str):
        if theme_id not in self.THEMES:
            raise ValueError(f"Unknown theme: {theme_id}")
        self.active_theme = theme_id
        self._save_preference('theme', theme_id)

    def is_event_enabled(self, event_id: str) -> bool:
        return event_id in self.enabled_events

    def toggle_event(self, event_id: str):
        if event_id in self.enabled_events:
            self.enabled_events.remove(event_id)
        else:
            self.enabled_events.append(event_id)
        self._save_preference('enabled_events', self.enabled_events)
```

---

## III. Implementation Phases

### Phase 1: Core Audio (Weeks 1-2)
- Audio engine with backend selection (sounddevice, pygame, playsound)
- Session lifecycle sounds (start, pause, resume, complete, error)
- Basic WAV file playback
- **Tests:** 15 unit tests

### Phase 2: Themes & Preferences (Weeks 3-4)
- Sound theme system (warcraft3, minimal, scifi)
- User preferences (enable/disable, volume, per-event config)
- Workflow and agent event sounds
- Sound file management
- **Tests:** 15 unit tests + 5 integration

---

## IV. Testing Plan

| Test Type | Count | Coverage |
|-----------|-------|----------|
| Audio engine | 10 | 90% |
| Session sounds | 10 | 90% |
| Workflow sounds | 5 | 85% |
| Theme manager | 10 | 95% |
| Integration | 5 | N/A |
| **Total** | **40** | **90%+** |

---

## V. Success Metrics

- [ ] Non-intrusive audio feedback working
- [ ] Cross-platform compatibility (macOS, Linux, Windows)
- [ ] 3 sound themes available
- [ ] User preferences persisted and working
- [ ] Warcraft III peon voices for startup/complete/error
- [ ] <50ms audio playback latency
- [ ] Zero dependencies required (graceful fallback)
- [ ] 40+ tests, 90%+ coverage
