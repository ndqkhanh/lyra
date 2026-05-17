"""Real-time progress spinners like Claude Code."""
from typing import Optional
import time


SPINNER_FRAMES = ["⏺", "✶", "✻", "✳", "✽", "✶"]

SPINNER_VERBS = [
    "Thinking", "Analyzing", "Processing", "Computing",
    "Researching", "Implementing", "Verifying", "Optimizing",
    "Blanching", "Roosting", "Galloping", "Puttering", "Pollinating"
]


class ProgressSpinner:
    """Animated spinner with verb rotation like Claude Code.

    Example output:
    ⏺ Thinking… (2s · ↓ 1.2k tokens)
    ✶ Analyzing… (5s · ↓ 3.4k tokens)
    ✻ Processing… (10s · ↓ 8.9k tokens)
    """

    def __init__(self):
        self.frame_index = 0
        self.verb_index = 0
        self.start_time: Optional[float] = None
        self.tokens_used = 0

    def start(self) -> None:
        """Start the spinner timer."""
        self.start_time = time.time()
        self.frame_index = 0
        self.verb_index = 0

    def next_frame(self, tokens: int = 0) -> str:
        """Get next spinner frame with verb and metrics.

        Args:
            tokens: Total tokens used so far

        Returns:
            Formatted spinner string like "⏺ Thinking… (2s · ↓ 1.2k tokens)"
        """
        frame = SPINNER_FRAMES[self.frame_index % len(SPINNER_FRAMES)]
        verb = SPINNER_VERBS[self.verb_index % len(SPINNER_VERBS)]
        self.frame_index += 1

        # Rotate verb every 6 frames (one full spinner cycle)
        if self.frame_index % len(SPINNER_FRAMES) == 0:
            self.verb_index += 1

        # Build status string
        status = f"{frame} {verb}…"

        # Add metrics if available
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed < 60:
                duration_str = f"{int(elapsed)}s"
            else:
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                duration_str = f"{minutes}m {seconds}s"

            if tokens > 0:
                tokens_str = f"↓ {tokens/1000:.1f}k tokens"
                status += f" ({duration_str} · {tokens_str})"
            else:
                status += f" ({duration_str})"

        return status

    def stop(self) -> None:
        """Stop the spinner."""
        self.start_time = None
