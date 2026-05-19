# Lyra Funny Sounds Integration - Implementation Plan

**Goal**: Add funny sound effects to Lyra for workflow events (inspired by Warcraft III peon notifications and Age of Empires sounds).

**Status**: Planning
**Created**: 2026-05-19
**Estimated Duration**: 2-3 days

---

## Overview

Implement a sound notification system that:
1. Plays funny sounds for key workflow events
2. Supports multiple sound themes (Warcraft, Age of Empires, memes, custom)
3. Integrates with Lyra's hook system
4. Provides volume control and muting
5. Works cross-platform (macOS, Linux, Windows)
6. Includes adaptive features (context-aware, time-based)

---

## Research Summary

### Sound Implementation Approaches

**From alexop.dev article:**
- Uses Claude Code's lifecycle hooks (SessionStart, UserPromptSubmit, Stop, PreCompact)
- Platform-native audio players: `afplay` (macOS), `aplay`/`paplay` (Linux), PowerShell (Windows)
- Background execution with `&` suffix to prevent blocking
- Configuration in `~/.claude/settings.json`

**From Warcraft III peon article:**
- Event mapping: task completed → "Job's done!", errors → "Something need doing?"
- Adaptive volume: increases if no response after 30 seconds
- Context-aware: different sounds per file type
- Productivity mode: reduces sounds near deadlines
- Multiplayer mode: syncs sounds across teams

### Popular Sound Categories

**Video Game Sounds** (from web research):
- Warcraft III: "Zug zug", "Job's done!", "Me not that kind of orc!"
- Age of Empires: Horn, "Yes", "All hail", "Wololo"
- Minecraft: Villager hum, oof sound
- Among Us: Suspicious sound
- Mario: Coin, power-up, 1-up
- Half-Life: Crowbar hit, health pickup

**Meme Sounds**:
- Bruh sound effect
- Vine boom
- Windows XP error
- Metal Gear alert
- Sad trombone
- Airhorn

---

## Architecture

### Core Components

```
lyra_research/
├── sounds/
│   ├── __init__.py
│   ├── sound_manager.py        # Core sound playback
│   ├── event_mapper.py         # Map events to sounds
│   ├── theme_manager.py        # Sound theme management
│   ├── audio_player.py         # Cross-platform audio
│   └── config.py               # Sound configuration
├── sounds/assets/              # Sound files
│   ├── warcraft/
│   ├── aoe/
│   ├── memes/
│   └── custom/
└── hooks/
    └── sound_hooks.py          # Hook integration
```

---

## Phase 0: Foundation (Day 1, Morning)

### 0.1 Cross-Platform Audio Player

**File**: `src/lyra_research/sounds/audio_player.py`

