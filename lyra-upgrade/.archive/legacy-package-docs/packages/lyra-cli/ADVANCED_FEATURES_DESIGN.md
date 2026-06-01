# Advanced Features Design (Phase 4)

## Overview

Phase 4 extends the skill marketplace with advanced capabilities for skill composition, templating, analytics, and configuration. These features enable power users to build complex workflows, track skill effectiveness, and customize skill behavior.

## 1. Skill Composition and Chaining

### 1.1 Concept

Allow skills to invoke other skills, creating multi-step workflows. Skills can pass data between stages, enabling complex research, analysis, and code generation pipelines.

### 1.2 Composition Format

#### Skill Definition with Composition

```json
{
  "name": "deep-research",
  "version": "1.0.0",
  "description": "Multi-stage research with synthesis",
  "category": "research",
  "execution": {
    "type": "composition",
    "stages": [
      {
        "name": "search",
        "skill": "web-search",
        "args": "${input}",
        "output": "search_results"
      },
      {
        "name": "analyze",
        "skill": "text-analyzer",
        "args": "${search_results}",
        "output": "analysis"
      },
      {
        "name": "synthesize",
        "skill": "report-writer",
        "args": {
          "data": "${analysis}",
          "format": "markdown"
        },
        "output": "final_report"
      }
    ],
    "return": "${final_report}"
  },
  "args": {
    "required": true,
    "hint": "research topic"
  }
}
```

#### Variable Interpolation

- `${input}` - User-provided arguments
- `${stage_name.output}` - Output from previous stage
- `${env.VAR_NAME}` - Environment variables
- `${config.key}` - User configuration values

### 1.3 Execution Engine

```python
# src/lyra_cli/cli/composition_engine.py

from dataclasses import dataclass
from typing import Any, Dict, Optional
import re


@dataclass
class StageResult:
    """Result from executing a composition stage."""
    name: str
    output: Any
    success: bool
    error: Optional[str] = None


class CompositionEngine:
    """Execute multi-stage skill compositions."""
    
    def __init__(self, skill_manager):
        self.skill_manager = skill_manager
        self.context: Dict[str, Any] = {}
    
    def execute(self, composition: dict, user_input: str) -> StageResult:
        """Execute a skill composition.
        
        Args:
            composition: Composition definition from skill JSON
            user_input: User-provided arguments
        
        Returns:
            Final stage result
        """
        self.context = {"input": user_input}
        stages = composition.get("stages", [])
        
        for stage in stages:
            result = self._execute_stage(stage)
            if not result.success:
                return result
            
            # Store stage output in context
            output_var = stage.get("output")
            if output_var:
                self.context[output_var] = result.output
        
        # Return final result
        return_expr = composition.get("return", "${output}")
        final_output = self._interpolate(return_expr)
        
        return StageResult(
            name="composition",
            output=final_output,
            success=True
        )
    
    def _execute_stage(self, stage: dict) -> StageResult:
        """Execute a single stage."""
        skill_name = stage["skill"]
        args_template = stage.get("args", "")
        
        # Interpolate arguments
        if isinstance(args_template, str):
            args = self._interpolate(args_template)
        elif isinstance(args_template, dict):
            args = {k: self._interpolate(v) for k, v in args_template.items()}
        else:
            args = args_template
        
        # Execute skill
        try:
            skill = self.skill_manager.skills.get(skill_name)
            if not skill:
                return StageResult(
                    name=stage["name"],
                    output=None,
                    success=False,
                    error=f"Skill '{skill_name}' not found"
                )
            
            # Execute skill (simplified - actual implementation would use session)
            output = self._execute_skill(skill, args)
            
            return StageResult(
                name=stage["name"],
                output=output,
                success=True
            )
        except Exception as e:
            return StageResult(
                name=stage["name"],
                output=None,
                success=False,
                error=str(e)
            )
    
    def _interpolate(self, template: str) -> str:
        """Interpolate variables in template string."""
        if not isinstance(template, str):
            return template
        
        # Replace ${var} with context values
        def replace_var(match):
            var_path = match.group(1)
            return str(self._resolve_path(var_path))
        
        return re.sub(r'\$\{([^}]+)\}', replace_var, template)
    
    def _resolve_path(self, path: str) -> Any:
        """Resolve dotted path in context."""
        parts = path.split(".")
        value = self.context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
    
    def _execute_skill(self, skill: dict, args: Any) -> Any:
        """Execute a skill and return output."""
        # Placeholder - actual implementation would integrate with session
        return f"Output from {skill['name']}"
```

