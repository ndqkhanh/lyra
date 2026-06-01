# Lyra Voice System with Funny Sounds

**Version**: 1.0  
**Date**: 2026-05-29  
**Status**: Design Proposal

## Overview

This document defines a comprehensive voice system for Lyra that combines:
1. **Sound effects** - Funny, personality-rich audio feedback
2. **Text-to-Speech (TTS)** - Agent responses as spoken audio
3. **Speech-to-Text (STT)** - Voice input for prompts
4. **Hook integration** - Lifecycle-based audio triggers

## Design Philosophy

**Personality over professionalism**: Lyra should feel like a helpful companion, not a corporate assistant. Sound effects add humor, reduce stress, and make long coding sessions more enjoyable.

**Non-intrusive**: All audio is optional and configurable. Users can disable entirely, choose sound packs, or create custom sounds.

**Cross-platform**: Works on macOS, Linux, and Windows with graceful fallbacks.

## 1. Sound Effect System

### Sound Categories

#### A. Session Lifecycle (4 sounds)

| Event | Sound | Description | Example |
|-------|-------|-------------|---------|
| **SessionStart** | Startup fanfare | Energetic greeting | "Ready to work!" (Peon voice) |
| **SessionEnd** | Completion chime | Satisfying closure | "Work complete!" |
| **SessionResume** | Welcome back | Friendly return | "Back to work!" |
| **SessionSave** | Save confirmation | Quick acknowledgment | *Disk save sound* |

#### B. User Interaction (6 sounds)

| Event | Sound | Description | Example |
|-------|-------|-------------|---------|
| **PromptSubmit** | Acknowledgment | "I got it" confirmation | "Yes, milord?" (Peon) |
| **PromptQueued** | Queue notification | Task added to queue | *Ding* |
| **LongPrompt** | Impressed reaction | For 500+ char prompts | "That's a lot of work!" |
| **EmptyPrompt** | Confused sound | User pressed Enter with no text | "Huh?" |
| **PasteDetected** | Paste notification | Large paste detected | *Whoosh* |
| **ImageAttached** | Image confirmation | Image successfully attached | *Camera shutter* |

#### C. Agent Activity (8 sounds)

| Event | Sound | Description | Example |
|-------|-------|-------------|---------|
| **ThinkingStart** | Thinking sound | Agent starts reasoning | *Gears turning* |
| **ThinkingEnd** | Eureka moment | Solution found | "Aha!" |
| **ToolExecute** | Tool activation | Running a tool | *Mechanical click* |
| **ToolSuccess** | Tool completion | Tool succeeded | *Success chime* |
| **ToolFail** | Tool error | Tool failed | "Oops!" |
| **CodeWrite** | Typing sound | Writing code | *Keyboard clacking* |
| **CodeReview** | Review sound | Reviewing code | *Page flip* |
| **TestRun** | Test execution | Running tests | *Countdown beep* |

#### D. Status Changes (7 sounds)

| Event | Sound | Description | Example |
|-------|-------|-------------|---------|
| **Success** | Victory fanfare | Task completed successfully | "All hail!" (AoE) |
| **Error** | Error alert | Something went wrong | "What?" (Peon) |
| **Warning** | Warning tone | Non-critical issue | *Gentle bell* |
| **ContextLow** | Calm notification | <50% context used | *Soft chime* |
| **ContextHigh** | Urgent warning | >80% context used | *Alert beep* |
| **ContextCompact** | Compression sound | Context compacted | "Wololo!" (AoE) |
| **BackgroundComplete** | Background notification | Background task done | *Notification ding* |

#### E. Special Events (5 sounds)

| Event | Sound | Description | Example |
|-------|-------|-------------|---------|
| **FirstRun** | Welcome tutorial | First time using Lyra | "Welcome, friend!" |
| **Achievement** | Achievement unlock | Milestone reached | *Level up sound* |
| **EasterEgg** | Hidden surprise | Secret command found | *Secret sound* |
| **Interrupt** | Interruption | User interrupted agent | *Record scratch* |
| **ForceExit** | Emergency stop | Force quit | *Explosion* |

### Sound Packs

#### Pack 1: Warcraft III Peon (Default)

**Theme**: Classic RTS worker unit  
**Personality**: Obedient, hardworking, slightly grumpy

