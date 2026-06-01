# 04. Animations - Lyra UI/UX Plan

**Version**: 1.0  
**Status**: ✅ Complete  
**Last Updated**: 2026-05-21

---

## Overview

This document defines animation and transition patterns for Lyra's terminal interface. Animations provide feedback, guide attention, and create a polished, responsive feel.

---

## Animation Principles

### 1. Purpose-Driven
- Every animation serves a purpose
- No animation for decoration only
- Enhance usability and feedback

### 2. Subtle and Fast
- Quick animations (100-300ms)
- Subtle movements
- Don't distract from content

### 3. Consistent
- Same animation for same action
- Predictable behavior
- Unified timing

### 4. Performant
- No frame drops
- Efficient rendering
- Graceful degradation

---

## Animation Types

### 1. Loading Animations

#### Spinner (Dots)
```
Frame 1: ⠋  Processing...
Frame 2: ⠙  Processing...
Frame 3: ⠹  Processing...
Frame 4: ⠸  Processing...
Frame 5: ⠼  Processing...
Frame 6: ⠴  Processing...
Frame 7: ⠦  Processing...
Frame 8: ⠧  Processing...
```

**Timing**: 80ms per frame (12.5 FPS)  
**Use Case**: General loading, waiting for response

**Implementation**:
```python
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
SPINNER_INTERVAL = 0.08  # 80ms

class Spinner:
    def __init__(self, text: str = "Loading..."):
        self.text = text
        self.frame = 0
    
    def next_frame(self) -> str:
        frame = SPINNER_FRAMES[self.frame % len(SPINNER_FRAMES)]
        self.frame += 1
        return f"{frame} {self.text}"
```

#### Progress Bar
```
Frame 1: [████░░░░░░░░░░░░░░░░] 20%
Frame 2: [████████░░░░░░░░░░░░] 40%
Frame 3: [████████████░░░░░░░░] 60%
Frame 4: [████████████████░░░░] 80%
Frame 5: [████████████████████] 100%
```

**Timing**: Update on progress change  
**Use Case**: File operations, downloads, multi-step tasks

**Implementation**:
```python
def render_progress_bar(progress: float, width: int = 20) -> str:
    filled = int(progress * width)
    bar = "█" * filled + "░" * (width - filled)
    percentage = int(progress * 100)
    return f"[{bar}] {percentage}%"
```

#### Pulse Animation
```
Frame 1: ○ Waiting...
Frame 2: ◐ Waiting...
Frame 3: ● Waiting...
Frame 4: ◑ Waiting...
```

**Timing**: 200ms per frame (5 FPS)  
**Use Case**: Idle state, waiting for user input

---

### 2. Transition Animations

#### Fade In
```
Frame 1: (opacity 0%)   [invisible]
Frame 2: (opacity 33%)  [faint]
Frame 3: (opacity 66%)  [visible]
Frame 4: (opacity 100%) [full]
```

**Timing**: 150ms total (50ms per frame)  
**Use Case**: New messages, notifications, panels

**Terminal Implementation**:
```python
# Terminal doesn't support true opacity, use color intensity
def fade_in_text(text: str, frame: int, total_frames: int = 3) -> str:
    if frame >= total_frames:
        return text
    
    # Use dim/bright ANSI codes to simulate fade
    if frame == 0:
        return f"\033[2m{text}\033[0m"  # Dim
    elif frame == 1:
        return text  # Normal
    else:
        return f"\033[1m{text}\033[0m"  # Bright
```

#### Slide In
```
Frame 1: [      Message]  (off-screen right)
Frame 2: [   Message   ]  (sliding in)
Frame 3: [Message      ]  (in position)
```

**Timing**: 200ms total  
**Use Case**: New messages, panels, modals

**Implementation**:
```python
def slide_in_text(text: str, frame: int, total_frames: int = 3, width: int = 60) -> str:
    if frame >= total_frames:
        return text.ljust(width)
    
    # Calculate position
    progress = frame / total_frames
    offset = int((1 - progress) * width)
    
    return " " * offset + text
```

#### Expand/Collapse
```
Expand:
Frame 1: [▶ Section]
Frame 2: [▼ Section
         ]
Frame 3: [▼ Section
           Content line 1
         ]
Frame 4: [▼ Section
           Content line 1
           Content line 2
         ]

Collapse: Reverse order
```

**Timing**: 100ms per line  
**Use Case**: Expandable sections, tool call details

---

### 3. Feedback Animations

