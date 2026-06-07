"""
VI + EN bilingual voice pipeline with language detection and code-switching.

Provides language-aware routing for Vietnamese and English speech
interfaces.  Each language path supports provider-swappable STT and TTS
(per Lyra's provider abstraction) with language-specific voice personas.

Key capabilities:
  1. **Language detection** -- classifies incoming speech as VI, EN, or
     mixed (code-switched) using a lightweight classifier.
  2. **Per-language provider routing** -- routes STT and TTS requests to
     the appropriate provider per detected language.
  3. **Code-switching detection** -- identifies mixed VI+EN utterances
     and routes segments independently.
  4. **Language-specific voice personas** -- configurable voice profiles
     per language (e.g. warm VI voice, neutral EN voice).

References:
    - Moshi (arXiv:2410.00037v2): English-only full-duplex; multilingual
      extension is identified as future work.
    - FDB-v3 (arXiv:2604.04847v1): English-only evaluation; code-switching
      and code-mixing are open benchmarking challenges.
    - OpenAI Whisper (MIT): 98-language support including VI, multilingual
      word-level timestamps.
    - Open ASR Leaderboard (arXiv:2510.06961v4): Multilingual degrades
      English WER by 0.27-0.65 pp; VI-specific accuracy unconfirmed for
      conversational speech.
"""

from __future__ import annotations

import re
import structlog
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VIETNAMESE_CHARACTERS: str = (
    "ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúý"
    "ĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậ"
    "ẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệ"
    "ỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợ"
    "ỤụỦủỨứỪừỬửỮữỰựỲỳỴỵỶỷỸỹ"
)
"""Full set of Vietnamese accented characters (lowercase + uppercase)."""

VIETNAMESE_PATTERN: re.Pattern = re.compile(
    f"[{VIETNAMESE_CHARACTERS}]"
)
"""Regex that matches any character unique to Vietnamese orthography."""

VIETNAMESE_STOP_WORDS: set[str] = {
    "của", "và", "có", "không", "là", "được", "cho", "với", "trong",
    "một", "những", "các", "này", "kia", "ấy", "đó", "nào", "sao",
    "thế", "nên", "bởi", "vì", "nhưng", "hoặc", "hay", "tại", "vào",
    "trên", "dưới", "ở", "từ", "đến", "ra", "về", "lên", "xuống",
    "qua", "lại", "rồi", "đã", "sẽ", "đang", "sắp", "vừa", "mới",
    "cần", "phải", "muốn", "có thể", "thể", "số", "người", "việc",
    "ai", "gì", "đâu", "nào", "sao", "thế nào", "bao nhiêu", "bao lâu",
}
"""Common Vietnamese stop words used in language detection heuristics."""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BilingualError(Exception):
    """Raised when the bilingual pipeline encounters a runtime error."""


class LanguageDetectionError(BilingualError):
    """Raised when language detection fails."""