```yaml
name: peon
description: "Warcraft III Peon voice lines"
sounds:
  session_start: "ready.mp3"           # "Ready to work!"
  prompt_submit: "yes_milord.mp3"      # "Yes, milord?"
  success: "work_complete.mp3"         # "Work complete!"
  error: "what.mp3"                    # "What?"
  context_compact: "more_work.mp3"     # "More work?"
  long_prompt: "me_busy.mp3"           # "Me busy, leave me alone!"
  tool_execute: "okie_dokie.mp3"       # "Okie dokie"
  background_complete: "job_done.mp3"  # "Job's done!"
```

#### Pack 2: Age of Empires

**Theme**: Medieval strategy game  
**Personality**: Regal, dramatic, epic

```yaml
name: age_of_empires
description: "Age of Empires sound effects"
sounds:
  session_start: "horn.mp3"            # War horn
  prompt_submit: "yes.mp3"             # "Yes"
  success: "allhail.mp3"               # "All hail!"
  error: "no.mp3"                      # "No"
  context_compact: "wololo.mp3"        # "Wololo!"
  tool_execute: "attack.mp3"           # Attack sound
  achievement: "victory.mp3"           # Victory fanfare
```

#### Pack 3: Meme Sounds

**Theme**: Internet culture  
**Personality**: Chaotic, humorous, modern

```yaml
name: memes
description: "Popular meme sound effects"
sounds:
  session_start: "hello_there.mp3"     # "Hello there!" (Obi-Wan)
  prompt_submit: "noted.mp3"           # "Noted"
  success: "nice.mp3"                  # "Nice"
  error: "bruh.mp3"                    # "Bruh"
  warning: "emotional_damage.mp3"      # "Emotional damage!"
  long_prompt: "aint_nobody.mp3"       # "Ain't nobody got time for that"
  interrupt: "record_scratch.mp3"      # *Record scratch*
  force_exit: "directed_by.mp3"        # "Directed by Robert B. Weide"
```

#### Pack 4: Retro Gaming

**Theme**: 8-bit/16-bit video games  
**Personality**: Nostalgic, energetic, arcade-like

```yaml
name: retro
description: "Classic video game sound effects"
sounds:
  session_start: "power_up.mp3"        # Power-up sound
  prompt_submit: "coin.mp3"            # Coin collect
  success: "level_up.mp3"              # Level up fanfare
  error: "damage.mp3"                  # Damage sound
  warning: "low_health.mp3"            # Low health beep
  tool_execute: "jump.mp3"             # Jump sound
  achievement: "1up.mp3"               # 1-UP sound
  context_compact: "warp_pipe.mp3"     # Warp pipe sound
```

#### Pack 5: Sci-Fi

**Theme**: Futuristic, space-age  
**Personality**: High-tech, robotic, sleek

```yaml
name: scifi
description: "Science fiction sound effects"
sounds:
  session_start: "system_online.mp3"   # "System online"
  prompt_submit: "acknowledged.mp3"    # "Acknowledged"
  success: "mission_complete.mp3"      # "Mission complete"
  error: "system_error.mp3"            # "System error"
  warning: "alert.mp3"                 # Red alert
  tool_execute: "engage.mp3"           # "Engage"
  thinking_start: "processing.mp3"     # Processing beep
  context_compact: "data_purge.mp3"    # Data purge sound
```

#### Pack 6: Kawaii/Anime

**Theme**: Cute Japanese aesthetics  
**Personality**: Adorable, cheerful, energetic

```yaml
name: kawaii
description: "Cute anime-style sound effects"
sounds:
  session_start: "ohayo.mp3"           # "Ohayō!" (Good morning)
  prompt_submit: "hai.mp3"             # "Hai!" (Yes)
  success: "yatta.mp3"                 # "Yatta!" (I did it)
  error: "ara_ara.mp3"                 # "Ara ara~"
  warning: "mou.mp3"                   # "Mou~" (Geez)
  long_prompt: "sugoi.mp3"             # "Sugoi!" (Amazing)
  achievement: "kawaii.mp3"            # "Kawaii~!"
```

## 2. Hook Integration

### Hook Configuration (~/.lyra/hooks.json)