#### Success Checkmark
```
Frame 1: ⏳ Processing...
Frame 2: ✓  Processing...
Frame 3: ✅ Done!
```

**Timing**: Instant transition  
**Use Case**: Task completion, successful operations

#### Error Shake
```
Frame 1: ❌ Error message
Frame 2:  ❌ Error message  (shift right)
Frame 3: ❌ Error message   (center)
Frame 4:  ❌ Error message  (shift right)
Frame 5: ❌ Error message   (center)
```

**Timing**: 50ms per frame (250ms total)  
**Use Case**: Errors, validation failures

**Implementation**:
```python
def shake_text(text: str, frame: int) -> str:
    if frame % 2 == 0:
        return text
    return " " + text
```

#### Typing Indicator
```
Frame 1: Agent is typing.
Frame 2: Agent is typing..
Frame 3: Agent is typing...
Frame 4: Agent is typing.
```

**Timing**: 300ms per frame  
**Use Case**: Waiting for agent response

---

### 4. Attention Animations

#### Blink
```
Frame 1: ⚠️  Warning message
Frame 2:    Warning message  (hidden)
Frame 3: ⚠️  Warning message
Frame 4:    Warning message  (hidden)
```

**Timing**: 500ms per frame (slow blink)  
**Use Case**: Warnings, important notifications

**Implementation**:
```python
def blink_text(text: str, frame: int, icon: str = "⚠️") -> str:
    if frame % 2 == 0:
        return f"{icon} {text}"
    return f"   {text}"  # Hide icon
```

#### Pulse Border
```
Frame 1: ┌─────────┐  (normal)
Frame 2: ┏━━━━━━━━━┓  (bold)
Frame 3: ┌─────────┐  (normal)
Frame 4: ┏━━━━━━━━━┓  (bold)
```

**Timing**: 400ms per frame  
**Use Case**: Active panel, focused element

---

### 5. State Transition Animations

#### Status Change
```
Idle → Active:
Frame 1: ○ Idle
Frame 2: ◐ Starting...
Frame 3: ● Active

Active → Complete:
Frame 1: ● Active
Frame 2: ◑ Finishing...
Frame 3: ✅ Complete
```

**Timing**: 150ms per frame  
**Use Case**: Agent state changes, task status

#### Mode Switch
```
Chat → Goal Mode:
Frame 1: 💬 Chat Mode
Frame 2: 💬→🎯 Switching...
Frame 3: 🎯 Goal Mode
```

**Timing**: 200ms total  
**Use Case**: Mode changes, view switches

---

## Animation Timing

### Timing Curves

**Ease-Out** (Fast start, slow end):
- Use for: Entering elements, appearing content
- Duration: 150-200ms
- Feel: Snappy, responsive

**Ease-In** (Slow start, fast end):
- Use for: Exiting elements, disappearing content
- Duration: 100-150ms
- Feel: Natural, smooth

**Linear** (Constant speed):
- Use for: Loading spinners, progress bars
- Duration: Varies
- Feel: Mechanical, predictable

**Ease-In-Out** (Slow start and end):
- Use for: Transitions, movements
- Duration: 200-300ms
- Feel: Smooth, polished

### Duration Guidelines

| Animation Type | Duration | FPS |
|---------------|----------|-----|
| Spinner | 80ms/frame | 12.5 |
| Progress bar | Instant | N/A |
| Fade in | 150ms | 20 |
| Slide in | 200ms | 20 |
| Expand/collapse | 100ms/line | 10 |
| Success/error | Instant | N/A |
| Typing indicator | 300ms/frame | 3.3 |
| Blink | 500ms/frame | 2 |
| Pulse | 400ms/frame | 2.5 |

---

## Animation System Architecture

### Animation Manager

```python
from typing import Callable, Optional
import time
import threading

class Animation:
    def __init__(
        self,
        frames: list[str],
        interval: float,
        loop: bool = True
    ):
        self.frames = frames
        self.interval = interval
        self.loop = loop
        self.current_frame = 0
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self, callback: Callable[[str], None]):
        """Start animation with callback for each frame"""
        self.running = True
        self.thread = threading.Thread(target=self._run, args=(callback,))
        self.thread.start()
    
    def stop(self):
        """Stop animation"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _run(self, callback: Callable[[str], None]):
        """Animation loop"""
        while self.running:
            frame = self.frames[self.current_frame]
            callback(frame)
            
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.running = False
                    break
            
            time.sleep(self.interval)
```

### Pre-built Animations