class CodeSwitchError(BilingualError):
    """Raised when code-switch segment routing fails."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Language(Enum):
    """Supported languages for the bilingual voice pipeline."""

    EN = "en"
    """English."""

    VI = "vi"
    """Vietnamese."""

    MIXED = "mixed"
    """Code-switched VI+EN utterance."""


class LanguageDetectionMethod(Enum):
    """Methods for detecting utterance language."""

    HEURISTIC = "heuristic"
    """Character- and lexicon-based heuristic (fast, no model)."""

    STT_HINT = "stt_hint"
    """Language hint from the STT provider's detection."""

    CLASSIFIER = "classifier"
    """Separate language classifier model (e.g. fastText, langdetect)."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LanguageResult:
    """Result of language detection on an utterance.

    Attributes:
        language: Detected language (EN, VI, or MIXED).
        confidence: Confidence score (0.0 - 1.0).
        method: Detection method used.
        vi_ratio: Fraction of the utterance detected as Vietnamese
            (0.0 - 1.0).  Useful for code-switching analysis.
        segments: If MIXED, language-tagged segments of the utterance.
    """

    language: Language
    confidence: float = 1.0
    method: LanguageDetectionMethod = LanguageDetectionMethod.HEURISTIC
    vi_ratio: float = 0.0
    segments: list[LanguageSegment] = field(default_factory=list)


@dataclass(frozen=True)
class LanguageSegment:
    """A single language segment within a code-switched utterance.

    Attributes:
        text: The text of this segment.
        language: Language of this segment.
        start_char: Character offset of the segment start.
        end_char: Character offset of the segment end.
        confidence: Per-segment language confidence.
    """

    text: str
    language: Language
    start_char: int
    end_char: int
    confidence: float = 1.0


@dataclass(frozen=True)
class VoicePersona:
    """Language-specific voice persona configuration.

    Attributes:
        language: Language this persona targets.
        voice_id: Provider-specific voice identifier.
        name: Human-readable persona name.
        speed: Speaking speed multiplier (1.0 = normal).
        pitch: Pitch shift in semitones (0 = none).
        stt_provider_hint: Preferred STT provider for this language
            (e.g. ``"whisper"``, ``"deepseek"``).
        tts_provider_hint: Preferred TTS provider for this language.
        additional_settings: Provider-specific settings.
    """

    language: Language
    voice_id: str
    name: str = ""
    speed: float = 1.0
    pitch: float = 0.0
    stt_provider_hint: str = ""
    tts_provider_hint: str = ""
    additional_settings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BilingualRoute:
    """Routing decision for a bilingual utterance.

    Attributes:
        text: The original utterance text.
        language: Detected primary language.
        persona: Voice persona to use for TTS.
        stt_provider_key: Key identifying the STT provider to use.
        tts_provider_key: Key identifying the TTS provider to use.
        segments: If code-switched, language-tagged segments.
    """

    text: str
    language: Language
    persona: VoicePersona
    stt_provider_key: str = "default"
    tts_provider_key: str = "default"
    segments: list[LanguageSegment] | None = None


@dataclass
class BilingualStats:
    """Aggregate statistics for the bilingual pipeline.

    Attributes:
        total_utterances: Total utterances processed.
        en_count: Number classified as English.
        vi_count: Number classified as Vietnamese.
        mixed_count: Number classified as code-switched.
        detection_failures: Number of detection failures.
        detection_method_counts: Map of method to usage count.
    """

    total_utterances: int = 0
    en_count: int = 0
    vi_count: int = 0
    mixed_count: int = 0
    detection_failures: int = 0
    detection_method_counts: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


class LanguageClassifier(Protocol):
    """Protocol for a language classification model."""

    async def classify(self, text: str) -> LanguageResult:
        """Classify the language of *text*.

        Args:
            text: The utterance text to classify.

        Returns:
            A ``LanguageResult`` with the detected language and confidence.
        """
        ...


# ---------------------------------------------------------------------------
# Heuristic language detector
# ---------------------------------------------------------------------------


class HeuristicLanguageDetector:
    """Lightweight heuristic-based language detector.

    Uses character-set detection and Vietnamese stop-word frequency to
    classify utterances as EN, VI, or MIXED.  No external model required --
    runs in sub-millisecond on any CPU.

    The heuristic is intentionally conservative: it only classifies as VI
    if there is strong Vietnamese signal (accented characters or multiple
    stop words).  Borderline cases default to EN.
    """

    def __init__(
        self,
        vi_threshold: float = 0.15,
        mixed_threshold: float = 0.05,
    ) -> None:
        """Initialise the heuristic detector.

        Args:
            vi_threshold: Minimum ratio of Vietnamese characters or stop
                words to classify as VI (default 0.15).
            mixed_threshold: If both EN and VI signals are above this
                ratio, classify as MIXED (default 0.05).
        """
        self._vi_threshold = vi_threshold
        self._mixed_threshold = mixed_threshold

    async def classify(self, text: str) -> LanguageResult:
        """Classify utterance language using heuristics.

        Args:
            text: The utterance text.

        Returns:
            A ``LanguageResult`` with the detection result.
        """
        if not text or not text.strip():
            return LanguageResult(
                language=Language.EN,
                confidence=1.0,
                method=LanguageDetectionMethod.HEURISTIC,
            )

        words = text.strip().split()
        total_chars = len(text.strip())
        total_words = max(1, len(words))

        # Count Vietnamese signals
        vi_char_count = len(VIETNAMESE_PATTERN.findall(text))
        vi_stop_count = sum(1 for w in words if w.lower() in VIETNAMESE_STOP_WORDS)

        # Compute ratios
        vi_char_ratio = vi_char_count / max(1, total_chars)
        vi_stop_ratio = vi_stop_count / total_words
        vi_ratio = max(vi_char_ratio, vi_stop_ratio)

        # Classify
        if vi_ratio >= self._vi_threshold:
            # Strong Vietnamese signal
            language = Language.VI
            confidence = min(1.0, vi_ratio * 1.5)
        elif vi_ratio >= self._mixed_threshold:
            # Mixed signal -- check for code-switching
            language, segments = self._detect_code_switch(text, words)
            if language == Language.VI:
                confidence = min(1.0, vi_ratio * 1.2)
            else:
                confidence = 0.6 + (vi_ratio * 0.4)
        else:
            language = Language.EN
            confidence = max(0.7, 1.0 - vi_ratio)

        return LanguageResult(
            language=language,
            confidence=round(confidence, 4),
            method=LanguageDetectionMethod.HEURISTIC,
            vi_ratio=round(vi_ratio, 4),
            segments=self._compute_segments(text, language, words),
        )

    def _detect_code_switch(
        self,
        text: str,
        words: list[str],
    ) -> tuple[Language, list[LanguageSegment]]:
        """Detect code-switching in mixed-language text.

        Uses consecutive-word analysis to find language boundaries:
        groups of consecutive Vietnamese words indicate VI segments,
        while groups of non-Vietnamese words indicate EN segments.

        Args:
            text: Full utterance text.
            words: Tokenised words from the utterance.

        Returns:
            A tuple of ``(Language, segments)`` where Language is MIXED
            if code-switching is detected, or the dominant language.
        """
        segments: list[LanguageSegment] = []
        current_lang: Language | None = None
        segment_start = 0
        vi_segment_count = 0
        en_segment_count = 0

        for i, word in enumerate(words):
            is_vi = self._is_vietnamese_word(word)

            word_lang = Language.VI if is_vi else Language.EN
            if current_lang is None:
                current_lang = word_lang
                segment_start = i
            elif word_lang != current_lang:
                # Finalise the current segment
                segment_text = " ".join(words[segment_start:i])
                seg = LanguageSegment(
                    text=segment_text,
                    language=current_lang,
                    start_char=len(" ".join(words[:segment_start])),
                    end_char=len(" ".join(words[:i])),
                )
                segments.append(seg)
                if current_lang == Language.VI:
                    vi_segment_count += 1
                else:
                    en_segment_count += 1

                current_lang = word_lang
                segment_start = i

        # Finalise the last segment
        if current_lang is not None:
            segment_text = " ".join(words[segment_start:])
            seg = LanguageSegment(
                text=segment_text,
                language=current_lang,
                start_char=len(" ".join(words[:segment_start])),
                end_char=len(text),
            )
            segments.append(seg)
            if current_lang == Language.VI:
                vi_segment_count += 1
            else:
                en_segment_count += 1

        # If both languages have meaningful segments, it's MIXED
        if vi_segment_count >= 1 and en_segment_count >= 1:
            return Language.MIXED, segments

        # Otherwise, use the dominant language
        dominant = Language.VI if vi_segment_count > en_segment_count else Language.EN
        return dominant, segments

    def _is_vietnamese_word(self, word: str) -> bool:
        """Check whether *word* looks like Vietnamese.

        Returns ``True`` if the word contains Vietnamese accented characters
        or matches a known Vietnamese stop word.
        """
        if VIETNAMESE_PATTERN.search(word):
            return True
        if word.lower() in VIETNAMESE_STOP_WORDS:
            return True
        return False

    def _compute_segments(
        self,
        text: str,
        language: Language,
        words: list[str],
    ) -> list[LanguageSegment]:
        """Build language-tagged segments for the utterance.

        For MIXED language, returns the segments detected by code-switch
        analysis.  For single-language utterances, returns a single segment.
        """
        if language == Language.MIXED:
            _, segments = self._detect_code_switch(text, words)
            return segments

        return [
            LanguageSegment(
                text=text.strip(),
                language=language,
                start_char=0,
                end_char=len(text.strip()),
                confidence=1.0,
            )
        ]


# ---------------------------------------------------------------------------
# BilingualRouter
# ---------------------------------------------------------------------------


class BilingualRouter:
    """Language-aware routing for VI+EN bilingual voice pipelines.

    Handles detection, routing, persona selection, and code-switching
    for mixed-language utterances.

    Usage::

        router = BilingualRouter(
            personas={
                Language.EN: VoicePersona(
                    language=Language.EN,
                    voice_id="alloy",
                    name="Alloy",
                    stt_provider_hint="openai",
                    tts_provider_hint="openai",
                ),
                Language.VI: VoicePersona(
                    language=Language.VI,
                    voice_id="nova",
                    name="Nova (Vietnamese)",
                    stt_provider_hint="deepseek",
                    tts_provider_hint="elevenlabs",
                    additional_settings={"language_hint": "vi"},
                ),
            }
        )

        route = await router.route("Xin chào, how are you?")
        assert route.language == Language.MIXED
        assert len(route.segments) == 2

    References:
        - Whisper (MIT): 98-language support.
        - Open ASR Leaderboard (arXiv:2510.06961v4): Multilingual WER
          degrades 0.27-0.65 pp; VI conversational accuracy unconfirmed.
        - FDB-v3 (arXiv:2604.04847v1): Code-switching benchmarking is
          open future work.
    """

    def __init__(
        self,
        personas: dict[Language, VoicePersona] | None = None,
        detector: LanguageClassifier | None = None,
        default_language: Language = Language.EN,
    ) -> None:
        """Initialise the bilingual router.

        Args:
            personas: Language-to-VoicePersona map.  If ``None``, default
                personas are created for EN and VI.
            detector: Language classifier.  If ``None``, a
                ``HeuristicLanguageDetector`` is used.
            default_language: Fallback language when detection is uncertain.
        """
        self._personas = personas or self._default_personas()
        self._detector = detector or HeuristicLanguageDetector()
        self._default_language = default_language
        self._stats = BilingualStats()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def stats(self) -> BilingualStats:
        """Aggregate routing statistics."""
        return self._stats

    @property
    def personas(self) -> dict[Language, VoicePersona]:
        """Registered voice personas by language."""
        return dict(self._personas)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def route(
        self,
        text: str,
    ) -> BilingualRoute:
        """Route *text* through the bilingual pipeline.

        Detects the language, selects the appropriate voice persona,
        and identifies the STT/TTS providers.

        Args:
            text: The transcribed utterance text.

        Returns:
            A ``BilingualRoute`` with language, persona, and provider keys.
        """
        self._stats.total_utterances += 1

        # 1. Detect language
        try:
            lang_result = await self._detector.classify(text)
        except Exception as exc:
            raise LanguageDetectionError(
                f"Language detection failed: {exc}"
            ) from exc

        # 2. Update stats
        method_key = lang_result.method.value
        self._stats.detection_method_counts[method_key] = (
            self._stats.detection_method_counts.get(method_key, 0) + 1
        )

        if lang_result.language == Language.EN:
            self._stats.en_count += 1
        elif lang_result.language == Language.VI:
            self._stats.vi_count += 1
        elif lang_result.language == Language.MIXED:
            self._stats.mixed_count += 1

        if lang_result.confidence < 0.3:
            self._stats.detection_failures += 1

        # 3. Select persona (prefer exact match, fall back to default)
        persona = self._select_persona(lang_result.language)

        # 4. Build route
        language_for_routing = lang_result.language
        if language_for_routing == Language.MIXED:
            # For code-switched utterances, use the first segment's language
            # as the primary provider hint
            if lang_result.segments:
                first_seg_lang = lang_result.segments[0].language
                persona = self._select_persona(first_seg_lang)

        return BilingualRoute(
            text=text,
            language=language_for_routing,
            persona=persona,
            stt_provider_key=persona.stt_provider_hint or "default",
            tts_provider_key=persona.tts_provider_hint or "default",
            segments=lang_result.segments if language_for_routing == Language.MIXED else None,
        )

    def persona_for_language(self, language: Language) -> VoicePersona:
        """Return the voice persona for a given language.

        Args:
            language: Target language.

        Returns:
            The configured ``VoicePersona`` for *language*, or the default
            persona if none is configured.
        """
        return self._select_persona(language)

    def register_persona(self, persona: VoicePersona) -> None:
        """Register or update a voice persona.

        Args:
            persona: The ``VoicePersona`` to register.
        """
        self._personas[persona.language] = persona

    def reset_stats(self) -> None:
        """Reset routing statistics."""
        self._stats = BilingualStats()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_persona(self, language: Language) -> VoicePersona:
        """Select the best voice persona for *language*.

        Prefers exact language match.  Falls back to EN personas if the
        requested language has no persona configured.
        """
        if language in self._personas:
            return self._personas[language]

        # Fallback to EN for unconfigured languages
        en_persona = self._personas.get(Language.EN)
        if en_persona:
            return en_persona

        # Final fallback: return a default persona
        return VoicePersona(
            language=language,
            voice_id="alloy",
            name=f"Default ({language.value})",
        )

    @staticmethod
    def _default_personas() -> dict[Language, VoicePersona]:
        """Create default voice personas for EN and VI."""
        return {
            Language.EN: VoicePersona(
                language=Language.EN,
                voice_id="alloy",
                name="Alloy (English)",
                stt_provider_hint="openai",
                tts_provider_hint="openai",
                speed=1.0,
                pitch=0.0,
            ),
            Language.VI: VoicePersona(
                language=Language.VI,
                voice_id="nova",
                name="Nova (Vietnamese)",
                stt_provider_hint="deepseek",
                tts_provider_hint="elevenlabs",
                speed=1.0,
                pitch=0.0,
                additional_settings={"language_hint": "vi"},
            ),
        }

    def detect_code_switching(
        self,
        text: str,
    ) -> tuple[list[LanguageSegment], Language]:
        """Detect code-switching segments in *text*.

        Useful for downstream processors that need to handle each language
        segment independently (e.g. applying per-language TTS).

        Args:
            text: The utterance text.

        Returns:
            A tuple of ``(segments, primary_language)``.
        """
        words = text.strip().split()
        primary_lang, segments = HeuristicLanguageDetector()._detect_code_switch(
            text, words
        )
        return segments, primary_lang