### 1.4 Commands

#### `/skill compose <name>`

Create a new composition skill interactively.

```bash
/skill compose deep-research
```

**Interactive Prompts:**
```
Creating composition skill: deep-research
Description: Multi-stage research with synthesis
Category: research

Stage 1:
  Name: search
  Skill: web-search
  Args: ${input}
  Output variable: search_results

Add another stage? (y/n): y

Stage 2:
  Name: analyze
  Skill: text-analyzer
  Args: ${search_results}
  Output variable: analysis

Add another stage? (y/n): y

Stage 3:
  Name: synthesize
  Skill: report-writer
  Args: {"data": "${analysis}", "format": "markdown"}
  Output variable: final_report

Add another stage? (y/n): n

Return value: ${final_report}

✓ Created composition skill: deep-research
✓ Saved to ~/.lyra/skills/deep-research.json

Usage: /deep-research <research topic>
```

## 2. Skill Templates and Scaffolding

### 2.1 Concept

Provide templates for common skill patterns, enabling users to quickly create new skills without writing JSON from scratch.

### 2.2 Template Format

```json
{
  "name": "prompt-skill-template",
  "description": "Template for simple prompt-based skills",
  "category": "template",
  "variables": [
    {
      "name": "skill_name",
      "prompt": "Skill name (kebab-case)",
      "required": true,
      "pattern": "^[a-z][a-z0-9-]*$"
    },
    {
      "name": "description",
      "prompt": "Brief description",
      "required": true
    },
    {
      "name": "category",
      "prompt": "Category",
      "required": true,
      "choices": ["research", "development", "testing", "documentation", "analysis"]
    },
    {
      "name": "keywords",
      "prompt": "Trigger keywords (comma-separated)",
      "required": false
    },
    {
      "name": "system_prompt",
      "prompt": "System prompt",
      "required": true,
      "multiline": true
    }
  ],
  "template": {
    "name": "{{skill_name}}",
    "version": "1.0.0",
    "description": "{{description}}",
    "category": "{{category}}",
    "execution": {
      "type": "prompt"
    },
    "trigger": {
      "keywords": "{{keywords|split(',')}}",
      "patterns": []
    },
    "args": {
      "required": true,
      "hint": "input"
    },
    "system_prompt": "{{system_prompt}}"
  }
}
```

### 2.3 Built-in Templates

1. **prompt-skill** - Simple prompt-based skill
2. **agent-skill** - Multi-turn agent with memory
3. **tool-skill** - Skill that executes external tools
4. **composition-skill** - Multi-stage workflow
5. **research-skill** - Web research with synthesis
6. **code-gen-skill** - Code generation with validation

### 2.4 Commands

#### `/skill new [template]`

Create a new skill from template.

```bash
/skill new prompt-skill
```

**Interactive Flow:**
```
Creating skill from template: prompt-skill

Skill name (kebab-case): code-explainer
Brief description: Explain code in simple terms
Category: 
  1. research
  2. development
  3. testing
  4. documentation
  5. analysis
Select (1-5): 4

Trigger keywords (comma-separated): explain,clarify,describe
System prompt (press Ctrl+D when done):
You are an expert at explaining code in simple, clear terms.
When given code, you:
1. Identify the main purpose
2. Explain key concepts
3. Highlight important patterns
4. Suggest improvements

✓ Created skill: code-explainer
✓ Saved to ~/.lyra/skills/code-explainer.json

Usage: /code-explainer <code or file path>
Example: /code-explainer src/main.py
```

