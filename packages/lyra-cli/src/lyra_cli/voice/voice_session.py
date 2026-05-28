"""Voice interaction session — wake word detection, conversation state,
command parsing, and response routing.

Provides a ``VoiceSession`` that manages the full voice interaction lifecycle:
- Wake word detection ("Hey Lyra")
- Push-to-talk activation
- Command parsing and routing
- Conversation state tracking
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from .sound_notifications import AgentState, SoundNotifier
from .stt_engine import STTBackend, STTResult, transcribe_audio
from .tts_engine import TTSBackend, TTSConfig, VoiceConfig, synthesize_speech

__all__ = [
    "SessionConfig",
    "WakeWordDetector",
    "WakeWordResult",
    "VoiceSession",
]

WAKE_WORDS: list[str] = ["hey lyra", "okay lyra", "lyra"]


class SessionState(Enum):
    """Voice session lifecycle states."""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass(frozen=True)
class WakeWordResult:
    """Result of wake word detection."""

    detected: bool
    confidence: float = 0.0
    phrase: str = ""
    remaining_text: str = ""

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            object.__setattr__(self, "confidence", 0.0)


@dataclass
class SessionConfig:
    """Configuration for a voice session."""

    wake_words: list[str] = field(default_factory=lambda: list(WAKE_WORDS))
    wake_word_sensitivity: float = 0.5
    inactivity_timeout: float = 30.0
    max_session_duration: float = 3600.0
    auto_stop_on_silence: bool = True
    push_to_talk: bool = False
    sound_enabled: bool = True
    language: str = "en"

    def __post_init__(self) -> None:
        self.wake_word_sensitivity = max(0.0, min(1.0, self.wake_word_sensitivity))
        self.inactivity_timeout = max(5.0, min(300.0, self.inactivity_timeout))
        self.max_session_duration = max(60.0, min(86400.0, self.max_session_duration))


class WakeWordDetector:
    """Detects wake words in transcribed text.

    Supports fuzzy matching and confidence scoring.
    """

    def __init__(self, wake_words: list[str] | None = None) -> None:
        self._wake_words = [w.lower().strip() for w in (wake_words or WAKE_WORDS)]
        self._patterns = [
            re.compile(rf"^{re.escape(w)}[\s,\.\?!]+(.+)$", re.IGNORECASE)
            for w in self._wake_words
        ]
        self._prefix_patterns = [
            re.compile(rf"^{re.escape(w)}[\s,\.\?!]*", re.IGNORECASE)
            for w in self._wake_words
        ]

    @property
    def wake_words(self) -> list[str]:
        return list(self._wake_words)

    def detect(self, text: str, sensitivity: float = 0.5) -> WakeWordResult:
        """Detect whether the given text contains a wake word.

        Parameters
        ----------
        text : str
            The transcribed text to check.
        sensitivity : float
            Detection sensitivity (0.0–1.0). Higher = more permissive.

        Returns
        -------
        WakeWordResult with detection status and remaining text.
        """
        if not text or not text.strip():
            return WakeWordResult(detected=False)

        cleaned = text.strip().lower()

        # Exact prefix match — highest confidence
        for pattern in self._patterns:
            match = pattern.match(cleaned)
            if match:
                return WakeWordResult(
                    detected=True,
                    confidence=1.0,
                    phrase=cleaned,
                    remaining_text=match.group(1).strip(),
                )

        # Substring match — lower confidence
        for wake_word in self._wake_words:
            idx = cleaned.find(wake_word)
            if idx >= 0:
                confidence = max(sensitivity, 0.6)
                remaining = cleaned[idx + len(wake_word):].strip()
                remaining = re.sub(r"^[\s,\.\?!]+", "", remaining)
                return WakeWordResult(
                    detected=True,
                    confidence=confidence,
                    phrase=cleaned,
                    remaining_text=remaining,
                )

        # Partial / fuzzy match for very short phrases
        words = cleaned.split()
        if len(words) <= 3:
            for wake_word in self._wake_words:
                wake_parts = wake_word.split()
                if len(wake_parts) == 1 and wake_parts[0] in cleaned:
                    return WakeWordResult(
                        detected=True,
                        confidence=sensitivity,
                        phrase=cleaned,
                        remaining_text=cleaned.replace(wake_parts[0], "").strip(),
                    )

        return WakeWordResult(detected=False)

    def strip_wake_word(self, text: str) -> str:
        """Remove any wake word prefix from the text."""
        for pattern in self._prefix_patterns:
            cleaned = pattern.sub("", text.strip()).strip()
            if cleaned:
                return cleaned
        return text.strip()


class VoiceSession:
    """Manages a voice interaction session.

    Handles wake word detection, transcription, TTS response,
    and conversation lifecycle events.
    """

    def __init__(
        self,
        config: SessionConfig | None = None,
        stt_backend: STTBackend | None = None,
        tts_backend: TTSBackend | None = None,
        sound_notifier: SoundNotifier | None = None,
        command_handler: Callable[[str], str] | None = None,
    ) -> None:
        self._config = config or SessionConfig()
        self._stt = stt_backend
        self._tts = tts_backend
        self._notifier = sound_notifier or SoundNotifier()
        self._command_handler = command_handler
        self._wake_detector = WakeWordDetector(self._config.wake_words)
        self._state = SessionState.IDLE
        self._conversation_history: list[dict[str, Any]] = []
        self._last_activity: datetime = datetime.now()
        self._session_start: datetime | None = None
        self._lock = threading.Lock()
        self._listeners: dict[str, list[Callable[..., None]]] = {}

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def config(self) -> SessionConfig:
        return self._config

    @property
    def conversation_history(self) -> list[dict[str, Any]]:
        return list(self._conversation_history)

    @property
    def session_duration(self) -> float:
        if self._session_start is None:
            return 0.0
        return (datetime.now() - self._session_start).total_seconds()

    @property
    def is_active(self) -> bool:
        return self._state not in (SessionState.IDLE, SessionState.STOPPED)

    @property
    def is_idle(self) -> bool:
        return self._state == SessionState.IDLE

    def on(self, event: str, callback: Callable[..., None]) -> None:
        """Register an event listener.

        Supported events: ``state_change``, ``wake_word``, ``command``,
        ``response``, ``error``.
        """
        self._listeners.setdefault(event, []).append(callback)

    def _emit(self, event: str, **kwargs: Any) -> None:
        for cb in self._listeners.get(event, []):
            try:
                cb(**kwargs)
            except Exception:
                pass

    def start(self) -> None:
        """Start the voice session."""
        if self._state == SessionState.STOPPED:
            raise RuntimeError("Session is stopped and cannot be restarted")
        self._state = SessionState.IDLE
        self._session_start = datetime.now()
        self._last_activity = datetime.now()
        self._conversation_history = []
        if self._config.sound_enabled:
            self._notifier.notify(AgentState.AGENT_READY)
        self._emit("state_change", state=self._state)

    def stop(self) -> None:
        """Stop the voice session."""
        self._state = SessionState.STOPPED
        if self._config.sound_enabled:
            self._notifier.notify(AgentState.TASK_COMPLETE)
        self._emit("state_change", state=self._state)

    def pause(self) -> None:
        """Pause listening without ending the session."""
        self._state = SessionState.PAUSED
        self._emit("state_change", state=self._state)

    def resume(self) -> None:
        """Resume listening after a pause."""
        if self._state == SessionState.PAUSED:
            self._state = SessionState.IDLE
            self._last_activity = datetime.now()
            self._emit("state_change", state=self._state)

    def check_timeout(self) -> bool:
        """Check if the session has timed out due to inactivity.

        Returns True if the session timed out.
        """
        if not self._config.auto_stop_on_silence:
            return False
        if self._state in (SessionState.PAUSED, SessionState.STOPPED):
            return False
        elapsed = (datetime.now() - self._last_activity).total_seconds()
        if elapsed > self._config.inactivity_timeout:
            self._state = SessionState.STOPPED
            self._emit("state_change", state=self._state)
            return True
        return False

    def check_max_duration(self) -> bool:
        """Check if the session has exceeded the max duration.

        Returns True if max duration exceeded.
        """
        if self._session_start is None:
            return False
        if self.session_duration > self._config.max_session_duration:
            self._state = SessionState.STOPPED
            self._emit("state_change", state=self._state)
            return True
        return False

    def process_text(self, text: str) -> str:
        """Process transcribed text through the voice pipeline.

        Handles wake word detection, command routing, and TTS response.

        Returns the spoken response text.
        """
        if not text or not text.strip():
            return ""

        self._last_activity = datetime.now()

        # Wake word detection
        result = self._wake_detector.detect(
            text, sensitivity=self._config.wake_word_sensitivity,
        )
        if result.detected:
            self._emit("wake_word", result=result)
            if self._config.sound_enabled:
                self._notifier.notify(AgentState.AGENT_READY)
            command_text = result.remaining_text or text
        else:
            if self._config.push_to_talk:
                return ""
            command_text = text

        self._state = SessionState.PROCESSING
        self._emit("state_change", state=self._state)

        if self._config.sound_enabled:
            self._notifier.notify(AgentState.AGENT_THINKING)

        # Route command
        response = self._route_command(command_text)

        self._conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "input": text,
            "command": command_text,
            "response": response,
            "wake_word_detected": result.detected,
        })

        # Speak response
        if response.strip():
            self._state = SessionState.SPEAKING
            self._emit("response", text=response)
            self._speak(response)

        self._state = SessionState.IDLE
        self._emit("state_change", state=self._state)
        if self._config.sound_enabled:
            self._notifier.notify(AgentState.TASK_COMPLETE)

        return response

    def _route_command(self, text: str) -> str:
        """Route a command to the registered handler."""
        if self._command_handler:
            return self._command_handler(text)
        return self._default_command_handler(text)

    @staticmethod
    def _default_command_handler(text: str) -> str:
        """Default command handler that echoes the input."""
        if not text.strip():
            return ""
        return f"I heard: {text}"

    def _speak(self, text: str) -> None:
        """Synthesize and route response text to TTS.

        This is a stub that can be overridden or connected to a TTS engine.
        """
        if self._tts is not None and text.strip():
            try:
                synthesize_speech(
                    text,
                    backend=self._tts,
                    voice=VoiceConfig(),
                )
            except Exception:
                pass

    def get_conversation_context(self, max_turns: int = 5) -> list[dict[str, Any]]:
        """Return the last N turns of conversation history."""
        return self._conversation_history[-max_turns:]
