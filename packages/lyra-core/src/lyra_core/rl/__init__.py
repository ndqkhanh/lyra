"""RL / Atropos trajectory tooling (hermes parity).

This module scaffolds the integration surface for the Tinker-Atropos
RL training pipeline. Actual trajectory API / GRPO wiring is deferred
to v1.8 Phase 20; the interface here (``TrajectoryRecorder``,
``RLEnvironment``, ``rl_list_environments`` tool) is what the agent
turn-loop and the LLM-facing ``rl_*`` tools bind against.

Reference: ``hermes-agent/website/docs/user-guide/features/rl-training.md``.
"""
from __future__ import annotations

from .trajectory import (
    RLEnvironment,
    RLTrajectoryError,
    TrajectoryRecord,
    TrajectoryRecorder,
    make_rl_list_environments_tool,
)

__all__ = [
    "RLEnvironment",
    "RLTrajectoryError",
    "TrajectoryRecord",
    "TrajectoryRecorder",
    "make_rl_list_environments_tool",
]
