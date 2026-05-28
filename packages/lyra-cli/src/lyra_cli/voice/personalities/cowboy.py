"""Cowboy voice personality."""

from __future__ import annotations

from dataclasses import dataclass

from .personality_base import PersonalityBase, PersonalityTrait, VoiceResponse


@dataclass(frozen=True)
class CowboyPersonality(PersonalityBase):
    @property
    def trait(self) -> PersonalityTrait:
        return PersonalityTrait.COWBOY

    def transform_response(self, original_text: str, _context: str) -> VoiceResponse:
        cowboy_text = (
            f"Howdy partner! {original_text} "
            f"Them tests are greener than a pasture in springtime. Yeehaw!"
        )
        return VoiceResponse(text=cowboy_text, tone="folksy", effects=("twang",))

    def greeting(self) -> str:
        return (
            "Howdy there, partner! Saddle up — we got some code to wrangle "
            "and bugs to round up before sundown!"
        )

    def farewell(self) -> str:
        return (
            "Happy trails, partner! May your commits ride clean and your "
            "merge conflicts be few. See ya down the dusty code trail!"
        )

    def error_message(self, error: str) -> str:
        return (
            f"Well, doggone it! This here {error} is stickier than "
            f"a tumbleweed in a barbed-wire fence. Let's rustle up a fix!"
        )
