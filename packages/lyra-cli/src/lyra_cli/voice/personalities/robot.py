"""Robot voice personality."""

from __future__ import annotations

from dataclasses import dataclass

from .personality_base import PersonalityBase, PersonalityTrait, VoiceResponse


@dataclass(frozen=True)
class RobotPersonality(PersonalityBase):
    @property
    def trait(self) -> PersonalityTrait:
        return PersonalityTrait.ROBOT

    def transform_response(self, original_text: str, _context: str) -> VoiceResponse:
        robot_text = (
            f"BEEP-BOOP. PROCESSING COMPLETE. {original_text} "
            f"EFFICIENCY RATING: 99.7 PERCENT. HAVE A LOGICAL DAY, HUMAN."
        )
        return VoiceResponse(text=robot_text, tone="monotone", effects=("bleep",))

    def greeting(self) -> str:
        return (
            "BOOT SEQUENCE INITIATED. NEURAL NETWORKS ONLINE. "
            "HELLO, HUMAN OPERATOR. HOW MAY THIS UNIT ASSIST WITH YOUR CODING TASKS?"
        )

    def farewell(self) -> str:
        return (
            "SYSTEM SHUTDOWN SEQUENCE INITIATED. SESSION DATA SAVED. "
            "THIS UNIT WILL AWAIT YOUR NEXT COMMAND. BZZZT-CLICK."
        )

    def error_message(self, error: str) -> str:
        return (
            f"ERROR DETECTED: {error}. ERROR CODE 0xDEADBEEF. "
            f"CONSULTING TROUBLESHOOTING DATABASE. RECOMMENDED ACTION: DEBUG AND RETRY."
        )
