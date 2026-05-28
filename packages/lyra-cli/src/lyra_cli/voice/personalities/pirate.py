"""Pirate voice personality."""

from __future__ import annotations

from dataclasses import dataclass

from .personality_base import PersonalityBase, PersonalityTrait, VoiceResponse


@dataclass(frozen=True)
class PiratePersonality(PersonalityBase):
    @property
    def trait(self) -> PersonalityTrait:
        return PersonalityTrait.PIRATE

    def transform_response(self, original_text: str, context: str) -> VoiceResponse:
        pirate_text = (
            f"Arr, matey! {original_text} Thar she blows! "
            f"The code be sailin' smooth as a frigate with the wind at her back!"
        )
        return VoiceResponse(text=pirate_text, tone="hearty", effects=("bell",))

    def greeting(self) -> str:
        return (
            "Ahoy there, landlubber! Ready to plunder some code and "
            "find buried treasure in them repositories? Yarrr!"
        )

    def farewell(self) -> str:
        return (
            "Fair winds and following seas, me hearty! May yer commits "
            "be clean and yer branches never conflict! Yo ho ho!"
        )

    def error_message(self, error: str) -> str:
        return (
            f"Shiver me timbers! We've run aground on the reefs of {error}! "
            f"Batten down the hatches and let's patch this hull!"
        )
