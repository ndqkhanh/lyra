"""Rule metadata models."""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class RuleCategory(Enum):
    """Rule categories."""
    CODING_STANDARDS = "coding-standards"
    TESTING = "testing"
    SECURITY = "security"
    PERFORMANCE = "performance"
    GIT_WORKFLOW = "git-workflow"
    DOCUMENTATION = "documentation"


class RuleSeverity(Enum):
    """Rule severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RuleMetadata:
    """Metadata for a rule."""

    name: str
    description: str
    category: RuleCategory
    severity: RuleSeverity
    enabled: bool = True
    file_path: Optional[str] = None
