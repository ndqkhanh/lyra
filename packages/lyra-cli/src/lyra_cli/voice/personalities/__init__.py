"""Voice personality system — transforms agent responses with character traits."""

from .butler import ButlerPersonality
from .cowboy import CowboyPersonality
from .drill_sergeant import DrillSergeantPersonality
from .personality_base import PersonalityBase, PersonalityTrait, VoiceResponse
from .pirate import PiratePersonality
from .robot import RobotPersonality
from .zen_master import ZenMasterPersonality

__all__ = [
    "PersonalityBase",
    "PersonalityTrait",
    "VoiceResponse",
    "PiratePersonality",
    "RobotPersonality",
    "ButlerPersonality",
    "CowboyPersonality",
    "ZenMasterPersonality",
    "DrillSergeantPersonality",
]
