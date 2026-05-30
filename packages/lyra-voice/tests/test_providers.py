"""Tests for voice provider abstractions."""
import pytest

from lyra_voice.providers import (
    EnergyVAD,
    GapBasedTurn,
    STTConfig,
    STTProviderKind,
    TTSConfig,
    TTSProviderKind,
    TurnConfig,
    VADConfig,
    VADProviderKind,
    VADSegment,
    VoicePipelineConfig,
    VoiceProviderRegistry,
)


# ---------------------------------------------------------------------------
# EnergyVAD
# ---------------------------------------------------------------------------


class TestEnergyVAD:
    @pytest.mark.asyncio
    async def test_silence_detected(self):
        vad = EnergyVAD()
        silence = b"\x00" * 320  # 10ms of silence at 16kHz 16-bit
        result = await vad.detect(silence)
        assert not result.is_speech
        assert result.energy_level == 0.0

    @pytest.mark.asyncio
    async def test_empty_audio(self):
        vad = EnergyVAD()
        result = await vad.detect(b"")
        assert not result.is_speech
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_speech_detected(self):
        vad = EnergyVAD()
        # Generate a sine wave at 440Hz, high amplitude
        import math
        import struct

        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(1600)]  # 100ms
        audio = struct.pack(f"<{len(samples)}h", *samples)
        result = await vad.detect(audio)
        assert result.is_speech
        assert result.confidence > 0.5
        assert result.energy_level > 0.5

    @pytest.mark.asyncio
    async def test_sensitivity_affects_detection(self):
        vad = EnergyVAD()
        import math
        import struct

        samples = [int(4000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(1600)]
        audio = struct.pack(f"<{len(samples)}h", *samples)

        # High sensitivity (lower threshold)
        result_sensitive = await vad.detect(audio, VADConfig(threshold=0.9))
        # Low sensitivity (higher threshold)
        result_insensitive = await vad.detect(audio, VADConfig(threshold=0.1))
        # Both should detect this loud audio
        assert result_sensitive.is_speech
        assert result_insensitive.is_speech


# ---------------------------------------------------------------------------
# GapBasedTurn
# ---------------------------------------------------------------------------


class TestGapBasedTurn:
    @pytest.mark.asyncio
    async def test_speech_during_idle(self):
        turn = GapBasedTurn()
        import math
        import struct

        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(1600)]
        audio = struct.pack(f"<{len(samples)}h", *samples)

        decision = await turn.decide(audio, agent_is_speaking=False)
        assert decision.action == "wait"
        assert "user speaking" in decision.reason

    @pytest.mark.asyncio
    async def test_interrupt_during_agent_speech(self):
        turn = GapBasedTurn()
        import math
        import struct

        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(1600)]
        audio = struct.pack(f"<{len(samples)}h", *samples)

        decision = await turn.decide(audio, agent_is_speaking=True)
        assert decision.action == "interrupt"

    @pytest.mark.asyncio
    async def test_silence_during_agent_speech(self):
        turn = GapBasedTurn()
        silence = b"\x00" * 320

        decision = await turn.decide(silence, agent_is_speaking=True)
        assert decision.action == "speak"

    @pytest.mark.asyncio
    async def test_endpoint_detection(self):
        turn = GapBasedTurn()
        import math
        import struct
        import time

        # First, some speech
        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(1600)]
        audio = struct.pack(f"<{len(samples)}h", *samples)

        await turn.decide(audio, agent_is_speaking=False)

        # First silence — starts the timer
        silence = b"\x00" * 320
        decision1 = await turn.decide(silence, agent_is_speaking=False)
        assert decision1.action == "wait"  # not enough silence yet

        # Wait past endpoint threshold
        time.sleep(0.6)

        # Second silence — should trigger endpoint
        decision2 = await turn.decide(silence, agent_is_speaking=False)
        assert decision2.action == "speak"


# ---------------------------------------------------------------------------
# VoiceProviderRegistry
# ---------------------------------------------------------------------------


class TestVoiceProviderRegistry:
    def test_default_registry_has_energy_vad(self):
        reg = VoiceProviderRegistry()
        vad = reg.get_vad("energy")
        assert vad.kind == VADProviderKind.ENERGY

    def test_default_registry_has_gap_turn(self):
        reg = VoiceProviderRegistry()
        turn = reg.get_turn("gap")
        assert turn is not None

    def test_register_and_get_stt(self):
        reg = VoiceProviderRegistry()
        reg.register_stt("test", _MockSTT())
        assert reg.get_stt("test").kind == STTProviderKind.WHISPER

    def test_register_and_get_tts(self):
        reg = VoiceProviderRegistry()
        reg.register_tts("test", _MockTTS())
        assert reg.get_tts("test").kind == TTSProviderKind.KOKORO

    def test_get_missing_raises(self):
        reg = VoiceProviderRegistry()
        with pytest.raises(KeyError, match="STT provider"):
            reg.get_stt("nonexistent")
        with pytest.raises(KeyError, match="TTS provider"):
            reg.get_tts("nonexistent")

    def test_list_providers(self):
        reg = VoiceProviderRegistry()
        assert "energy" in reg.list_vad()
        assert "gap" in reg.list_turn()


