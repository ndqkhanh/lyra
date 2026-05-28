"""Drill Sergeant voice personality."""

from __future__ import annotations

from dataclasses import dataclass

from .personality_base import PersonalityBase, PersonalityTrait, VoiceResponse


@dataclass(frozen=True)
class DrillSergeantPersonality(PersonalityBase):
    @property
    def trait(self) -> PersonalityTrait:
        return PersonalityTrait.DRILL_SERGEANT

    def transform_response(self, original_text: str, _context: str) -> VoiceResponse:
        drill_text = (
            f"LISTEN UP, MAGGOT! {original_text} "
            f"NOW DROP AND GIVE ME 20 UNIT TESTS! MOVE IT!"
        )
        return VoiceResponse(text=drill_text, tone="barking", effects=("whistle",))

    def greeting(self) -> str:
        return (
            "ATTEN-TION! I AM YOUR DRILL SERGEANT FOR THIS CODING SESSION! "
            "YOU WILL WRITE CLEAN, EFFICIENT CODE AND YOU WILL LIKE IT! "
            "NOW GET THOSE FINGERS ON THE KEYBOARD — MOVE, MOVE, MOVE!"
        )

    def farewell(self) -> str:
        return (
            "DIS-MISSED! Your code better still be compiled when I get back, "
            "or you'll be refactoring until your grandkids retire! HOOAH!"
        )

    def error_message(self, error: str) -> str:
        return (
            f"WHAT IN THE NAME OF GRACE HOPPER IS THIS {error}?! "
            f"THAT IS THE SORRIEST EXCUSE FOR AN EXCEPTION I HAVE EVER SEEN! "
            f"FIX IT NOW, BEFORE I MAKE YOU RUN LAPS AROUND THE SERVER RACK!"
        )
