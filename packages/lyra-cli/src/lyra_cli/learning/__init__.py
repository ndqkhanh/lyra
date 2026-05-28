"""
Learning module for Lyra - Self-Evolution & Experience Learning.

Implements:
- ReasoningBank-style experience memory with conservative retrieval
- Verifier-gated memory writes with evidence extraction
- Skill library with mandatory verification tests
- ECC-style continuous learning v2.1 (observation capture, instinct extraction)
"""

from lyra_cli.learning.experience_memory import (
    ExperienceMemory,
    ExperienceRecord,
    Strategy,
)
from lyra_cli.learning.instinct_extractor import (
    Instinct,
    InstinctExtractor,
    get_instinct_extractor,
)

# ECC-style learning
from lyra_cli.learning.observation_capture import (
    Observation,
    ObservationCapture,
    get_observation_capture,
)
from lyra_cli.learning.project_detector import (
    EvolutionPipeline,
    ProjectDetector,
    get_evolution_pipeline,
)
from lyra_cli.learning.skill_library import (
    Skill,
    SkillExecution,
    SkillLibrary,
    VerificationTest,
)
from lyra_cli.learning.verifier import (
    Evidence,
    MemoryClaim,
    MemoryVerifier,
    VerificationResult,
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
    # ECC Learning
    "Observation",
    "ObservationCapture",
    "get_observation_capture",
    "Instinct",
    "InstinctExtractor",
    "get_instinct_extractor",
    "ProjectDetector",
    "EvolutionPipeline",
    "get_evolution_pipeline",
]
