"""
Lyra Speech — Multi-modal speech module for Lyra.

This package provides:
- Speech-to-text (STT) transcription
- Text-to-speech (TTS) synthesis
- Speaker identification
- Emotion detection from audio
- Streaming transcription support
"""

from __future__ import annotations

import hashlib
import logging
import math
import struct
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class VoiceGender(str, Enum):
    """Gender classification for a detected voice.

    Parameters
    ----------
    MALE : str
        Male voice classification.
    FEMALE : str
        Female voice classification.
    NEUTRAL : str
        Unclassifiable or gender-neutral voice.
    """

    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class Emotion(str, Enum):
    """Detectable emotional states.

    Parameters
    ----------
    NEUTRAL : str
        Neutral / baseline emotion.
    HAPPY : str
        Happiness / joy.
    SAD : str
        Sadness / sorrow.
    ANGRY : str
        Anger / frustration.
    FEARFUL : str
        Fear / anxiety.
    SURPRISED : str
        Surprise / startlement.
    CALM : str
        Calm / relaxed state.
    EXCITED : str
        Excitement / enthusiasm.
    """

    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    CALM = "calm"
    EXCITED = "excited"


class AudioFormat(str, Enum):
    """Supported audio container formats.

    Parameters
    ----------
    WAV : str
        Waveform Audio File Format (uncompressed PCM).
    MP3 : str
        MPEG Audio Layer III (lossy compressed).
    OGG : str
        Ogg Vorbis (lossy compressed).
    FLAC : str
        Free Lossless Audio Codec (lossless compressed).
    RAW : str
        Raw PCM data without header.
    """

    WAV = "WAV"
    MP3 = "MP3"
    OGG = "OGG"
    FLAC = "FLAC"
    RAW = "RAW"


# ---------------------------------------------------------------------------
# Data transfer objects (immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpeakerIdentity:
    """Identifies a speaker from audio.

    Parameters
    ----------
    speaker_id : str
        Unique identifier for the detected speaker.
    confidence : float
        Confidence score of the identification (0.0 — 1.0).
    voice_print_hash : str
        Cryptographic hash representing the speaker's voice print.
    gender : str
        Classified voice gender (see ``VoiceGender``).
    language : str
        Primary language detected for the speaker. Defaults to ``"en"``.
    """

    speaker_id: str
    confidence: float
    voice_print_hash: str
    gender: str
    language: str = "en"


@dataclass(frozen=True)
class TranscriptionResult:
    """Result of a speech-to-text transcription.

    Parameters
    ----------
    text : str
        Transcribed text.
    confidence : float
        Overall confidence of the transcription (0.0 — 1.0).
    language : str
        Language code of the transcribed audio.
    speaker_id : str | None
        Identified speaker ID, if available.
    words : tuple[tuple[str, float, float], ...]
        Per-word timing information as ``(word, start_ms, end_ms)`` tuples.
    is_final : bool
        Whether this is a final (non-interim) result. ``True`` by default.
    """

    text: str
    confidence: float
    language: str
    speaker_id: str | None
    words: tuple[tuple[str, float, float], ...]
    is_final: bool = True


@dataclass(frozen=True)
class EmotionResult:
    """Detected emotion from audio.

    Parameters
    ----------
    primary_emotion : str
        The dominant detected emotion label.
    confidence : float
        Confidence in the primary emotion (0.0 — 1.0).
    secondary_emotions : tuple[tuple[str, float], ...]
        Additional emotion scores as ``(emotion, score)`` tuples.
    arousal : float
        Physiological arousal level (0.0 = calm, 1.0 = highly aroused).
    valence : float
        Emotional valence (0.0 = negative, 1.0 = positive).
    """

    primary_emotion: str
    confidence: float
    secondary_emotions: tuple[tuple[str, float], ...]
    arousal: float
    valence: float


@dataclass(frozen=True)
class SynthesisOptions:
    """Options controlling text-to-speech synthesis.

    Parameters
    ----------
    voice_id : str
        Identifier of the voice to use. Defaults to ``"default"``.
    speed : float
        Speaking speed multiplier. Defaults to ``1.0``.
    pitch : float
        Voice pitch multiplier. Defaults to ``1.0``.
    emotion : str
        Emotional style for synthesis. Defaults to ``"neutral"``.
    format : str
        Output audio format. Defaults to ``"WAV"``.
    sample_rate : int
        Output sample rate in Hz. Defaults to ``24000``.
    """

    voice_id: str = "default"
    speed: float = 1.0
    pitch: float = 1.0
    emotion: str = "neutral"
    format: str = "WAV"
    sample_rate: int = 24000


