"""
Lyra Omni-Domain Specialization — Expert Card System & Domain Routing.

5-Layer Architecture:
  Layer 1 — Domain Router (router.py) — classifies task domain
  Layer 2 — Expert Card System (experts.py) — loads domain identity + knowledge
  Layer 3 — Generalist Foundation — shared reasoning across domains
  Layer 4 — Specialist Execution (validation.py) — domain-specific tools + validation
  Layer 5 — Memory & Knowledge Transfer (fusion.py) — cross-domain learning

Design principles:
  - Frozen dataclasses, full type annotations, production-quality
  - Structural constraints over LLM instructions for enforcement
  - Domain-specific disclaimers for regulated domains
  - Cross-domain knowledge transfer with confidence scoring
"""

from lyra_domain.experts import ExpertRegistry
from lyra_domain.fusion import CrossDomainFusion
from lyra_domain.models import (
    Capability,
    ComplexityLevel,
    CrossDomainMapping,
    DomainClassification,
    DomainType,
    ExpertCard,
    KnowledgeCategory,
    KnowledgeSource,
    MultiDomainResult,
    ValidationMethod,
)
from lyra_domain.router import DomainRouter
from lyra_domain.validation import DomainValidator

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Layer 0 — Models
    "DomainType",
    "ExpertCard",
    "DomainClassification",
    "MultiDomainResult",
    "KnowledgeSource",
    "KnowledgeCategory",
    "Capability",
    "CrossDomainMapping",
    "ComplexityLevel",
    "ValidationMethod",
    # Layer 1 — Router
    "DomainRouter",
    # Layer 2 — Registry
    "ExpertRegistry",
    # Layer 4 — Validation
    "DomainValidator",
    # Layer 5 — Fusion
    "CrossDomainFusion",
]
