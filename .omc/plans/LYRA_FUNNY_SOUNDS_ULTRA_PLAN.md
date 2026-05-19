# Lyra Funny Sounds Integration - Ultra Plan

## Overview

Transform Lyra into an engaging, personality-rich AI agent by integrating iconic and hilarious sound effects from popular video games and memes. This feature will provide audio feedback for various events, making development more enjoyable and helping users stay aware of Lyra's status without constantly checking the terminal.

## Research Summary

### Inspiration Sources

1. **Warcraft III Peon Notifications** ([Medium Article](https://freedium-mirror.cfd/https://medium.com/@gentechimports/warcraft-iii-peon-voice-notifications-for-claude-code-a-developers-story-dd6842deb852))
   - Increased session length from 45 to 73 minutes
   - Reduced context switches by 67%
   - 40% increase in daily code output
   - Transformed debugging from dreaded to enjoyable

2. **Age of Empires Sound Effects** ([alexop.dev](https://alexop.dev/posts/how-i-added-sound-effects-to-claude-code-with-hooks/))
   - Simple hook-based implementation
   - Background audio playback (non-blocking)
   - Event-driven architecture
   - Cross-platform support

3. **Community Ecosystem**
   - 40+ voice packs available (Portal GLaDOS, StarCraft, Age of Empires, Civilization)
   - Active community creating custom sound packs
   - Proven psychological benefits

### Key Findings

**Psychological Impact**:
- Treats AI as a tool/game rather than coworker
- Reduces cognitive load from status checking
- Makes long-running tasks less frustrating
- Increases engagement and productivity

**Technical Requirements**:
- Event-driven hook system
- Background audio playback
- Cross-platform audio support
- Configurable sound mappings
- Volume control and adaptive behavior

## Goals

1. **Engagement**: Make Lyra fun and personality-rich
2. **Awareness**: Audio feedback for task completion
3. **Productivity**: Reduce context switching
4. **Customization**: Multiple sound packs and themes
5. **Community**: Enable user-created sound packs

## Architecture

### Phase 1: Audio System Foundation (Week 1)

**Package**: `lyra-audio`

**Components**:

1. **Audio Player** (`audio_player.py`)
   ```python
   class AudioPlayer:
       """Cross-platform audio playback."""
       
       def __init__(self):
           self.platform = self._detect_platform()
           self.player = self._get_player()
       
       def play(self, sound_path: str, blocking: bool = False):
           """Play audio file."""
           if self.platform == "darwin":  # macOS
               cmd = f"afplay {sound_path}"
           elif self.platform == "linux":
               cmd = f"aplay {sound_path}"
           elif self.platform == "win32":  # Windows
               cmd = f'powershell.exe -c (New-Object Media.SoundPlayer "{sound_path}").PlaySync()'
           
           if not blocking:
               cmd += " &"
           
           subprocess.run(cmd, shell=True)
       
       def play_async(self, sound_path: str):
           """Play audio in background thread."""
           threading.Thread(target=self.play, args=(sound_path,)).start()
   ```

2. **Sound Manager** (`sound_manager.py`)
   ```python
   class SoundManager:
       """Manage sound effects and themes."""
       
       def __init__(self, sounds_dir: str = "~/.lyra/sounds"):
           self.sounds_dir = Path(sounds_dir).expanduser()
           self.sounds_dir.mkdir(parents=True, exist_ok=True)
           self.player = AudioPlayer()
           self.config = self._load_config()
           self.current_theme = self.config.get("theme", "warcraft")
       
       def play_event(self, event: str):
           """Play sound for event."""
           sound_file = self._get_sound_for_event(event)
           if sound_file and sound_file.exists():
               self.player.play_async(str(sound_file))
       
       def _get_sound_for_event(self, event: str) -> Optional[Path]:
           """Get sound file for event based on theme."""
           theme_dir = self.sounds_dir / self.current_theme
           mapping = self.config.get("mappings", {}).get(event)
           if mapping:
               return theme_dir / mapping
           return None
   ```

3. **Event Hook System** (`event_hooks.py`)
   ```python
   class EventHookSystem:
       """Hook system for audio events."""
       
       def __init__(self):
           self.sound_manager = SoundManager()
           self.hooks = self._load_hooks()
       
       def trigger(self, event: str, context: Dict[str, Any] = None):
           """Trigger event hooks."""
           # Play sound
           self.sound_manager.play_event(event)
           
           # Execute custom hooks
           if event in self.hooks:
               for hook in self.hooks[event]:
                   self._execute_hook(hook, context)
       
       def register_hook(self, event: str, callback: Callable):
           """Register custom hook."""
           if event not in self.hooks:
               self.hooks[event] = []
           self.hooks[event].append(callback)
   ```

### Phase 2: Sound Pack Library (Week 2)

**Sound Packs to Include**:

#### 1. Warcraft III - Peon Pack (Default)
- **session_start**: "Zug zug!" (Ready to work)
- **task_start**: "Work, work!" (Task started)
- **task_complete**: "Job's done!" (Task completed)
- **prompt_submit**: "Ready to work!" (Accepting command)
- **error_general**: "Something need doing?" (General error)
- **error_syntax**: "Me not that kind of orc!" (Syntax error)
- **error_logic**: "That not possible!" (Logic error)
- **rate_limit**: "Me tired... need rest." (Rate limit)
- **milestone**: "For the Horde!" (After 10 completions)
- **context_compact**: "Hmm?" (Context compaction)

#### 2. Age of Empires - Monk Pack
- **session_start**: Horn sound (Battle begins)
- **prompt_submit**: "Yes!" (Villager acknowledgment)
- **task_complete**: "All hail!" (Victory)
- **context_compact**: "Wololo!" (Priest conversion)
- **error**: "No!" (Villager denial)
- **milestone**: "Victory!" (Achievement)

#### 3. Portal - GLaDOS Pack
- **session_start**: "Hello, imbecile." (Sarcastic greeting)
- **task_start**: "Initiating test protocol." (Task start)
- **task_complete**: "Test complete." (Success)
- **error**: "Did you just throw that?" (Error)
- **rate_limit**: "I'm going to kill you." (Threat)
- **milestone**: "The cake is a lie." (Achievement)
- **context_compact**: "Deploying surprise." (Compaction)

#### 4. StarCraft - Terran Pack
- **session_start**: "In the rear with the gear!" (SCV ready)
- **task_start**: "You want a piece of me, boy?" (Marine)
- **task_complete**: "Hell, it's about time!" (Tychus)
- **error**: "We're in trouble!" (Alert)
- **milestone**: "Battlecruiser operational!" (Achievement)

#### 5. Minecraft - Villager Pack
- **session_start**: "Hmm" (Villager greeting)
- **task_complete**: "Hmm hmm!" (Happy villager)
- **error**: "Huh?" (Confused villager)
- **milestone**: "Hrr!" (Excited villager)

#### 6. Mario - Classic Pack
- **session_start**: "Let's-a go!" (Mario)
- **task_complete**: "Wahoo!" (Success)
- **error**: "Mamma mia!" (Error)
- **milestone**: "1-UP!" (Achievement)
- **coin_collect**: Coin sound (Small win)

#### 7. Metal Gear Solid - Alert Pack
- **session_start**: Codec call sound
- **error**: "!" Alert sound (Spotted)
- **task_complete**: Mission complete jingle
- **milestone**: "Kept you waiting, huh?" (Snake)

#### 8. Meme Pack - Internet Classics
- **session_start**: "It's free real estate"
- **task_complete**: "Noice" (Click)
- **error**: "Bruh" sound effect
- **rate_limit**: "Ain't nobody got time for that"
- **milestone**: "Stonks" (Achievement)

### Phase 3: Advanced Features (Week 3)

**1. Adaptive Volume System**
```python
class AdaptiveVolumeController:
    """Adjust volume based on context."""
    
    def __init__(self):
        self.base_volume = 0.7
        self.last_interaction = time.time()
    
    def get_volume(self) -> float:
        """Get current volume level."""
        idle_time = time.time() - self.last_interaction
        
        # Increase volume after 30 seconds of no response
        if idle_time > 30:
            return min(1.0, self.base_volume + 0.3)
        
        return self.base_volume
    
    def update_interaction(self):
        """Update last interaction time."""
        self.last_interaction = time.time()
```

**2. Time-Based Behavior**
```python
class TimeBehaviorController:
    """Adjust behavior based on time of day."""
    
    def should_be_ridiculous(self) -> bool:
        """20% more ridiculous after 5 PM."""
        hour = datetime.now().hour
        if hour >= 17:  # After 5 PM
            return random.random() < 0.2
        return False
    
    def get_sound_variant(self, event: str) -> str:
        """Get sound variant based on time."""
        if self.should_be_ridiculous():
            return f"{event}_ridiculous"
        return event
```

**3. Productivity Mode**
```python
class ProductivityModeController:
    """Reduce sounds near deadlines."""
    
    def __init__(self):
        self.deadline = None
        self.productivity_mode = False
    
    def set_deadline(self, deadline: datetime):
        """Set project deadline."""
        self.deadline = deadline
        self._update_mode()
    
    def _update_mode(self):
        """Update productivity mode based on deadline."""
        if self.deadline:
            days_until = (self.deadline - datetime.now()).days
            self.productivity_mode = days_until <= 3
    
    def should_play_sound(self, event: str) -> bool:
        """Check if sound should play."""
        if not self.productivity_mode:
            return True
        
        # Only play critical sounds in productivity mode
        critical_events = ["error", "task_complete", "milestone"]
        return event in critical_events
```

**4. Multiplayer Mode (Team Sync)**
```python
class MultiplayerModeController:
    """Synchronize sounds across team."""
    
    def __init__(self, team_id: str):
        self.team_id = team_id
        self.redis_client = redis.Redis()
    
    def broadcast_event(self, event: str):
        """Broadcast event to team."""
        self.redis_client.publish(
            f"lyra:team:{self.team_id}",
            json.dumps({"event": event, "timestamp": time.time()})
        )
    
    def listen_for_events(self):
        """Listen for team events."""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(f"lyra:team:{self.team_id}")
        
        for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                self.play_team_event(data["event"])
```

### Phase 4: Sound Pack Manager (Week 4)

**Features**:

1. **Sound Pack Installation**
   ```bash
   lyra sounds install warcraft
   lyra sounds install glados
   lyra sounds install custom --url https://github.com/user/pack.git
   ```

2. **Sound Pack Creation**
   ```bash
   lyra sounds create my-pack
   # Creates template structure:
   # ~/.lyra/sounds/my-pack/
   #   ├── manifest.json
   #   ├── session_start.mp3
   #   ├── task_complete.mp3
   #   └── ...
   ```

3. **Sound Pack Marketplace**
   ```python
   class SoundPackMarketplace:
       """Browse and install community sound packs."""
       
       def list_packs(self) -> List[SoundPack]:
           """List available sound packs."""
           response = requests.get("https://lyra-sounds.io/api/packs")
           return [SoundPack(**pack) for pack in response.json()]
       
       def install_pack(self, pack_id: str):
           """Install sound pack."""
           pack = self._download_pack(pack_id)
           self._extract_pack(pack)
           self._validate_pack(pack)
   ```

4. **Sound Pack Manifest**
   ```json
   {
     "name": "Warcraft III - Peon Pack",
     "version": "1.0.0",
     "author": "Lyra Community",
     "description": "Classic Warcraft III peon voice lines",
     "sounds": {
       "session_start": "zug_zug.mp3",
       "task_start": "work_work.mp3",
       "task_complete": "jobs_done.mp3",
       "error_general": "something_need_doing.mp3"
     },
     "metadata": {
       "game": "Warcraft III",
       "character": "Peon",
       "language": "en",
       "tags": ["funny", "nostalgic", "gaming"]
     }
   }
   ```

### Phase 5: Configuration & UI (Week 5)

**1. Configuration File** (`~/.lyra/sounds.json`)
```json
{
  "enabled": true,
  "theme": "warcraft",
  "volume": 0.7,
  "adaptiveVolume": true,
  "productivityMode": false,
  "deadline": null,
  "multiplayerMode": false,
  "teamId": null,
  "eventMappings": {
    "session_start": true,
    "task_start": true,
    "task_complete": true,
    "prompt_submit": false,
    "error": true,
    "milestone": true,
    "context_compact": true
  },
  "customSounds": {
    "error_critical": "~/.lyra/sounds/custom/alarm.mp3"
  }
}
```

**2. CLI Commands**
```bash
# Enable/disable sounds
lyra sounds on
lyra sounds off

# Change theme
lyra sounds theme warcraft
lyra sounds theme glados
lyra sounds theme mario

# List available themes
lyra sounds list

# Configure volume
lyra sounds volume 0.8

# Enable productivity mode
lyra sounds productivity on --deadline 2026-05-25

# Test sounds
lyra sounds test session_start
lyra sounds test all

# Preview theme
lyra sounds preview warcraft

# Enable multiplayer mode
lyra sounds multiplayer on --team my-team-id
```

**3. Interactive Configuration**
```bash
lyra sounds config
# Interactive menu:
# 1. Enable/disable sounds
# 2. Select theme
# 3. Configure volume
# 4. Enable adaptive volume
# 5. Set productivity mode
# 6. Configure event mappings
# 7. Test sounds
```

**4. Desktop App Integration**
- Sound settings panel
- Theme selector with preview
- Volume slider
- Event mapping checkboxes
- Real-time sound testing
- Visual waveform display

### Phase 6: Community Features (Week 6)

**1. Sound Pack Repository**
- GitHub-based sound pack hosting
- Community contributions
- Rating and review system
- Download statistics

**2. Sound Pack Editor**
```bash
lyra sounds edit my-pack
# Opens interactive editor:
# - Record/import sounds
# - Map sounds to events
# - Test sound pack
# - Export for sharing
```

**3. Sound Pack Sharing**
```bash
# Publish to marketplace
lyra sounds publish my-pack --public

# Share via URL
lyra sounds share my-pack
# Returns: https://lyra-sounds.io/packs/username/my-pack

# Export as zip
lyra sounds export my-pack --output my-pack.zip
```

**4. Community Challenges**
- Weekly sound pack themes
- Most creative sound pack awards
- Featured sound packs
- User showcases

## Implementation Details

### Event Types

```python
class LyraEvent(Enum):
    """Lyra audio events."""
    
    # Session events
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    
    # Task events
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    
    # User interaction
    PROMPT_SUBMIT = "prompt_submit"
    PROMPT_CANCEL = "prompt_cancel"
    
    # Errors
    ERROR_GENERAL = "error_general"
    ERROR_SYNTAX = "error_syntax"
    ERROR_LOGIC = "error_logic"
    ERROR_NETWORK = "error_network"
    ERROR_RATE_LIMIT = "error_rate_limit"
    
    # System events
    CONTEXT_COMPACT = "context_compact"
    MEMORY_SAVE = "memory_save"
    CACHE_HIT = "cache_hit"
    
    # Achievements
    MILESTONE_10 = "milestone_10"
    MILESTONE_50 = "milestone_50"
    MILESTONE_100 = "milestone_100"
    STREAK_7 = "streak_7"
    PERFECT_DAY = "perfect_day"
    
    # Special
    EASTER_EGG = "easter_egg"
    RANDOM_FUN = "random_fun"
```

### Audio File Requirements

**Format**: MP3, WAV, OGG
**Duration**: 0.5-3 seconds (short and punchy)
**Sample Rate**: 44.1kHz
**Bit Rate**: 128-320 kbps
**Channels**: Mono or Stereo
**Volume**: Normalized to -14 LUFS

### Cross-Platform Audio Support

```python
class PlatformAudioPlayer:
    """Platform-specific audio playback."""
    
    @staticmethod
    def get_player() -> AudioPlayer:
        """Get platform-specific player."""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            return MacOSAudioPlayer()
        elif system == "Linux":
            return LinuxAudioPlayer()
        elif system == "Windows":
            return WindowsAudioPlayer()
        else:
            return FallbackAudioPlayer()

class MacOSAudioPlayer(AudioPlayer):
    def play(self, path: str):
        subprocess.Popen(["afplay", path])

class LinuxAudioPlayer(AudioPlayer):
    def play(self, path: str):
        # Try multiple players
        for player in ["aplay", "paplay", "ffplay"]:
            if shutil.which(player):
                subprocess.Popen([player, path])
                return

class WindowsAudioPlayer(AudioPlayer):
    def play(self, path: str):
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
```

## Testing Strategy

### Unit Tests
- Audio player initialization
- Sound file loading
- Event mapping
- Volume control
- Theme switching

### Integration Tests
- Hook system integration
- Cross-platform audio playback
- Sound pack installation
- Configuration management

### E2E Tests
- Full sound pack workflow
- Theme switching during session
- Adaptive volume behavior
- Productivity mode activation

### User Testing
- A/B testing different sound packs
- Productivity impact measurement
- User satisfaction surveys
- Sound preference analysis

## Success Metrics

1. **Engagement**: 50% of users enable sounds
2. **Productivity**: 20% increase in session length
3. **Awareness**: 60% reduction in status checking
4. **Community**: 100+ community sound packs
5. **Satisfaction**: 4.5+ star rating

## Timeline

- **Week 1**: Audio system foundation
- **Week 2**: Sound pack library (8 packs)
- **Week 3**: Advanced features (adaptive, time-based, productivity)
- **Week 4**: Sound pack manager & marketplace
- **Week 5**: Configuration & UI
- **Week 6**: Community features & launch
- **Week 7**: Beta testing & feedback
- **Week 8**: Public release

## Sound Pack Roadmap

### Launch (8 packs)
1. Warcraft III - Peon
2. Age of Empires - Monk
3. Portal - GLaDOS
4. StarCraft - Terran
5. Minecraft - Villager
6. Mario - Classic
7. Metal Gear Solid - Alert
8. Meme Pack - Internet Classics

### Post-Launch (Community)
- Civilization - Narrator
- Zelda - Link
- Sonic - Classic
- Street Fighter - Hadouken
- Doom - Demon
- Half-Life - Gordon Freeman
- Overwatch - Heroes
- League of Legends - Champions
- Anime - Various characters
- Movie Quotes - Classics

## Legal Considerations

### Copyright & Fair Use
- Use royalty-free sounds when possible
- Obtain licenses for copyrighted material
- Provide attribution in manifest files
- Community packs require copyright compliance

### Sound Sources
1. **Royalty-Free Libraries**:
   - [Pixabay](https://pixabay.com/sound-effects/)
   - [Freesound](https://freesound.org/)
   - [Zapsplat](https://www.zapsplat.com/)

2. **Game Sound Extraction** (Fair Use):
   - Personal use only
   - Educational purposes
   - Transformative use
   - No commercial distribution

3. **Community Contributions**:
   - User-generated content
   - Original recordings
   - Licensed material
   - Public domain sounds

## Future Enhancements

1. **AI-Generated Voices**: Custom voice synthesis for personalized sound packs
2. **Voice Commands**: "Lyra, change theme to GLaDOS"
3. **Spatial Audio**: 3D audio positioning for different event types
4. **Music Integration**: Background music themes
5. **Haptic Feedback**: Vibration patterns for mobile/desktop
6. **Visual Effects**: Synchronized animations with sounds
7. **Sound Mixing**: Layer multiple sounds for complex events
8. **Accessibility**: Visual alternatives for hearing-impaired users

## References

- [Warcraft III Peon Notifications](https://freedium-mirror.cfd/https://medium.com/@gentechimports/warcraft-iii-peon-voice-notifications-for-claude-code-a-developers-story-dd6842deb852)
- [Adding Sound Effects to Claude Code](https://alexop.dev/posts/how-i-added-sound-effects-to-claude-code-with-hooks/)
- [Claude Sounds Project](https://daveschumaker.net/claude-sounds-better-notifications-for-claude-code/)
- [XDA: Claude Code Warcraft Sounds](https://www.xda-developers.com/claude-code-now-makes-warcraft-noises-to-get-my-attention/)
- [Know Your Meme: Gaming Memes 2024](https://knowyourmeme.com/editorials/kym-review-the-top-gaming-memes-of-2024)
- [Voicemod Sound Memes](https://tuna.voicemod.net/sounds/tag/games/)
- [MyInstants Meme Soundboard](https://www.myinstants.com/en/search/?name=MEME)
- [The Sounds Resource](https://sounds.spriters-resource.com/)
- [Portal GLaDOS Sounds](https://www.sounds-resource.com/pc_computer/portal/sound/886/)
- [Soundstripe Notification Sounds](https://www.soundstripe.com/blogs/best-phone-notification-sound-effects)

---

## Quick Start Guide

### For Users

1. **Install Lyra Audio**:
   ```bash
   pip install lyra-audio
   ```

2. **Enable Sounds**:
   ```bash
   lyra sounds on
   ```

3. **Choose Theme**:
   ```bash
   lyra sounds theme warcraft
   ```

4. **Test It**:
   ```bash
   lyra sounds test all
   ```

### For Developers

1. **Integrate Audio Events**:
   ```python
   from lyra_audio import EventHookSystem
   
   hooks = EventHookSystem()
   
   # Trigger events
   hooks.trigger(LyraEvent.SESSION_START)
   hooks.trigger(LyraEvent.TASK_COMPLETE)
   ```

2. **Create Custom Sound Pack**:
   ```bash
   lyra sounds create my-pack
   cd ~/.lyra/sounds/my-pack
   # Add your MP3 files
   # Edit manifest.json
   lyra sounds activate my-pack
   ```

3. **Share Your Pack**:
   ```bash
   lyra sounds publish my-pack --public
   ```

---

**Let's make Lyra the most fun and engaging AI agent ever! 🎮🔊🎉**