```python
class Animations:
    @staticmethod
    def spinner(text: str = "Loading...") -> Animation:
        frames = [f"{s} {text}" for s in ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"]]
        return Animation(frames, interval=0.08, loop=True)
    
    @staticmethod
    def dots(text: str = "Loading") -> Animation:
        frames = [f"{text}.", f"{text}..", f"{text}..."]
        return Animation(frames, interval=0.3, loop=True)
    
    @staticmethod
    def pulse() -> Animation:
        frames = ["○", "◐", "●", "◑"]
        return Animation(frames, interval=0.2, loop=True)
    
    @staticmethod
    def typing() -> Animation:
        frames = ["typing.", "typing..", "typing..."]
        return Animation(frames, interval=0.3, loop=True)
```

### Usage Example

```python
# Create and start spinner
spinner = Animations.spinner("Processing request")

def update_display(frame: str):
    print(f"\r{frame}", end="", flush=True)

spinner.start(update_display)

# Do work...
time.sleep(5)

# Stop spinner
spinner.stop()
print("\r✅ Done!          ")
```

---

## Transition System

### Transition Manager

```python
class Transition:
    def __init__(
        self,
        duration: float,
        easing: str = "ease-out"
    ):
        self.duration = duration
        self.easing = easing
        self.start_time: Optional[float] = None
    
    def start(self):
        """Start transition"""
        self.start_time = time.time()
    
    def progress(self) -> float:
        """Get current progress (0.0 to 1.0)"""
        if not self.start_time:
            return 0.0
        
        elapsed = time.time() - self.start_time
        progress = min(elapsed / self.duration, 1.0)
        
        # Apply easing
        if self.easing == "ease-out":
            return 1 - (1 - progress) ** 2
        elif self.easing == "ease-in":
            return progress ** 2
        elif self.easing == "ease-in-out":
            if progress < 0.5:
                return 2 * progress ** 2
            return 1 - 2 * (1 - progress) ** 2
        else:  # linear
            return progress
    
    def is_complete(self) -> bool:
        """Check if transition is complete"""
        return self.progress() >= 1.0
```

### Transition Effects

```python
class TransitionEffects:
    @staticmethod
    def fade_in(text: str, progress: float) -> str:
        """Fade in text using color intensity"""
        if progress < 0.33:
            return f"\033[2m{text}\033[0m"  # Dim
        elif progress < 0.66:
            return text  # Normal
        else:
            return f"\033[1m{text}\033[0m"  # Bright
    
    @staticmethod
    def slide_in(text: str, progress: float, width: int) -> str:
        """Slide in text from right"""
        offset = int((1 - progress) * width)
        return " " * offset + text
    
    @staticmethod
    def expand(lines: list[str], progress: float) -> list[str]:
        """Expand content line by line"""
        visible_lines = int(progress * len(lines))
        return lines[:visible_lines]
```

---

## Performance Optimization

### 1. Frame Rate Control

```python
class FrameRateController:
    def __init__(self, target_fps: int = 20):
        self.target_fps = target_fps
        self.frame_time = 1.0 / target_fps
        self.last_frame = time.time()
    
    def wait(self):
        """Wait to maintain target FPS"""
        now = time.time()
        elapsed = now - self.last_frame
        sleep_time = self.frame_time - elapsed
        
        if sleep_time > 0:
            time.sleep(sleep_time)
        
        self.last_frame = time.time()
```

### 2. Render Optimization

```python
class RenderCache:
    def __init__(self):
        self.cache: dict[str, str] = {}
    
    def get_or_render(
        self,
        key: str,
        render_func: Callable[[], str]
    ) -> str:
        """Get cached render or compute new one"""
        if key not in self.cache:
            self.cache[key] = render_func()
        return self.cache[key]
    
    def invalidate(self, key: str):
        """Invalidate cache entry"""
        if key in self.cache:
            del self.cache[key]
```

### 3. Graceful Degradation

```python
class AnimationConfig:
    def __init__(self):
        self.enabled = True
        self.reduced_motion = False
    
    def should_animate(self) -> bool:
        """Check if animations should run"""
        if not self.enabled:
            return False
        if self.reduced_motion:
            return False
        return True
    
    def get_duration(self, default: float) -> float:
        """Get animation duration (0 if disabled)"""
        if not self.should_animate():
            return 0.0
        if self.reduced_motion:
            return default * 0.5  # Faster animations
        return default
```

---

## Animation Best Practices

### 1. Use Animations Sparingly
- Only animate when it adds value
- Don't animate everything
- Respect user preferences (reduced motion)