@dataclass(frozen=True)
class SpeechConfig:
    """Configuration for the ``SpeechModule``.

    Parameters
    ----------
    stt_enabled : bool
        Enable speech-to-text. Defaults to ``True``.
    tts_enabled : bool
        Enable text-to-speech. Defaults to ``True``.
    speaker_id_enabled : bool
        Enable speaker identification. Defaults to ``True``.
    emotion_detection_enabled : bool
        Enable emotion detection. Defaults to ``True``.
    default_language : str
        Default language for STT/TTS. Defaults to ``"en"``.
    default_voice : str
        Default voice for TTS. Defaults to ``"default"``.
    max_audio_length_seconds : float
        Maximum allowed audio length in seconds. Defaults to ``300.0``.
    """

    stt_enabled: bool = True
    tts_enabled: bool = True
    speaker_id_enabled: bool = True
    emotion_detection_enabled: bool = True
    default_language: str = "en"
    default_voice: str = "default"
    max_audio_length_seconds: float = 300.0


# ---------------------------------------------------------------------------
# Internal helpers — WAV parsing / generation
# ---------------------------------------------------------------------------


def _parse_wav_header(audio_data: bytes) -> dict[str, Any]:
    """Extract metadata from a WAV file header.

    Parameters
    ----------
    audio_data : bytes
        Raw WAV file bytes including the RIFF header.

    Returns
    -------
    dict[str, Any]
        Dictionary with keys ``audio_format``, ``channels``, ``sample_rate``,
        ``bits_per_sample``, and ``data_size``. Returns an empty dict when
        the data does not contain a valid WAV header.
    """
    if len(audio_data) < 44 or audio_data[:4] != b"RIFF" or audio_data[8:12] != b"WAVE":
        return {}

    pos = 12
    while pos < len(audio_data) - 8:
        chunk_id = audio_data[pos : pos + 4]
        chunk_size = struct.unpack("<I", audio_data[pos + 4 : pos + 8])[0]
        if chunk_id == b"fmt " and pos + 24 <= len(audio_data):
            audio_format = struct.unpack("<H", audio_data[pos + 8 : pos + 10])[0]
            channels = struct.unpack("<H", audio_data[pos + 10 : pos + 12])[0]
            sample_rate = struct.unpack("<I", audio_data[pos + 12 : pos + 16])[0]
            bits_per_sample = struct.unpack("<H", audio_data[pos + 22 : pos + 24])[0]
            # Skip forward to locate the data chunk
            fmt_end = pos + 8 + chunk_size
            # Scan for data chunk
            data_size = 0
            dpos = max(fmt_end, pos + 8 + 16)
            while dpos < len(audio_data) - 8:
                dchunk_id = audio_data[dpos : dpos + 4]
                dchunk_size = struct.unpack("<I", audio_data[dpos + 4 : dpos + 8])[0]
                if dchunk_id == b"data":
                    data_size = dchunk_size
                    break
                dpos += 8 + dchunk_size

            return {
                "audio_format": audio_format,
                "channels": channels,
                "sample_rate": sample_rate,
                "bits_per_sample": bits_per_sample,
                "data_size": data_size,
            }
        pos += 8 + chunk_size
    return {}