```json
{
  "SessionStart": [
    {
      "type": "sound",
      "pack": "peon",
      "sound": "session_start",
      "volume": 0.7
    }
  ],
  "UserPromptSubmit": [
    {
      "type": "sound",
      "pack": "peon",
      "sound": "prompt_submit",
      "volume": 0.5,
      "conditions": {
        "prompt_length_min": 10
      }
    }
  ],
  "Stop": [
    {
      "type": "sound",
      "pack": "peon",
      "sound": "success",
      "volume": 0.8,
      "conditions": {
        "exit_code": 0
      }
    },
    {
      "type": "sound",
      "pack": "peon",
      "sound": "error",
      "volume": 0.8,
      "conditions": {
        "exit_code_not": 0
      }
    }
  ],
  "PreCompact": [
    {
      "type": "sound",
      "pack": "age_of_empires",
      "sound": "context_compact",
      "volume": 0.6
    }
  ],
  "ToolExecute": [
    {
      "type": "sound",
      "pack": "peon",
      "sound": "tool_execute",
      "volume": 0.4
    }
  ],
  "BackgroundTaskComplete": [
    {
      "type": "sound",
      "pack": "peon",
      "sound": "background_complete",
      "volume": 0.9,
      "notification": true
    }
  ]
}
```

### Conditional Sound Triggers

```json
{
  "conditions": {
    "prompt_length_min": 100,        // Minimum prompt length
    "prompt_length_max": 1000,       // Maximum prompt length
    "exit_code": 0,                  // Specific exit code
    "exit_code_not": 0,              // Not this exit code
    "context_usage_min": 0.8,        // Context usage threshold
    "time_of_day": "morning",        // morning|afternoon|evening|night
    "day_of_week": "friday",         // monday-sunday
    "tool_name": "terminal",         // Specific tool
    "model": "opus",                 // Specific model
    "session_duration_min": 3600     // Minimum session duration (seconds)
  }
}
```

## 3. Audio Playback Implementation

### Cross-Platform Audio Players

```python
import os
import platform
import subprocess
from pathlib import Path

class AudioPlayer:
    def __init__(self, sounds_dir: str = "~/.lyra/sounds"):
        self.sounds_dir = Path(sounds_dir).expanduser()
        self.platform = platform.system()
        self.player = self._detect_player()
    
    def _detect_player(self) -> str:
        """Detect available audio player"""
        if self.platform == "Darwin":  # macOS
            return "afplay"
        elif self.platform == "Linux":
            # Try multiple players in order of preference
            for player in ["paplay", "aplay", "ffplay"]:
                if subprocess.run(["which", player], capture_output=True).returncode == 0:
                    return player
            return None
        elif self.platform == "Windows":
            return "powershell"
        return None
    
    def play(self, sound_file: str, volume: float = 1.0, background: bool = True):
        """Play sound file"""
        if not self.player:
            return  # No player available, silently skip
        
        sound_path = self.sounds_dir / sound_file
        if not sound_path.exists():
            return  # Sound file not found, silently skip
        
        if self.platform == "Darwin":
            cmd = ["afplay", str(sound_path)]
            if volume < 1.0:
                cmd.extend(["--volume", str(volume)])
        
        elif self.platform == "Linux":
            if self.player == "paplay":
                cmd = ["paplay", str(sound_path)]
                if volume < 1.0:
                    cmd.extend(["--volume", str(int(volume * 65536))])
            elif self.player == "aplay":
                cmd = ["aplay", "-q", str(sound_path)]
            elif self.player == "ffplay":
                cmd = ["ffplay", "-nodisp", "-autoexit", "-volume", str(int(volume * 100)), str(sound_path)]
        
        elif self.platform == "Windows":
            cmd = [
                "powershell", "-c",
                f"(New-Object Media.SoundPlayer '{sound_path}').PlaySync()"
            ]
        
        if background:
            cmd.append("&")  # Run in background
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
```

### Sound Manager

