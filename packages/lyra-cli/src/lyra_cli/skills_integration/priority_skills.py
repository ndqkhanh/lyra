"""Priority skills from Claude Code ecosystem - Top 10 MVP."""

from dataclasses import dataclass
from typing import Any


@dataclass
class SkillDefinition:
    """Definition of a skill."""

    name: str
    description: str
    triggers: list[str]
    handler: Any
    model: str = "sonnet"


class PrioritySkills:
    """Top 10 priority skills for immediate value."""

    @staticmethod
    def get_all() -> list[SkillDefinition]:
        """Get all priority skills."""
        return [
            # 1. Code Review
            SkillDefinition(
                name="code-reviewer",
                description="Review code for quality, security, and best practices",
                triggers=["review", "code review", "check code"],
                handler=PrioritySkills.code_reviewer,
                model="sonnet",
            ),
            # 2. Test Generation
            SkillDefinition(
                name="tdd-guide",
                description="Generate tests following TDD methodology",
                triggers=["test", "tdd", "write tests"],
                handler=PrioritySkills.tdd_guide,
                model="sonnet",
            ),
            # 3. Bug Fixing
            SkillDefinition(
                name="debugger",
                description="Debug and fix issues systematically",
                triggers=["debug", "fix bug", "troubleshoot"],
                handler=PrioritySkills.debugger,
                model="sonnet",
            ),
            # 4. Documentation
            SkillDefinition(
                name="doc-writer",
                description="Write clear technical documentation",
                triggers=["document", "write docs", "readme"],
                handler=PrioritySkills.doc_writer,
                model="haiku",
            ),
            # 5. Refactoring
            SkillDefinition(
                name="refactor-clean",
                description="Refactor code for clarity and maintainability",
                triggers=["refactor", "clean up", "improve code"],
                handler=PrioritySkills.refactor_clean,
                model="sonnet",
            ),
            # 6. Security Review
            SkillDefinition(
                name="security-reviewer",
                description="Identify security vulnerabilities",
                triggers=["security", "vulnerabilities", "secure"],
                handler=PrioritySkills.security_reviewer,
                model="sonnet",
            ),
            # 7. Performance Optimization
            SkillDefinition(
                name="performance-optimizer",
                description="Optimize code for performance",
                triggers=["optimize", "performance", "speed up"],
                handler=PrioritySkills.performance_optimizer,
                model="sonnet",
            ),
            # 8. API Design
            SkillDefinition(
                name="api-designer",
                description="Design clean, RESTful APIs",
                triggers=["api", "endpoint", "rest"],
                handler=PrioritySkills.api_designer,
                model="sonnet",
            ),
            # 9. Database Optimization
            SkillDefinition(
                name="db-optimizer",
                description="Optimize database queries and schema",
                triggers=["database", "query", "sql"],
                handler=PrioritySkills.db_optimizer,
                model="sonnet",
            ),
            # 10. Architecture Review
            SkillDefinition(
                name="architect",
                description="Review and design system architecture",
                triggers=["architecture", "design", "system design"],
                handler=PrioritySkills.architect,
                model="opus",
            ),
        ]

    @staticmethod
    async def code_reviewer(context: dict[str, Any]) -> str:
        """Review code for quality and best practices."""
        return "Code review: Analyzing code quality, security, and best practices..."

    @staticmethod
    async def tdd_guide(context: dict[str, Any]) -> str:
        """Guide test-driven development."""
        return "TDD Guide: Writing tests first, then implementation..."

    @staticmethod
    async def debugger(context: dict[str, Any]) -> str:
        """Debug issues systematically."""
        return "Debugger: Analyzing issue, identifying root cause..."

    @staticmethod
    async def doc_writer(context: dict[str, Any]) -> str:
        """Write technical documentation."""
        return "Doc Writer: Creating clear, comprehensive documentation..."

    @staticmethod
    async def refactor_clean(context: dict[str, Any]) -> str:
        """Refactor code for clarity."""
        return "Refactor: Improving code structure and readability..."

    @staticmethod
    async def security_reviewer(context: dict[str, Any]) -> str:
        """Review security vulnerabilities."""
        return "Security Review: Checking for OWASP Top 10 vulnerabilities..."

    @staticmethod
    async def performance_optimizer(context: dict[str, Any]) -> str:
        """Optimize performance."""
        return "Performance: Analyzing bottlenecks and optimizing..."

    @staticmethod
    async def api_designer(context: dict[str, Any]) -> str:
        """Design APIs."""
        return "API Design: Creating RESTful, well-structured APIs..."

    @staticmethod
    async def db_optimizer(context: dict[str, Any]) -> str:
        """Optimize database."""
        return "DB Optimizer: Analyzing queries and schema..."

    @staticmethod
    async def architect(context: dict[str, Any]) -> str:
        """Review architecture."""
        return "Architect: Reviewing system design and architecture..."


class SkillMatcher:
    """Match user input to skills."""

    def __init__(self):
        self.skills = {s.name: s for s in PrioritySkills.get_all()}

    def match(self, text: str) -> list[SkillDefinition]:
        """Match text to skills based on triggers."""
        text_lower = text.lower()
        matches = []

        for skill in self.skills.values():
            for trigger in skill.triggers:
                if trigger in text_lower:
                    matches.append(skill)
                    break

        return matches

    def get_skill(self, name: str) -> SkillDefinition | None:
        """Get skill by name."""
        return self.skills.get(name)
