"""harness_core.continuous_learning — learn from user edits to agent output.

When a user edits something the agent produced, the edit is the gradient
signal: it tells you what the agent should have done. Recording these
(agent_output, user_edit) pairs and extracting patterns from them is the
PRELUDE / CIPHER pattern — durable preference learning without explicit
labels.

Pipeline:

    1. :class:`EditRecorder` captures pairs as :class:`EditEvent` records.
    2. :class:`PreferenceExtractor` distills :class:`LearnedPreference`
       records from edits. The built-in :class:`HeuristicExtractor`
       detects length / vocabulary / tone / structure preferences with
       deterministic rules; production wires LLM-backed extractors
       through the same Protocol.
    3. :class:`ContinuousLearner` orchestrates: applies the extractor,
       writes preferences as PROCEDURAL :class:`MemoryItem` (namespace
       = user_id), and optionally emits witnesses.

Used by Orion-Code (per-user code-style preferences), Mentat-Learn
(per-channel writing-style learning), Polaris (research-output style),
Lyra (architecture-doc style preferences).
"""
from __future__ import annotations

from .extractor import HeuristicExtractor
from .learner import ContinuousLearner
from .recorder import EditRecorder
from .types import (
    EditEvent,
    LearnedPreference,
    LearningReport,
    PreferenceExtractor,
)

__all__ = [
    "ContinuousLearner",
    "EditEvent",
    "EditRecorder",
    "HeuristicExtractor",
    "LearnedPreference",
    "LearningReport",
    "PreferenceExtractor",
]
