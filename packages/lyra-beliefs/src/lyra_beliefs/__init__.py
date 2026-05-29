"""Lyra Beliefs — Domain knowledge and belief management.

A Belief is what the agent KNOWS (domain knowledge, patterns, conventions).
A Skill is what the agent DOES (actions, tools, workflows).
This separation enables targeted evolution: evolve knowledge independently of actions.

Supports:
- Bayesian, Jeffrey's rule, and AGM belief updates
- Knowledge base with facts, rules, and ontology
- Deductive, inductive, abductive, and default inference
- Contradiction detection and resolution
- Source reliability tracking and consensus building
"""

from __future__ import annotations

from .belief_system import (
    Belief,
    BeliefSet,
    BeliefSource,
    BeliefStatus,
    BeliefSystem,
    ConditionalProbability,
    UpdateMethod,
)
from .consistency import (
    ConsistencyManager,
    Contradiction,
    InconsistentSubset,
    ResolutionStrategy,
)
from .exceptions import (
    BeliefError,
    BeliefNotFoundError,
    InconsistentBeliefError,
    InferenceError,
    KnowledgeBaseError,
    RevisionError,
    SourceReliabilityError,
    UpdateError,
)
from .inference import (
    InferenceEngine,
    InferenceResult,
    InferenceType,
)
from .knowledge_base import (
    Fact,
    KnowledgeBase,
    KnowledgeVersion,
    OntologyConcept,
    Rule,
    RuleType,
)
from .updating import (
    BeliefUpdater,
    ConsensusResult,
    EvidencePacket,
    SourceProfile,
)

__all__ = [
    # Belief system
    "BeliefSource",
    "BeliefStatus",
    "UpdateMethod",
    "Belief",
    "BeliefSet",
    "ConditionalProbability",
    "BeliefSystem",
    # Knowledge base
    "RuleType",
    "Rule",
    "Fact",
    "OntologyConcept",
    "KnowledgeVersion",
    "KnowledgeBase",
    # Inference
    "InferenceType",
    "InferenceResult",
    "InferenceEngine",
    # Consistency
    "Contradiction",
    "InconsistentSubset",
    "ResolutionStrategy",
    "ConsistencyManager",
    # Updating
    "SourceProfile",
    "EvidencePacket",
    "ConsensusResult",
    "BeliefUpdater",
    # Exceptions
    "BeliefError",
    "BeliefNotFoundError",
    "InconsistentBeliefError",
    "InferenceError",
    "KnowledgeBaseError",
    "UpdateError",
    "RevisionError",
    "SourceReliabilityError",
]
