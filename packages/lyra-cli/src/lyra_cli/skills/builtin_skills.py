"""Built-in skills registration"""

from .skill_manager import SkillManager, SkillDefinition
from .skill_loader import get_registry


def register_builtin_skills(manager: SkillManager):
    """Register all built-in skills"""
    registry = get_registry()

    # Plan skill
    plan_skill = SkillDefinition(
        name="plan",
        description="Create implementation plan for complex tasks",
        triggers=["plan", "design", "how to implement"],
        tags=["planning", "architecture"],
        model="opus",
        tools=["Read", "Grep", "Glob"],
        prompt="""Create a detailed implementation plan.

Steps:
1. Analyze requirements
2. Break down into phases
3. Identify dependencies
4. List risks and mitigations
5. Provide step-by-step plan

Output a clear, actionable plan."""
    )
    registry.register(plan_skill)
    manager.register_skill(plan_skill)

    # Review skill
    review_skill = SkillDefinition(
        name="review",
        description="Review code for quality and correctness",
        triggers=["review", "check", "audit"],
        tags=["quality", "review"],
        model="sonnet",
        tools=["Read", "Grep"],
        prompt="""Review code for:
- Correctness bugs
- Logic errors
- Edge cases
- Error handling
- Code quality

Provide severity-rated feedback."""
    )
    registry.register(review_skill)
    manager.register_skill(review_skill)

    # Test skill
    test_skill = SkillDefinition(
        name="test",
        description="Write tests following TDD",
        triggers=["test", "tdd", "write tests"],
        tags=["testing", "tdd"],
        model="sonnet",
        tools=["Read", "Write", "Edit", "Bash"],
        prompt="""Guide TDD workflow:
1. Write failing test
2. Implement minimal code
3. Refactor
4. Repeat

Follow red-green-refactor cycle."""
    )
    registry.register(test_skill)
    manager.register_skill(test_skill)
