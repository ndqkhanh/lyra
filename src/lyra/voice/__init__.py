"""
Voice subsystem for Lyra -- audio capture, STT, TTS, and streaming pipeline.

Provides a full-duplex voice interface built on the S1 provider abstraction:
  1. Capture  -- microphone recording via ``sounddevice`` + VAD (``webrtcvad``)
  2. STT      -- speech-to-text through ``AnthropicSTT`` / ``DeepSeekSTT``
  3. TTS      -- text-to-speech through ``ElevenLabsTTS`` (stub) / ``OpenAITTS``
  4. Router   -- routes transcribed text to the P1 ``OrchestratorAgent``
  5. Pipeline -- end-to-end streaming pipeline with barge-in and latency tracking

Typical usage::

    from lyra.voice.pipeline import VoicePipeline
    from lyra.voice.capture import AudioCapture
    from lyra.voice.stt import OpenAISTT
    from lyra.voice.tts import OpenAITTS
    from lyra.voice.router import VoiceAgentRouter

    cap = AudioCapture()
    stt = OpenAISTT(provider=openai_adapter)
    tts = OpenAITTS(provider=openai_adapter)
    router = VoiceAgentRouter(orchestrator.run)

    pipeline = VoicePipeline(capture=cap, stt=stt, tts=tts, router=router)
    await pipeline.run()
"""

from lyra.voice.capture import (
    AudioCapture,
    AudioCaptureError,
    AudioChunk,
    AudioChunkWithVad,
    VADError,
)
from lyra.voice.pipeline import (
    PipelineStats,
    VoicePipeline,
    BargeInEvent,
    PipelineError,
)
from lyra.voice.router import VoiceAgentRouter, RouterError
from lyra.voice.stt import (
    STTProvider,
    AnthropicSTT,
    DeepSeekSTT,
    OpenAISTT,
    STTError,
)
from lyra.voice.tts import (
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
