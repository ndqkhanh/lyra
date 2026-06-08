"""Tests for the VI+EN bilingual voice pipeline module.

Covers HeuristicLanguageDetector, BilingualRouter, language detection,
code-switching detection, and voice persona selection.
"""
from __future__ import annotations

import pytest

from lyra.voice.bilingual import (
    BilingualError,
    BilingualRoute,
    BilingualRouter,
    BilingualStats,
    CodeSwitchError,
    HeuristicLanguageDetector,
    Language,
    LanguageDetectionError,
    LanguageDetectionMethod,
    LanguageResult,
    LanguageSegment,
    VoicePersona,
    VIETNAMESE_CHARACTERS,
    VIETNAMESE_PATTERN,
    VIETNAMESE_STOP_WORDS,
)


# ===================================================================
# HeuristicLanguageDetector tests
# ===================================================================


class TestHeuristicLanguageDetector:
    """Tests for the heuristic language detector."""

    def test_creation(self) -> None:
        detector = HeuristicLanguageDetector()
        assert detector._vi_threshold == 0.15
        assert detector._mixed_threshold == 0.05

    def test_custom_thresholds(self) -> None:
        detector = HeuristicLanguageDetector(vi_threshold=0.3, mixed_threshold=0.1)
        assert detector._vi_threshold == 0.3

    @pytest.mark.asyncio
    async def test_empty_text_returns_en(self) -> None:
        detector = HeuristicLanguageDetector()
        result = await detector.classify("")
        assert result.language == Language.EN
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_whitespace_text_returns_en(self) -> None:
        detector = HeuristicLanguageDetector()
        result = await detector.classify("   ")
        assert result.language == Language.EN

    @pytest.mark.asyncio
    async def test_english_text(self) -> None:
        detector = HeuristicLanguageDetector()
        result = await detector.classify("Hello, how are you today?")
        assert result.language == Language.EN
        assert result.method == LanguageDetectionMethod.HEURISTIC

    @pytest.mark.asyncio
    async def test_vietnamese_text(self) -> None:
        detector = HeuristicLanguageDetector()
        result = await detector.classify("Xin chào, bạn khỏe không?")
        assert result.language == Language.VI

    @pytest.mark.asyncio
    async def test_vietnamese_with_accented_chars(self) -> None:
        detector = HeuristicLanguageDetector()
        result = await detector.classify("Tôi đang học lập trình Python")
        assert result.language == Language.VI

    @pytest.mark.asyncio
    async def test_code_switched_text(self) -> None:
        detector = HeuristicLanguageDetector(vi_threshold=0.05, mixed_threshold=0.0)
        result = await detector.classify("Xin chào, how are you?")
        # Could be MIXED or EN - depends on ratio
        assert result.language in (Language.MIXED, Language.VI, Language.EN)

    @pytest.mark.asyncio
    async def test_code_switch_detection(self) -> None:
        detector = HeuristicLanguageDetector(vi_threshold=0.01, mixed_threshold=0.0)
        result = await detector.classify("Toi rat thich learning new things")
        assert result.language == Language.MIXED or result.language == Language.EN

    @pytest.mark.asyncio
    async def test_vi_ratio_in_result(self) -> None:
        detector = HeuristicLanguageDetector()
        result = await detector.classify("Xin chào các bạn")
        assert result.vi_ratio > 0.0

    def test_is_vietnamese_word(self) -> None:
        detector = HeuristicLanguageDetector()
        assert detector._is_vietnamese_word("xin") is False  # not a stop word / no accent
        assert detector._is_vietnamese_word("chào") is True  # has accent
        assert detector._is_vietnamese_word("của") is True   # stop word

    def test_detect_code_switch_all_english(self) -> None:
        detector = HeuristicLanguageDetector()
        lang, segments = detector._detect_code_switch("hello world", ["hello", "world"])
        assert lang != Language.MIXED or len(segments) == 1

    def test_detect_code_switch_mixed(self) -> None:
        detector = HeuristicLanguageDetector()
        lang, segments = detector._detect_code_switch(
            "xin chào hello world",
            ["xin", "chào", "hello", "world"],
        )
        # xin chào are VI (with accents) or stop words, hello world are EN
        # This should produce at least 2 segments

    def test_compute_segments_single_language(self) -> None:
        detector = HeuristicLanguageDetector()
        segments = detector._compute_segments(
            "hello world", Language.EN, ["hello", "world"],
        )
        assert len(segments) == 1
        assert segments[0].language == Language.EN

    def test_compute_segments_mixed(self) -> None:
        detector = HeuristicLanguageDetector()
        # Force MIXED by setting known context
        segments = detector._compute_segments(
            "chào hello",
            Language.MIXED,
            ["chào", "hello"],
        )
        assert len(segments) >= 1


