"""
PRISMA Module

Implements PRISMA-trAIce compliance checking and risk-of-bias assessment
for systematic reviews.
"""

from .prisma_checker import (
    PRISMAComplianceChecker,
    PRISMAResult,
    PRISMAItem,
    PRISMAItemResult,
)
from .bias_assessor import (
    RiskOfBiasAssessor,
    BiasAssessment,
    BiasDomain,
    RiskLevel,
    DomainAssessment,
)

__all__ = [
    "PRISMAComplianceChecker",
    "PRISMAResult",
    "PRISMAItem",
    "PRISMAItemResult",
    "RiskOfBiasAssessor",
    "BiasAssessment",
    "BiasDomain",
    "RiskLevel",
    "DomainAssessment",
]
