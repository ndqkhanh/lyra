# Skills Architecture Proposal for Lyra

**Version:** 1.0  
**Date:** 2026-05-29  
**Status:** Proposal

---

## 1. Overview

This document proposes a comprehensive skills architecture for Lyra that:
1. Adopts Claude Code plugin format for marketplace compatibility
2. Extends it with Lyra-specific features (auto-evaluation, composition, evolution)
3. Maintains backward compatibility with existing Lyra skills
4. Enables community contributions through a skill marketplace

---

## 2. Skill Definition Format

### 2.1 Basic Skill Structure

```markdown
---
# Required fields
name: skill-name
description: One-line description for discovery and auto-invocation
version: 1.0.0

# Optional metadata
author: Author Name
license: MIT
keywords: [keyword1, keyword2, keyword3]
category: engineering | design | research | operations | security

# Lyra-specific fields
tier: keep | watch | rewrite | retire | promote
data_access_level: raw | redacted | verified_only
task_type: open-ended | outcome-gradable

# Composition
dependencies:
  - skill-id: another-skill
    version: ">=1.0.0"
  - skill-id: third-skill
    version: "^2.0.0"

parameters:
  - name: input_file
    type: string
    required: true
    description: Path to input file
  - name: output_format
    type: string
    required: false
    default: json
    enum: [json, yaml, toml]

# Triggers (when Claude should auto-invoke)
triggers:
  - pattern: "analyze code quality"
    confidence: 0.8
  - pattern: "security scan"
    confidence: 0.9

# Tool permissions
allowed_tools:
  - Read
  - Grep
  - Bash(npm run *)
disallowed_tools:
  - Write(/etc/**)
  - Edit(/etc/**)

# Hooks (skill-specific automation)
hooks:
  pre_use:
    - type: command
      command: "echo 'Starting skill...'"
  post_use:
    - type: command
      command: "echo 'Skill completed'"
  on_failure:
    - type: command
      command: "echo 'Skill failed'"

# Quality gates
quality_gates:
  - type: test
    command: pytest tests/
  - type: lint
    command: ruff check .
  - type: security
    command: bandit -r src/

# Metrics (for auto-evaluation)
metrics:
  success_rate_threshold: 0.8
  avg_execution_time_ms: 5000
  token_budget: 10000
---

# Skill Name

Brief introduction to what this skill does and when to use it.

## When to Use

- Scenario 1
- Scenario 2
- Scenario 3

## Workflow

1. **Step 1:** Description
2. **Step 2:** Description
3. **Step 3:** Description

## Examples

### Example 1: Basic Usage

```bash
/skill-name --input file.py --output json
```

### Example 2: Advanced Usage

```bash
/skill-name --input file.py --output yaml --verbose
```

## Parameters

- `input_file` (required): Path to input file
- `output_format` (optional, default: json): Output format (json, yaml, toml)

## Output

Description of what the skill returns.

## Error Handling

Common errors and how to resolve them.

## References

- [External Doc 1](https://example.com)
- [External Doc 2](https://example.com)
```

### 2.2 Skill Frontmatter Schema

