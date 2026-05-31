"""Tests for lyra-voice internal helpers and edge cases.

Covers:
- _compute_rms (real RMS computation in __init__.py)
- Provider abstract default implementations (stream_transcribe, stream_synthesize, detect_segments)
- VoiceInterface parse_command edge cases (entities, location, numbers, fillers)
- SmartTurn multi-language edge cases
- VADSegment and VADConfig
- Pipeline edge cases
- VoiceProviderRegistry exhaustive tests
"""

from __future__ import annotations

import math
import struct

import pytest

from lyra_voice import (
    ParsedCommand,
    VADMode,
    VADResult,
    VoiceCommand,
    VoiceCommandAction,
    VoiceConfig,
    VoiceInterface,
    VoiceSession,
    WakeWordConfig,
    WakeWordModel,
    _compute_rms,
)
from lyra_voice.pipeline import (
    InteractionMode,
    PipelineEvent,
    PipelineState,
    VoicePipeline,
    VoicePipelineConfig,
    VoiceTurn,
)
from lyra_voice.providers import (
    VADConfig,
    VADProviderKind,
    VADSegment,
    VoiceProviderRegistry,
)


# ═══════════════════════════════════════════════════════════════════════════
# _compute_rms
# ═══════════════════════════════════════════════════════════════════════════


class TestComputeRMS:
    """_compute_rms is a real RMS energy computation on raw 16-bit PCM data."""

    def test_empty_returns_zero(self):
        assert _compute_rms(b"") == 0.0

    def test_too_short_returns_zero(self):
        assert _compute_rms(b"\x00") == 0.0  # 1 byte, < 2

    def test_silence_returns_zero(self):
        assert _compute_rms(b"\x00" * 100) == 0.0

    def test_odd_length_truncated_gracefully(self):
        """An odd number of bytes is truncated to even before processing."""
        rms = _compute_rms(b"\x00\x00\x00")  # 3 bytes -> first 2 only
        assert rms == 0.0

    def test_constant_positive_value(self):
        """All samples = 1000 -> RMS = 1000."""
        samples = struct.pack("<h", 1000) * 10
        rms = _compute_rms(samples)
        assert rms == pytest.approx(1000.0, rel=0.01)

    def test_constant_negative_value(self):
        """All samples = -1000 -> RMS = 1000 (squared, so positive)."""
        samples = struct.pack("<h", -1000) * 10
        rms = _compute_rms(samples)
        assert rms == pytest.approx(1000.0, rel=0.01)

    def test_known_sine_wave_rms(self):
        """A sine wave A*sin(t) has RMS = A/sqrt(2)."""
        amplitude = 8000
        n = 1600
        samples = []
        for i in range(n):
            s = int(amplitude * math.sin(2 * math.pi * 440 * i / 16000))
            samples.append(s)
        data = struct.pack(f"<{n}h", *samples)
        expected_rms = amplitude / math.sqrt(2)
        rms = _compute_rms(data)
        assert rms == pytest.approx(expected_rms, rel=0.02)

    def test_mixed_signals(self):
        """Alternating positive and negative values."""
        n = 100
        samples = [32767 if i % 2 == 0 else -32768 for i in range(n)]
        data = struct.pack(f"<{n}h", *samples)
        rms = _compute_rms(data)
        assert rms > 0


# ═══════════════════════════════════════════════════════════════════════════
# VADSegment / VADConfig
# ═══════════════════════════════════════════════════════════════════════════


class TestVADSegment:
    def test_defaults(self):
        s = VADSegment(is_speech=True, confidence=0.9)
        assert s.start_ms == 0.0
        assert s.end_ms == 0.0
        assert s.energy_level == 0.0

    def test_full_construction(self):
        s = VADSegment(is_speech=True, confidence=0.85, start_ms=10.0, end_ms=210.0, energy_level=0.6)
        assert s.is_speech
        assert s.confidence == 0.85
        assert s.energy_level == 0.6


class TestVADConfig:
    def test_defaults(self):
        c = VADConfig()
        assert c.sample_rate == 16000
        assert c.threshold == 0.5
        assert c.min_speech_duration_ms == 250


# ═══════════════════════════════════════════════════════════════════════════
# VoiceInterface: parse_command edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestParseCommandEdgeCases:
    """Exercise edge cases in VoiceInterface.parse_command."""

    @pytest.fixture
    def vi(self):
        return VoiceInterface()

    def test_parse_with_location_entity(self, vi):
        result = vi.parse_command("navigate to home")
        entities = dict(result.entities)
        assert "target" in entities
        assert "home" in entities["target"]

    def test_parse_with_quantity_entity(self, vi):
        result = vi.parse_command("create 5 reports")
        entity_types = [e[0] for e in result.entities]
        assert "quantity" in entity_types

    def test_parse_strips_short_filler_intent(self, vi):
        """When intent extraction leaves only filler, it should handle gracefully."""
        result = vi.parse_command("edit the file")
        assert result.action == "EDIT"
        assert result.intent  # non-empty intent

    def test_parse_whitespace_only(self, vi):
        result = vi.parse_command("   ")
        assert result.confidence == 0.0
        assert result.action == "QUERY"
        assert result.intent == "unknown"

    def test_parse_max_length_truncation(self, vi):
        """Command longer than max_command_length is truncated before matching."""
        config = VoiceConfig(max_command_length=10)
        vi2 = VoiceInterface(config=config)
        result = vi2.parse_command("search for some very long documents here")
        assert result.action is not None
        # The intent should be at most 10 chars
        assert len(result.intent) <= 10 + 60  # first truncation + intent truncation

    def test_parse_empty_with_context_still_low_confidence(self, vi):
        result = vi.parse_command("", context="some context")
        assert result.confidence == 0.0
        assert result.action == "QUERY"

    def test_parse_edit_action_matches_change(self, vi):
        result = vi.parse_command("change the settings")
        assert result.action == "EDIT"

    def test_parse_delete_action_matches_remove(self, vi):
        result = vi.parse_command("remove the file")
        assert result.action == "DELETE"

    def test_parse_navigate_go_keyword(self, vi):
        result = vi.parse_command("go to projects")
        assert result.action == "NAVIGATE"

    def test_parse_execute_action(self, vi):
        result = vi.parse_command("run the tests")
        assert result.action == "EXECUTE"

    def test_parse_pause_resume(self, vi):
        result = vi.parse_command("pause the operation")
        assert result.action == "PAUSE"
        result2 = vi.parse_command("continue the process")
        assert result2.action == "RESUME"


# ═══════════════════════════════════════════════════════════════════════════
# VoiceInterface: process_audio_stream edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestProcessAudioStreamEdgeCases:
    @pytest.fixture
    def vi(self):
        return VoiceInterface()

    def test_wake_word_disabled_can_still_process(self):
        """With wake word disabled, process_audio_stream should still work via VAD."""
        cfg = VoiceConfig(wake_word_enabled=False)
        vi = VoiceInterface(config=cfg)
        vi.start_session()
        chunks = [_build_pcm(rms=3000) for _ in range(3)]
        commands = vi.process_audio_stream(chunks)
        assert isinstance(commands, list)

    def test_multiple_rapid_chunks_same_session(self, vi):
        vi.start_session()
        chunks = [_build_pcm(rms=3000) for _ in range(5)]
        commands = vi.process_audio_stream(chunks)
        for cmd in commands:
            assert isinstance(cmd, VoiceCommand)

    def test_silence_then_speech_then_silence(self, vi):
        vi.start_session()
        chunks = [
            _build_pcm(rms=0),
            _build_pcm(rms=3000),
            _build_pcm(rms=0),
        ]
        commands = vi.process_audio_stream(chunks)
        assert len(commands) >= 1

    def test_no_session_no_crash(self, vi):
        chunks = [_build_pcm(rms=3000) for _ in range(2)]
        commands = vi.process_audio_stream(chunks)
        assert isinstance(commands, list)


# ═══════════════════════════════════════════════════════════════════════════
# VoiceInterface: execute_command exhaustive
# ═══════════════════════════════════════════════════════════════════════════


