"""Interrupt handling — barge-in, pause, resume, and undo for agent sessions."""

from dataclasses import dataclass, field
from enum import Enum
import time


class InterruptSignal(str, Enum):
    PAUSE = "pause"
    RESUME = "resume"
    ABORT = "abort"
    ROLLBACK = "rollback"
    BARGE_IN = "barge_in"  # Voice-mode interrupt


@dataclass
class InterruptHandler:
    """Handles mid-run interrupts: pause, resume, abort, rollback.

    Supports both CLI (Ctrl+C) and voice (barge-in) interrupt sources.
    """

    max_pause_seconds: float = 300  # Auto-resume after 5 min paused
    _paused_at: float | None = None
    _signal: InterruptSignal | None = None
    _checkpoints: dict[str, dict] = field(default_factory=dict)

    @property
    def is_paused(self) -> bool:
        return self._signal == InterruptSignal.PAUSE

    @property
    def current_signal(self) -> InterruptSignal | None:
        return self._signal

    def send(self, signal: InterruptSignal):
        """Send an interrupt signal to the agent."""
        self._signal = signal
        if signal == InterruptSignal.PAUSE:
            self._paused_at = time.time()

    def clear(self):
        """Clear the current interrupt signal."""
        self._signal = None
        self._paused_at = None

    def should_auto_resume(self) -> bool:
        """Check if a paused session should auto-resume."""
        if not self.is_paused or self._paused_at is None:
            return False
        return (time.time() - self._paused_at) > self.max_pause_seconds

    def save_checkpoint(self, name: str, state: dict):
        """Save a checkpoint for potential rollback."""
        self._checkpoints[name] = {
            "state": state,
            "timestamp": time.time(),
        }

    def restore_checkpoint(self, name: str) -> dict | None:
        """Restore state from a named checkpoint."""
        cp = self._checkpoints.get(name)
        return cp["state"] if cp else None

    def list_checkpoints(self) -> list[str]:
        return sorted(self._checkpoints.keys())

    def handle_barge_in(self, transcript: str) -> InterruptSignal | None:
        """Detect barge-in intent from voice transcript."""
        barge_triggers = ["stop", "wait", "pause", "hold on", "cancel", "never mind"]
        transcript_lower = transcript.lower().strip()
        if any(t in transcript_lower for t in barge_triggers):
            return InterruptSignal.BARGE_IN
        return None