```python
import platform
import subprocess
from pathlib import Path
from typing import Optional
from enum import Enum

class AudioBackend(Enum):
    """Audio playback backends"""
    AFPLAY = "afplay"      # macOS
    APLAY = "aplay"        # Linux (ALSA)
    PAPLAY = "paplay"      # Linux (PulseAudio)
    POWERSHELL = "powershell"  # Windows

class AudioPlayer:
    """
    Cross-platform audio player
    
    Automatically detects platform and uses appropriate audio backend.
    """
    
    def __init__(self):
        self.backend = self._detect_backend()
        
    def _detect_backend(self) -> AudioBackend:
        """Detect appropriate audio backend for current platform"""
        system = platform.system()
        
        if system == "Darwin":
            return AudioBackend.AFPLAY
        elif system == "Linux":
            # Check if paplay is available (PulseAudio)
            if self._command_exists("paplay"):
                return AudioBackend.PAPLAY
            return AudioBackend.APLAY
        elif system == "Windows":
            return AudioBackend.POWERSHELL
        else:
            raise RuntimeError(f"Unsupported platform: {system}")
            
    def _command_exists(self, command: str) -> bool:
        """Check if command exists in PATH"""
        try:
            subprocess.run([command, "--version"], 
                         capture_output=True, 
                         timeout=1)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
            
    def play(self, sound_path: Path, volume: float = 1.0, 
             background: bool = True) -> Optional[subprocess.Popen]:
        """
        Play sound file
        
        Args:
            sound_path: Path to sound file
            volume: Volume level (0.0 to 1.0)
            background: Run in background (non-blocking)
            
        Returns:
            Process handle if background=True, None otherwise
        """
        if not sound_path.exists():
            raise FileNotFoundError(f"Sound file not found: {sound_path}")
            
        command = self._build_command(sound_path, volume)
        
        if background:
            # Run in background, don't wait
            return subprocess.Popen(command, 
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        else:
            # Run and wait for completion
            subprocess.run(command, 
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
            return None
            
    def _build_command(self, sound_path: Path, volume: float) -> list:
        """Build platform-specific audio command"""
        if self.backend == AudioBackend.AFPLAY:
            # macOS: afplay -v <volume> <file>
            return ["afplay", "-v", str(volume), str(sound_path)]
            
        elif self.backend == AudioBackend.PAPLAY:
            # Linux PulseAudio: paplay --volume <0-65536> <file>
            pa_volume = int(volume * 65536)
            return ["paplay", "--volume", str(pa_volume), str(sound_path)]
            
        elif self.backend == AudioBackend.APLAY:
            # Linux ALSA: aplay <file>
            # Note: ALSA doesn't support volume in command
            return ["aplay", str(sound_path)]
            
        elif self.backend == AudioBackend.POWERSHELL:
            # Windows PowerShell
            ps_command = f'(New-Object Media.SoundPlayer "{sound_path}").PlaySync()'
            return ["powershell.exe", "-c", ps_command]
            
        raise RuntimeError(f"Unsupported backend: {self.backend}")
```

**Tests**: `tests/test_audio_player.py`
- Test backend detection
- Test command building
- Test play with mock subprocess
- Test volume control
- Test background vs foreground

### 0.2 Sound Theme Manager

**File**: `src/lyra_research/sounds/theme_manager.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import json

@dataclass
class SoundTheme:
    """Sound theme definition"""
    name: str
    description: str
    sounds: Dict[str, str]  # event -> sound_file mapping
    
class ThemeManager:
    """
    Manages sound themes
    
    Built-in themes:
    - warcraft: Warcraft III peon sounds
    - aoe: Age of Empires sounds
    - memes: Internet meme sounds
    - minimal: Subtle notification sounds
    """
    
    def __init__(self, sounds_dir: Path = None):
        self.sounds_dir = sounds_dir or Path(__file__).parent / "assets"
        self.themes = self._load_builtin_themes()
        
    def _load_builtin_themes(self) -> Dict[str, SoundTheme]:
        """Load built-in sound themes"""
        return {
            "warcraft": SoundTheme(
                name="warcraft",
                description="Warcraft III peon voice lines",
                sounds={
                    "session_start": "warcraft/zug_zug.mp3",
                    "task_start": "warcraft/ready_to_work.mp3",
                    "task_complete": "warcraft/job_done.mp3",
                    "error": "warcraft/something_need_doing.mp3",
                    "syntax_error": "warcraft/me_not_that_kind_orc.mp3",
                    "logic_error": "warcraft/that_not_possible.mp3",
                    "rate_limit": "warcraft/me_tired.mp3",
                    "milestone": "warcraft/for_the_horde.mp3",
                    "compact": "warcraft/work_work.mp3"
                }
            ),
            "aoe": SoundTheme(
                name="aoe",
                description="Age of Empires villager sounds",
                sounds={
                    "session_start": "aoe/horn.mp3",
                    "task_start": "aoe/yes.mp3",
                    "task_complete": "aoe/allhail.mp3",
                    "error": "aoe/no.mp3",
                    "compact": "aoe/wololo.mp3",
                    "milestone": "aoe/victory.mp3"
                }
            ),
            "memes": SoundTheme(
                name="memes",
                description="Internet meme sounds",
                sounds={
                    "session_start": "memes/hello_there.mp3",
                    "task_start": "memes/lets_go.mp3",
                    "task_complete": "memes/nice.mp3",
                    "error": "memes/bruh.mp3",
                    "syntax_error": "memes/windows_error.mp3",
                    "rate_limit": "memes/sad_trombone.mp3",
                    "milestone": "memes/airhorn.mp3",
                    "compact": "memes/thanos_snap.mp3"
                }
            ),
            "minimal": SoundTheme(
                name="minimal",
                description="Subtle notification sounds",
                sounds={
                    "session_start": "minimal/chime.mp3",
                    "task_start": "minimal/click.mp3",
                    "task_complete": "minimal/ding.mp3",
                    "error": "minimal/error.mp3",
                    "compact": "minimal/whoosh.mp3"
                }
            )
        }
        
    def get_theme(self, theme_name: str) -> Optional[SoundTheme]:
        """Get theme by name"""
        return self.themes.get(theme_name)
        
    def list_themes(self) -> List[str]:
        """List available theme names"""
        return list(self.themes.keys())
        
    def get_sound_path(self, theme_name: str, event: str) -> Optional[Path]:
        """
        Get full path to sound file for event
        
        Args:
            theme_name: Theme name
            event: Event name
            
        Returns:
            Path to sound file, or None if not found
        """
        theme = self.get_theme(theme_name)
        if not theme:
            return None
            
        sound_file = theme.sounds.get(event)
        if not sound_file:
            return None
            
        return self.sounds_dir / sound_file
```

