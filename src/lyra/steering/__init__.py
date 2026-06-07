"""Steering module — human-in-the-loop interrupt, redirect, and approval.

Provides the steer-by-exception interface: peek, reply, approve, redirect
running agents without restarting them. Integrates with the supervisor daemon's
fleet view for multi-session steering.

Also provides preference learning, trust calibration, and identity-anonymized
steering for adaptive human-AI collaboration.
"""

from lyra.steering.panel import SteerPanel, SteerAction, ApprovalGate
from lyra.steering.interrupt import InterruptHandler, InterruptSignal
from lyra.steering.preference_learner import (
    PreferenceLearner,
    ProactiveElicitation,
    DecoupledRewind,
    IdentityAnonymizedSteering,
)
from lyra.steering.trust_calibrator import TrustCalibrator

__all__ = [
    "SteerPanel", "SteerAction", "ApprovalGate",
    "InterruptHandler", "InterruptSignal",
    "PreferenceLearner",
    "ProactiveElicitation",
    "DecoupledRewind",
    "IdentityAnonymizedSteering",
    "TrustCalibrator",
]