### 2. Keep Animations Fast
- Most animations: 100-300ms
- Loading spinners: Continuous
- Avoid long animations (>500ms)

### 3. Provide Feedback
- Show loading states
- Indicate progress
- Confirm actions

### 4. Be Consistent
- Same animation for same action
- Consistent timing
- Unified style

### 5. Test Performance
- Monitor frame rates
- Check CPU usage
- Test on slow terminals

---

## Accessibility Considerations

### Reduced Motion

```python
import os

def prefers_reduced_motion() -> bool:
    """Check if user prefers reduced motion"""
    # Check environment variable
    if os.getenv("LYRA_REDUCED_MOTION") == "1":
        return True
    
    # Check system preference (macOS)
    try:
        import subprocess
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleReduceMotion"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() == "1"
    except:
        return False

# Usage
if not prefers_reduced_motion():
    # Show animations
    spinner.start()
else:
    # Show static indicator
    print("⏳ Loading...")
```

### Alternative Indicators

For users with reduced motion preferences:
- Replace spinners with static "⏳ Loading..."
- Replace progress bars with percentage text
- Replace animations with instant state changes
- Provide text descriptions of state changes

---

## Testing Animations

### Test Cases

1. **Timing Tests**:
   - Verify frame rates
   - Check animation duration
   - Test timing curves

2. **Visual Tests**:
   - Check for flicker
   - Verify smooth transitions
   - Test on different terminals

3. **Performance Tests**:
   - Monitor CPU usage
   - Check memory usage
   - Test with many animations

4. **Accessibility Tests**:
   - Test reduced motion mode
   - Verify text alternatives
   - Check screen reader compatibility

### Test Implementation

```python
import unittest
import time

class TestAnimations(unittest.TestCase):
    def test_spinner_timing(self):
        """Test spinner frame rate"""
        spinner = Animations.spinner()
        frames_rendered = 0
        
        def count_frames(frame: str):
            nonlocal frames_rendered
            frames_rendered += 1
        
        spinner.start(count_frames)
        time.sleep(1.0)
        spinner.stop()
        
        # Should render ~12.5 frames per second
        self.assertAlmostEqual(frames_rendered, 12.5, delta=2)
    
    def test_transition_progress(self):
        """Test transition progress calculation"""
        transition = Transition(duration=1.0, easing="linear")
        transition.start()
        
        time.sleep(0.5)
        progress = transition.progress()
        
        self.assertAlmostEqual(progress, 0.5, delta=0.1)
```

---

## Animation Library

### Complete Animation Set

```python
class LyraAnimations:
    # Loading animations
    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"]
    DOTS = [".", "..", "..."]
    PULSE = ["○", "◐", "●", "◑"]
    
    # Status animations
    SUCCESS = ["⏳", "✓", "✅"]
    ERROR = ["⏳", "✗", "❌"]
    WARNING = ["⏳", "⚠", "⚠️"]
    
    # State animations
    IDLE_TO_ACTIVE = ["○", "◐", "●"]
    ACTIVE_TO_COMPLETE = ["●", "◑", "✅"]
    
    # Timing constants
    FAST = 0.1      # 100ms
    NORMAL = 0.2    # 200ms
    SLOW = 0.3      # 300ms
    
    @classmethod
    def create(cls, name: str, text: str = "") -> Animation:
        """Create animation by name"""
        animations = {
            "spinner": (cls.SPINNER, 0.08),
            "dots": (cls.DOTS, 0.3),
            "pulse": (cls.PULSE, 0.2),
            "success": (cls.SUCCESS, 0.15),
            "error": (cls.ERROR, 0.15),
            "warning": (cls.WARNING, 0.15),
        }
        
        if name not in animations:
            raise ValueError(f"Unknown animation: {name}")
        
        frames, interval = animations[name]
        if text:
            frames = [f"{f} {text}" for f in frames]
        
        return Animation(frames, interval, loop=(name in ["spinner", "dots", "pulse"]))
```

---

## Summary

This animation system provides:
- ✅ 5 animation types (loading, transition, feedback, attention, state)
- ✅ Animation manager with threading support
- ✅ Transition system with easing functions
- ✅ Performance optimization (frame rate control, caching)
- ✅ Accessibility support (reduced motion)
- ✅ Complete animation library
- ✅ Testing framework

**Key Features**:
- Fast and subtle animations (100-300ms)
- Consistent timing and behavior
- Performant implementation
- Accessible with reduced motion support
- Easy to use API

**Next**: See 05-INFORMATION_ARCHITECTURE.md for content organization and hierarchy.