**Tests**: `tests/test_theme_manager.py`
- Test load builtin themes
- Test get theme
- Test list themes
- Test get sound path
- Test missing theme/event

### 0.3 Sound Manager

**File**: `src/lyra_research/sounds/sound_manager.py`

```python
from pathlib import Path
from typing import Optional
from .audio_player import AudioPlayer
from .theme_manager import ThemeManager
from .config import SoundConfig

class SoundManager:
    """
    Main sound management system
    
    Features:
    - Play sounds for events
    - Theme switching
    - Volume control
    - Mute/unmute
    - Adaptive volume
    """
    
    def __init__(self, config: Optional[SoundConfig] = None):
        self.config = config or SoundConfig()
        self.player = AudioPlayer()
        self.theme_manager = ThemeManager()
        self.muted = False
        
    def play_event(self, event: str, volume: Optional[float] = None):
        """
        Play sound for event
        
        Args:
            event: Event name (e.g., "task_complete")
            volume: Override volume (uses config if None)
        """
        if self.muted or not self.config.enabled:
            return
            
        # Get sound path from current theme
        sound_path = self.theme_manager.get_sound_path(
            self.config.theme, 
            event
        )
        
        if not sound_path or not sound_path.exists():
            return
            
        # Use provided volume or config volume
        vol = volume if volume is not None else self.config.volume
        
        # Play in background
        self.player.play(sound_path, volume=vol, background=True)
        
    def set_theme(self, theme_name: str):
        """Change sound theme"""
        if theme_name in self.theme_manager.list_themes():
            self.config.theme = theme_name
            self.config.save()
            
    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)"""
        self.config.volume = max(0.0, min(1.0, volume))
        self.config.save()
        
    def mute(self):
        """Mute all sounds"""
        self.muted = True
        
    def unmute(self):
        """Unmute sounds"""
        self.muted = False
        
    def toggle_mute(self) -> bool:
        """Toggle mute state"""
        self.muted = not self.muted
        return self.muted
```

**Tests**: `tests/test_sound_manager.py`
- Test play event
- Test mute/unmute
- Test volume control
- Test theme switching
- Test disabled sounds

---

### 0.4 Sound Configuration

**File**: `src/lyra_research/sounds/config.py`