```python
from dataclasses import dataclass, field
from typing import Literal

@dataclass(frozen=True)
class SkillDependency:
    skill_id: str
    version: str  # semver range: ">=1.0.0", "^2.0.0", "~1.2.3"

@dataclass(frozen=True)
class SkillParameter:
    name: str
    type: Literal["string", "int", "float", "bool", "list", "dict"]
    required: bool
    description: str
    default: str | int | float | bool | list | dict | None = None
    enum: list[str] | None = None

@dataclass(frozen=True)
class SkillTrigger:
    pattern: str
    confidence: float  # 0.0 to 1.0

@dataclass(frozen=True)
class SkillHook:
    type: Literal["command", "http", "mcp_tool", "prompt", "agent"]
    command: str | None = None
    url: str | None = None
    tool: str | None = None
    prompt: str | None = None
    agent: str | None = None

@dataclass(frozen=True)
class QualityGate:
    type: Literal["test", "lint", "security", "performance"]
    command: str
    threshold: float | None = None

@dataclass(frozen=True)
class SkillMetrics:
    success_rate_threshold: float = 0.8
    avg_execution_time_ms: int = 5000
    token_budget: int = 10000

@dataclass(frozen=True)
class SkillManifest:
    # Required
    name: str
    description: str
    version: str
    
    # Optional metadata
    author: str | None = None
    license: str | None = None
    keywords: list[str] = field(default_factory=list)
    category: str | None = None
    
    # Lyra-specific
    tier: str | None = None
    data_access_level: str | None = None
    task_type: str | None = None
    
    # Composition
    dependencies: list[SkillDependency] = field(default_factory=list)
    parameters: list[SkillParameter] = field(default_factory=list)
    
    # Triggers
    triggers: list[SkillTrigger] = field(default_factory=list)
    
    # Permissions
    allowed_tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)
    
    # Hooks
    hooks: dict[str, list[SkillHook]] = field(default_factory=dict)
    
    # Quality gates
    quality_gates: list[QualityGate] = field(default_factory=list)
    
    # Metrics
    metrics: SkillMetrics = field(default_factory=SkillMetrics)
    
    # Content
    content: str = ""
    path: str = ""
```

---

## 3. Plugin Structure

### 3.1 Directory Layout

```text
lyra-plugin-engineering/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── skills/
│   ├── code-review/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   │   ├── patterns.md
│   │   │   └── checklist.md
│   │   └── scripts/
│   │       └── analyze.py
│   ├── refactor/
│   │   └── SKILL.md
│   └── test-generation/
│       └── SKILL.md
├── agents/
│   ├── code-reviewer.md
│   └── test-engineer.md
├── hooks/
│   └── hooks.json
├── .mcp.json                    # Optional MCP servers
├── lsp/                         # Optional LSP config
│   └── config.json
├── README.md
├── LICENSE
└── CHANGELOG.md
```

### 3.2 Plugin Manifest (plugin.json)

```json
{
  "name": "engineering",
  "version": "1.0.0",
  "description": "Engineering skills for code review, refactoring, and testing",
  "author": {
    "name": "Lyra Team",
    "email": "team@lyra.dev",
    "url": "https://lyra.dev"
  },
  "repository": "https://github.com/lyra/lyra-plugin-engineering",
  "homepage": "https://lyra.dev/plugins/engineering",
  "license": "MIT",
  "keywords": [
    "engineering",
    "code-review",
    "refactoring",
    "testing",
    "tdd"
  ],
  "category": "engineering",
  "lyra": {
    "min_version": "0.1.0",
    "max_version": "1.0.0"
  },
  "dependencies": {
    "lyra-plugin-core": "^1.0.0"
  },
  "skills": [
    {
      "id": "code-review",
      "path": "skills/code-review/SKILL.md",
      "featured": true
    },
    {
      "id": "refactor",
      "path": "skills/refactor/SKILL.md",
      "featured": false
    },
    {
      "id": "test-generation",
      "path": "skills/test-generation/SKILL.md",
      "featured": true
    }
  ],
  "agents": [
    {
      "id": "code-reviewer",
      "path": "agents/code-reviewer.md"
    },
    {
      "id": "test-engineer",
      "path": "agents/test-engineer.md"
    }
  ],
  "hooks": {
    "path": "hooks/hooks.json"
  },
  "mcp_servers": {
    "path": ".mcp.json"
  },
  "lsp_servers": {
    "path": "lsp/config.json"
  }
}
```

---

## 4. Skill Discovery Mechanism

### 4.1 Discovery Sources

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SkillSource:
    """A source from which skills can be discovered."""
    type: Literal["local", "plugin", "marketplace", "git"]
    path: Path | str
    priority: int = 0  # Higher priority = loaded first
    enabled: bool = True

# Default sources (in priority order)
DEFAULT_SOURCES = [
    SkillSource(type="local", path="./.lyra/skills", priority=100),
    SkillSource(type="local", path="~/.lyra/skills", priority=90),
    SkillSource(type="plugin", path="~/.lyra/plugins", priority=80),
    SkillSource(type="marketplace", path="https://marketplace.lyra.dev", priority=70),
]
```

### 4.2 Discovery Algorithm

```python
class SkillDiscovery:
    """Discovers and loads skills from multiple sources."""
    
    def __init__(self, sources: list[SkillSource]):
        self.sources = sorted(sources, key=lambda s: s.priority, reverse=True)
        self.cache: dict[str, SkillManifest] = {}
    
    def discover_all(self) -> list[SkillManifest]:
        """Discover all skills from all sources."""
        skills: dict[str, SkillManifest] = 
        
        for source in self.sources:
            if not source.enabled:
                continue
            
            discovered = self._discover_from_source(source)
            
            # Higher priority sources override lower priority
            for skill in discovered:
                if skill.name not in skills:
                    skills[skill.name] = skill
        
        return list(skills.values())
    
    def _discover_from_source(self, source: SkillSource) -> list[SkillManifest]:
        """Discover skills from a single source."""
        if source.type == "local":
            return self._discover_local(Path(source.path).expanduser())
        elif source.type == "plugin":
            return self._discover_plugins(Path(source.path).expanduser())
        elif source.type == "marketplace":
            return self._discover_marketplace(source.path)
        elif source.type == "git":
            return self._discover_git(source.path)
        return []
    
    def _discover_local(self, path: Path) -> list[SkillManifest]:
        """Discover skills from local directory."""
        skills = []
        
        if not path.exists():
            return skills
        
        # Find all SKILL.md files
        for skill_file in path.rglob("SKILL.md"):
            try:
                manifest = self._load_skill_file(skill_file)
                skills.append(manifest)
            except Exception as e:
                logger.warning(f"Failed to load skill {skill_file}: {e}")
        
        return skills
    
    def _discover_plugins(self, path: Path) -> list[SkillManifest]:
        """Discover skills from installed plugins."""
        skills = []
        
        if not path.exists():
            return skills
        
        # Find all plugin.json files
        for plugin_file in path.rglob("plugin.json"):
            try:
                plugin = self._load_plugin(plugin_file)
                skills.extend(plugin.skills)
            except Exception as e:
                logger.warning(f"Failed to load plugin {plugin_file}: {e}")
        
        return skills
    
    def _discover_marketplace(self, url: str) -> list[SkillManifest]:
        """Discover skills from marketplace API."""
        # TODO: Implement marketplace API client
        return []
    
    def _discover_git(self, url: str) -> list[SkillManifest]:
        """Discover skills from git repository."""
        # TODO: Implement git clone + discovery
        return []
```

### 4.3 Skill Indexing

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class SkillIndex:
    """Multi-index for fast skill lookup."""
    by_name: dict[str, SkillManifest]
    by_keyword: dict[str, list[SkillManifest]]
    by_category: dict[str, list[SkillManifest]]
    by_trigger: dict[str, list[SkillManifest]]
    
    @classmethod
    def build(cls, skills: list[SkillManifest]) -> "SkillIndex":
        """Build indexes from skill list."""
        by_name = {s.name: s for s in skills}
        by_keyword: dict[str, list[SkillManifest]] = {}
        by_category: dict[str, list[SkillManifest]] = {}
        by_trigger: dict[str, list[SkillManifest]] = {}
        
        for skill in skills:
            # Index by keywords
            for keyword in skill.keywords:
                by_keyword.setdefault(keyword, []).append(skill)
            
            # Index by category
            if skill.category:
                by_category.setdefault(skill.category, []).append(skill)
            
            # Index by triggers
            for trigger in skill.triggers:
                by_trigger.setdefault(trigger.pattern, []).append(skill)
        
        return cls(
            by_name=by_name,
            by_keyword=by_keyword,
            by_category=by_category,
            by_trigger=by_trigger,
        )
    
    def search(self, query: str) -> list[SkillManifest]:
        """Search skills by query string."""
        results: set[SkillManifest] = set()
        
        # Exact name match
        if query in self.by_name:
            results.add(self.by_name[query])
        
        # Keyword match
        for keyword, skills in self.by_keyword.items():
            if query.lower() in keyword.lower():
                results.update(skills)
        
        # Category match
        for category, skills in self.by_category.items():
            if query.lower() in category.lower():
                results.update(skills)
        
        # Trigger pattern match
        for pattern, skills in self.by_trigger.items():
            if query.lower() in pattern.lower():
                results.update(skills)
        
        # Description match
        for skill in self.by_name.values():
            if query.lower() in skill.description.lower():
                results.add(skill)
        
        return list(results)
```

---

## 5. Skill Versioning Strategy

### 5.1 Semantic Versioning

Skills follow [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** version: incompatible API changes (breaking changes to parameters, output format)
- **MINOR** version: backward-compatible functionality additions
- **PATCH** version: backward-compatible bug fixes

### 5.2 Version Resolution

```python
from packaging import version as pkg_version

class VersionResolver:
    """Resolves skill dependencies using semantic versioning."""
    
    def resolve(
        self,
        dependencies: list[SkillDependency],
        available: dict[str, list[SkillManifest]],
    ) -> dict[str, SkillManifest]:
        """Resolve dependencies to specific versions."""
        resolved: dict[str, SkillManifest] = {}
        
        for dep in dependencies:
            candidates = available.get(dep.skill_id, [])
            
            # Filter by version constraint
            matching = [
                s for s in candidates
                if self._matches_constraint(s.version, dep.version)
            ]
            
            if not matching:
                raise ValueError(
                    f"No version of {dep.skill_id} matches {dep.version}"
                )
            
            # Pick highest matching version
            best = max(matching, key=lambda s: pkg_version.parse(s.version))
            resolved[dep.skill_id] = best
        
        return resolved
    
    def _matches_constraint(self, version: str, constraint: str) -> bool:
        """Check if version matches constraint."""
        v = pkg_version.parse(version)
        
        if constraint.startswith("^"):
            # ^1.2.3 means >=1.2.3 <2.0.0
            base = pkg_version.parse(constraint[1:])
            return v >= base and v.major == base.major
        
        elif constraint.startswith("~"):
            # ~1.2.3 means >=1.2.3 <1.3.0
            base = pkg_version.parse(constraint[1:])
            return v >= base and v.major == base.major and v.minor == base.minor
        
        elif constraint.startswith(">="):
            base = pkg_version.parse(constraint[2:])
            return v >= base
        
        elif constraint.startswith("<="):
            base = pkg_version.parse(constraint[2:])
            return v <= base
        
        elif constraint.startswith(">"):
            base = pkg_version.parse(constraint[1:])
            return v > base
        
        elif constraint.startswith("<"):
            base = pkg_version.parse(constraint[1:])
            return v < base
        
        else:
            # Exact match
            return v == pkg_version.parse(constraint)
```

### 5.3 Version Migration

```python
@dataclass
class VersionMigration:
    """Migration script for upgrading skill versions."""
    from_version: str
    to_version: str
    script: Callable[[dict], dict]  # Transform old params to new params
    
class SkillMigrator:
    """Handles skill version migrations."""
    
    def __init__(self):
        self.migrations: dict[str, list[VersionMigration]] = {}
    
    def register(self, skill_id: str, migration: VersionMigration):
        """Register a migration for a skill."""
        self.migrations.setdefault(skill_id, []).append(migration)
    
    def migrate(
        self,
        skill_id: str,
        from_version: str,
        to_version: str,
        params: dict,
    ) -> dict:
        """Migrate parameters from old version to new version."""
        migrations = self.migrations.get(skill_id, [])
        
        # Find migration path
        path = self._find_migration_path(migrations, from_version, to_version)
        
        # Apply migrations in sequence
        result = params
        for migration in path:
            result = migration.script(result)
        
        return result
    
    def _find_migration_path(
        self,
        migrations: list[VersionMigration],
        from_version: str,
        to_version: str,
    ) -> list[VersionMigration]:
        """Find shortest migration path between versions."""
        # TODO: Implement graph search (BFS/Dijkstra)
        return []
```

---

## 6. Skill Composition Patterns

### 6.1 Sequential Composition (Pipeline)

```yaml
---
name: full-code-review
description: Complete code review pipeline
version: 1.0.0
category: engineering

pipeline:
  - skill: security-scan
    params:
      severity: high
  - skill: code-quality-check
    params:
      threshold: 0.8
  - skill: test-coverage-check
    params:
      min_coverage: 80
  - skill: generate-review-report
    params:
      format: markdown
---

# Full Code Review

Runs a complete code review pipeline:
1. Security scan
2. Code quality check
3. Test coverage check
4. Generate review report
```

### 6.2 Parallel Composition (Fan-out)

```yaml
---
name: multi-linter
description: Run multiple linters in parallel
version: 1.0.0
category: engineering

parallel:
  - skill: ruff-check
  - skill: mypy-check
  - skill: bandit-check
  - skill: black-check

aggregation: all_must_pass
---

# Multi-Linter

Runs multiple linters in parallel and aggregates results.
```

### 6.3 Conditional Composition (Branching)

```yaml
---
name: smart-deploy
description: Deploy with environment-specific checks
version: 1.0.0
category: operations

conditional:
  - condition: env == "production"
    skill: production-safety-check
  - condition: env == "staging"
    skill: staging-smoke-test
  - condition: env == "development"
    skill: dev-quick-check

then:
  - skill: deploy
    params:
      env: ${env}
---

# Smart Deploy

Runs environment-specific checks before deployment.
```

### 6.4 Composition Engine

```python
class SkillComposer:
    """Composes skills into pipelines."""
    
    def __init__(self, executor: SkillExecutor):
        self.executor = executor
    
    async def execute_pipeline(
        self,
        pipeline: list[dict],
        context: dict,
    ) -> list[dict]:
        """Execute skills sequentially, passing output to next."""
        results = []
        
        for step in pipeline:
            skill_id = step["skill"]
            params = step.get("params", {})
            
            # Resolve parameter references from context
            resolved_params = self._resolve_params(params, context)
            
            # Execute skill
            result = await self.executor.execute(skill_id, resolved_params)
            results.append(result)
            
            # Update context with result
            context[f"{skill_id}_result"] = result
        
        return results
    
    async def execute_parallel(
        self,
        parallel: list[dict],
        context: dict,
    ) -> list[dict]:
        """Execute skills in parallel."""
        tasks = []
        
        for step in parallel:
            skill_id = step["skill"]
            params = step.get("params", {})
            resolved_params = self._resolve_params(params, context)
            
            task = self.executor.execute(skill_id, resolved_params)
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    async def execute_conditional(
        self,
        conditional: list[dict],
        then: list[dict],
        context: dict,
    ) -> list[dict]:
        """Execute skills conditionally."""
        # Evaluate conditions
        for branch in conditional:
            condition = branch["condition"]
            if self._evaluate_condition(condition, context):
                skill_id = branch["skill"]
                params = branch.get("params", {})
                resolved_params = self._resolve_params(params, context)
                
                result = await self.executor.execute(skill_id, resolved_params)
                context[f"{skill_id}_result"] = result
                break
        
        # Execute then branch
        return await self.execute_pipeline(then, context)
    
    def _resolve_params(self, params: dict, context: dict) -> dict:
        """Resolve parameter references like ${var}."""
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                resolved[key] = context.get(var_name, value)
            else:
                resolved[key] = value
        
        return resolved
    
    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """Evaluate condition expression."""
        # Simple expression evaluator (can be extended)
        # Example: "env == 'production'"
        try:
            return eval(condition, {"__builtins__": {}}, context)
        except Exception:
            return False
```

---

## 7. Integration with Existing Lyra Components

### 7.1 SkillLoader Integration

```python
# Extend existing SkillLoader to support new format
class EnhancedSkillLoader(SkillLoader):
    """Extended skill loader with plugin support."""
    
    def __init__(self):
        super().__init__()
        self.discovery = SkillDiscovery(DEFAULT_SOURCES)
        self.index: SkillIndex | None = None
        self.resolver = VersionResolver()
        self.composer = SkillComposer(SkillExecutor())
    
    def load_all(self) -> list[SkillManifest]:
        """Load all skills from all sources."""
        skills = self.discovery.discover_all()
        self.index = SkillIndex.build(skills)
        return skills
    
    def search(self, query: str) -> list[SkillManifest]:
        """Search skills by query."""
        if not self.index:
            self.load_all()
        return self.index.search(query)
    
    def resolve_dependencies(
        self,
        skill: SkillManifest,
    ) -> dict[str, SkillManifest]:
        """Resolve skill dependencies."""
        available = {
            s.name: [s] for s in self.load_all()
        }
        return self.resolver.resolve(skill.dependencies, available)
```

### 7.2 SkillCurator Integration

```python
# Extend curator to handle plugin metadata
class EnhancedSkillCurator(SkillCurator):
    """Extended curator with plugin awareness."""
    
    def curate_plugin(self, plugin_path: Path) -> PluginReport:
        """Curate all skills in a plugin."""
        plugin = self._load_plugin(plugin_path)
        
        skill_reports = []
        for skill_ref in plugin.skills:
            skill_path = plugin_path / skill_ref["path"]
            report = self.curate_skill(skill_path)
            skill_reports.append(report)
        
        return PluginReport(
            plugin_name=plugin.name,
            plugin_version=plugin.version,
            skill_reports=skill_reports,
            overall_tier=self._aggregate_tier(skill_reports),
        )
```

### 7.3 SkillRouter Integration

```python
# Extend router to use new indexing
class EnhancedSkillRouter(SkillRouter):
    """Extended router with semantic search."""
    
    def __init__(self, loader: EnhancedSkillLoader):
        super().__init__()
        self.loader = loader
    
    def route(self, query: str) -> SkillManifest | None:
        """Route query to best matching skill."""
        candidates = self.loader.search(query)
        
        if not candidates:
            return None
        
        # Score candidates by trigger confidence
        scored = []
        for skill in candidates:
            score = self._score_skill(query, skill)
            scored.append((score, skill))
        
        # Return highest scoring skill
        scored.sort(reverse=True)
        return scored[0][1] if scored else None
    
    def _score_skill(self, query: str, skill: SkillManifest) -> float:
        """Score skill relevance to query."""
        score = 0.0
        
        # Exact name match
        if query.lower() == skill.name.lower():
            score += 1.0
        
        # Keyword match
        for keyword in skill.keywords:
            if keyword.lower() in query.lower():
                score += 0.5
        
        # Trigger pattern match
        for trigger in skill.triggers:
            if trigger.pattern.lower() in query.lower():
                score += trigger.confidence
        
        # Description match
        if query.lower() in skill.description.lower():
            score += 0.3
        
        return score
```

---

## 8. Backward Compatibility

### 8.1 Migration Path

1. **Phase 1:** Support both old and new formats
   - Old format: Simple SKILL.md without frontmatter
   - New format: SKILL.md with extended frontmatter

2. **Phase 2:** Auto-migrate old skills
   - Detect old format
   - Generate minimal frontmatter
   - Preserve content

3. **Phase 3:** Deprecate old format
   - Warn on old format usage
   - Provide migration tool

### 8.2 Migration Tool

```python
class SkillMigrationTool:
    """Migrates old skills to new format."""
    
    def migrate_skill(self, old_path: Path) -> Path:
        """Migrate old skill to new format."""
        content = old_path.read_text()
        
        # Extract name from filename or first heading
        name = self._extract_name(content)
        
        # Generate minimal frontmatter
        frontmatter = {
            "name": name,
            "description": self._extract_description(content),
            "version": "1.0.0",
        }
        
        # Write new format
        new_content = self._format_skill(frontmatter, content)
        new_path = old_path.with_suffix(".new.md")
        new_path.write_text(new_content)
        
        return new_path
```

---

## 9. Next Steps

1. **Review and approve** this architecture proposal
2. **Create detailed technical specs** for each component
3. **Implement Phase 1** (plugin system foundation)
4. **Test with 10 migrated skills**
5. **Iterate based on feedback**

---

## 10. Appendices

### A. Example Skills

See `/docs/research/example-skills/` for:
- `engineering-code-review.md`
- `design-ui-audit.md`
- `research-literature-review.md`
- `operations-deploy-check.md`
- `security-vulnerability-scan.md`

### B. API Reference

See `/docs/api/skills-api.md` for complete API documentation.

### C. Migration Guide

See `/docs/guides/skill-migration.md` for step-by-step migration instructions.
