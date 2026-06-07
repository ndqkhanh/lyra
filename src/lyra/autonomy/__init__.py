"""Autonomy module — continuous unattended operation with crash recovery.

Provides the continuous-operation loop that lets Lyra sessions run
without a terminal attached, managed by the supervisor daemon.
"""

from lyra.autonomy.loop import AutonomyLoop, LoopState, RunMode
from lyra.autonomy.recovery import CrashRecovery, RecoveryAction

__all__ = ["AutonomyLoop", "LoopState", "RunMode", "CrashRecovery", "RecoveryAction"]