```python
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class SoundConfig:
    """Sound system configuration"""
    enabled: bool = True
    theme: str = "warcraft"
    volume: float = 0.5
    adaptive_volume: bool = False
    context_aware: bool = False
    productivity_mode: bool = False
    
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path.home() / ".lyra" / "sounds_config.json"
        if self.config_path.exists():
            self._load()
            
    def _load(self):
        """Load config from file"""
        with open(self.config_path) as f:
            data = json.load(f)
            self.enabled = data.get("enabled", True)
            self.theme = data.get("theme", "warcraft")
            self.volume = data.get("volume", 0.5)
            self.adaptive_volume = data.get("adaptive_volume", False)
            self.context_aware = data.get("context_aware", False)
            self.productivity_mode = data.get("productivity_mode", False)
            
    def save(self):
        """Save config to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump({
                "enabled": self.enabled,
                "theme": self.theme,
                "volume": self.volume,
                "adaptive_volume": self.adaptive_volume,
                "context_aware": self.context_aware,
                "productivity_mode": self.productivity_mode
            }, f, indent=2)
```

**Tests**: `tests/test_sound_config.py`
- Test load config
- Test save config
- Test default values
- Test config persistence

---

## Phase 1: Event Mapping (Day 1, Afternoon)

### 1.1 Event Mapper

**File**: `src/lyra_research/sounds/event_mapper.py`

```python
from enum import Enum
from typing import Optional

class SoundEvent(Enum):
    """Sound events"""
    SESSION_START = "session_start"
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    ERROR = "error"
    SYNTAX_ERROR = "syntax_error"
    LOGIC_ERROR = "logic_error"
    RATE_LIMIT = "rate_limit"
    MILESTONE = "milestone"
    COMPACT = "compact"
    
class EventMapper:
    """
    Maps Lyra events to sound events
    
    Provides intelligent event detection and mapping.
    """
    
    def map_error(self, error_message: str) -> SoundEvent:
        """
        Map error message to specific sound event
        
        Args:
            error_message: Error message text
            
        Returns:
            Appropriate sound event
        """
        msg_lower = error_message.lower()
        
        # Syntax errors
        if any(kw in msg_lower for kw in ["syntax", "parse", "unexpected token"]):
            return SoundEvent.SYNTAX_ERROR
            
        # Logic errors
        if any(kw in msg_lower for kw in ["assertion", "logic", "invalid"]):
            return SoundEvent.LOGIC_ERROR
            
        # Rate limiting
        if any(kw in msg_lower for kw in ["rate limit", "too many requests", "quota"]):
            return SoundEvent.RATE_LIMIT
            
        # Generic error
        return SoundEvent.ERROR
        
    def detect_milestone(self, task_count: int) -> Optional[SoundEvent]:
        """
        Detect milestone achievements
        
        Args:
            task_count: Number of completed tasks
            
        Returns:
            MILESTONE event if milestone reached, None otherwise
        """
        # Milestones at 10, 25, 50, 100 tasks
        if task_count in [10, 25, 50, 100]:
            return SoundEvent.MILESTONE
        return None
```

**Tests**: `tests/test_event_mapper.py`
- Test map syntax error
- Test map logic error
- Test map rate limit
- Test detect milestone
- Test generic error

## Phase 2: Hook Integration (Day 2, Morning)

### 2.1 Sound Hooks

**File**: `src/lyra_research/hooks/sound_hooks.py`

```python
from ..sounds.sound_manager import SoundManager
from ..sounds.event_mapper import SoundEvent, EventMapper

class SoundHooks:
    """
    Hook integration for sound system
    
    Connects Lyra lifecycle events to sound playback.
    """
    
    def __init__(self):
        self.sound_manager = SoundManager()
        self.event_mapper = EventMapper()
        self.task_count = 0
        
    def on_session_start(self):
        """Hook: Session started"""
        self.sound_manager.play_event(SoundEvent.SESSION_START.value)
        
    def on_task_start(self, task_description: str):
        """Hook: Task started"""
        self.sound_manager.play_event(SoundEvent.TASK_START.value)
        
    def on_task_complete(self, task_description: str):
        """Hook: Task completed"""
        self.task_count += 1
        
        # Check for milestone
        milestone = self.event_mapper.detect_milestone(self.task_count)
        if milestone:
            self.sound_manager.play_event(milestone.value)
        else:
            self.sound_manager.play_event(SoundEvent.TASK_COMPLETE.value)
            
    def on_error(self, error_message: str):
        """Hook: Error occurred"""
        event = self.event_mapper.map_error(error_message)
        self.sound_manager.play_event(event.value)
        
    def on_compact(self):
        """Hook: Context compaction"""
        self.sound_manager.play_event(SoundEvent.COMPACT.value)
```