#### `/skill template list`

List available templates.

```bash
/skill template list
```

**Output:**
```
Available Skill Templates:

  prompt-skill
  Simple prompt-based skill for single-turn interactions
  
  agent-skill
  Multi-turn agent with conversation memory
  
  tool-skill
  Skill that executes external CLI tools
  
  composition-skill
  Multi-stage workflow with data passing
  
  research-skill
  Web research with synthesis and reporting
  
  code-gen-skill
  Code generation with validation and testing

Use '/skill new <template>' to create a skill from template
```

## 3. Skill Analytics and Usage Tracking

### 3.1 Concept

Track skill usage, performance, and effectiveness to help users understand which skills are most valuable and identify optimization opportunities.

### 3.2 Analytics Data Model

```python
# src/lyra_cli/cli/skill_analytics.py

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, List, Optional


@dataclass
class SkillInvocation:
    """Record of a single skill invocation."""
    skill_name: str
    timestamp: datetime
    duration_ms: int
    success: bool
    error: Optional[str] = None
    args_length: int = 0
    output_length: int = 0


@dataclass
class SkillStats:
    """Aggregated statistics for a skill."""
    skill_name: str
    total_invocations: int
    successful_invocations: int
    failed_invocations: int
    avg_duration_ms: float
    total_duration_ms: int
    first_used: datetime
    last_used: datetime
    success_rate: float


class SkillAnalytics:
    """Track and analyze skill usage."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = data_dir / "skill_usage.jsonl"
    
    def record_invocation(self, invocation: SkillInvocation):
        """Record a skill invocation."""
        record = {
            "skill_name": invocation.skill_name,
            "timestamp": invocation.timestamp.isoformat(),
            "duration_ms": invocation.duration_ms,
            "success": invocation.success,
            "error": invocation.error,
            "args_length": invocation.args_length,
            "output_length": invocation.output_length
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record) + "\n")
    
    def get_stats(self, skill_name: Optional[str] = None) -> Dict[str, SkillStats]:
        """Get aggregated statistics for skills.
        
        Args:
            skill_name: If provided, return stats for specific skill only
        
        Returns:
            Dict of skill_name -> SkillStats
        """
        if not self.log_file.exists():
            return {}
        
        # Parse log file
        invocations: Dict[str, List[SkillInvocation]] = {}
        
        with open(self.log_file) as f:
            for line in f:
                record = json.loads(line)
                name = record["skill_name"]
                
                if skill_name and name != skill_name:
                    continue
                
                if name not in invocations:
                    invocations[name] = []
                
                invocations[name].append(SkillInvocation(
                    skill_name=name,
                    timestamp=datetime.fromisoformat(record["timestamp"]),
                    duration_ms=record["duration_ms"],
                    success=record["success"],
                    error=record.get("error"),
                    args_length=record.get("args_length", 0),
                    output_length=record.get("output_length", 0)
                ))
        
        # Compute statistics
        stats = {}
        for name, invocs in invocations.items():
            total = len(invocs)
            successful = sum(1 for i in invocs if i.success)
            failed = total - successful
            total_duration = sum(i.duration_ms for i in invocs)
            avg_duration = total_duration / total if total > 0 else 0
            
            timestamps = [i.timestamp for i in invocs]
            first_used = min(timestamps)
            last_used = max(timestamps)
            
            success_rate = (successful / total * 100) if total > 0 else 0
            
            stats[name] = SkillStats(
                skill_name=name,
                total_invocations=total,
                successful_invocations=successful,
                failed_invocations=failed,
                avg_duration_ms=avg_duration,
                total_duration_ms=total_duration,
                first_used=first_used,
                last_used=last_used,
                success_rate=success_rate
            )
        
        return stats
    
    def get_top_skills(self, limit: int = 10, sort_by: str = "invocations") -> List[SkillStats]:
        """Get top skills by usage or performance.
        
        Args:
            limit: Maximum number of skills to return
            sort_by: Sort criteria - "invocations", "duration", "success_rate"
        
        Returns:
            List of SkillStats sorted by criteria
        """
        stats = self.get_stats()
        
        if sort_by == "invocations":
            sorted_stats = sorted(
                stats.values(),
                key=lambda s: s.total_invocations,
                reverse=True
            )
        elif sort_by == "duration":
            sorted_stats = sorted(
                stats.values(),
                key=lambda s: s.total_duration_ms,
                reverse=True
            )
        elif sort_by == "success_rate":
            sorted_stats = sorted(
                stats.values(),
                key=lambda s: s.success_rate,
                reverse=True
            )
        else:
            sorted_stats = list(stats.values())
        
        return sorted_stats[:limit]
```

