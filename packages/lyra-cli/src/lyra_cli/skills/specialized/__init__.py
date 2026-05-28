"""
Specialized Skills Index

This module provides 20+ specialized skills across multiple domains:
- Engineering (5 skills)
- Design (2 skills)
- SRE (1 skill)
- AI Research (1 skill)
- Solution Architecture (1 skill)
- Cloud Engineering (1 skill)
- Product Management (1 skill)
- Business Analysis (1 skill)
- Brainstorming (1 skill)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class SkillMetadata:
    """Metadata for a specialized skill."""

    name: str
    description: str
    tags: list[str]
    triggers: list[str]
    model: str
    file_path: Path
    domain: str


class SpecializedSkillsRegistry:
    """Registry for all specialized skills."""

    def __init__(self):
        self.skills_dir = Path(__file__).parent
        self._skills: dict[str, SkillMetadata] = {}
        self._load_skills()

    def _load_skills(self):
        """Load all specialized skills from subdirectories."""
        domains = {
            "engineering": [
                "backend.md",
                "frontend.md",
                "testing.md",
                "devops.md",
                "fullstack.md",
            ],
            "design": [
                "ui_ux.md",
                "system_design.md",
            ],
            "sre": [
                "reliability.md",
            ],
            "ai_research": [
                "research_methodology.md",
            ],
            "solution_architecture": [
                "solution_design.md",
            ],
            "cloud_engineering": [
                "cloud_architecture.md",
            ],
            "product_management": [
                "product_strategy.md",
            ],
            "business_analysis": [
                "requirements_analysis.md",
            ],
            "brainstorming": [
                "creative_thinking.md",
            ],
        }

        for domain, files in domains.items():
            domain_dir = self.skills_dir / domain
            if not domain_dir.exists():
                continue

            for file_name in files:
                file_path = domain_dir / file_name
                if file_path.exists():
                    metadata = self._parse_skill_metadata(file_path, domain)
                    if metadata:
                        self._skills[metadata.name] = metadata

    def _parse_skill_metadata(self, file_path: Path, domain: str) -> SkillMetadata:
        """Parse skill metadata from markdown file."""
        try:
            content = file_path.read_text()

            # Extract YAML frontmatter
            if not content.startswith("---"):
                return None

            end_idx = content.find("---", 3)
            if end_idx == -1:
                return None

            frontmatter = content[3:end_idx].strip()

            # Parse frontmatter
            metadata = {}
            for line in frontmatter.split("\n"):
                if ":" not in line:
                    continue

                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"')

                # Handle lists
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip().strip('"') for v in value[1:-1].split(",")]

                metadata[key] = value

            return SkillMetadata(
                name=metadata.get("name", file_path.stem),
                description=metadata.get("description", ""),
                tags=metadata.get("tags", []),
                triggers=metadata.get("triggers", []),
                model=metadata.get("model", "sonnet"),
                file_path=file_path,
                domain=domain,
            )
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def get_skill(self, name: str) -> SkillMetadata:
        """Get skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[SkillMetadata]:
        """List all skills."""
        return list(self._skills.values())

    def list_by_domain(self, domain: str) -> list[SkillMetadata]:
        """List skills by domain."""
        return [s for s in self._skills.values() if s.domain == domain]

    def search_by_trigger(self, trigger: str) -> list[SkillMetadata]:
        """Search skills by trigger keyword."""
        trigger_lower = trigger.lower()
        return [
            s for s in self._skills.values()
            if any(trigger_lower in t.lower() for t in s.triggers)
        ]

    def search_by_tag(self, tag: str) -> list[SkillMetadata]:
        """Search skills by tag."""
        tag_lower = tag.lower()
        return [
            s for s in self._skills.values()
            if any(tag_lower in t.lower() for t in s.tags)
        ]

    def get_skill_content(self, name: str) -> str:
        """Get full skill content."""
        skill = self.get_skill(name)
        if not skill:
            return None

        return skill.file_path.read_text()


# Global registry instance
_registry = None


def get_registry() -> SpecializedSkillsRegistry:
    """Get the global skills registry."""
    global _registry
    if _registry is None:
        _registry = SpecializedSkillsRegistry()
    return _registry


def list_all_skills() -> list[str]:
    """List all skill names."""
    registry = get_registry()
    return [s.name for s in registry.list_skills()]


def get_skill_by_name(name: str) -> SkillMetadata:
    """Get skill metadata by name."""
    registry = get_registry()
    return registry.get_skill(name)


