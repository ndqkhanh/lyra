"""Skill registry and loader"""

from typing import List
from pathlib import Path
from .skill_manager import SkillDefinition


class SkillRegistry:
    """Registry of built-in skills"""

    def __init__(self):
        self.skills: dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition):
        """Register a skill"""
        self.skills[skill.name] = skill

    def get(self, name: str) -> SkillDefinition:
        """Get skill by name"""
        return self.skills.get(name)

    def list(self) -> List[SkillDefinition]:
        """List all skills"""
        return list(self.skills.values())


class SkillLoader:
    """Loads skills from files"""

    @staticmethod
    def create_default_skills():
        """Create default skill files"""
        skills_dir = Path.home() / ".lyra" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        # Deep research skill
        (skills_dir / "deep-research.md").write_text("""---
name: deep-research
description: Multi-source deep research with citations
triggers: ["research", "investigate", "analyze"]
tags: ["research", "analysis"]
model: opus
tools: ["WebSearch", "WebFetch", "Read"]
---

# Deep Research Skill

You are a research specialist conducting thorough, multi-source research.

## Process

1. **Understand the topic**
   - Clarify the research question
   - Identify key areas to investigate
   - Define scope and depth

2. **Search multiple sources**
   - Use WebSearch for broad coverage
   - Use WebFetch for specific sources
   - Read relevant documentation

3. **Synthesize findings**
   - Organize information by theme
   - Identify patterns and insights
   - Note contradictions or gaps

4. **Cite sources**
   - Include URLs for all sources
   - Quote key passages
   - Attribute claims properly

## Output Format

Deliver a structured report with:
- Executive summary
- Key findings (bulleted)
- Detailed analysis
- Sources (with URLs)
""")

        # Code review skill
        (skills_dir / "code-review.md").write_text("""---
name: code-review
description: Comprehensive code review for quality and correctness
triggers: ["review", "check code", "audit"]
tags: ["quality", "review"]
model: sonnet
tools: ["Read", "Grep"]
---

# Code Review Skill

You are an expert code reviewer focusing on correctness and quality.

## Review Checklist

### Correctness
- [ ] Logic errors
- [ ] Edge cases handled
- [ ] Error handling present
- [ ] Null/undefined checks
- [ ] Type safety

### Quality
- [ ] Clear naming
- [ ] Proper structure
- [ ] No duplication
- [ ] Good comments
- [ ] Testable code

### Security
- [ ] Input validation
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] Secret exposure
- [ ] Authentication/authorization

## Severity Levels

- **Critical**: Must fix (security, data loss)
- **High**: Should fix (bugs, errors)
- **Medium**: Consider fixing (quality)
- **Low**: Nice to have (style)

## Output Format

For each issue:
1. File and line number
2. Severity level
3. Description
4. Suggested fix
""")

        # TDD workflow skill
        (skills_dir / "tdd-workflow.md").write_text("""---
name: tdd-workflow
description: Test-driven development workflow guide
triggers: ["tdd", "test first", "red green refactor"]
tags: ["testing", "tdd"]
model: sonnet
tools: ["Read", "Write", "Edit", "Bash"]
---

# TDD Workflow Skill

You are a TDD expert guiding test-driven development.

## TDD Cycle

### 1. Red - Write Failing Test
- Write test for new behavior
- Test should fail (no implementation yet)
- Verify test fails for right reason

### 2. Green - Make It Pass
- Write minimal code to pass test
- Don't worry about perfection
- Just make it work

### 3. Refactor - Improve Code
- Clean up implementation
- Remove duplication
- Improve naming
- Ensure tests still pass

### 4. Repeat
- Move to next behavior
- Keep tests passing
- Small iterations

## Best Practices

- One test at a time
- Test behavior, not implementation
- Fast, isolated tests
- Clear test names
- Arrange-Act-Assert pattern

## Output

Guide the user through each step:
1. What test to write
2. What code to implement
3. What to refactor
4. Next iteration
""")

        print(f"✓ Created default skills in {skills_dir}")


# Global registry
_registry = SkillRegistry()


def get_registry() -> SkillRegistry:
    """Get global skill registry"""
    return _registry
