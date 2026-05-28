"""Memory abstraction layer — distills concrete episodes into generalized knowledge."""

from lyra_memory.abstraction.concept_abstractor import (
    AbstractConcept,
    AbstractionLevel,
    ConceptAbstractor,
)
from lyra_memory.abstraction.pattern_recognizer import (
    CrossEpisodePattern,
    PatternRecognizer,
)

__all__ = [
    "AbstractConcept",
    "AbstractionLevel",
    "ConceptAbstractor",
    "CrossEpisodePattern",
    "PatternRecognizer",
]