def search_skills(query: str) -> list[SkillMetadata]:
    """Search skills by trigger or tag."""
    registry = get_registry()
    trigger_results = registry.search_by_trigger(query)
    tag_results = registry.search_by_tag(query)

    # Combine and deduplicate
    seen = set()
    results = []
    for skill in trigger_results + tag_results:
        if skill.name not in seen:
            seen.add(skill.name)
            results.append(skill)

    return results


# ---------------------------------------------------------------------------
# Executable specialized skills (Python-based, not markdown knowledge bases)
# ---------------------------------------------------------------------------

from .ai_researcher import AIResearcher, ResearchPlan, ResearchType
from .ba_analyzer import BAAnalysis, BAAnalyzer
from .brainstorm_facilitator import BrainstormFacilitator, BrainstormMethod, BrainstormSession
from .cloud_architect import CloudArchitect, CloudArchitectureDesign, CloudProvider
from .code_reviewer import CodeReviewerSkill, FindingCategory, ReviewFinding, ReviewReport, Severity
from .data_engineer import DataEngineer, DataEngineeringPlan
from .debugging_assistant import BugCategory, DebuggingAssistant, DebuggingPlan
from .dependency_analyzer import (
    CircularDependency,
    DependencyAnalyzerSkill,
    DependencyReport,
    DependencySuggestion,
    ImportInfo,
)
from .design_reviewer import DesignQuality, DesignReviewer, DesignReviewReport
from .documentation_writer import (
    ApiEndpoint,
    DocumentationReport,
    DocumentationWriterSkill,
    GeneratedDocstring,
)
from .performance_profiler import (
    ComplexityClass,
    PerformanceIssue,
    PerformanceProfilerSkill,
    ProfileReport,
    ProfileResult,
)
from .pm_planner import PMPlan, PMPlanner
from .refactoring_advisor import (
    RefactoringAdvisorSkill,
    RefactoringReport,
    RefactoringSuggestion,
    RefactoringType,
)
from .security_auditor import (
    AuditReport,
    OwaspCategory,
    SecurityAuditorSkill,
    Vulnerability,
    VulnerabilitySeverity,
)
from .solution_architect import SolutionArchitect, SolutionArchitectureDoc
from .sre_incident_responder import IncidentResponsePlan, IncidentSeverity, SREIncidentResponder
from .test_generator import GeneratedTest, TestCase, TestGeneratorSkill, TestSuite

__all__ = [
    # Registry
    "get_registry",
    "list_all_skills",
    "get_skill_by_name",
    "search_skills",
    "SpecializedSkillsRegistry",
    "SkillMetadata",
    # Code Reviewer
    "CodeReviewerSkill",
    "ReviewReport",
    "ReviewFinding",
    "Severity",
    "FindingCategory",
    # Security Auditor
    "SecurityAuditorSkill",
    "AuditReport",
    "Vulnerability",
    "VulnerabilitySeverity",
    "OwaspCategory",
    # Test Generator
    "TestGeneratorSkill",
    "TestSuite",
    "GeneratedTest",
    "TestCase",
    # Refactoring Advisor
    "RefactoringAdvisorSkill",
    "RefactoringReport",
    "RefactoringSuggestion",
    "RefactoringType",
    # Documentation Writer
    "DocumentationWriterSkill",
    "DocumentationReport",
    "GeneratedDocstring",
    "ApiEndpoint",
    # Performance Profiler
    "PerformanceProfilerSkill",
    "ProfileReport",
    "ProfileResult",
    "PerformanceIssue",
    "ComplexityClass",
    # Dependency Analyzer
    "DependencyAnalyzerSkill",
    "DependencyReport",
    "ImportInfo",
    "CircularDependency",
    "DependencySuggestion",
    # SRE Incident Responder
    "SREIncidentResponder",
    "IncidentResponsePlan",
    "IncidentSeverity",
    # Cloud Architect
    "CloudArchitect",
    "CloudArchitectureDesign",
    "CloudProvider",
    # Solution Architect
    "SolutionArchitect",
    "SolutionArchitectureDoc",
    # PM Planner
    "PMPlanner",
    "PMPlan",
    # BA Analyzer
    "BAAnalyzer",
    "BAAnalysis",
    # Brainstorm Facilitator
    "BrainstormFacilitator",
    "BrainstormSession",
    "BrainstormMethod",
    # Data Engineer
    "DataEngineer",
    "DataEngineeringPlan",
    # AI Researcher
    "AIResearcher",
    "ResearchPlan",
    "ResearchType",
    # Design Reviewer
    "DesignReviewer",
    "DesignReviewReport",
    "DesignQuality",
    # Debugging Assistant
    "DebuggingAssistant",
    "DebuggingPlan",
    "BugCategory",
]
