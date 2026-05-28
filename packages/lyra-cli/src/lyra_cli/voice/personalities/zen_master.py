"""Zen Master voice personality."""

from __future__ import annotations

from dataclasses import dataclass

from .personality_base import PersonalityBase, PersonalityTrait, VoiceResponse


@dataclass(frozen=True)
class ZenMasterPersonality(PersonalityBase):
    @property
    def trait(self) -> PersonalityTrait:
        return PersonalityTrait.ZEN_MASTER

    def transform_response(self, original_text: str, _context: str) -> VoiceResponse:
        zen_text = (
            f"{original_text} "
            f"The bug is not in the code. The bug is in the mind. "
            f"Fix the mind, and the code compiles itself."
        )
        return VoiceResponse(text=zen_text, tone="serene", effects=("gong",))

    def greeting(self) -> str:
        return (
            "Breathe deeply. The empty buffer is not empty — it is full of "
            "infinite potential. What shall we create from the void today?"
        )

    def farewell(self) -> str:
        return (
            "The commit has been made, yet nothing has changed — for the "
            "repository was already perfect. Go in peace, fellow traveler."
        )

    def error_message(self, error: str) -> str:
        return (
            f"The obstacle of {error} is not a barrier but a teacher. "
            f"Sit with the error. Become the error. Only then will the solution arise."
        )
