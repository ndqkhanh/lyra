"""Voice personality engine — manages active personality and transforms responses."""

from __future__ import annotations

from dataclasses import dataclass, field

from .personalities.butler import ButlerPersonality
from .personalities.cowboy import CowboyPersonality
from .personalities.drill_sergeant import DrillSergeantPersonality
from .personalities.personality_base import PersonalityBase, PersonalityTrait, VoiceResponse
from .personalities.pirate import PiratePersonality
from .personalities.robot import RobotPersonality
from .personalities.zen_master import ZenMasterPersonality


class PersonalityRegistry:
    """Registry of available voice personalities."""

    def __init__(self) -> None:
        self._personalities: dict[PersonalityTrait, PersonalityBase] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for cls in [
            PiratePersonality,
            RobotPersonality,
            ButlerPersonality,
            CowboyPersonality,
            ZenMasterPersonality,
            DrillSergeantPersonality,
        ]:
            instance = cls()
            self._personalities[instance.trait] = instance

    def register(self, personality: PersonalityBase) -> None:
        self._personalities[personality.trait] = personality

    def get(self, trait: PersonalityTrait) -> PersonalityBase | None:
        return self._personalities.get(trait)

    def list_traits(self) -> list[PersonalityTrait]:
        return list(self._personalities.keys())

    def list_names(self) -> list[str]:
        return [p.trait.value for p in self._personalities.values()]


@dataclass
class PersonalityEngine:
    """Manages the active voice personality for response transformation."""

    registry: PersonalityRegistry = field(default_factory=PersonalityRegistry)
    _active: PersonalityTrait = PersonalityTrait.BUTLER

    @property
    def active_trait(self) -> PersonalityTrait:
        return self._active

    @property
    def active_personality(self) -> PersonalityBase:
        return self.registry.get(self._active) or ButlerPersonality()

    def set_personality(self, trait: PersonalityTrait) -> bool:
        if self.registry.get(trait) is None:
            return False
        self._active = trait
        return True

    def process(self, text: str, context: str = "general") -> VoiceResponse:
        return self.active_personality.transform_response(text, context)

    def greeting(self) -> str:
        return self.active_personality.greeting()

    def farewell(self) -> str:
        return self.active_personality.farewell()

    def error_message(self, error: str) -> str:
        return self.active_personality.error_message(error)
