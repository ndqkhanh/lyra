"""Abstract base class for voice personalities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class PersonalityTrait(StrEnum):
    PIRATE = "pirate"
    ROBOT = "robot"
    BUTLER = "butler"
    COWBOY = "cowboy"
    ZEN_MASTER = "zen_master"
    DRILL_SERGEANT = "drill_sergeant"
    WARCRAFT3_PEON = "warcraft3_peon"


@dataclass(frozen=True)
class VoiceResponse:
    text: str
    tone: str
    effects: tuple[str, ...] = ()


class PersonalityBase(ABC):
    """Base class for voice personality transformations."""

    @property
    @abstractmethod
    def trait(self) -> PersonalityTrait: ...

    @abstractmethod
    def transform_response(self, original_text: str, context: str) -> VoiceResponse: ...

    @abstractmethod
    def greeting(self) -> str: ...

    @abstractmethod
    def farewell(self) -> str: ...

    def error_message(self, error: str) -> str:
        return f"An error occurred: {error}"