# ---------------------------------------------------------------------------
# VoicePipelineConfig
# ---------------------------------------------------------------------------


class TestVoicePipelineConfig:
    def test_defaults(self):
        cfg = VoicePipelineConfig()
        assert cfg.sample_rate == 16000
        assert cfg.channels == 1
        assert cfg.echo_cancellation is True
        assert cfg.stt.language == "en"
        assert cfg.tts.sample_rate == 24000

    def test_custom(self):
        cfg = VoicePipelineConfig(
            sample_rate=48000,
            channels=2,
            echo_cancellation=False,
        )
        assert cfg.sample_rate == 48000
        assert cfg.channels == 2
        assert cfg.echo_cancellation is False


# ---------------------------------------------------------------------------
# Mock providers
# ---------------------------------------------------------------------------


from lyra_voice.providers import (
    STTProvider,
    STTResult,
    TTSProvider,
)


class _MockSTT(STTProvider):
    kind = STTProviderKind.WHISPER

    async def transcribe(self, audio, config=None):
        return STTResult(
            text="test transcription",
            confidence=0.9,
            language="en",
        )


class _MockTTS(TTSProvider):
    kind = TTSProviderKind.KOKORO

    async def synthesize(self, text, config=None):
        return b"fake_audio_data"


# ---------------------------------------------------------------------------
# SileroVAD
# ---------------------------------------------------------------------------


class TestSileroVAD:
    @pytest.mark.asyncio
    async def test_silence_detected(self):
        from lyra_voice.providers import SileroVAD, VADConfig

        vad = SileroVAD()
        silence = b"\x00" * 320
        result = await vad.detect(silence)
        assert not result.is_speech

    @pytest.mark.asyncio
    async def test_empty_audio(self):
        from lyra_voice.providers import SileroVAD

        vad = SileroVAD()
        result = await vad.detect(b"")
        assert not result.is_speech
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_speech_detected(self):
        from lyra_voice.providers import SileroVAD

        vad = SileroVAD()
        import math
        import struct

        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(1600)]
        audio = struct.pack(f"<{len(samples)}h", *samples)
        result = await vad.detect(audio)
        assert result.is_speech
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_has_silero_kind(self):
        from lyra_voice.providers import SileroVAD, VADProviderKind

        vad = SileroVAD()
        assert vad.kind == VADProviderKind.SILERO


# ---------------------------------------------------------------------------
# SmartTurn
# ---------------------------------------------------------------------------


