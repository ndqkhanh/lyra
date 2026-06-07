"""
Voice subsystem for Lyra -- audio capture, STT, TTS, streaming pipeline,
full-duplex capabilities, and Tier B innovations.

Provides:
  1. Capture   -- microphone recording via ``sounddevice`` + VAD (``webrtcvad``)
  2. STT       -- speech-to-text through ``AnthropicSTT`` / ``DeepSeekSTT``
  3. TTS       -- text-to-speech through ``ElevenLabsTTS`` (stub) / ``OpenAITTS``
  4. Router    -- routes transcribed text to the P1 ``OrchestratorAgent``
  5. Pipeline  -- end-to-end streaming pipeline with barge-in
  6. InnerMonologueEngine -- text-before-audio at 80 ms frames (Moshi pattern)
  7. FullDuplexHandler    -- simultaneous listen+speak with turn-taking state machine
  8. BilingualRouter      -- VI+EN bilingual path with code-switching detection
  9. MetricCollector      -- latency measurement and FDB-v3 benchmark metrics

Tier B (full-duplex speech-to-speech) capabilities implement the Inner
Monologue pattern from Moshi (arXiv:2410.00037v2) with Think-before-Speak
CoT from VoxMind (arXiv:2604.15710v1) and benchmark metrics from
Full-Duplex-Bench-v3 (arXiv:2604.04847v1).  See each module's docstring
for detailed references.

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

# Tier B -- full-duplex speech-to-speech capabilities
from lyra.voice.inner_monologue import (
    ChainOfThoughtProvider,
    CoTResult,
    InnerMonologueEngine,
    InnerMonologueFrame,
    InnerMonologueError,
    MonologueLatencySnapshot,
    MonologueStage,
    TbSError,
    ThinkStrategy,
)
from lyra.voice.duplex import (
    AECProcessor,
    AudioFrame,
    BargeInEvent as DuplexBargeInEvent,
    BargeInType,
    DuplexError,
    DuplexStats,
    FullDuplexHandler,
    SemanticEndpointer,
    TurnRecord,
    TurnState,
)
from lyra.voice.bilingual import (
    BilingualError,
    BilingualRoute,
    BilingualRouter,
    BilingualStats,
    CodeSwitchError,
    HeuristicLanguageDetector,
    Language,
    LanguageClassifier,
    LanguageDetectionError,
    LanguageDetectionMethod,
    LanguageResult,
    LanguageSegment,
    VoicePersona,
)
from lyra.voice.benchmarks import (
    BenchmarkError,
    BenchmarkMetric,
    BenchmarkReport,
    ContinuousMonitor,
    FDBV3Metrics,
    MetricCollector,
    PercentileResult,
    PipelineStage,
    TauVoiceBridge,
)

__version__ = "1.1.0"

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
    # Inner Monologue (Tier B)
    "InnerMonologueEngine",
    "InnerMonologueFrame",
    "InnerMonologueError",
    "TbSError",
    "ThinkStrategy",
    "MonologueStage",
    "MonologueLatencySnapshot",
    "ChainOfThoughtProvider",
    "CoTResult",
    # Full Duplex (Tier B)
    "FullDuplexHandler",
    "TurnState",
    "TurnRecord",
    "DuplexStats",
    "BargeInType",
    "DuplexBargeInEvent",
    "DuplexError",
    "AudioFrame",
    "AECProcessor",
    "SemanticEndpointer",
    # Bilingual (Tier B)
    "Language",
    "LanguageDetectionMethod",
    "LanguageResult",
    "LanguageSegment",
    "LanguageClassifier",
    "LanguageDetectionError",
    "CodeSwitchError",
    "BilingualError",
    "BilingualRouter",
    "BilingualRoute",
    "BilingualStats",
    "VoicePersona",
    "HeuristicLanguageDetector",
    # Benchmarks (Tier B)
    "PipelineStage",
    "BenchmarkMetric",
    "PercentileResult",
    "FDBV3Metrics",
    "BenchmarkReport",
    "BenchmarkError",
    "MetricCollector",
    "ContinuousMonitor",
    "TauVoiceBridge",
]