**Tests**: `tests/test_sound_hooks.py`
- Test session start hook
- Test task start hook
- Test task complete hook
- Test error hook
- Test milestone detection
- Test compact hook

---

## Phase 3: Advanced Features (Day 2, Afternoon)

### 3.1 Adaptive Volume

**File**: `src/lyra_research/sounds/adaptive_volume.py`

```python
from datetime import datetime, timedelta
from typing import Optional

class AdaptiveVolume:
    """
    Adaptive volume adjustment
    
    Increases volume if user hasn't responded to completion notification.
    """
    
    def __init__(self, base_volume: float = 0.5):
        self.base_volume = base_volume
        self.last_completion: Optional[datetime] = None
        self.no_response_threshold = timedelta(seconds=30)
        
    def get_volume(self, event: str) -> float:
        """
        Get adaptive volume for event
        
        Args:
            event: Event name
            
        Returns:
            Adjusted volume level
        """
        if event != "task_complete":
            return self.base_volume
            
        # Check if previous completion was ignored
        if self.last_completion:
            elapsed = datetime.now() - self.last_completion
            if elapsed > self.no_response_threshold:
                # Increase volume by 50%
                return min(1.0, self.base_volume * 1.5)
                
        return self.base_volume
        
    def mark_completion(self):
        """Mark task completion time"""
        self.last_completion = datetime.now()
        
    def mark_response(self):
        """Mark user response (resets adaptive volume)"""
        self.last_completion = None
```

**Tests**: `tests/test_adaptive_volume.py`
- Test base volume
- Test volume increase after no response
- Test reset on response
- Test threshold timing

---

### 3.2 Context-Aware Sounds

**File**: `src/lyra_research/sounds/context_aware.py`

```python
from pathlib import Path
from typing import Optional

class ContextAwareSounds:
    """
    Context-aware sound selection
    
    Chooses different sounds based on file type, time of day, etc.
    """
    
    def __init__(self, theme_manager):
        self.theme_manager = theme_manager
        
    def get_context_sound(self, event: str, context: dict) -> Optional[str]:
        """
        Get context-specific sound
        
        Args:
            event: Base event name
            context: Context information (file_type, time, etc.)
            
        Returns:
            Modified event name or None
        """
        # File type specific sounds
        if "file_path" in context:
            file_path = Path(context["file_path"])
            suffix = file_path.suffix
            
            # Python files
            if suffix == ".py":
                if event == "task_complete":
                    return "task_complete_python"
                    
            # Test files
            if "test" in file_path.name:
                if event == "task_complete":
                    return "task_complete_test"
                    
        # Time-based sounds
        if "time" in context:
            hour = context["time"].hour
            
            # After 5 PM: 20% more ridiculous
            if hour >= 17:
                if event == "task_complete":
                    return "task_complete_evening"
                    
        return None
```

**Tests**: `tests/test_context_aware.py`
- Test file type detection
- Test time-based sounds
- Test fallback to default

---

### 3.3 Productivity Mode

**File**: `src/lyra_research/sounds/productivity_mode.py`

```python
from datetime import datetime, date
from typing import Optional

class ProductivityMode:
    """
    Productivity mode
    
    Reduces funny sounds near deadlines or during focus time.
    """
    
    def __init__(self):
        self.deadlines = []  # List of (date, description)
        self.focus_mode = False
        
    def add_deadline(self, deadline_date: date, description: str):
        """Add a deadline"""
        self.deadlines.append((deadline_date, description))
        
    def is_near_deadline(self, days_threshold: int = 3) -> bool:
        """Check if near any deadline"""
        today = date.today()
        for deadline_date, _ in self.deadlines:
            days_until = (deadline_date - today).days
            if 0 <= days_until <= days_threshold:
                return True
        return False
        
    def should_reduce_sounds(self) -> bool:
        """Check if sounds should be reduced"""
        return self.focus_mode or self.is_near_deadline()
        
    def get_volume_multiplier(self) -> float:
        """Get volume multiplier for productivity mode"""
        if self.should_reduce_sounds():
            return 0.3  # Reduce to 30%
        return 1.0
```