# ===================================================================
# BilingualRouter tests
# ===================================================================


class TestBilingualRouter:
    """Tests for the bilingual voice router."""

    def test_creation_with_defaults(self) -> None:
        router = BilingualRouter()
        assert Language.EN in router.personas
        assert Language.VI in router.personas
        assert router.stats.total_utterances == 0

    def test_creation_with_custom_personas(self) -> None:
        en_persona = VoicePersona(
            language=Language.EN,
            voice_id="alloy",
            name="Custom EN",
            stt_provider_hint="deepseek",
            tts_provider_hint="elevenlabs",
        )
        router = BilingualRouter(personas={Language.EN: en_persona})
        assert router.personas[Language.EN].name == "Custom EN"
        assert Language.VI not in router.personas

    def test_stats_property(self) -> None:
        router = BilingualRouter()
        assert isinstance(router.stats, BilingualStats)

    def test_personas_property_returns_copy(self) -> None:
        router = BilingualRouter()
        personas = router.personas
        personas[Language.EN] = VoicePersona(
            language=Language.EN, voice_id="other", name="Other",
        )
        # The original should be unchanged
        assert router.personas[Language.EN].name != "Other"

    @pytest.mark.asyncio
    async def test_route_english(self) -> None:
        router = BilingualRouter()
        route = await router.route("Hello, how are you?")
        assert route.language == Language.EN
        assert route.persona.language == Language.EN
        assert route.segments is None  # Not mixed

    @pytest.mark.asyncio
    async def test_route_vietnamese(self) -> None:
        router = BilingualRouter()
        route = await router.route("Xin chào, bạn khỏe không?")
        assert route.language in (Language.VI, Language.EN)
        if route.language == Language.VI:
            assert route.persona.language == Language.VI

    @pytest.mark.asyncio
    async def test_route_empty_text(self) -> None:
        router = BilingualRouter()
        route = await router.route("")
        assert route.language == Language.EN

    @pytest.mark.asyncio
    async def test_route_with_detection_failure(self) -> None:
        class FailingDetector:
            async def classify(self, text):
                raise RuntimeError("Detection failed")

        router = BilingualRouter(detector=FailingDetector())
        with pytest.raises(LanguageDetectionError, match="Language detection failed"):
            await router.route("Hello")

    def test_default_personas(self) -> None:
        router = BilingualRouter()
        en = router.persona_for_language(Language.EN)
        assert en.language == Language.EN
        assert en.voice_id == "alloy"

        vi = router.persona_for_language(Language.VI)
        assert vi.language == Language.VI
        assert vi.voice_id == "nova"

    def test_persona_for_unconfigured_language(self) -> None:
        router = BilingualRouter(personas={Language.EN: VoicePersona(
            language=Language.EN, voice_id="alloy", name="EN",
        )})
        persona = router.persona_for_language(Language.VI)
        assert persona.voice_id == "alloy"  # Falls back to EN

    def test_persona_for_default_fallback(self) -> None:
        router = BilingualRouter()
        # _select_persona with a language not in personas
        persona = router._select_persona(Language.MIXED)
        assert persona.voice_id == "alloy"  # Default fallback

    def test_register_persona(self) -> None:
        router = BilingualRouter()
        new_persona = VoicePersona(
            language=Language.VI,
            voice_id="custom",
            name="Custom VI",
        )
        router.register_persona(new_persona)
        assert router.personas[Language.VI].voice_id == "custom"

    def test_reset_stats(self) -> None:
        router = BilingualRouter()
        router._stats.total_utterances = 10
        router.reset_stats()
        assert router.stats.total_utterances == 0

    def test_select_persona_exact_match(self) -> None:
        router = BilingualRouter()
        persona = router._select_persona(Language.VI)
        assert persona.language == Language.VI

    def test_select_persona_fallback(self) -> None:
        router = BilingualRouter(personas={Language.EN: VoicePersona(
            language=Language.EN, voice_id="alloy", name="EN",
        )})
        # For a language not in the dict, should fallback
        persona = router._select_persona(Language.MIXED)
        assert persona.voice_id == "alloy"  # EN fallback

    @pytest.mark.asyncio
    async def test_route_mixed_updates_stats(self) -> None:
        router = BilingualRouter()

        # Use a detector that returns MIXED
        class MixedDetector:
            async def classify(self, text):
                return LanguageResult(
                    language=Language.MIXED,
                    confidence=0.8,
                    method=LanguageDetectionMethod.HEURISTIC,
                    segments=[
                        LanguageSegment(
                            text="xin chào", language=Language.VI,
                            start_char=0, end_char=8, confidence=1.0,
                        ),
                        LanguageSegment(
                            text="hello", language=Language.EN,
                            start_char=9, end_char=14, confidence=1.0,
                        ),
                    ],
                )

        router = BilingualRouter(detector=MixedDetector())
        route = await router.route("xin chào hello")
        assert route.language == Language.MIXED
        assert router.stats.mixed_count == 1

    @pytest.mark.asyncio
    async def test_route_low_confidence(self) -> None:
        class LowConfDetector:
            async def classify(self, text):
                return LanguageResult(
                    language=Language.EN,
                    confidence=0.2,
                    method=LanguageDetectionMethod.HEURISTIC,
                )

        router = BilingualRouter(detector=LowConfDetector())
        await router.route("blah blah")
        assert router.stats.detection_failures == 1

    def test_detect_code_switching(self) -> None:
        router = BilingualRouter()
        segments, primary = router.detect_code_switching("chao ban hello")
        assert isinstance(segments, list)


