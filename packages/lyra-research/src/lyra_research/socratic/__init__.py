"""
Socratic Questioning Module

Implements State-Challenge-Reflect protocol for exploratory research.
Based on Academic Research Skills repository best practices.
"""

from .socratic_agent import (
    SocraticQuestioningAgent,
    SocraticDialogue,
    IntentType,
    UserState,
    Challenge,
)
from .devils_advocate import (
    DevilsAdvocateProtocol,
    AdvocateResult,
    ConcessionThreshold,
)
from .intent_detector import (
    IntentDetector,
    Intent,
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