**Tests**: `tests/test_productivity_mode.py`
- Test deadline detection
- Test focus mode
- Test volume reduction
- Test deadline threshold

---

## Phase 4: CLI & Configuration (Day 3, Morning)

### 4.1 CLI Commands

**File**: `src/lyra_research/cli/sound_commands.py`

```python
import click
from ..sounds.sound_manager import SoundManager
from ..sounds.theme_manager import ThemeManager

@click.group()
def sounds():
    """Sound system management"""
    pass

@sounds.command()
def enable():
    """Enable sounds"""
    manager = SoundManager()
    manager.config.enabled = True
    manager.config.save()
    click.echo("✓ Sounds enabled")

@sounds.command()
def disable():
    """Disable sounds"""
    manager = SoundManager()
    manager.config.enabled = False
    manager.config.save()
    click.echo("✓ Sounds disabled")

@sounds.command()
def mute():
    """Mute sounds temporarily"""
    manager = SoundManager()
    manager.mute()
    click.echo("✓ Sounds muted (temporary)")

@sounds.command()
def unmute():
    """Unmute sounds"""
    manager = SoundManager()
    manager.unmute()
    click.echo("✓ Sounds unmuted")

@sounds.command()
@click.argument('theme_name')
def theme(theme_name):
    """Set sound theme"""
    manager = SoundManager()
    theme_mgr = ThemeManager()
    
    if theme_name not in theme_mgr.list_themes():
        click.echo(f"❌ Unknown theme: {theme_name}")
        click.echo(f"Available themes: {', '.join(theme_mgr.list_themes())}")
        return
        
    manager.set_theme(theme_name)
    click.echo(f"✓ Theme set to: {theme_name}")

@sounds.command()
def themes():
    """List available themes"""
    theme_mgr = ThemeManager()
    click.echo("\nAvailable sound themes:\n")
    for name in theme_mgr.list_themes():
        theme = theme_mgr.get_theme(name)
        click.echo(f"  {name}: {theme.description}")

@sounds.command()
@click.argument('volume', type=float)
def volume(volume):
    """Set volume (0.0 to 1.0)"""
    if not 0.0 <= volume <= 1.0:
        click.echo("❌ Volume must be between 0.0 and 1.0")
        return
        
    manager = SoundManager()
    manager.set_volume(volume)
    click.echo(f"✓ Volume set to: {volume:.1f}")

@sounds.command()
@click.argument('event')
def test(event):
    """Test play a sound event"""
    manager = SoundManager()
    manager.play_event(event)
    click.echo(f"✓ Playing: {event}")
```

**Tests**: `tests/test_sound_commands.py`
- Test enable/disable
- Test mute/unmute
- Test theme switching
- Test volume control
- Test sound test

## Phase 5: Sound Assets & Documentation (Day 3, Afternoon)

### 5.1 Sound Asset Acquisition

**Strategy**: Use royalty-free sound sources