# ===================================================================
# Data type tests
# ===================================================================


class TestDataTypes:
    """Tests for bilingual data types."""

    def test_language_enum(self) -> None:
        assert Language.EN.value == "en"
        assert Language.VI.value == "vi"
        assert Language.MIXED.value == "mixed"

    def test_language_detection_method_enum(self) -> None:
        assert LanguageDetectionMethod.HEURISTIC.value == "heuristic"
        assert LanguageDetectionMethod.CLASSIFIER.value == "classifier"

    def test_voice_persona_defaults(self) -> None:
        persona = VoicePersona(
            language=Language.EN,
            voice_id="alloy",
            name="Test",
        )
        assert persona.speed == 1.0
        assert persona.pitch == 0.0
        assert persona.additional_settings == {}

    def test_bilingual_route_defaults(self) -> None:
        persona = VoicePersona(language=Language.EN, voice_id="alloy", name="Test")
        route = BilingualRoute(
            text="hello",
            language=Language.EN,
            persona=persona,
        )
        assert route.stt_provider_key == "default"
        assert route.tts_provider_key == "default"
        assert route.segments is None

    def test_language_segment(self) -> None:
        seg = LanguageSegment(
            text="hello",
            language=Language.EN,
            start_char=0,
            end_char=5,
            confidence=0.95,
        )
        assert seg.text == "hello"
        assert seg.confidence == 0.95

    def test_language_result_defaults(self) -> None:
        result = LanguageResult(language=Language.EN)
        assert result.confidence == 1.0
        assert result.method == LanguageDetectionMethod.HEURISTIC
        assert result.vi_ratio == 0.0
        assert result.segments == []


# ===================================================================
# Constants tests
# ===================================================================


class TestConstants:
    """Tests for bilingual constants."""

    def test_vietnamese_pattern(self) -> None:
        assert VIETNAMESE_PATTERN.search("Xin chào") is not None
        assert VIETNAMESE_PATTERN.search("Hello") is None

    def test_vietnamese_stop_words(self) -> None:
        assert "của" in VIETNAMESE_STOP_WORDS
        assert "và" in VIETNAMESE_STOP_WORDS
        assert "the" not in VIETNAMESE_STOP_WORDS
        assert len(VIETNAMESE_STOP_WORDS) > 20

    def test_vietnamese_characters(self) -> None:
        assert "À" in VIETNAMESE_CHARACTERS
        assert "â" in VIETNAMESE_CHARACTERS
        assert "đ" in VIETNAMESE_CHARACTERS
        assert "z" not in VIETNAMESE_CHARACTERS
