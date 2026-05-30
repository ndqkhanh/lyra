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
