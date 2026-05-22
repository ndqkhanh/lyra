"""Emotional Intelligence — emotion recognition, expression calibration, adaptive empathy."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)
__all__ = ["EmotionState", "EmotionEngine"]

EMOTIONS = ["anger", "fear", "joy", "sadness", "surprise", "disgust", "trust", "anticipation", "neutral"]

@dataclass
class EmotionState:
    primary: str = "neutral"; intensity: float = 0.5; valence: float = 0.0

class EmotionEngine:
    def __init__(self):
        self._state = EmotionState()

    def recognize(self, text: str) -> EmotionState:
        text_lower = text.lower()
        if any(w in text_lower for w in ["angry", "furious", "annoyed"]):
            self._state = EmotionState("anger", 0.8, -0.8)
        elif any(w in text_lower for w in ["happy", "great", "wonderful", "love"]):
            self._state = EmotionState("joy", 0.7, 0.9)
        elif any(w in text_lower for w in ["sad", "sorry", "unfortunate", "miss"]):
            self._state = EmotionState("sadness", 0.6, -0.6)
        elif any(w in text_lower for w in ["fear", "worried", "afraid", "scared"]):
            self._state = EmotionState("fear", 0.7, -0.7)
        return self._state

    def calibrate_response(self, user_emotion: EmotionState) -> dict:
        tone_map = {"anger": "calm", "fear": "reassuring", "joy": "enthusiastic", "sadness": "gentle", "neutral": "neutral"}
        return {"suggested_tone": tone_map.get(user_emotion.primary, "neutral"), "empathy_level": min(1.0, abs(user_emotion.valence) + 0.3), "response_length": "concise" if user_emotion.primary in ["anger", "fear"] else "normal"}

    @property
    def state(self) -> EmotionState: return self._state
