"""Butler voice personality."""

from __future__ import annotations

from dataclasses import dataclass

from .personality_base import PersonalityBase, PersonalityTrait, VoiceResponse


@dataclass(frozen=True)
class ButlerPersonality(PersonalityBase):
    @property
    def trait(self) -> PersonalityTrait:
        return PersonalityTrait.BUTLER

    def transform_response(self, original_text: str, _context: str) -> VoiceResponse:
        butler_text = (
            f"Very good, sir. {original_text} "
            f"Shall I prepare anything else for your review?"
        )
        return VoiceResponse(text=butler_text, tone="dignified", effects=("chime",))

    def greeting(self) -> str:
        return (
            "Good day, sir. Your development environment has been prepared "
            "and all dependencies are in order. How may I be of service?"
        )

    def farewell(self) -> str:
        return (
            "Until next time, sir. I shall keep your repository in pristine "
            "condition in your absence. Do take care."
        )

    def error_message(self, error: str) -> str:
        return (
            f"I do beg your pardon, sir, but we seem to have encountered "
            f"a rather troubling issue: {error}. I shall investigate posthaste."
        )
