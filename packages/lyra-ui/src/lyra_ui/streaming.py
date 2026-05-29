"""
Streaming - Streaming output with progressive rendering.

Features:
- Token-by-token streaming
- Cancellation support
- Pause/resume functionality
- Backpressure handling
"""

import asyncio
from collections.abc import AsyncIterator, Callable

from rich.live import Live
from rich.text import Text


class StreamHandler:
    """
    Streaming response handler.

    Features:
    - Async streaming
    - Progressive rendering
    - Cancellation support
    """

    def __init__(self):
        """Initialize stream handler."""
        self.is_cancelled = False
        self.is_paused = False
        self.buffer = []

    async def stream_response(
        self,
        stream: AsyncIterator[str],
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        """
        Stream response with progressive rendering.

        Args:
            stream: Async iterator of tokens
            on_token: Optional callback for each token

        Returns:
            Complete response text
        """
        full_response = []

        try:
            async for token in stream:
                if self.is_cancelled:
                    break

                while self.is_paused:
                    await asyncio.sleep(0.1)

                full_response.append(token)
                self.buffer.append(token)

                if on_token:
                    on_token(token)

        except asyncio.CancelledError:
            self.is_cancelled = True
            raise

        return "".join(full_response)

    def cancel(self):
        """Cancel streaming."""
        self.is_cancelled = True

    def pause(self):
        """Pause streaming."""
        self.is_paused = True

    def resume(self):
        """Resume streaming."""
        self.is_paused = False

    def get_buffer(self) -> str:
        """Get current buffer content."""
        return "".join(self.buffer)

    def clear_buffer(self):
        """Clear buffer."""
        self.buffer.clear()


class LiveStreamDisplay:
    """
    Live streaming display with Rich.

    Features:
    - Real-time rendering
    - Progressive updates
    - Smooth scrolling
    """

    def __init__(self):
        """Initialize live stream display."""
        self.text = Text()
        self.live: Live | None = None

    def start(self):
        """Start live display."""
        if self.live is None:
            self.live = Live(self.text, refresh_per_second=10)
            self.live.start()

    def stop(self):
        """Stop live display."""
        if self.live:
            self.live.stop()
            self.live = None

    def append_token(self, token: str):
        """
        Append token to display.

        Args:
            token: Token to append
        """
        self.text.append(token)
        if self.live:
            self.live.update(self.text)

    def clear(self):
        """Clear display."""
        self.text = Text()
        if self.live:
            self.live.update(self.text)


class StreamingProgress:
    """
    Streaming progress indicator.

    Features:
    - Token count
    - Elapsed time
    - Streaming rate
    """

    def __init__(self):
        """Initialize streaming progress."""
        self.token_count = 0
        self.start_time: float | None = None
        self.end_time: float | None = None

    def start(self):
        """Start tracking."""
        import time

        self.start_time = time.time()
        self.token_count = 0

    def stop(self):
        """Stop tracking."""
        import time

        self.end_time = time.time()

    def increment(self, count: int = 1):
        """
        Increment token count.

        Args:
            count: Number of tokens to add
        """
        self.token_count += count

    def get_rate(self) -> float:
        """
        Get streaming rate (tokens/second).

        Returns:
            Tokens per second
        """
        import time

        if self.start_time is None:
            return 0.0

        elapsed = (self.end_time or time.time()) - self.start_time
        if elapsed == 0:
            return 0.0

        return self.token_count / elapsed

    def get_elapsed(self) -> float:
        """
        Get elapsed time in seconds.

        Returns:
            Elapsed time
        """
        import time

        if self.start_time is None:
            return 0.0

        return (self.end_time or time.time()) - self.start_time
