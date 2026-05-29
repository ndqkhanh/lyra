"""
Token-level streaming with backpressure and cognitive-latency awareness.

Implements an async token stream that supports:
  - Token-by-token read / write
  - Backpressure via buffer-threshold pausing
  - Latency classification per the Cognitive Latency Stack
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum

from lyra_streaming.models import StreamState, StreamToken

logger = logging.getLogger(__name__)


class CognitiveLatencyTier(Enum):
    """Cognitive Latency Stack tiers for UX responsiveness.

    * perception:   0 - 400 ms   (instantaneous)
    * comprehension: 400 ms - 2 s (still feels interactive)
    * decision:      2 - 10 s    (user expects a pause)
    * background:    10 - 60 s+  (acceptable for batch work)
    """

    PERCEPTION = "perception"
    COMPREHENSION = "comprehension"
    DECISION = "decision"
    BACKGROUND = "background"

    @classmethod
    def classify(cls, duration_ms: float) -> CognitiveLatencyTier:
        if duration_ms <= 400:
            return cls.PERCEPTION
        if duration_ms <= 2000:
            return cls.COMPREHENSION
        if duration_ms <= 10000:
            return cls.DECISION
        return cls.BACKGROUND


class TokenStream:
    """An async token stream for a single run.

    Producers call ``write()`` to push tokens; consumers call ``read()``
    to receive them.  When the buffer exceeds ``backpressure_threshold``
    the stream signals backpressure via an `asyncio.Event`.
    """

    def __init__(
        self,
        run_id: str,
        backpressure_threshold: int = 100,
    ) -> None:
        self.run_id = run_id
        self._state = StreamState(run_id=run_id)
        self._queue: asyncio.Queue[StreamToken | None] = asyncio.Queue()
        self._backpressure_threshold = backpressure_threshold
        self._backpressure_event = asyncio.Event()
        self._backpressure_event.set()  # Start unblocked
        self._started_at = datetime.now(timezone.utc)

    async def write(self, token: StreamToken) -> None:
        """Write a token to the stream, blocking if backpressure is active.

        Args:
            token: The `StreamToken` to emit.
        """
        if not self._state.is_active:
            logger.warning("Token write on inactive stream %s", self.run_id)
            return

        await self._backpressure_event.wait()

        await self._queue.put(token)
        self._state.buffer.append(token)
        self._state.total_tokens += 1

        # Signal backpressure when buffer exceeds threshold
        if self._queue.qsize() >= self._backpressure_threshold:
            self._backpressure_event.clear()
            logger.debug(
                "Backpressure applied on stream %s (buffer=%d)", self.run_id, self._queue.qsize()
            )

    async def read(self) -> StreamToken | None:
        """Await and return the next token, or ``None`` if the stream is finished.

        Returns:
            The next `StreamToken` or ``None`` for end-of-stream.
        """
        if not self._state.is_active and self._queue.empty():
            return None

        token = await self._queue.get()

        # Release backpressure when buffer drains below half threshold
        if self._queue.qsize() < self._backpressure_threshold // 2:
            if not self._backpressure_event.is_set():
                self._backpressure_event.set()
                logger.debug(
                    "Backpressure released on stream %s (buffer=%d)",
                    self.run_id,
                    self._queue.qsize(),
                )

        return token

    async def flush(self) -> None:
        """Signal end-of-stream by placing a sentinel in the queue."""
        if self._state.is_active:
            self._state.is_active = False
            await self._queue.put(None)
        logger.debug("Stream %s flushed (total tokens=%d)", self.run_id, self._state.total_tokens)

    def apply_backpressure(self, threshold: int) -> None:
        """Dynamically adjust the backpressure threshold.

        Args:
            threshold: New max buffer size before backpressure activates.
        """
        self._backpressure_threshold = max(1, threshold)
        if self._queue.qsize() >= self._backpressure_threshold:
            self._backpressure_event.clear()
        else:
            self._backpressure_event.set()
        logger.debug(
            "Stream %s backpressure threshold set to %d", self.run_id, self._backpressure_threshold
        )

    @property
    def is_active(self) -> bool:
        """Return ``True`` if the stream is still accepting writes."""
        return self._state.is_active

    @property
    def total_tokens(self) -> int:
        """Return the total number of tokens written to the stream."""
        return self._state.total_tokens

    def get_buffer_size(self) -> int:
        """Return the current number of un-consumed tokens in the buffer."""
        return self._queue.qsize()

    def get_latency_tier(self) -> CognitiveLatencyTier:
        """Classify the current stream duration using the cognitive latency stack."""
        elapsed_ms = (datetime.now(timezone.utc) - self._started_at).total_seconds() * 1000
        return CognitiveLatencyTier.classify(elapsed_ms)


class StreamController:
    """Manages multiple `TokenStream` instances keyed by ``run_id``.

    Usage::

        controller = StreamController()
        stream = controller.create_stream("run-1")
        await stream.write(StreamToken(content="Hello", position=0))
        ...
        controller.close_stream("run-1")
    """

    def __init__(self) -> None:
        self._streams: dict[str, TokenStream] = {}

    def create_stream(self, run_id: str, backpressure_threshold: int = 100) -> TokenStream:
        """Create and register a new `TokenStream` for *run_id*.

        Args:
            run_id: Unique run identifier.
            backpressure_threshold: Initial backpressure buffer limit.

        Returns:
            A new `TokenStream`.

        Raises:
            ValueError: If a stream for *run_id* already exists.
        """
        if run_id in self._streams:
            raise ValueError(f"Stream for run_id {run_id!r} already exists")

        stream = TokenStream(run_id=run_id, backpressure_threshold=backpressure_threshold)
        self._streams[run_id] = stream
        logger.info("Stream created for run %s", run_id)
        return stream

    def get_stream(self, run_id: str) -> TokenStream | None:
        """Return the stream for *run_id* or ``None``."""
        return self._streams.get(run_id)

    async def close_stream(self, run_id: str) -> None:
        """Flush and remove the stream for *run_id*.

        Args:
            run_id: The stream to close.

        Raises:
            KeyError: If no stream exists for *run_id*.
        """
        stream = self._streams.get(run_id)
        if stream is None:
            raise KeyError(f"No stream for run_id {run_id!r}")

        await stream.flush()
        del self._streams[run_id]
        logger.info("Stream closed for run %s", run_id)

    def get_active_streams(self) -> dict[str, TokenStream]:
        """Return a snapshot of all currently active streams."""
        return dict(self._streams)
