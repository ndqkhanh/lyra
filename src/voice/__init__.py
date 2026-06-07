"""
Voice subsystem for Lyra -- audio capture, STT, TTS, and streaming pipeline.

Provides a full-duplex voice interface built on the S1 provider abstraction:
  1. Capture  -- microphone recording via ``sounddevice`` + VAD (``webrtcvad``)
  2. STT      -- speech-to-text through ``AnthropicSTT`` / ``DeepSeekSTT``
  3. TTS      -- text-to-speech through ``ElevenLabsTTS`` (stub) / ``OpenAITTS``
  4. Router   -- routes transcribed text to the P1 ``OrchestratorAgent``
  5. Pipeline -- end-to-end streaming pipeline with barge-in and latency tracking

Typical usage::

    from src.voice.pipeline import VoicePipeline
    from src.voice.capture import AudioCapture
    from src.voice.stt import OpenAISTT
    from src.voice.tts import OpenAITTS
    from src.voice.router import VoiceAgentRouter

    cap = AudioCapture()
    stt = OpenAISTT(provider=openai_adapter)
    tts = OpenAITTS(provider=openai_adapter)
    router = VoiceAgentRouter(orchestrator.run)

    pipeline = VoicePipeline(capture=cap, stt=stt, tts=tts, router=router)
    await pipeline.run()
"""

from src.voice.capture import (
    AudioCapture,
    AudioCaptureError,
    AudioChunk,
    AudioChunkWithVad,
    VADError,
)
from src.voice.pipeline import (
    PipelineStats,
    VoicePipeline,
    BargeInEvent,
    PipelineError,
)
from src.voice.router import VoiceAgentRouter, RouterError
from src.voice.stt import (
    STTProvider,
    AnthropicSTT,
    DeepSeekSTT,
    OpenAISTT,
    STTError,
)
from src.voice.tts import (
    TTSProvider,
    ElevenLabsTTS,
    OpenAITTS,
    TTSProviderLocal,
    TTSError,
)

__version__ = "1.0.0"

__all__ = [
    # Capture
    "AudioCapture",
    "AudioCaptureError",
    "AudioChunk",
    "AudioChunkWithVad",
    "VADError",
    # STT
    "STTProvider",
    "AnthropicSTT",
    "DeepSeekSTT",
    "OpenAISTT",
    "STTError",
    # TTS
    "TTSProvider",
    "TTSProviderLocal",
    "ElevenLabsTTS",
    "OpenAITTS",
    "TTSError",
    # Router
    "VoiceAgentRouter",
    "RouterError",
    # Pipeline
    "VoicePipeline",
    "PipelineStats",
    "BargeInEvent",
    "PipelineError",
]
