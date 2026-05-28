"""Speech-to-Text engine with multiple backend support and confidence scoring.

Backends:
1. WhisperBackend — local OpenAI Whisper (``openai-whisper`` or ``faster-whisper``)
2. SpeechRecognitionBackend — Google Speech Recognition via ``speech-recognition``

Audio format detection is automatic via file extension.
Confidence scores are normalised to 0.0–1.0.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = [
    "STTResult",
    "STTBackend",
    "WhisperBackend",
    "SpeechRecognitionBackend",
    "STTError",
    "transcribe_audio",
]

SUPPORTED_FORMATS: frozenset[str] = frozenset({
    ".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".aiff", ".aac",
})


class STTError(Exception):
    """Raised when speech-to-text transcription fails."""


@dataclass(frozen=True)
class STTResult:
    """Result of a speech-to-text transcription."""

    text: str
    confidence: float = 0.0
    language: str = "en"
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            object.__setattr__(self, "confidence", 0.0)


@runtime_checkable
class STTBackend(Protocol):
    """Interface every STT backend must satisfy."""

    name: str

    def transcribe(self, *, audio_path: Path) -> STTResult: ...


class WhisperBackend:
    """Local transcription via ``openai-whisper`` or ``faster-whisper``.

    Falls back gracefully if neither package is installed.
    Attempts ``faster-whisper`` first (CPU-optimised), then
    ``openai-whisper``.
    """

    def __init__(self, model: str = "base", language: str | None = None) -> None:
        self.name = "whisper"
        self._model = model
        self._language = language
        self._use_faster: bool = False
        self._available = self._try_import()

    def _try_import(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
            self._use_faster = True
            return True
        except ImportError:
            pass
        try:
            import whisper  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def available(self) -> bool:
        return self._available

    def _transcribe_faster(self, audio_path: Path) -> STTResult:
        from faster_whisper import WhisperModel

        model = WhisperModel(self._model, device="cpu", compute_type="int8")
        segments, info = model.transcribe(
            str(audio_path),
            language=self._language,
        )
        text = " ".join(seg.text for seg in segments)
        confidence = info.average_logprob if info else 0.0
        return STTResult(
            text=text.strip(),
            confidence=max(0.0, min(1.0, (confidence + 2.0) / 4.0)),
            language=info.language if info else "en",
        )

    def _transcribe_whisper(self, audio_path: Path) -> STTResult:
        import whisper

        model = whisper.load_model(self._model)
        result = model.transcribe(
            str(audio_path),
            language=self._language,
        )
        segments = result.get("segments", [])
        avg_confidence = (
            sum(s.get("confidence", 0.0) for s in segments) / len(segments)
            if segments else 0.0
        )
        return STTResult(
            text=result.get("text", "").strip(),
            confidence=avg_confidence,
            language=result.get("language", "en"),
            duration_seconds=result.get("duration", 0.0),
        )

    def transcribe(self, *, audio_path: Path) -> STTResult:
        if not self._available:
            raise STTError("Whisper is not installed")
        if self._use_faster:
            return self._transcribe_faster(audio_path)
        return self._transcribe_whisper(audio_path)


class SpeechRecognitionBackend:
    """Cloud-based transcription via ``speech-recognition`` library.

    Uses Google Speech Recognition by default.
    Falls back gracefully if ``speech-recognition`` is not installed.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.name = "speech-recognition"
        self._api_key = api_key
        self._available = self._try_import()

    @staticmethod
    def _try_import() -> bool:
        try:
            import speech_recognition  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def available(self) -> bool:
        return self._available

    def transcribe(self, *, audio_path: Path) -> STTResult:
        if not self._available:
            raise STTError("speech-recognition is not installed")
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        audio_format = audio_path.suffix.lower().lstrip(".")

        audio_file: sr.AudioFile
        with sr.AudioFile(str(audio_path)) as audio_file:
            audio_data = recognizer.record(audio_file)

        try:
            if self._api_key:
                result = recognizer.recognize_google(audio_data, key=self._api_key, show_all=True)
            else:
                result = recognizer.recognize_google(audio_data, show_all=True)
        except sr.UnknownValueError:
            return STTResult(text="", confidence=0.0)
        except sr.RequestError as exc:
            raise STTError(f"Speech recognition API error: {exc}") from exc

        if isinstance(result, dict) and "alternative" in result:
            alt = result["alternative"]
            if alt:
                text = alt[0].get("transcript", "")
                confidence = alt[0].get("confidence", 0.0)
                return STTResult(text=text, confidence=confidence)

        if isinstance(result, str):
            return STTResult(text=result, confidence=0.5)

        return STTResult(text=str(result), confidence=0.0)
        _ = audio_format  # kept for potential future use


def detect_audio_format(path: Path) -> str | None:
    """Detect audio format from file extension.

    Returns None if the format is unsupported.
    """
    ext = path.suffix.lower()
    return ext if ext in SUPPORTED_FORMATS else None


def transcribe_audio(
    path: Path | str,
    *,
    backend: STTBackend | None = None,
    language: str | None = None,
) -> STTResult:
    """Transcribe an audio file to text.

    Parameters
    ----------
    path : Path | str
        Path to the audio file.
    backend : STTBackend | None
        STT backend to use. Auto-detected if not provided.
    language : str | None
        Optional language hint (e.g. ``"en"``, ``"vi"``).

    Returns
    -------
    STTResult with transcribed text and confidence.
    """
    p = Path(path)
    fmt = detect_audio_format(p)
    if fmt is None:
        raise STTError(f"Unsupported audio format: {p.suffix}")

    engine = backend or _auto_detect_backend(language)
    return engine.transcribe(audio_path=p)


def _auto_detect_backend(language: str | None = None) -> STTBackend:
    """Auto-detect the best available STT backend."""
    whisper = WhisperBackend(language=language)
    if whisper.available:
        return whisper
    srb = SpeechRecognitionBackend()
    if srb.available:
        return srb
    raise STTError("No STT backend available (install whisper or speech-recognition)")