### 3.3 Commands

#### `/skill stats [name]`

Show usage statistics for skills.

```bash
/skill stats                    # All skills
/skill stats auto-research      # Specific skill
```

**Output (all skills):**
```
Skill Usage Statistics

Top Skills by Invocations:
  1. auto-research        142 invocations  (98.6% success)  avg 2.3s
  2. code-reviewer         89 invocations  (100% success)   avg 1.8s
  3. tdd-guide            67 invocations  (95.5% success)  avg 3.1s
  4. doc-writer           45 invocations  (100% success)   avg 1.2s
  5. refactor-helper      34 invocations  (97.1% success)  avg 2.7s

Total invocations: 377
Average success rate: 98.2%
Total time saved: 14.2 hours

Use '/skill stats <name>' for detailed statistics
```

**Output (specific skill):**
```
Statistics for auto-research

Usage:
  Total invocations: 142
  Successful: 140 (98.6%)
  Failed: 2 (1.4%)
  
Performance:
  Average duration: 2.3s
  Total time: 5.4 hours
  
Timeline:
  First used: 2026-04-15 09:23:14
  Last used: 2026-05-16 14:32:08
  Days active: 31
  
Recent Failures:
  2026-05-14 11:45:23 - Network timeout
  2026-05-10 16:12:45 - Rate limit exceeded
```

#### `/skill analytics export`

Export analytics data for external analysis.

```bash
/skill analytics export --format csv --output skill_usage.csv
```

## 4. Advanced Skill Configuration

### 4.1 Concept

Allow users to customize skill behavior through configuration files, enabling personalization without modifying skill definitions.

### 4.2 Configuration Format

#### User Configuration File

Location: `~/.lyra/skill_config.json`

```json
{
  "skills": {
    "auto-research": {
      "max_sources": 10,
      "search_depth": "deep",
      "output_format": "markdown",
      "include_citations": true,
      "custom_prompt_suffix": "Focus on recent developments (last 2 years)"
    },
    "code-reviewer": {
      "severity_threshold": "medium",
      "check_security": true,
      "check_performance": true,
      "check_style": false,
      "max_issues": 20
    },
    "tdd-guide": {
      "test_framework": "pytest",
      "coverage_threshold": 80,
      "generate_fixtures": true,
      "mock_external_deps": true
    }
  },
  "global": {
    "timeout_seconds": 300,
    "retry_on_failure": true,
    "max_retries": 3,
    "log_level": "info"
  }
}
```

### 4.3 Configuration Schema

Each skill can define its configuration schema:

```json
{
  "name": "auto-research",
  "config_schema": {
    "max_sources": {
      "type": "integer",
      "default": 5,
      "min": 1,
      "max": 20,
      "description": "Maximum number of sources to search"
    },
    "search_depth": {
      "type": "string",
      "default": "normal",
      "choices": ["quick", "normal", "deep"],
      "description": "How thoroughly to search"
    },
    "output_format": {
      "type": "string",
      "default": "markdown",
      "choices": ["markdown", "plain", "json"],
      "description": "Output format for research results"
    },
    "include_citations": {
      "type": "boolean",
      "default": true,
      "description": "Include source citations in output"
    }
  }
}
```

### 4.4 Commands

#### `/skill config <name>`

Configure a skill interactively.

```bash
/skill config auto-research
```

