"""
Lyra Multimodal - Voice and vision capabilities.

This package provides:
- Vision analysis for images and screenshots
- Speech-to-text (STT)
- Text-to-speech (TTS)
- Voice command recognition
"""

from lyra_multimodal.vision import ImageType, VisionAnalysis, VisionAnalyzer
from lyra_multimodal.voice import (
    SynthesisResult,
    TranscriptionResult,
    VoiceEngine,
    VoiceInterface,
)

__version__ = "0.1.0"

__all__ = [
    # Vision
    "VisionAnalyzer",
    "VisionAnalysis",
    "ImageType",
    # Voice
    "VoiceInterface",
    "VoiceEngine",
    "TranscriptionResult",
    "SynthesisResult",
]