```python
from dataclasses import dataclass
from typing import Dict, Optional
import yaml

@dataclass
class SoundPack:
    name: str
    description: str
    sounds: Dict[str, str]

class SoundManager:
    def __init__(self, config_path: str = "~/.lyra/config.yaml"):
        self.config_path = Path(config_path).expanduser()
        self.player = AudioPlayer()
        self.packs: Dict[str, SoundPack] = {}
        self.current_pack: Optional[str] = None
        self.enabled = True
        self.volume = 0.7
        
        self.load_config()
        self.load_packs()
    
    def load_config(self):
        """Load sound configuration"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
                sound_config = config.get("sound", {})
                self.enabled = sound_config.get("enabled", True)
                self.volume = sound_config.get("volume", 0.7)
                self.current_pack = sound_config.get("pack", "peon")
    
    def load_packs(self):
        """Load all sound packs"""
        packs_dir = Path("~/.lyra/sounds/packs").expanduser()
        if not packs_dir.exists():
            return
        
        for pack_file in packs_dir.glob("*.yaml"):
            with open(pack_file) as f:
                data = yaml.safe_load(f)
                pack = SoundPack(**data)
                self.packs[pack.name] = pack
    
    def play_event(self, event: str, volume: Optional[float] = None):
        """Play sound for event"""
        if not self.enabled or not self.current_pack:
            return
        
        pack = self.packs.get(self.current_pack)
        if not pack:
            return
        
        sound_file = pack.sounds.get(event)
        if not sound_file:
            return
        
        vol = volume if volume is not None else self.volume
        self.player.play(sound_file, volume=vol)
    
    def set_pack(self, pack_name: str):
        """Switch to different sound pack"""
        if pack_name in self.packs:
            self.current_pack = pack_name
    
    def toggle(self):
        """Toggle sound on/off"""
        self.enabled = not self.enabled
```

## 4. Text-to-Speech (TTS)

### TTS Integration

