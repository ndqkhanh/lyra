"""Voice personality system — transforms agent responses with character traits."""

from .personality_base import PersonalityBase, PersonalityTrait, VoiceResponse
from .pirate import PiratePersonality
from .robot import RobotPersonality
from .butler import ButlerPersonality
from .cowboy import CowboyPersonality
from .zen_master import ZenMasterPersonality
from .drill_sergeant import DrillSergeantPersonality

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
