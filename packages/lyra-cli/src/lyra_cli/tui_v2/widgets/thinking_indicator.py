"""Thinking time indicator."""
import time
from typing import Optional


class ThinkingIndicator:
    """Shows thinking time like Claude Code.

    Example: "✶ Roosting… (2m 53s · ↓ 2.6k tokens · thought for 28s)"
    """

    def __init__(self):
        self.thinking_start: Optional[float] = None
        self.thinking_duration: float = 0

    def start_thinking(self) -> None:
        """Mark start of thinking phase."""
        self.thinking_start = time.time()

    def end_thinking(self) -> None:
        """Mark end of thinking phase."""
        if self.thinking_start:
            self.thinking_duration = time.time() - self.thinking_start
            self.thinking_start = None

    def is_thinking(self) -> bool:
        """Check if currently thinking."""
        return self.thinking_start is not None

    def get_duration(self) -> float:
        """Get thinking duration in seconds."""
        if self.thinking_start:
            return time.time() - self.thinking_start
        return self.thinking_duration

    def format(self, total_duration: float, tokens: int, verb: str = "Roosting") -> str:
        """Format thinking indicator.

        Args:
            total_duration: Total operation duration in seconds
            tokens: Total tokens used
            verb: Verb to display (e.g., "Roosting", "Thinking")

        Returns:
            Formatted string like "✶ Roosting… (2m 53s · ↓ 2.6k tokens · thought for 28s)"
        """
        if self.thinking_duration == 0 and not self.thinking_start:
            return ""

        # Format total duration
        if total_duration < 60:
            duration_str = f"{int(total_duration)}s"
        else:
            minutes = int(total_duration // 60)
            seconds = int(total_duration % 60)
            duration_str = f"{minutes}m {seconds}s"

        # Format tokens
        tokens_str = f"↓ {tokens/1000:.1f}k tokens"

        # Format thinking time
        thinking_time = self.get_duration()
        if thinking_time < 60:
            thinking_str = f"thought for {int(thinking_time)}s"
        else:
            minutes = int(thinking_time // 60)
            seconds = int(thinking_time % 60)
            thinking_str = f"thought for {minutes}m {seconds}s"

        return f"✶ {verb}… ({duration_str} · {tokens_str} · {thinking_str})"

    def reset(self) -> None:
        """Reset thinking state."""
        self.thinking_start = None
        self.thinking_duration = 0