**Sources**:
1. **Warcraft III sounds**: Extract from game files or use fan-made recreations
2. **Age of Empires sounds**: Community sound packs
3. **Meme sounds**: [MyInstants](https://www.myinstants.com/), [Voicemod Tuna](https://tuna.voicemod.net/)
4. **Minimal sounds**: [Freesound.org](https://freesound.org/)

**Directory Structure**:
```
src/lyra_research/sounds/assets/
├── warcraft/
│   ├── zug_zug.mp3
│   ├── ready_to_work.mp3
│   ├── job_done.mp3
│   ├── something_need_doing.mp3
│   ├── me_not_that_kind_orc.mp3
│   ├── that_not_possible.mp3
│   ├── me_tired.mp3
│   ├── for_the_horde.mp3
│   └── work_work.mp3
├── aoe/
│   ├── horn.mp3
│   ├── yes.mp3
│   ├── allhail.mp3
│   ├── no.mp3
│   ├── wololo.mp3
│   └── victory.mp3
├── memes/
│   ├── hello_there.mp3
│   ├── lets_go.mp3
│   ├── nice.mp3
│   ├── bruh.mp3
│   ├── windows_error.mp3
│   ├── sad_trombone.mp3
│   ├── airhorn.mp3
│   └── thanos_snap.mp3
└── minimal/
    ├── chime.mp3
    ├── click.mp3
    ├── ding.mp3
    ├── error.mp3
    └── whoosh.mp3
```

**License Compliance**:
- Document source and license for each sound
- Include LICENSE.txt in assets directory
- Prefer CC0 or CC-BY licensed sounds

---

### 5.2 User Documentation

**File**: `docs/FUNNY_SOUNDS.md`

```markdown
# Funny Sounds Integration

## Overview

Lyra includes a sound notification system that plays funny sounds for workflow events, making your research sessions more engaging and helping you notice when long-running tasks complete.

## Quick Start

```bash
# Enable sounds
lyra sounds enable

# Choose a theme
lyra sounds theme warcraft

# Set volume
lyra sounds volume 0.5

# Test it out
lyra sounds test task_complete
```

## Available Themes

### Warcraft III Peon
Classic Warcraft III peon voice lines:
- Session start: "Zug zug!"
- Task complete: "Job's done!"
- Error: "Something need doing?"
- Rate limit: "Me tired... need rest."

```bash
lyra sounds theme warcraft
```

### Age of Empires
Age of Empires villager sounds:
- Session start: Battle horn
- Task complete: "All hail!"
- Compact: "Wololo!"

```bash
lyra sounds theme aoe
```

### Memes
Internet meme sounds:
- Task complete: "Nice!"
- Error: Bruh sound effect
- Milestone: Airhorn

```bash
lyra sounds theme memes
```

### Minimal
Subtle notification sounds for professional environments:
- Task complete: Ding
- Error: Error beep

```bash
lyra sounds theme minimal
```

## Commands

```bash
# Enable/disable
lyra sounds enable
lyra sounds disable

# Mute temporarily (doesn't save to config)
lyra sounds mute
lyra sounds unmute

# Change theme
lyra sounds theme <theme_name>

# List available themes
lyra sounds themes

# Set volume (0.0 to 1.0)
lyra sounds volume 0.5

# Test a sound
lyra sounds test task_complete
```

## Configuration

Edit `~/.lyra/sounds_config.json`:

```json
{
  "enabled": true,
  "theme": "warcraft",
  "volume": 0.5,
  "adaptive_volume": false,
  "context_aware": false,
  "productivity_mode": false
}
```

### Advanced Features

**Adaptive Volume**: Increases volume if you don't respond to completion notification
```json
"adaptive_volume": true
```

**Context-Aware**: Different sounds for different file types
```json
"context_aware": true
```

**Productivity Mode**: Reduces sounds near deadlines
```json
"productivity_mode": true
```

## Events

Sounds play for these events:
- `session_start`: New session begins
- `task_start`: Task starts
- `task_complete`: Task completes
- `error`: Generic error
- `syntax_error`: Syntax error
- `logic_error`: Logic error
- `rate_limit`: Rate limit hit
- `milestone`: Milestone reached (10, 25, 50, 100 tasks)
- `compact`: Context compaction

## Custom Sounds

Add your own sounds:

1. Create directory: `~/.lyra/sounds/custom/`
2. Add MP3 files
3. Create theme definition: `~/.lyra/sounds/custom_theme.json`

```json
{
  "name": "custom",
  "description": "My custom sounds",
  "sounds": {
    "session_start": "custom/my_start.mp3",
    "task_complete": "custom/my_complete.mp3"
  }
}
```

## Troubleshooting

**No sound playing?**
- Check if sounds are enabled: `lyra sounds status`
- Test audio player: `lyra sounds test task_complete`
- Verify volume: `lyra sounds volume 0.8`

**Wrong audio backend?**
- macOS: Uses `afplay`
- Linux: Uses `paplay` or `aplay`
- Windows: Uses PowerShell

**Sound files missing?**
- Verify assets directory exists
- Check file permissions
- Re-download sound pack

## Platform Support

- ✅ macOS (afplay)
- ✅ Linux (PulseAudio/ALSA)
- ✅ Windows (PowerShell)
- ✅ WSL (PowerShell bridge)
```

---

## Testing Strategy

### Unit Tests (50 tests total)

1. **AudioPlayer** (10 tests)
   - Backend detection
   - Command building
   - Play with mock subprocess
   - Volume control
   - Background vs foreground

2. **ThemeManager** (8 tests)
   - Load builtin themes
   - Get theme
   - List themes
   - Get sound path
   - Missing theme/event

3. **SoundManager** (10 tests)
   - Play event
   - Mute/unmute
   - Volume control
   - Theme switching
   - Disabled sounds

4. **EventMapper** (6 tests)
   - Map syntax error
   - Map logic error
   - Map rate limit
   - Detect milestone
   - Generic error

5. **SoundHooks** (8 tests)
   - Session start hook
   - Task start hook
   - Task complete hook
   - Error hook
   - Milestone detection
   - Compact hook

6. **AdaptiveVolume** (4 tests)
   - Base volume
   - Volume increase
   - Reset on response
   - Threshold timing

7. **ContextAware** (4 tests)
   - File type detection
   - Time-based sounds
   - Fallback to default

### Integration Tests (10 tests)

1. Full sound workflow
2. Theme switching
3. Volume persistence
4. Mute state
5. Adaptive volume in action
6. Context-aware selection
7. Productivity mode
8. CLI integration
9. Config persistence
10. Cross-platform compatibility

---

## Success Criteria

- [ ] All 60 tests passing
- [ ] Sounds play on all platforms (macOS, Linux, Windows)
- [ ] All 4 themes implemented with sound files
- [ ] Volume control works
- [ ] Mute/unmute works
- [ ] Theme switching works
- [ ] Adaptive volume increases after no response
- [ ] Context-aware sounds work
- [ ] Productivity mode reduces volume
- [ ] CLI commands work
- [ ] Configuration persists
- [ ] Documentation complete

---

## Sound Event Mapping Reference

| Lyra Event | Warcraft | Age of Empires | Memes | Minimal |
|------------|----------|----------------|-------|---------|
| Session start | "Zug zug!" | Horn | "Hello there" | Chime |
| Task start | "Ready to work" | "Yes" | "Let's go" | Click |
| Task complete | "Job's done!" | "All hail!" | "Nice!" | Ding |
| Error | "Something need doing?" | "No" | "Bruh" | Error beep |
| Syntax error | "Me not that kind of orc!" | "No" | Windows error | Error beep |
| Logic error | "That not possible!" | "No" | "Bruh" | Error beep |
| Rate limit | "Me tired..." | "No" | Sad trombone | Error beep |
| Milestone | "For the Horde!" | Victory | Airhorn | Ding |
| Compact | "Work work" | "Wololo!" | Thanos snap | Whoosh |

---

## Future Enhancements

1. **Multiplayer mode**: Sync sounds across team for pair programming
2. **Custom sound packs**: Community-contributed themes
3. **Sound visualization**: Visual feedback for deaf/hard-of-hearing users
4. **Streaming integration**: OBS/Twitch sound alerts
5. **Voice synthesis**: Generate custom voice lines
6. **Sound mixing**: Layer multiple sounds
7. **Spatial audio**: 3D sound positioning
8. **Haptic feedback**: Vibration on mobile devices

---

## References

- Sound implementation guide: https://alexop.dev/posts/how-i-added-sound-effects-to-claude-code-with-hooks/
- Warcraft peon notifications: https://freedium-mirror.cfd/https://medium.com/@gentechimports/warcraft-iii-peon-voice-notifications-for-claude-code-a-developers-story-dd6842deb852
- MyInstants soundboard: https://www.myinstants.com/
- Voicemod Tuna: https://tuna.voicemod.net/
- Freesound: https://freesound.org/
- Sound design guide: https://www.toptal.com/designers/ux/ux-sounds-guide