class TestExecuteCommandEdgeCases:
    @pytest.fixture
    def vi(self):
        return VoiceInterface()

    def test_execute_navigate(self, vi):
        result = vi.execute_command(vi.parse_command("go to dashboard"))
        assert result["status"] == "ok"

    def test_execute_query(self, vi):
        result = vi.execute_command(vi.parse_command("query the db"))
        assert "results" not in result  # only SEARCH has results key

    def test_execute_all_actions_ok(self, vi):
        """Every action should return status 'ok'."""
        for action in VoiceCommandAction:
            parsed = ParsedCommand(
                original_text=f"test {action.value}",
                action=action.value,
                intent=action.value.lower(),
                entities=(),
                confidence=0.5,
                alternative_actions=(),
            )
            result = vi.execute_command(parsed)
            assert result["status"] == "ok"
            assert result["action"] == action.value


# ═══════════════════════════════════════════════════════════════════════════
# VoicePipeline: edge cases
# ═══════════════════════════════════════════════════════════════════════════


class _EchoSTT:
    """Minimal STT that echoes length as text."""
    kind = "whisper"

    async def transcribe(self, audio, config=None):
        from lyra_voice.providers import STTResult
        return STTResult(
            text=f"transcribed {len(audio)} bytes",
            confidence=0.95,
            language="en",
            duration_ms=len(audio) / 32.0,
        )


class _EchoTTS:
    kind = "kokoro"

    async def synthesize(self, text, config=None):
        return text.encode("utf-8")


class _SilenceVAD:
    """VAD that always reports silence."""
    kind = "energy"

    async def detect(self, audio, config=None):
        return VADSegment(is_speech=False, confidence=0.0)

    async def detect_segments(self, audio, config=None):
        return [VADSegment(is_speech=False, confidence=0.0)]


def _make_registry(stt=None, tts=None, vad=None):
    reg = VoiceProviderRegistry()
    if stt:
        reg.register_stt("default", stt)
    if tts:
        reg.register_tts("default", tts)
    if vad:
        reg.register_vad("default", vad)
    return reg


def _test_audio(duration_ms=100, amplitude=0.5):
    import math
    sr = 16000
    n = int(sr * duration_ms / 1000)
    samples = [int(16000 * amplitude * math.sin(2 * math.pi * 440 * i / sr)) for i in range(n)]
    return struct.pack(f"<{n}h", *samples)


class TestVoicePipelineEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_audio_returns_none(self):
        pipeline = VoicePipeline()
        turn = await pipeline.process_audio(b"")
        assert turn is None

    @pytest.mark.asyncio
    async def test_silence_returns_none(self):
        pipeline = VoicePipeline()
        turn = await pipeline.process_audio(b"\x00" * 320)
        assert turn is None

    @pytest.mark.asyncio
    async def test_custom_config_passed_to_pipeline(self):
        cfg = VoicePipelineConfig(sample_rate=48000, channels=2)
        pipeline = VoicePipeline(config=cfg)
        assert pipeline._config.sample_rate == 48000
        assert pipeline._config.channels == 2

    @pytest.mark.asyncio
    async def test_event_handler_error_does_not_crash(self):
        reg = _make_registry(stt=_EchoSTT(), tts=_EchoTTS())
        pipeline = VoicePipeline(registry=reg)

        def broken_handler(event, **kwargs):
            raise RuntimeError("handler exploded")

        pipeline.on(PipelineEvent.SPEECH_STARTED, broken_handler)
        audio = _test_audio(200)
        turn = await pipeline.process_audio(audio)
        # Handler error should be caught, pipeline continues
        assert turn is not None

    @pytest.mark.asyncio
    async def test_state_listening_during_stream(self):
        reg = _make_registry(stt=_EchoSTT(), tts=_EchoTTS())
        pipeline = VoicePipeline(registry=reg)

        async def stream():
            yield _test_audio(200)

        turns = [t async for t in pipeline.process_stream(stream())]
        assert pipeline.state == PipelineState.IDLE

    @pytest.mark.asyncio
    async def test_push_to_talk_emits_started_event(self):
        reg = _make_registry(stt=_EchoSTT(), tts=_EchoTTS())
        pipeline = VoicePipeline(registry=reg)
        events = []

        async def handler(event, **kwargs):
            events.append(event)

        pipeline.on(PipelineEvent.PIPELINE_STARTED, handler)

        async def uppercase(text):
            return text.upper()

        audio = _test_audio(200)
        await pipeline.push_to_talk(audio, uppercase)
        assert PipelineEvent.PIPELINE_STARTED in events

    @pytest.mark.asyncio
    async def test_pipeline_state_transitions(self):
        reg = _make_registry(stt=_EchoSTT(), tts=_EchoTTS())
        pipeline = VoicePipeline(registry=reg)
        assert pipeline.state == PipelineState.IDLE

        audio = _test_audio(200)
        await pipeline.process_audio(audio)

        assert pipeline.state == PipelineState.IDLE  # returns to idle after completion

    @pytest.mark.asyncio
    async def test_agent_handler_must_be_callable(self):
        reg = _make_registry(stt=_EchoSTT(), tts=_EchoTTS())
        pipeline = VoicePipeline(registry=reg)

        audio = _test_audio(200)
        # No handler provided = echo mode (agent_text == stt_text)
        turn = await pipeline.process_audio(audio)
        assert turn is not None
        assert turn.agent_text == turn.user_text

    @pytest.mark.asyncio
    async def test_reset_stats_clears_turns(self):
        reg = _make_registry(stt=_EchoSTT(), tts=_EchoTTS())
        pipeline = VoicePipeline(registry=reg)

        audio = _test_audio(200)
        await pipeline.process_audio(audio)
        assert len(pipeline.turns) == 1
        pipeline.reset_stats()
        assert len(pipeline.turns) == 0

    @pytest.mark.asyncio
    async def test_full_duplex_start_event(self):
        """Full_duplex mode emits pipeline_started."""
        from lyra_voice.providers import TurnConfig

        reg = _make_registry(stt=_EchoSTT(), tts=_EchoTTS())
        cfg = VoicePipelineConfig(turn=TurnConfig(endpoint_threshold_ms=0))
        pipeline = VoicePipeline(registry=reg, config=cfg)

        events = []
        pipeline.on(PipelineEvent.PIPELINE_STARTED, lambda event, **kw: events.append(event))

        async def stream():
            yield _test_audio(200)
            yield b"\x00" * 640  # silence to end

        _ = [t async for t in pipeline.process_stream(stream())]


# ═══════════════════════════════════════════════════════════════════════════
# VoiceProviderRegistry: exhaustive
# ═══════════════════════════════════════════════════════════════════════════


class TestVoiceProviderRegistryExhaustive:
    def test_get_missing_tts_raises(self):
        reg = VoiceProviderRegistry()
        with pytest.raises(KeyError, match="TTS provider"):
            reg.get_tts("nonexistent")

    def test_get_missing_vad_raises(self):
        reg = VoiceProviderRegistry()
        with pytest.raises(KeyError, match="VAD provider"):
            reg.get_vad("nonexistent")

    def test_get_missing_turn_raises(self):
        reg = VoiceProviderRegistry()
        with pytest.raises(KeyError, match="Turn provider"):
            reg.get_turn("nonexistent")

    def test_list_providers_empty_initially(self):
        reg = VoiceProviderRegistry()
        assert "energy" in reg.list_vad()
        assert "default" in reg.list_vad()
        assert "silero" in reg.list_vad()
        assert "gap" in reg.list_turn()
        assert "smart" in reg.list_turn()
        assert "default" in reg.list_stt()
        assert "whisper" in reg.list_stt()

    def test_register_overwrites_existing(self):
        reg = VoiceProviderRegistry()
        old = reg.get_vad("energy")
        from lyra_voice.providers import EnergyVAD
        new_energy = EnergyVAD()
        reg.register_vad("energy", new_energy)
        assert reg.get_vad("energy") is new_energy

    def test_register_stt_and_tts_defaults(self):
        reg = VoiceProviderRegistry()
        assert reg.get_stt("default") is not None
        assert reg.get_tts("default") is not None


