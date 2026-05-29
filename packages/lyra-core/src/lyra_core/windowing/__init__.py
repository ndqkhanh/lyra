"""
Context Windowing System

Manages sliding context windows for efficient memory usage.

Features:
- Sliding window management
- Window overlap control
- Priority-based retention
- Automatic window rotation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import deque
import time


@dataclass
class ContextWindow:
    """A window of context with metadata"""
    id: str
    content: List[Any]
    start_index: int
    end_index: int
    priority: float = 1.0
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)

    def size(self) -> int:
        """Get window size"""
        return len(self.content)

    def touch(self):
        """Update access time"""
        self.accessed_at = time.time()


class SlidingWindowManager:
    """
    Sliding window manager for context

    Manages multiple overlapping windows with automatic rotation.
    """

    def __init__(
        self,
        window_size: int = 1000,
        overlap: int = 100,
        max_windows: int = 10
    ):
        self.window_size = window_size
        self.overlap = overlap
        self.max_windows = max_windows
        self.windows: deque[ContextWindow] = deque(maxlen=max_windows)
        self.current_index = 0
        self._window_counter = 0

    def add_content(self, content: Any, priority: float = 1.0):
        """Add content to current window"""
        if not self.windows or self._should_create_new_window():
            self._create_new_window()

        current_window = self.windows[-1]
        current_window.content.append(content)
        current_window.end_index = self.current_index
        self.current_index += 1

    def _should_create_new_window(self) -> bool:
        """Check if we should create a new window"""
        if not self.windows:
            return True

        current_window = self.windows[-1]
        return current_window.size() >= self.window_size

    def _create_new_window(self):
        """Create a new window"""
        start_index = self.current_index

        # Calculate overlap with previous window
        if self.windows:
            prev_window = self.windows[-1]
            overlap_content = prev_window.content[-self.overlap:]
            start_index = prev_window.end_index - self.overlap
        else:
            overlap_content = []

        window = ContextWindow(
            id=f"window_{self._window_counter}",
            content=overlap_content.copy(),
            start_index=start_index,
            end_index=start_index
        )

        self.windows.append(window)
        self._window_counter += 1

    def get_window(self, window_id: str) -> Optional[ContextWindow]:
        """Get window by ID"""
        for window in self.windows:
            if window.id == window_id:
                window.touch()
                return window
        return None

    def get_active_window(self) -> Optional[ContextWindow]:
        """Get currently active window"""
        if self.windows:
            return self.windows[-1]
        return None

    def get_all_content(self) -> List[Any]:
        """Get all content from all windows"""
        all_content = []
        for window in self.windows:
            all_content.extend(window.content)
        return all_content

    def get_recent_content(self, n: int) -> List[Any]:
        """Get N most recent items"""
        all_content = self.get_all_content()
        return all_content[-n:] if len(all_content) >= n else all_content

    def clear_old_windows(self, keep_recent: int = 3):
        """Clear old windows, keeping only recent ones"""
        while len(self.windows) > keep_recent:
            self.windows.popleft()

    def get_stats(self) -> Dict:
        """Get windowing statistics"""
        if not self.windows:
            return {
                'total_windows': 0,
                'total_items': 0,
                'avg_window_size': 0.0
            }

        total_items = sum(w.size() for w in self.windows)
        avg_size = total_items / len(self.windows)

        return {
            'total_windows': len(self.windows),
            'max_windows': self.max_windows,
            'window_size': self.window_size,
            'overlap': self.overlap,
            'total_items': total_items,
            'avg_window_size': avg_size,
            'current_index': self.current_index
        }


class PriorityWindowManager:
    """
    Priority-based window manager

    Retains high-priority windows longer.
    """

    def __init__(self, max_windows: int = 10):
        self.max_windows = max_windows
        self.windows: List[ContextWindow] = []
        self._window_counter = 0

    def add_window(
        self,
        content: List[Any],
        priority: float = 1.0,
        metadata: Optional[Dict] = None
    ) -> ContextWindow:
        """Add a new window"""
        window = ContextWindow(
            id=f"window_{self._window_counter}",
            content=content,
            start_index=0,
            end_index=len(content),
            priority=priority,
            metadata=metadata or {}
        )

        self.windows.append(window)
        self._window_counter += 1

        # Evict low-priority windows if needed
        if len(self.windows) > self.max_windows:
            self._evict_lowest_priority()

        return window

    def _evict_lowest_priority(self):
        """Evict lowest priority window"""
        if not self.windows:
            return

        # Sort by priority (ascending)
        self.windows.sort(key=lambda w: w.priority)
        # Remove lowest priority
        self.windows.pop(0)

    def get_window(self, window_id: str) -> Optional[ContextWindow]:
        """Get window by ID"""
        for window in self.windows:
            if window.id == window_id:
                window.touch()
                return window
        return None

    def get_high_priority_windows(self, threshold: float = 0.8) -> List[ContextWindow]:
        """Get windows above priority threshold"""
        return [w for w in self.windows if w.priority >= threshold]

    def update_priority(self, window_id: str, priority: float):
        """Update window priority"""
        for window in self.windows:
            if window.id == window_id:
                window.priority = priority
                break

    def get_stats(self) -> Dict:
        """Get statistics"""
        if not self.windows:
            return {
                'total_windows': 0,
                'avg_priority': 0.0
            }

        avg_priority = sum(w.priority for w in self.windows) / len(self.windows)

        return {
            'total_windows': len(self.windows),
            'max_windows': self.max_windows,
            'avg_priority': avg_priority,
            'high_priority_count': len(self.get_high_priority_windows())
        }


class AdaptiveWindowManager:
    """
    Adaptive window manager

    Automatically adjusts window size based on content.
    """

    def __init__(
        self,
        min_window_size: int = 500,
        max_window_size: int = 2000,
        target_utilization: float = 0.8
    ):
        self.min_window_size = min_window_size
        self.max_window_size = max_window_size
        self.target_utilization = target_utilization
        self.current_window_size = min_window_size
        self.windows: List[ContextWindow] = []
        self._window_counter = 0

    def add_content(self, content: List[Any]) -> ContextWindow:
        """Add content and create window"""
        window = ContextWindow(
            id=f"window_{self._window_counter}",
            content=content,
            start_index=0,
            end_index=len(content)
        )

        self.windows.append(window)
        self._window_counter += 1

        # Adjust window size based on utilization
        self._adjust_window_size(len(content))

        return window

    def _adjust_window_size(self, content_size: int):
        """Adjust window size based on content"""
        utilization = content_size / self.current_window_size

        if utilization > self.target_utilization:
            # Increase window size
            new_size = min(
                self.max_window_size,
                int(self.current_window_size * 1.2)
            )
            self.current_window_size = new_size
        elif utilization < self.target_utilization * 0.5:
            # Decrease window size
            new_size = max(
                self.min_window_size,
                int(self.current_window_size * 0.8)
            )
            self.current_window_size = new_size

    def get_recommended_size(self) -> int:
        """Get recommended window size"""
        return self.current_window_size

    def get_stats(self) -> Dict:
        """Get statistics"""
        if not self.windows:
            return {
                'total_windows': 0,
                'current_window_size': self.current_window_size
            }

        avg_content_size = sum(w.size() for w in self.windows) / len(self.windows)
        utilization = avg_content_size / self.current_window_size

        return {
            'total_windows': len(self.windows),
            'current_window_size': self.current_window_size,
            'min_window_size': self.min_window_size,
            'max_window_size': self.max_window_size,
            'avg_content_size': avg_content_size,
            'utilization': utilization
        }
