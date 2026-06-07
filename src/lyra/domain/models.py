"""
Domain data models for Lyra AGI Omni-Domain Specialization.

Frozen dataclasses representing Expert Cards, domain classifications,
knowledge sources, capabilities, and cross-domain mappings across all
9 domain specializations.
"""

from __future__ import annotations

import datetime
import enum
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class DomainType(enum.Enum):
    """Specialized knowledge domains supported by Lyra AGI."""
    CODING = "coding"
    FINANCE = "finance"
    MEDICAL = "medical"
    LEGAL = "legal"
    SCIENTIFIC = "scientific"
    EDUCATION = "education"
    ENGINEERING = "engineering"
    CREATIVE = "creative"
    BUSINESS = "business"


class KnowledgeCategory(enum.Enum):
    """Classification for knowledge sources within a domain."""
    PRIMARY_LITERATURE = "primary_literature"
    REFERENCE_MANUAL = "reference_manual"
    REGULATORY_FRAMEWORK = "regulatory_framework"
    CASE_STUDY = "case_study"
    BEST_PRACTICE = "best_practice"
    TOOL_DOCUMENTATION = "tool_documentation"
    COMMUNITY_KNOWLEDGE = "community_knowledge"
    HISTORICAL_DATA = "historical_data"


class ComplexityLevel(enum.Enum):
    """Estimated complexity of a domain task."""
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"
    EXTREME = "extreme"


class ValidationMethod(enum.Enum):
    """How domain output should be validated."""
    STATIC_ANALYSIS = "static_analysis"
    TEST_SUITE = "test_suite"
    EXPERT_REVIEW = "expert_review"
    COMPLIANCE_CHECK = "compliance_check"
    EMPIRICAL_VALIDATION = "empirical_validation"
    PEER_REVIEW = "peer_review"
    FORMAL_VERIFICATION = "formal_verification"


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeSource:
    """A curated, trusted source of domain knowledge."""
    title: str
    url: str = ""
    credibility_score: float = 0.8  # 0.0 to 1.0
    last_updated: datetime.datetime = field(default_factory=datetime.datetime.now)
    category: KnowledgeCategory = KnowledgeCategory.PRIMARY_LITERATURE

    def __post_init__(self) -> None:
        if not 0.0 <= self.credibility_score <= 1.0:
            raise ValueError(
                f"credibility_score must be in [0, 1], got {self.credibility_score}"
            )


@dataclass(frozen=True)
class Capability:
    """A specific capability within a domain expert's repertoire."""
    name: str
    description: str
    tools_required: tuple[str, ...] = field(default_factory=tuple)
    validation_method: ValidationMethod = ValidationMethod.EXPERT_REVIEW


@dataclass(frozen=True)
class ExpertCard:
    """Complete identity and knowledge card for a domain expert.

    Six-component architecture:
      1. Identity & Role — who the expert is
      2. Guiding Principles — what rules they follow
      3. Core Capabilities — what they can do
      4. Foundational Knowledge Base — curated trusted sources
      5. User Context — how they interact with the user
      6. Activation Command — when to activate this expert
    """
    # Component 1: Identity & Role
    identity: str
    role: str

    # Component 2: Guiding Principles
    guiding_principles: tuple[str, ...] = field(default_factory=tuple)

    # Component 3: Core Capabilities
    capabilities: tuple[Capability, ...] = field(default_factory=tuple)

    # Component 4: Foundational Knowledge Base
    knowledge_base: tuple[KnowledgeSource, ...] = field(default_factory=tuple)

    # Component 5: User Context
    user_context: str = ""
    interaction_style: str = "professional"

    # Component 6: Activation Command
    activation_command: str = ""
    domain: DomainType = DomainType.CODING

    # Metadata
    version: str = "0.1.0"
    model_preference: str = ""
    disclaimer: str = ""
    max_tokens_recommended: int = 4096
    temperature_recommended: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.temperature_recommended <= 2.0:
            raise ValueError(
                f"temperature_recommended must be in [0, 2], "
                f"got {self.temperature_recommended}"
            )


@dataclass(frozen=True)
class DomainClassification:
    """Result of classifying a task into a domain."""
    domain_type: DomainType
    confidence: float = 0.5  # 0.0 to 1.0
    subdomain: str = ""
    complexity: ComplexityLevel = ComplexityLevel.MODERATE
    reasoning: str = ""
    keywords: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )


@dataclass(frozen=True)
class MultiDomainResult:
    """Result when a task spans multiple domains."""
    primary: DomainClassification
    secondary: tuple[DomainClassification, ...] = field(default_factory=tuple)
    requires_fusion: bool = False
    fusion_strategy: str = "sequential"


@dataclass(frozen=True)
class CrossDomainMapping:
    """Maps transferable knowledge between two domains."""
    source_domain: DomainType
    target_domain: DomainType
    transferable_knowledge: str
    adaptation_required: str = ""
    confidence: float = 0.5
    analogies: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )
