# Skills Library

## Overview

Lyra's skills library provides reusable workflow definitions and domain knowledge for common development tasks. Skills are the primary workflow surface in Lyra.

## Architecture

The skill system consists of three core components:

1. **SkillMetadata**: Data structure for skill definitions
2. **SkillRegistry**: Loads and manages skills from directories
3. **SkillLoader**: Loads skill content and generates codemaps

## Skill Format

Skills are defined as Markdown files named `SKILL.md` with YAML frontmatter:

```markdown
---
name: skill-name
description: What this skill provides
origin: ECC
tags: [tag1, tag2]
triggers: [keyword1, keyword2]
---

# Skill Name

Skill documentation here...
```

## Available Skills (20 Core Skills)

### Development Skills

1. **tdd-workflow** - Test-driven development patterns
2. **python-patterns** - Python best practices and idioms
3. **testing-patterns** - Testing strategies and patterns
4. **refactoring-patterns** - Code refactoring techniques
5. **debugging-techniques** - Debugging strategies
6. **error-handling** - Error handling patterns
7. **async-patterns** - Asynchronous programming patterns
8. **code-organization** - Code organization patterns

### Quality & Review Skills

9. **code-review-checklist** - Code review checklist
10. **security-checklist** - Security validation checklist
11. **testing-strategies** - Testing strategies for projects

### Architecture & Design Skills

12. **api-design** - RESTful API design patterns
13. **architecture-patterns** - System architecture patterns
14. **database-patterns** - Database design patterns

### Performance & Optimization Skills

15. **performance-optimization** - Performance optimization techniques

### DevOps & Infrastructure Skills

16. **git-workflow** - Git workflow patterns
17. **ci-cd-patterns** - CI/CD pipeline patterns
18. **monitoring-observability** - Monitoring and observability
19. **deployment-strategies** - Deployment strategies

### Documentation Skills

20. **documentation-standards** - Documentation writing standards

## Usage

### Loading Skills

```python
from pathlib import Path
from lyra_cli.core.skill_registry import SkillRegistry

# Initialize registry with skill directories
registry = SkillRegistry(skill_dirs=[
    Path("src/lyra_cli/skills"),
    Path.home() / ".lyra" / "skills"
])

# Load all skills
skills = registry.load_skills()
```

### Searching Skills

```python
# Search by name, description, or tags
results = registry.search_skills("testing")

for skill in results:
    print(f"{skill.name}: {skill.description}")
```

### Getting Skills by Trigger

```python
# Get skills triggered by keyword
results = registry.get_by_trigger("tdd")

for skill in results:
    print(f"Triggered: {skill.name}")
```

### Loading Skill Content

```python
from lyra_cli.core.skill_loader import SkillLoader

loader = SkillLoader()
skill = registry.get_skill("tdd-workflow")
content = loader.load_skill_content(skill)
```

## Skill Directories

Skills are loaded from multiple directories in priority order:

1. **Built-in**: `src/lyra_cli/skills/` - Core skills shipped with Lyra
2. **User**: `~/.lyra/skills/` - User-defined global skills
3. **Project**: `.lyra/skills/` - Project-specific skills

## Creating Custom Skills

Create a new skill by adding a directory with `SKILL.md`:

```bash
mkdir -p ~/.lyra/skills/my-custom-skill
```

Create `~/.lyra/skills/my-custom-skill/SKILL.md`:

```markdown
---
name: my-custom-skill
description: Custom skill for specific workflow
origin: user
tags: [custom, workflow]
triggers: [custom, myskill]
---

# My Custom Skill

## Overview
What this skill provides...

## When to Use
When to use this skill...

## Patterns
Workflow patterns and examples...
```

## Skill Tags

Use tags to categorize skills:

- **testing**: Testing-related skills
- **patterns**: Design patterns
- **best-practices**: Best practice guidelines
- **security**: Security-related skills
- **performance**: Performance optimization
- **devops**: DevOps and infrastructure
- **documentation**: Documentation skills

## Skill Triggers

Triggers are keywords that automatically suggest skills:

- **tdd**: Triggers tdd-workflow skill
- **review**: Triggers code-review-checklist
- **security**: Triggers security-checklist
- **python**: Triggers python-patterns
- **api**: Triggers api-design

## Best Practices

1. **Use Specific Skills**: Prefer specialized skills over generic ones
2. **Search First**: Search for existing skills before creating new ones
3. **Tag Appropriately**: Use relevant tags for discoverability
4. **Keep Skills Focused**: One skill per workflow or pattern
5. **Include Examples**: Provide concrete examples in skills

## Testing

Run skill system tests:

```bash
cd packages/lyra-cli
python -m pytest tests/skills/ -v
```

## API Reference

### SkillMetadata

```python
@dataclass
class SkillMetadata:
    name: str
    description: str
    origin: str
    tags: List[str]
    triggers: Optional[List[str]] = None
    codemap: Optional[str] = None
    file_path: Optional[str] = None
```

### SkillRegistry

```python
class SkillRegistry:
    def load_skills() -> Dict[str, SkillMetadata]
    def get_skill(name: str) -> Optional[SkillMetadata]
    def search_skills(query: str) -> List[SkillMetadata]
    def get_by_trigger(keyword: str) -> List[SkillMetadata]
    def list_skills() -> List[SkillMetadata]
```

### SkillLoader

```python
class SkillLoader:
    def load_skill_content(skill: SkillMetadata) -> str
    def generate_codemap(skill_name: str, skill_dir: Path) -> Optional[str]
```
