"""
Socratic Questioning Module

Implements State-Challenge-Reflect protocol for exploratory research.
Based on Academic Research Skills repository best practices.
"""

from .devils_advocate import (
    AdvocateResult,
    ConcessionThreshold,
    DevilsAdvocateProtocol,
)
from .intent_detector import (
    Intent,
    IntentDetector,
)
from .socratic_agent import (
    Challenge,
    IntentType,
    SocraticDialogue,
    SocraticQuestioningAgent,
    UserState,
)

__all__ = [
    "SocraticQuestioningAgent",
    "SocraticDialogue",
    "IntentType",
    "UserState",
    "Challenge",
    "DevilsAdvocateProtocol",
    "AdvocateResult",
    "ConcessionThreshold",
    "IntentDetector",
    "Intent",
]