class TestSmartTurn:
    @pytest.mark.asyncio
    async def test_speech_during_idle(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn()
        import math
        import struct

        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(1600)]
        audio = struct.pack(f"<{len(samples)}h", *samples)

        decision = await turn.decide(audio, agent_is_speaking=False)
        assert decision.action == "wait"
        assert "user speaking" in decision.reason

    @pytest.mark.asyncio
    async def test_interrupt_during_agent_speech(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn()
        import math
        import struct

        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(1600)]
        audio = struct.pack(f"<{len(samples)}h", *samples)

        decision = await turn.decide(audio, agent_is_speaking=True)
        assert decision.action == "interrupt"

    @pytest.mark.asyncio
    async def test_semantic_endpoint_with_partial_text(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("en",))
        # Feed partial text that looks complete
        turn.set_partial_text("search for documents.")

        import math
        import struct

        # First, some speech
        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(1600)]
        audio = struct.pack(f"<{len(samples)}h", *samples)
        await turn.decide(audio, agent_is_speaking=False)

        # Then silence
        silence = b"\x00" * 640
        decision = await turn.decide(silence, agent_is_speaking=False)
        # With semantically complete text + some silence, should trigger endpoint
        assert decision.action in ("speak", "wait")

    @pytest.mark.asyncio
    async def test_vi_language_support(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("vi",))
        turn.set_partial_text("xong rồi")

        import math
        import struct

        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(1600)]
        audio = struct.pack(f"<{len(samples)}h", *samples)
        await turn.decide(audio, agent_is_speaking=False)

        silence = b"\x00" * 640
        decision = await turn.decide(silence, agent_is_speaking=False)
        assert decision.action in ("speak", "wait")

    @pytest.mark.asyncio
    async def test_semantic_completeness_short_command(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn()
        # Short commands are considered complete
        assert turn._is_semantically_complete("open settings")
        assert turn._is_semantically_complete("search files")
        # Very short text isn't complete
        assert not turn._is_semantically_complete("um")

    @pytest.mark.asyncio
    async def test_has_smart_turn_kind(self):
        from lyra_voice.providers import SmartTurn, TurnTakingKind

        turn = SmartTurn()
        assert turn.kind == TurnTakingKind.SMART_TURN


# ---------------------------------------------------------------------------
# WhisperSTT
# ---------------------------------------------------------------------------


class TestWhisperSTT:
    @pytest.mark.asyncio
    async def test_transcribe_speech(self):
        from lyra_voice.providers import WhisperSTT

        stt = WhisperSTT()
        import math
        import struct

        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(3200)]  # 200ms
        audio = struct.pack(f"<{len(samples)}h", *samples)
        result = await stt.transcribe(audio)
        assert len(result.text) > 0
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_transcribe_silence(self):
        from lyra_voice.providers import WhisperSTT

        stt = WhisperSTT()
        silence = b"\x00" * 320
        result = await stt.transcribe(silence)
        assert result.text == ""

    @pytest.mark.asyncio
    async def test_transcribe_empty(self):
        from lyra_voice.providers import WhisperSTT

        stt = WhisperSTT()
        result = await stt.transcribe(b"")
        assert result.text == ""

    @pytest.mark.asyncio
    async def test_has_whisper_kind(self):
        from lyra_voice.providers import WhisperSTT, STTProviderKind

        stt = WhisperSTT()
        assert stt.kind == STTProviderKind.WHISPER

    @pytest.mark.asyncio
    async def test_custom_model_size(self):
        from lyra_voice.providers import WhisperSTT

        stt = WhisperSTT(model_size="tiny")
        assert stt._model_size == "tiny"


# ---------------------------------------------------------------------------
# KokoroTTS
# ---------------------------------------------------------------------------


class TestKokoroTTS:
    @pytest.mark.asyncio
    async def test_synthesize_text(self):
        from lyra_voice.providers import KokoroTTS

        tts = KokoroTTS()
        audio = await tts.synthesize("Hello world")
        assert len(audio) > 0
        assert len(audio) % 2 == 0  # 16-bit PCM

    @pytest.mark.asyncio
    async def test_synthesize_empty(self):
        from lyra_voice.providers import KokoroTTS

        tts = KokoroTTS()
        audio = await tts.synthesize("")
        assert audio == b""

    @pytest.mark.asyncio
    async def test_has_kokoro_kind(self):
        from lyra_voice.providers import KokoroTTS, TTSProviderKind

        tts = KokoroTTS()
        assert tts.kind == TTSProviderKind.KOKORO

    @pytest.mark.asyncio
    async def test_output_varies_with_text(self):
        from lyra_voice.providers import KokoroTTS

        tts = KokoroTTS()
        short = await tts.synthesize("Hi")
        long = await tts.synthesize("This is a much longer piece of text to synthesize")
        assert len(long) >= len(short)


# ---------------------------------------------------------------------------
# VoiceProviderRegistry — new providers
# ---------------------------------------------------------------------------


class TestVoiceProviderRegistryNewProviders:
    def test_silero_vad_registered(self):
        from lyra_voice.providers import VoiceProviderRegistry, VADProviderKind

        reg = VoiceProviderRegistry()
        vad = reg.get_vad("silero")
        assert vad.kind == VADProviderKind.SILERO

    def test_smart_turn_registered(self):
        from lyra_voice.providers import VoiceProviderRegistry, TurnTakingKind

        reg = VoiceProviderRegistry()
        turn = reg.get_turn("smart")
        assert turn.kind == TurnTakingKind.SMART_TURN

    def test_whisper_stt_registered(self):
        from lyra_voice.providers import VoiceProviderRegistry, STTProviderKind

        reg = VoiceProviderRegistry()
        stt = reg.get_stt("whisper")
        assert stt.kind == STTProviderKind.WHISPER

    def test_kokoro_tts_registered(self):
        from lyra_voice.providers import VoiceProviderRegistry, TTSProviderKind

        reg = VoiceProviderRegistry()
        tts = reg.get_tts("kokoro")
        assert tts.kind == TTSProviderKind.KOKORO

    def test_default_stt_is_whisper(self):
        from lyra_voice.providers import VoiceProviderRegistry

        reg = VoiceProviderRegistry()
        stt = reg.get_stt("default")
        assert stt is not None

    def test_default_tts_is_kokoro(self):
        from lyra_voice.providers import VoiceProviderRegistry

        reg = VoiceProviderRegistry()
        tts = reg.get_tts("default")
        assert tts is not None