**Interactive Flow:**
```
Configuring: auto-research

Current Configuration:
  max_sources: 5 (default)
  search_depth: normal (default)
  output_format: markdown (default)
  include_citations: true (default)

Options:
  1. max_sources (1-20) [current: 5]
  2. search_depth (quick/normal/deep) [current: normal]
  3. output_format (markdown/plain/json) [current: markdown]
  4. include_citations (true/false) [current: true]
  5. Save and exit
  6. Reset to defaults

Select option (1-6): 1
Enter value for max_sources (1-20): 10

Select option (1-6): 2
Enter value for search_depth (quick/normal/deep): deep

Select option (1-6): 5

✓ Configuration saved to ~/.lyra/skill_config.json

New configuration:
  max_sources: 10
  search_depth: deep
  output_format: markdown
  include_citations: true
```

#### `/skill config list`

List all configured skills.

```bash
/skill config list
```

**Output:**
```
Configured Skills:

  auto-research
    max_sources: 10 (default: 5)
    search_depth: deep (default: normal)
    
  code-reviewer
    severity_threshold: medium (default: low)
    check_security: true (default: true)
    check_performance: true (default: false)
    
  tdd-guide
    test_framework: pytest (default: pytest)
    coverage_threshold: 80 (default: 80)

Use '/skill config <name>' to modify configuration
Use '/skill config reset <name>' to reset to defaults
```

## 5. Implementation Plan

### Phase 4.1: Skill Composition (Week 1-2)

1. Implement `CompositionEngine` class
2. Add composition execution to skill manager
3. Create `/skill compose` command
4. Write unit tests for composition engine
5. Write integration tests for multi-stage workflows

### Phase 4.2: Skill Templates (Week 3)

1. Define template format and built-in templates
2. Implement template rendering engine
3. Create `/skill new` and `/skill template` commands
4. Write tests for template system
5. Document template creation guide

### Phase 4.3: Analytics (Week 4)

1. Implement `SkillAnalytics` class
2. Add invocation tracking to skill execution
3. Create `/skill stats` and `/skill analytics` commands
4. Write tests for analytics system
5. Add analytics dashboard (optional)

### Phase 4.4: Configuration (Week 5)

1. Define configuration schema format
2. Implement configuration loading and validation
3. Create `/skill config` commands
4. Integrate configuration with skill execution
5. Write tests for configuration system

### Phase 4.5: Integration and Testing (Week 6)

1. Integration testing across all Phase 4 features
2. Performance optimization
3. Documentation updates
4. User acceptance testing
5. Bug fixes and polish

## 6. Testing Strategy

### Unit Tests

1. **CompositionEngine Tests**
   - Variable interpolation
   - Stage execution
   - Error handling
   - Context management

2. **Template Tests**
   - Template rendering
   - Variable validation
   - Built-in templates

3. **Analytics Tests**
   - Invocation recording
   - Statistics computation
   - Data export

4. **Configuration Tests**
   - Schema validation
   - Configuration loading
   - Default values

### Integration Tests

1. **End-to-End Composition**
   - Multi-stage workflow execution
   - Data passing between stages
   - Error propagation

2. **Template to Execution**
   - Create skill from template
   - Execute created skill
   - Verify behavior

3. **Analytics Collection**
   - Execute skills
   - Verify analytics recorded
   - Query statistics

4. **Configuration Application**
   - Configure skill
   - Execute with custom config
   - Verify behavior changes

## 7. Success Metrics

- **Composition**: 80% of power users create at least one composition skill
- **Templates**: 90% of new skills created using templates
- **Analytics**: Users can identify top 5 most-used skills
- **Configuration**: 60% of users customize at least one skill

## 8. Future Enhancements

1. **Visual Composition Builder** - Drag-and-drop workflow designer
2. **Skill Marketplace Integration** - Share compositions and templates
3. **Advanced Analytics** - ML-based skill recommendations
4. **A/B Testing** - Compare different skill configurations
5. **Skill Versioning** - Track configuration changes over time
