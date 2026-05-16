"""
Learning module for Lyra - Self-Evolution & Experience Learning.

Implements:
- ReasoningBank-style experience memory with conservative retrieval
- Verifier-gated memory writes with evidence extraction
- Skill library with mandatory verification tests
"""

from lyra_cli.learning.experience_memory import (
    Strategy,
    ExperienceRecord,
    ExperienceMemory,
)

from lyra_cli.learning.verifier import (
    Evidence,
    MemoryClaim,
    VerificationResult,
    MemoryVerifier,
)

from lyra_cli.learning.skill_library import (
    VerificationTest,
    SkillExecution,
    Skill,
    SkillLibrary,
)

__all__ = [
    # Experience Memory
    "Strategy",
    "ExperienceRecord",
    "ExperienceMemory",
    # Verifier
    "Evidence",
    "MemoryClaim",
    "VerificationResult",
    "MemoryVerifier",
    # Skill Library
    "VerificationTest",
    "SkillExecution",
    "Skill",
    "SkillLibrary",
]