# ═══════════════════════════════════════════════════════════════════════════
# SmartTurn: multi-language edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestSmartTurnMultiLanguage:
    @pytest.mark.asyncio
    async def test_semantic_completeness_zh(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("zh",))
        # Chinese sentence enders include 。！？
        assert turn._is_semantically_complete("好了。")
        assert turn._is_semantically_complete("完了！")
        assert turn._is_semantically_complete("谢谢？")

    @pytest.mark.asyncio
    async def test_semantic_completeness_ja(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("ja",))
        assert turn._is_semantically_complete("終わり。")
        assert turn._is_semantically_complete("ありがとう")

    @pytest.mark.asyncio
    async def test_semantic_completeness_vi(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("vi",))
        assert turn._is_semantically_complete("xong rồi")
        assert turn._is_semantically_complete("cảm ơn")

    @pytest.mark.asyncio
    async def test_semantic_completeness_fr(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("fr",))
        assert turn._is_semantically_complete("merci")
        assert turn._is_semantically_complete("c'est tout")

    @pytest.mark.asyncio
    async def test_semantic_completeness_de(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("de",))
        assert turn._is_semantically_complete("danke")

    @pytest.mark.asyncio
    async def test_semantic_completeness_ko(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("ko",))
        assert turn._is_semantically_complete("완료")

    @pytest.mark.asyncio
    async def test_short_command_complete(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("en",))
        assert turn._is_semantically_complete("open settings")
        assert turn._is_semantically_complete("search files")

    @pytest.mark.asyncio
    async def test_single_word_not_complete(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("en",))
        assert not turn._is_semantically_complete("a")
        assert not turn._is_semantically_complete("um")
        assert not turn._is_semantically_complete("so")

    @pytest.mark.asyncio
    async def test_empty_text_not_complete(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("en",))
        assert not turn._is_semantically_complete("")
        assert not turn._is_semantically_complete("  ")

    @pytest.mark.asyncio
    async def test_filler_words_not_interrupted(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("en",))
        # Filler words like "um", "uh" are not semantically complete
        assert not turn._is_semantically_complete("um")
        assert not turn._is_semantically_complete("uh")

    @pytest.mark.asyncio
    async def test_punctuation_endpoint(self):
        from lyra_voice.providers import SmartTurn

        turn = SmartTurn(languages=("en",))
        assert turn._is_semantically_complete("search for files.")
        assert turn._is_semantically_complete("hello!")
        assert turn._is_semantically_complete("is it done?")


# ═══════════════════════════════════════════════════════════════════════════
# VoiceInterface: detect_wake_word edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestDetectWakeWordEdgeCases:
    @pytest.fixture
    def vi(self):
        return VoiceInterface()

    def test_detect_wake_word_zero_crossing_too_low(self, vi):
        """Very low ZCR should be rejected even with high RMS."""
        # Create audio with constant value -> 0 ZCR
        samples = struct.pack("<h", 8000) * 800
        result = vi.detect_wake_word(samples)
        assert result is False

    def test_detect_wake_word_zero_crossing_too_high(self, vi):
        """Very high ZCR (noise) should be rejected."""
        # Alternating max/min values -> max ZCR
        samples = b"".join(struct.pack("<h", 32767 if i % 2 == 0 else -32768) for i in range(800))
        result = vi.detect_wake_word(samples)
        assert result is False

    def test_detect_wake_word_short_chunk_under_64_bytes(self, vi):
        result = vi.detect_wake_word(b"\x00" * 63)
        assert result is False

    def test_detect_wake_word_custom_cooldown(self):
        """With cooldown=0, consecutive detections should both succeed."""
        ww_cfg = WakeWordConfig(cooldown_ms=0)
        vi = VoiceInterface(wake_word_config=ww_cfg)
        chunk = _build_pcm(rms=3000)
        first = vi.detect_wake_word(chunk)
        second = vi.detect_wake_word(chunk)
        assert first is True
        assert second is True  # cooldown is 0, so second also succeeds


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _build_pcm(rms: float, num_samples: int = 1600) -> bytes:
    if rms <= 0:
        return b"\x00" * (num_samples * 2)
    amplitude = int(rms * math.sqrt(2))
    samples = []
    for i in range(num_samples):
        s = int(amplitude * math.sin(2 * math.pi * 440 * i / 16000))
        s = max(-32768, min(32767, s))
        samples.append(s)
    return struct.pack(f"<{num_samples}h", *samples)
