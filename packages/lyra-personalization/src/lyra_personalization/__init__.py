"""
Lyra Personalization System - User modeling and personalization for Lyra AGI.

Implements SAGER-inspired two-representation user models:
- Rich internal representation with complete user model
- Compact injection representation (~30-200 tokens)

And SPARK-inspired tripartite memory:
- Working memory (session-scoped)
- Episodic memory (recent interactions)
- Semantic memory (long-term knowledge)

With E2P + PerFit embedding-based personalization.
"""

from lyra_personalization.autonomy import (
    AutonomyController,
    EscalationRecord,
)
from lyra_personalization.embeddings import (
    EmbeddingManager,
    PrivacyBudget,
)
from lyra_personalization.memory import (
    MemoryEntry,
    TripartiteMemory,
)
from lyra_personalization.models import (
    AutonomyLevel,
    CommunicationStyle,
    CompactEmbedding,
    EpisodicMemory,
    InteractionRecord,
    RichRepresentation,
    SemanticMemory,
    SkillLevel,
    UserProfile,
    WorkingMemory,
)
from lyra_personalization.profile import UserProfileManager

__version__ = "0.1.0"

__all__ = [
    # Models
    "UserProfile",
    "RichRepresentation",
    "CompactEmbedding",
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "InteractionRecord",
    "SkillLevel",
    "AutonomyLevel",
    "CommunicationStyle",
    # Profile
    "UserProfileManager",
    # Embeddings
    "EmbeddingManager",
    "PrivacyBudget",
    # Memory
    "TripartiteMemory",
    "MemoryEntry",
    # Autonomy
    "AutonomyController",
    "EscalationRecord",
]