```python
import pyttsx3  # Cross-platform TTS

class TTSManager:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.enabled = False
        self.rate = 150  # Words per minute
        self.volume = 0.8
        
        self._configure()
    
    def _configure(self):
        """Configure TTS engine"""
        self.engine.setProperty('rate', self.rate)
        self.engine.setProperty('volume', self.volume)
        
        # Select voice (prefer female voice if available)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'female' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
    
    def speak(self, text: str, async_mode: bool = True):
        """Speak text"""
        if not self.enabled:
            return
        
        # Strip markdown and code blocks
        clean_text = self._clean_text(text)
        
        if async_mode:
            self.engine.say(clean_text)
            self.engine.runAndWait()
        else:
            self.engine.say(clean_text)
    
    def _clean_text(self, text: str) -> str:
        """Remove markdown and code blocks"""
        import re
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '[code block]', text)
        # Remove inline code
        text = re.sub(r'`[^`]+`', '[code]', text)
        # Remove markdown formatting
        text = re.sub(r'[*_~]', '', text)
        return text
    
    def toggle(self):
        """Toggle TTS on/off"""
        self.enabled = not self.enabled
```

### Voice Commands

```bash
# Enable TTS
/voice tts

# Disable TTS
/voice off

# Adjust speech rate
/voice rate 200

# Select voice
/voice select
```

## 5. Speech-to-Text (STT)

### STT Integration

```python
import speech_recognition as sr

class STTManager:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.enabled = False
    
    def listen(self, timeout: int = 5) -> Optional[str]:
        """Listen for voice input"""
        if not self.enabled:
            return None
        
        with self.microphone as source:
            # Adjust for ambient noise
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            print("🎤 Listening...")
            try:
                audio = self.recognizer.listen(source, timeout=timeout)
                text = self.recognizer.recognize_google(audio)
                print(f"📝 Recognized: {text}")
                return text
            except sr.WaitTimeoutError:
                print("⏱️ Timeout - no speech detected")
                return None
            except sr.UnknownValueError:
                print("❓ Could not understand audio")
                return None
            except sr.RequestError as e:
                print(f"❌ Error: {e}")
                return None
    
    def toggle(self):
        """Toggle STT on/off"""
        self.enabled = not self.enabled
```

### Voice Input Keybinding

- `Ctrl+B` - Start voice recording
- Speak prompt
- Automatic submission when silence detected
- `Esc` to cancel

## 6. Configuration

### User Configuration (~/.lyra/config.yaml)

```yaml
sound:
  enabled: true
  pack: peon                    # Default sound pack
  volume: 0.7                   # Global volume (0.0-1.0)
  
  # Per-event volume overrides
  volumes:
    session_start: 0.8
    success: 0.9
    error: 0.8
    background_complete: 1.0    # Max volume for important events
  
  # Disable specific events
  disabled_events:
    - tool_execute              # Too frequent
    - thinking_start            # Too noisy
  
  # Time-based rules
  quiet_hours:
    enabled: true
    start: "22:00"
    end: "08:00"
    volume: 0.3                 # Reduced volume during quiet hours

tts:
  enabled: false
  rate: 150                     # Words per minute
  volume: 0.8
  voice: "female"               # male|female|auto
  
  # Only speak certain message types
  speak_only:
    - final_response            # Agent's final answer
    - error                     # Error messages
    - warning                   # Warnings

stt:
  enabled: false
  timeout: 5                    # Seconds to wait for speech
  language: "en-US"
  auto_submit: true             # Submit after silence detected
```

## 7. Sound Pack Creation

### Custom Sound Pack Template

```yaml
name: custom
description: "My custom sound pack"
author: "Your Name"
version: "1.0"

sounds:
  # Session lifecycle
  session_start: "start.mp3"
  session_end: "end.mp3"
  session_resume: "resume.mp3"
  session_save: "save.mp3"
  
  # User interaction
  prompt_submit: "submit.mp3"
  prompt_queued: "queued.mp3"
  long_prompt: "long.mp3"
  empty_prompt: "empty.mp3"
  paste_detected: "paste.mp3"
  image_attached: "image.mp3"
  
  # Agent activity
  thinking_start: "think_start.mp3"
  thinking_end: "think_end.mp3"
  tool_execute: "tool.mp3"
  tool_success: "tool_ok.mp3"
  tool_fail: "tool_fail.mp3"
  code_write: "code.mp3"
  code_review: "review.mp3"
  test_run: "test.mp3"
  
  # Status changes
  success: "success.mp3"
  error: "error.mp3"
  warning: "warning.mp3"
  context_low: "context_low.mp3"
  context_high: "context_high.mp3"
  context_compact: "compact.mp3"
  background_complete: "bg_done.mp3"
  
  # Special events
  first_run: "welcome.mp3"
  achievement: "achievement.mp3"
  easter_egg: "secret.mp3"
  interrupt: "interrupt.mp3"
  force_exit: "exit.mp3"
```

### Sound Pack CLI

```bash
# List available packs
lyra sound packs

# Preview sound pack
lyra sound preview peon

# Install sound pack from URL
lyra sound install https://example.com/pack.zip

# Create new sound pack
lyra sound create my-pack

# Test specific sound
lyra sound test peon session_start
```

## 8. Testing & Validation

### Sound Pack Validator

```python
def validate_sound_pack(pack_path: Path) -> List[str]:
    """Validate sound pack completeness"""
    errors = []
    
    required_sounds = [
        "session_start", "prompt_submit", "success", "error",
        "tool_execute", "context_compact"
    ]
    
    with open(pack_path) as f:
        pack = yaml.safe_load(f)
    
    # Check required fields
    if "name" not in pack:
        errors.append("Missing 'name' field")
    if "sounds" not in pack:
        errors.append("Missing 'sounds' field")
        return errors
    
    # Check required sounds
    for sound in required_sounds:
        if sound not in pack["sounds"]:
            errors.append(f"Missing required sound: {sound}")
    
    # Check sound files exist
    sounds_dir = pack_path.parent / pack["name"]
    for sound_file in pack["sounds"].values():
        sound_path = sounds_dir / sound_file
        if not sound_path.exists():
            errors.append(f"Sound file not found: {sound_file}")
    
    return errors
```

## 9. Future Enhancements

1. **Dynamic sound generation** - AI-generated sounds based on context
2. **Voice cloning** - Clone your own voice for TTS
3. **Spatial audio** - 3D audio positioning for different agents
4. **Music integration** - Background music during long operations
5. **Sound themes** - Seasonal/holiday sound packs
6. **Community marketplace** - Share and download sound packs
7. **Adaptive volume** - Auto-adjust based on ambient noise
8. **Multi-language TTS** - Support for multiple languages
9. **Voice commands** - Control Lyra entirely by voice
10. **Sound visualization** - Visual waveforms for audio feedback

---

**Design by**: Document Specialist Agent  
**Date**: 2026-05-29  
**Status**: Ready for implementation  
**Fun factor**: 🎉🎉🎉🎉🎉 (5/5 peons)
