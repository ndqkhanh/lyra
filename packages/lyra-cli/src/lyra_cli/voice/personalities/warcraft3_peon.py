"""Warcraft III Peon voice personality."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .personality_base import PersonalityBase, PersonalityTrait, VoiceResponse


_STARTUP_LINES = (
    "Zug zug! Ready to work!",
    "Work, work!",
    "Something need doing?",
)

_TASK_START_LINES = (
    "Job's done!",
)

_TASK_COMPLETE_LINES = (
    "Work complete!",
    "More work?",
)

_ERROR_LINES = (
    "I'm not ready!",
    "Me not that kind of orc!",
)

_WAKE_LINES = (
    "Yesh, milord?",
    "What you want?",
)

_SLEEP_LINES = (
    "I need sleep...",
)

_COST_WARNING_LINES = (
    "Not enough gold!",
    "We need more gold!",
)

_AGENT_SPAWN_LINES = (
    "Ready to work!",
)


@dataclass(frozen=True)
class Warcraft3PeonPersonality(PersonalityBase):
    """Warcraft III peon-themed voice personality for agent events."""

    name: str = "Warcraft III Peon"
    theme: str = "warcraft3"
    icon: str = "\U0001fa97"

    _response_map: dict[str, tuple[str, ...]] = field(default_factory=lambda: {
        "startup": _STARTUP_LINES,
        "task_start": _TASK_START_LINES,
        "task_complete": _TASK_COMPLETE_LINES,
        "error": _ERROR_LINES,
        "wake": _WAKE_LINES,
        "sleep": _SLEEP_LINES,
        "cost_warning": _COST_WARNING_LINES,
        "agent_spawn": _AGENT_SPAWN_LINES,
    }, compare=False, hash=False)

    @property
    def trait(self) -> PersonalityTrait:
        return PersonalityTrait.WARCRAFT3_PEON

    def transform_response(self, original_text: str, context: str) -> VoiceResponse:
        peon_text = (
            f"Work work! {original_text} "
            f"Something need doing?"
        )
        return VoiceResponse(text=peon_text, tone="gruff", effects=("grunt",))

    def greeting(self) -> str:
        return "Zug zug! Ready to work!"

    def farewell(self) -> str:
        return "Me going now. Zug zug!"

    def error_message(self, error: str) -> str:
        lines = _ERROR_LINES
        line = random.choice(lines)
        return f"{line} {error}"

    def get_response(self, trait: PersonalityTrait, context: dict) -> VoiceResponse:
        """Get an event-specific peon voice response.

        Parameters
        ----------
        trait : PersonalityTrait
            The personality trait (must match WARCRAFT3_PEON).
        context : dict
            Must contain an ``event`` key (e.g. ``"startup"``, ``"task_complete"``).
            Optional keys: ``"detail"`` for additional context.

        Returns
        -------
        VoiceResponse
            A peon voice line matching the event.
        """
        event = context.get("event", "startup")
        lines = self._response_map.get(event, _STARTUP_LINES)
        line = random.choice(lines)
        return VoiceResponse(text=line, tone="gruff", effects=("grunt",))