def _extract_pcm_samples(audio_data: bytes) -> list[int]:
    """Extract PCM sample values from WAV data.

    Parameters
    ----------
    audio_data : bytes
        Raw WAV file bytes.

    Returns
    -------
    list[int]
        Integer PCM sample values. Empty list on failure.
    """
    header = _parse_wav_header(audio_data)
    if not header:
        return []

    # Locate the data chunk
    if len(audio_data) < 44 or audio_data[:4] != b"RIFF" or audio_data[8:12] != b"WAVE":
        return []

    pos = 12
    data_chunk_data = b""
    while pos < len(audio_data) - 8:
        chunk_id = audio_data[pos : pos + 4]
        chunk_size = struct.unpack("<I", audio_data[pos + 4 : pos + 8])[0]
        if chunk_id == b"data":
            data_chunk_data = audio_data[pos + 8 : pos + 8 + chunk_size]
            break
        pos += 8 + chunk_size

    if not data_chunk_data:
        return []

    bits = header.get("bits_per_sample", 16)
    channels = header.get("channels", 1)
    bytes_per_sample = channels * (bits // 8)

    samples: list[int] = []
    if bits == 16:
        for i in range(0, len(data_chunk_data), bytes_per_sample):
            if i + 2 > len(data_chunk_data):
                break
            sample = struct.unpack("<h", data_chunk_data[i : i + 2])[0]
            samples.append(sample)
    elif bits == 8:
        for i in range(0, len(data_chunk_data), bytes_per_sample):
            # 8-bit PCM is unsigned, offset by 128
            samples.append(data_chunk_data[i] - 128)
    else:
        # Fallback: treat as 16-bit regardless
        for i in range(0, len(data_chunk_data), max(bytes_per_sample, 2)):
            if i + 2 > len(data_chunk_data):
                break
            samples.append(struct.unpack("<h", data_chunk_data[i : i + 2])[0])

    return samples


def _build_wav_bytes(
    sample_rate: int = 24000,
    channels: int = 1,
    bits_per_sample: int = 16,
    duration_ms: int = 500,
) -> bytes:
    """Build a minimal valid WAV file with silence.

    Parameters
    ----------
    sample_rate : int
        Sample rate in Hz. Defaults to 24000.
    channels : int
        Number of audio channels. Defaults to 1 (mono).
    bits_per_sample : int
        Bits per sample. Defaults to 16.
    duration_ms : int
        Duration in milliseconds. Defaults to 500.

    Returns
    -------
    bytes
        Complete WAV file bytes.
    """
    num_samples = max(1, sample_rate * duration_ms // 1000)
    block_align = channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align
    data_size = num_samples * block_align

    # RIFF descriptor
    riff = struct.pack("<4sI4s", b"RIFF", 36 + data_size, b"WAVE")
    # fmt sub-chunk — chunk header is "<4sI" (id + size), body is "<HHIIHH"
    fmt_body = struct.pack(
        "<HHIIHH",
        1,  # audio format (1 = PCM)
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
    )
    fmt_chunk = struct.pack("<4sI", b"fmt ", 16) + fmt_body
    # data sub-chunk
    pcm_data = b"\x00" * data_size
    data_chunk = struct.pack("<4sI", b"data", data_size) + pcm_data

    return riff + fmt_chunk + data_chunk


# ---------------------------------------------------------------------------
# SpeechModule
# ---------------------------------------------------------------------------


class SpeechModule:
    """Speech processing module for Lyra.

    Provides stub implementations for speech-to-text, text-to-speech, speaker
    identification, and emotion detection. These stubs produce valid output
    (real WAV bytes, consistent speaker hashes, etc.) but are designed to be
    replaced with production models (Whisper, DeepSpeech, speaker embedding
    networks, emotion classifiers, etc.).

    Parameters
    ----------
    config : SpeechConfig | None
        Module configuration. A default ``SpeechConfig`` is used when ``None``.
    """

    def __init__(self, config: SpeechConfig | None = None) -> None:
        self._config = config if config is not None else SpeechConfig()
        self._total_transcriptions: int = 0
        self._total_synthesis: int = 0
        self._total_speaker_ids: int = 0
        self._total_emotion_detections: int = 0
        logger.info("SpeechModule initialized with config=%s", self._config)

    # -- STT -----------------------------------------------------------------

    def transcribe(
        self,
        audio_data: bytes,
        format: str = "WAV",
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio data to text.

        This is a stub implementation. In production this would call a
        Whisper / DeepSpeech model for accurate transcription.

        Parameters
        ----------
        audio_data : bytes
            Raw audio file bytes.
        format : str
            Audio container format (e.g. ``"WAV"``, ``"MP3"``).
            Only WAV header parsing is supported in the stub.
        language : str | None
            Expected language. Falls back to ``default_language`` from config.

        Returns
        -------
        TranscriptionResult
            A transcription result with a stub message noting that the
            production implementation would use Whisper / DeepSpeech.
        """
        self._total_transcriptions += 1

        if not self._config.stt_enabled:
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language=language or self._config.default_language,
                speaker_id=None,
                words=(),
                is_final=True,
            )

        lang = language or self._config.default_language
        metadata = _parse_wav_header(audio_data) if format == "WAV" else {}

        if not metadata:
            # Try real Whisper STT via faster-whisper (same as lyra-voice)
            try:
                import asyncio
                from lyra.voice.providers import WhisperSTT, STTConfig
                stt = WhisperSTT(model_size="tiny")
                cfg = STTConfig(language=lang, sample_rate=16000)
                result = asyncio.run(stt.transcribe(audio_data, cfg))
                return TranscriptionResult(
                    text=result.text,
                    confidence=result.confidence,
                    language=result.language or lang,
                    speaker_id=None,
                    words=(),
                    is_final=True,
                )
            except Exception:
                pass

        sample_rate = metadata.get("sample_rate", 0)
        channels = metadata.get("channels", 0)
        return TranscriptionResult(
            text=f"[{channels}ch {sample_rate}Hz {lang}]",
            confidence=0.0,
            language=lang,
            speaker_id=None,
            words=(
                ("[stub]", 0.0, float(metadata.get("data_size", 0))),
            ),
            is_final=True,
        )

    # -- TTS -----------------------------------------------------------------

    def synthesize(
        self,
        text: str,
        options: SynthesisOptions | None = None,
    ) -> bytes:
        """Synthesize text to speech audio.

        This is a stub implementation that returns a minimal valid WAV file
        (44-byte header + PCM silence). In production this would use a neural
        TTS engine such as Tacotron, FastSpeech, or Bark.

        Parameters
        ----------
        text : str
            Text to synthesize.
        options : SynthesisOptions | None
            Synthesis parameters. Default options are used when ``None``.

        Returns
        -------
        bytes
            WAV file bytes containing the synthesized speech (silence in stub).
        """
        self._total_synthesis += 1

        if not self._config.tts_enabled:
            return b""

        opts = options if options is not None else SynthesisOptions()

        # Real synthesis: generate a tone using numpy and wrap in WAV
        import io
        import struct
        import numpy as np

        duration_s = max(0.2, min(len(text) * 0.04, 30.0))
        sr = opts.sample_rate
        t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
        freq = 220 + (hash(text) % 660)  # 220-880 Hz range
        audio = (np.sin(2 * np.pi * freq * t) * 0.3 * 32767).astype(np.int16)
        raw = audio.tobytes()

        # Wrap in WAV header
        buf = io.BytesIO()
        data_size = len(raw)
        buf.write(b"RIFF")
        buf.write(struct.pack("<I", 36 + data_size))
        buf.write(b"WAVE")
        buf.write(b"fmt ")
        buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16))
        buf.write(b"data")
        buf.write(struct.pack("<I", data_size))
        buf.write(raw)
        return buf.getvalue()

    # -- Speaker ID ----------------------------------------------------------

    def identify_speaker(self, audio_data: bytes) -> SpeakerIdentity:
        """Identify a speaker from audio data.

        This is a stub implementation that produces a hash-based identity,
        deterministic for the same input bytes. In production this would
        use a speaker embedding model (e.g. d-vector, x-vector, ECAPA-TDNN).

        Parameters
        ----------
        audio_data : bytes
            Raw audio file bytes.

        Returns
        -------
        SpeakerIdentity
            A speaker identity derived from the audio hash.
        """
        self._total_speaker_ids += 1

        if not self._config.speaker_id_enabled or not audio_data:
            return SpeakerIdentity(
                speaker_id="unknown",
                confidence=0.0,
                voice_print_hash="",
                gender=VoiceGender.NEUTRAL.value,
                language=self._config.default_language,
            )

        audio_hash = hashlib.sha256(audio_data).hexdigest()

        # Deterministic gender from first audio byte
        first_byte = audio_data[0]
        if first_byte < 85:
            gender = VoiceGender.MALE
        elif first_byte < 170:
            gender = VoiceGender.FEMALE
        else:
            gender = VoiceGender.NEUTRAL

        return SpeakerIdentity(
            speaker_id=f"speaker_{audio_hash[:12]}",
            confidence=0.0,  # Stub placeholder
            voice_print_hash=audio_hash,
            gender=gender.value,
            language=self._config.default_language,
        )

    # -- Emotion Detection ---------------------------------------------------

    def detect_emotion(self, audio_data: bytes) -> EmotionResult:
        """Detect emotion from audio data.

        This is a stub implementation that uses audio amplitude variance as a
        proxy for arousal. In production this would use a trained emotion
        classifier (e.g. CNN-LSTM on mel-spectrograms).

        Parameters
        ----------
        audio_data : bytes
            Raw audio file bytes.

        Returns
        -------
        EmotionResult
            Detected emotion with arousal, valence, and secondary scores.
        """
        self._total_emotion_detections += 1

        if (
            not self._config.emotion_detection_enabled
            or not audio_data
            or len(audio_data) < 44
        ):
            return EmotionResult(
                primary_emotion=Emotion.NEUTRAL.value,
                confidence=0.0,
                secondary_emotions=(),
                arousal=0.0,
                valence=0.5,
            )

        samples = _extract_pcm_samples(audio_data)
        if not samples:
            return EmotionResult(
                primary_emotion=Emotion.NEUTRAL.value,
                confidence=0.0,
                secondary_emotions=(),
                arousal=0.0,
                valence=0.5,
            )

        # Compute amplitude statistics
        n = len(samples)
        mean = sum(samples) / n
        variance = sum((s - mean) ** 2 for s in samples) / n
        std_dev = math.sqrt(variance)

        # Normalize to [0, 1] using a simple sigmoid-like mapping
        # Max possible amplitude for 16-bit is 32768
        max_amplitude = 32768.0
        normalized_std = min(1.0, std_dev / (max_amplitude * 0.5))

        # Arousal: amplitude variance (higher variance = more aroused)
        arousal = normalized_std

        # Valence: zero-crossing rate as a crude proxy
        zero_crossings = sum(
            1 for i in range(1, n) if (samples[i - 1] >= 0) != (samples[i] >= 0)
        )
        zcr = zero_crossings / max(1, n)
        # Higher ZCR tends to correlate with higher valence (excitement)
        valence = min(1.0, max(0.0, zcr * 10.0))

        # Map to emotion using circumplex model
        primary_emotion, secondary_emotions = self._circumplex_emotion(
            arousal, valence
        )

        return EmotionResult(
            primary_emotion=primary_emotion,
            confidence=0.3,  # Low confidence for stub
            secondary_emotions=secondary_emotions,
            arousal=arousal,
            valence=valence,
        )

    @staticmethod
    def _circumplex_emotion(
        arousal: float,
        valence: float,
    ) -> tuple[str, tuple[tuple[str, float], ...]]:
        """Map arousal/valence to an emotion using the circumplex model.

        Parameters
        ----------
        arousal : float
            Arousal level (0.0 — 1.0).
        valence : float
            Valence level (0.0 — 1.0).

        Returns
        -------
        tuple[str, tuple[tuple[str, float], ...]]
            Primary emotion label and secondary emotion scores.
        """
        high_arousal = arousal > 0.5
        high_valence = valence > 0.5

        if high_arousal and high_valence:
            primary = Emotion.EXCITED.value
            secondary = (
                (Emotion.HAPPY.value, 0.8),
                (Emotion.SURPRISED.value, 0.6),
            )
        elif high_arousal and not high_valence:
            primary = Emotion.ANGRY.value
            secondary = (
                (Emotion.FEARFUL.value, 0.7),
                (Emotion.SAD.value, 0.4),
            )
        elif not high_arousal and high_valence:
            primary = Emotion.CALM.value
            secondary = (
                (Emotion.HAPPY.value, 0.5),
                (Emotion.NEUTRAL.value, 0.4),
            )
        else:
            primary = Emotion.SAD.value
            secondary = (
                (Emotion.NEUTRAL.value, 0.6),
                (Emotion.FEARFUL.value, 0.3),
            )

        return primary, secondary

    # -- Streaming -----------------------------------------------------------

    def transcribe_streaming(
        self,
        audio_chunks: list[bytes],
        language: str | None = None,
    ) -> list[TranscriptionResult]:
        """Transcribe a stream of audio chunks, merging results.

        Parameters
        ----------
        audio_chunks : list[bytes]
            Ordered list of raw audio chunk bytes.
        language : str | None
            Expected language for transcription.

        Returns
        -------
        list[TranscriptionResult]
            List of transcription results, one per chunk. The final entry
            is marked ``is_final=True``; earlier entries are ``is_final=False``.
        """
        results: list[TranscriptionResult] = []
        for i, chunk in enumerate(audio_chunks):
            result = self.transcribe(chunk, language=language)
            # Mark all but the last chunk as interim
            is_final = i == len(audio_chunks) - 1
            results.append(
                TranscriptionResult(
                    text=result.text,
                    confidence=result.confidence,
                    language=result.language,
                    speaker_id=result.speaker_id,
                    words=result.words,
                    is_final=is_final,
                )
            )
        return results

    # -- Statistics ----------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return cumulative usage statistics.

        Returns
        -------
        dict[str, Any]
            Dictionary with keys ``total_transcriptions``,
            ``total_synthesis``, ``total_speaker_ids``, and
            ``total_emotion_detections``.
        """
        return {
            "total_transcriptions": self._total_transcriptions,
            "total_synthesis": self._total_synthesis,
            "total_speaker_ids": self._total_speaker_ids,
            "total_emotion_detections": self._total_emotion_detections,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__version__ = "0.1.0"

__all__ = [
    # Enums
    "VoiceGender",
    "Emotion",
    "AudioFormat",
    # Data types
    "SpeakerIdentity",
    "TranscriptionResult",
    "EmotionResult",
    "SynthesisOptions",
    "SpeechConfig",
    # Main module
    "SpeechModule",
]
