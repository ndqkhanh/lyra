# Intelligent Skills System: Part 2 - Creator, Evaluation, and Evolution

**Continuation of skills-system-breakthrough.md**

---

## 4. Skill Creator Patterns

### 4.1 Overview

The Skill Creator automatically generates new skills from patterns, templates, and successful trajectories. Research shows that **LLM-guided synthesis** combined with **formal validation** achieves the best results.

### 4.2 Template Generation

#### 4.2.1 Pattern Extraction

**Research Foundation**:
- [Program Synthesis (2026)](https://www.frontiersin.org/articles/10.3389/frai.2026.1816684) - AI-driven code generation
- [LLM-Guided Synthesis](https://arxiv.org/html/2503.15540) - Compositional program synthesis

**Implementation**:

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
import re

@dataclass
class ExecutionPattern:
    """Pattern extracted from execution trajectory."""
    pattern_type: str  # "tool_sequence", "decision_tree", "error_recovery"
    frequency: float  # How often this pattern appears
    success_rate: float  # Success rate when pattern is used
    context: Dict  # Context where pattern is effective
    steps: List[str]  # Sequence of steps
    tools_used: List[str]  # Tools involved
    
class PatternExtractor:
    """Extract reusable patterns from execution trajectories."""
    
    def __init__(self):
        self.min_frequency = 0.3  # Pattern must appear in 30%+ of executions
        self.min_success_rate = 0.7  # Pattern must succeed 70%+ of time
    
    def extract_patterns(
        self,
        trajectories: List['Trajectory']
    ) -> List[ExecutionPattern]:
        """Extract patterns from trajectories."""
        patterns = []
        
        # Extract tool sequences
        tool_patterns = self._extract_tool_sequences(trajectories)
        patterns.extend(tool_patterns)
        
        # Extract decision trees
        decision_patterns = self._extract_decision_trees(trajectories)
        patterns.extend(decision_patterns)
        
        # Extract error recovery patterns
        recovery_patterns = self._extract_recovery_patterns(trajectories)
        patterns.extend(recovery_patterns)
        
        # Filter by frequency and success rate
        filtered = [
            p for p in patterns
            if p.frequency >= self.min_frequency and
               p.success_rate >= self.min_success_rate
        ]
        
        return filtered
    
    def _extract_tool_sequences(
        self,
        trajectories: List['Trajectory']
    ) -> List[ExecutionPattern]:
        """Extract common tool usage sequences."""
        sequences = {}
        
        for traj in trajectories:
            # Extract tool sequence
            tools = [step.tool for step in traj.steps if step.tool]
            
            # Generate n-grams (sequences of length 2-5)
            for n in range(2, 6):
                for i in range(len(tools) - n + 1):
                    seq = tuple(tools[i:i+n])
                    
                    if seq not in sequences:
                        sequences[seq] = {'count': 0, 'successes': 0}
                    
                    sequences[seq]['count'] += 1
                    if traj.success:
                        sequences[seq]['successes'] += 1
        
        # Convert to patterns
        patterns = []
        total_trajs = len(trajectories)
        
        for seq, stats in sequences.items():
            frequency = stats['count'] / total_trajs
            success_rate = stats['successes'] / stats['count']
            
            patterns.append(ExecutionPattern(
                pattern_type="tool_sequence",
                frequency=frequency,
                success_rate=success_rate,
                context={},
                steps=[f"Use {tool}" for tool in seq],
                tools_used=list(seq)
            ))
        
        return patterns
    
    def _extract_decision_trees(
        self,
        trajectories: List['Trajectory']
    ) -> List[ExecutionPattern]:
        """Extract decision tree patterns."""
        # Simplified implementation
        # In practice, would use decision tree learning algorithms
        patterns = []
        
        # Group trajectories by context
        context_groups = {}
        for traj in trajectories:
            context_key = self._get_context_key(traj.context)
            if context_key not in context_groups:
                context_groups[context_key] = []
            context_groups[context_key].append(traj)
        
        # Extract patterns for each context
        for context_key, trajs in context_groups.items():
            if len(trajs) < 3:  # Need minimum samples
                continue
            
            # Find common decision points
            # (Simplified - would use actual decision tree algorithm)
            successful = [t for t in trajs if t.success]
            if len(successful) / len(trajs) >= 0.7:
                patterns.append(ExecutionPattern(
                    pattern_type="decision_tree",
                    frequency=len(trajs) / len(trajectories),
                    success_rate=len(successful) / len(trajs),
                    context=self._parse_context_key(context_key),
                    steps=self._extract_common_steps(successful),
                    tools_used=self._extract_common_tools(successful)
                ))
        
        return patterns
    
    def _extract_recovery_patterns(
        self,
        trajectories: List['Trajectory']
    ) -> List[ExecutionPattern]:
        """Extract error recovery patterns."""
        patterns = []
        
        # Find trajectories with errors that recovered
        recovered = [
            t for t in trajectories
            if t.had_errors and t.success
        ]
        
        if not recovered:
            return patterns
        
        # Analyze recovery strategies
        recovery_strategies = {}
        
        for traj in recovered:
            # Find error and recovery steps
            for i, step in enumerate(traj.steps):
                if step.error:
                    # Look at next few steps for recovery
                    recovery_steps = traj.steps[i+1:i+4]
                    recovery_key = tuple(s.action for s in recovery_steps)
                    
                    if recovery_key not in recovery_strategies:
                        recovery_strategies[recovery_key] = {
                            'count': 0,
                            'successes': 0
                        }
                    
                    recovery_strategies[recovery_key]['count'] += 1
                    if traj.success:
                        recovery_strategies[recovery_key]['successes'] += 1
        
        # Convert to patterns
        for recovery_key, stats in recovery_strategies.items():
            if stats['count'] >= 2:  # Seen at least twice
                patterns.append(ExecutionPattern(
                    pattern_type="error_recovery",
                    frequency=stats['count'] / len(trajectories),
                    success_rate=stats['successes'] / stats['count'],
                    context={},
                    steps=list(recovery_key),
                    tools_used=[]
                ))
        
        return patterns
    
    def _get_context_key(self, context: Dict) -> str:
        """Generate context key for grouping."""
        return f"{context.get('task_type')}:{context.get('language')}:{context.get('framework')}"
    
    def _parse_context_key(self, key: str) -> Dict:
        """Parse context key back to dict."""
        parts = key.split(':')
        return {
            'task_type': parts[0],
            'language': parts[1],
            'framework': parts[2]
        }
    
    def _extract_common_steps(self, trajectories: List['Trajectory']) -> List[str]:
        """Extract common steps from trajectories."""
        # Simplified - would use sequence alignment
        if not trajectories:
            return []
        
        # Return steps from most successful trajectory
        best = max(trajectories, key=lambda t: t.quality_score or 0)
        return [step.action for step in best.steps]
    
    def _extract_common_tools(self, trajectories: List['Trajectory']) -> List[str]:
        """Extract common tools from trajectories."""
        tool_counts = {}
        
        for traj in trajectories:
            for step in traj.steps:
                if step.tool:
                    tool_counts[step.tool] = tool_counts.get(step.tool, 0) + 1
        
        # Return tools used in majority of trajectories
        threshold = len(trajectories) * 0.5
        return [tool for tool, count in tool_counts.items() if count >= threshold]
```

#### 4.2.2 Template Library

```python
from typing import Dict, List
from jinja2 import Template

class SkillTemplateLibrary:
    """Library of skill templates."""
    
    def __init__(self):
        self.templates: Dict[str, Template] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default skill templates."""
        
        # Tool sequence template
        self.templates['tool_sequence'] = Template("""---
name: {{ name }}
description: {{ description }}
version: 1.0.0
tools: {{ tools | tojson }}
---

# {{ name }}

{{ description }}

## When to Use

{{ when_to_use }}

## Workflow

{% for step in steps %}
{{ loop.index }}. {{ step }}
{% endfor %}

## Success Criteria

- All steps completed successfully
- Expected output generated
- No errors encountered
""")
        
        # Decision tree template
        self.templates['decision_tree'] = Template("""---
name: {{ name }}
description: {{ description }}
version: 1.0.0
tools: {{ tools | tojson }}
---

# {{ name }}

{{ description }}

## Decision Logic

{% for decision in decisions %}
### {{ decision.condition }}

{{ decision.action }}

{% endfor %}

## Execution Flow

1. Analyze current context
2. Evaluate decision conditions
3. Execute appropriate action
4. Verify outcome
""")
        
        # Error recovery template
        self.templates['error_recovery'] = Template("""---
name: {{ name }}
description: {{ description }}
version: 1.0.0
tools: {{ tools | tojson }}
---

# {{ name }}

{{ description }}

## Error Handling

{% for error_type, recovery in error_handlers.items() %}
### {{ error_type }}

Recovery strategy:
{{ recovery }}

{% endfor %}

## Recovery Workflow

1. Detect error type
2. Select recovery strategy
3. Execute recovery steps
4. Verify recovery success
5. Resume or fail gracefully
""")
    
    def generate_skill(
        self,
        pattern: ExecutionPattern,
        **kwargs
    ) -> str:
        """Generate skill from pattern using template."""
        template = self.templates.get(pattern.pattern_type)
        
        if not template:
            raise ValueError(f"No template for pattern type: {pattern.pattern_type}")
        
        # Prepare template variables
        variables = {
            'name': kwargs.get('name', self._generate_name(pattern)),
            'description': kwargs.get('description', self._generate_description(pattern)),
            'tools': pattern.tools_used,
            'steps': pattern.steps,
            **kwargs
        }
        
        return template.render(**variables)
    
    def _generate_name(self, pattern: ExecutionPattern) -> str:
        """Generate skill name from pattern."""
        if pattern.pattern_type == "tool_sequence":
            tools_str = "-".join(pattern.tools_used[:3])
            return f"auto-{tools_str}"
        elif pattern.pattern_type == "decision_tree":
            context = pattern.context
            return f"auto-{context.get('task_type', 'task')}-handler"
        elif pattern.pattern_type == "error_recovery":
            return f"auto-error-recovery"
        
        return "auto-generated-skill"
    
    def _generate_description(self, pattern: ExecutionPattern) -> str:
        """Generate skill description from pattern."""
        if pattern.pattern_type == "tool_sequence":
            return f"Automatically generated skill using {', '.join(pattern.tools_used)}"
        elif pattern.pattern_type == "decision_tree":
            return f"Context-aware skill for {pattern.context.get('task_type', 'tasks')}"
        elif pattern.pattern_type == "error_recovery":
            return "Automatically generated error recovery skill"
        
        return "Automatically generated skill"
```

### 4.3 Code Synthesis

#### 4.3.1 LLM-Based Generation

**Research Foundation**:
- [Self-Improving Language Models (2025)](https://arxiv.org/html/2507.14172v2) - Evolutionary program synthesis
- [LLM-Assisted Synthesis](https://arxiv.org/html/2410.14835v2) - High-assurance programs

**Implementation**:

```python
from typing import Optional, List
import anthropic

class SkillSynthesizer:
    """Synthesize skills using LLM."""
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-opus-4-20250514"
    
    async def synthesize_from_pattern(
        self,
        pattern: ExecutionPattern,
        examples: Optional[List['Trajectory']] = None
    ) -> str:
        """Synthesize skill from pattern."""
        
        # Build prompt
        prompt = self._build_synthesis_prompt(pattern, examples)
        
        # Generate skill
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        skill_content = response.content[0].text
        
        return skill_content
    
    def _build_synthesis_prompt(
        self,
        pattern: ExecutionPattern,
        examples: Optional[List['Trajectory']]
    ) -> str:
        """Build prompt for skill synthesis."""
        
        prompt = f"""Generate a reusable skill from the following pattern:

Pattern Type: {pattern.pattern_type}
Frequency: {pattern.frequency:.2%}
Success Rate: {pattern.success_rate:.2%}
Tools Used: {', '.join(pattern.tools_used)}

Steps:
"""
        
        for i, step in enumerate(pattern.steps, 1):
            prompt += f"{i}. {step}\n"
        
        if pattern.context:
            prompt += f"\nContext: {pattern.context}\n"
        
        if examples:
            prompt += "\n## Example Executions\n\n"
            for i, traj in enumerate(examples[:3], 1):
                prompt += f"### Example {i}\n"
                prompt += f"Success: {traj.success}\n"
                prompt += f"Steps: {len(traj.steps)}\n"
                prompt += "\n"
        
        prompt += """
Create a skill in the following format:

---
name: skill-name
description: Clear description of what this skill does
version: 1.0.0
tools: [list, of, tools]
---

# Skill Name

Brief introduction.

## When to Use

- Scenario 1
- Scenario 2

## Workflow

1. Step 1
2. Step 2
3. Step 3

## Success Criteria

- Criterion 1
- Criterion 2

Make the skill:
1. Clear and actionable
2. Reusable across similar contexts
3. Well-documented
4. Include error handling
"""
        
        return prompt
    
    async def refine_skill(
        self,
        skill_content: str,
        feedback: str
    ) -> str:
        """Refine skill based on feedback."""
        
        prompt = f"""Refine the following skill based on feedback:

## Current Skill

{skill_content}

## Feedback

{feedback}

## Instructions

Improve the skill to address the feedback while maintaining its core functionality.
Return the complete refined skill in the same format.
"""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        return response.content[0].text
```

### 4.4 Validation

#### 4.4.1 Static Analysis

```python
import ast
from typing import List, Tuple

class SkillValidator:
    """Validate generated skills."""
    
    def __init__(self):
        self.required_fields = ['name', 'description', 'version', 'tools']
    
    def validate(self, skill_content: str) -> Tuple[bool, List[str]]:
        """Validate skill content."""
        issues = []
        
        # Parse frontmatter
        try:
            frontmatter, content = self._parse_skill(skill_content)
        except Exception as e:
            return False, [f"Failed to parse skill: {e}"]
        
        # Check required fields
        for field in self.required_fields:
            if field not in frontmatter:
                issues.append(f"Missing required field: {field}")
        
        # Validate name
        if 'name' in frontmatter:
            if not self._is_valid_name(frontmatter['name']):
                issues.append(f"Invalid skill name: {frontmatter['name']}")
        
        # Validate version
        if 'version' in frontmatter:
            if not self._is_valid_version(frontmatter['version']):
                issues.append(f"Invalid version: {frontmatter['version']}")
        
        # Validate tools
        if 'tools' in frontmatter:
            if not isinstance(frontmatter['tools'], list):
                issues.append("Tools must be a list")
        
        # Check content structure
        if not content.strip():
            issues.append("Skill content is empty")
        
        # Check for required sections
        required_sections = ['When to Use', 'Workflow']
        for section in required_sections:
            if f"## {section}" not in content:
                issues.append(f"Missing required section: {section}")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def _parse_skill(self, content: str) -> Tuple[Dict, str]:
        """Parse skill frontmatter and content."""
        import yaml
        
        # Split frontmatter and content
        parts = content.split('---', 2)
        if len(parts) < 3:
            raise ValueError("Invalid skill format: missing frontmatter")
        
        frontmatter = yaml.safe_load(parts[1])
        skill_content = parts[2].strip()
        
        return frontmatter, skill_content
    
    def _is_valid_name(self, name: str) -> bool:
        """Check if skill name is valid."""
        import re
        # Allow alphanumeric, hyphens, underscores
        return bool(re.match(r'^[a-z0-9-_]+$', name))
    
    def _is_valid_version(self, version: str) -> bool:
        """Check if version is valid semver."""
        import re
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))
```

### 4.5 Quality Scoring

**Research Foundation**:
- [Code Quality Metrics (2026)](https://www.qodo.ai/glossary/code-quality-metrics/) - Quality benchmarks
- [Software Metrics Guide](https://oobeya.io/blog/software-engineering-metrics-complete-guide-2026) - Comprehensive metrics

**Implementation**:

```python
from typing import Dict
import re

class SkillQualityScorer:
    """Score skill quality."""
    
    def __init__(self):
        self.weights = {
            'completeness': 0.3,
            'clarity': 0.25,
            'reusability': 0.2,
            'documentation': 0.15,
            'maintainability': 0.1
        }
    
    def score(self, skill_content: str) -> Dict[str, float]:
        """Score skill quality."""
        scores = {}
        
        # Completeness score
        scores['completeness'] = self._score_completeness(skill_content)
        
        # Clarity score
        scores['clarity'] = self._score_clarity(skill_content)
        
        # Reusability score
        scores['reusability'] = self._score_reusability(skill_content)
        
        # Documentation score
        scores['documentation'] = self._score_documentation(skill_content)
        
        # Maintainability score
        scores['maintainability'] = self._score_maintainability(skill_content)
        
        # Overall score
        scores['overall'] = sum(
            scores[key] * self.weights[key]
            for key in self.weights
        )
        
        return scores
    
    def _score_completeness(self, content: str) -> float:
        """Score completeness (0-1)."""
        score = 0.0
        
        # Check for required sections
        required_sections = [
            'When to Use',
            'Workflow',
            'Success Criteria'
        ]
        
        for section in required_sections:
            if f"## {section}" in content:
                score += 1.0 / len(required_sections)
        
        return score
    
    def _score_clarity(self, content: str) -> float:
        """Score clarity (0-1)."""
        score = 1.0
        
        # Penalize very short descriptions
        if len(content) < 200:
            score -= 0.3
        
        # Penalize unclear language
        unclear_phrases = ['maybe', 'possibly', 'might', 'could be']
        for phrase in unclear_phrases:
            if phrase in content.lower():
                score -= 0.1
        
        # Reward clear structure
        if re.search(r'^\d+\.', content, re.MULTILINE):
            score += 0.2
        
        return max(0.0, min(1.0, score))
    
    def _score_reusability(self, content: str) -> float:
        """Score reusability (0-1)."""
        score = 0.5  # Base score
        
        # Reward parameterization
        if 'parameter' in content.lower() or 'input' in content.lower():
            score += 0.2
        
        # Reward context awareness
        if 'context' in content.lower() or 'when' in content.lower():
            score += 0.2
        
        # Penalize hardcoded values
        if re.search(r'["\']\/[^"\']+["\']', content):  # Hardcoded paths
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _score_documentation(self, content: str) -> float:
        """Score documentation quality (0-1)."""
        score = 0.0
        
        # Check for examples
        if '## Example' in content or '```' in content:
            score += 0.4
        
        # Check for error handling documentation
        if 'error' in content.lower() or 'failure' in content.lower():
            score += 0.3
        
        # Check for references
        if 'http' in content or 'reference' in content.lower():
            score += 0.3
        
        return score
    
    def _score_maintainability(self, content: str) -> float:
        """Score maintainability (0-1)."""
        score = 1.0
        
        # Penalize excessive length
        if len(content) > 5000:
            score -= 0.2
        
        # Penalize complexity
        num_steps = len(re.findall(r'^\d+\.', content, re.MULTILINE))
        if num_steps > 20:
            score -= 0.3
        
        # Reward modularity
        if 'invoke' in content.lower() or 'call' in content.lower():
            score += 0.2
        
        return max(0.0, min(1.0, score))
```

---

## 5. Auto-Evaluation Framework

### 5.1 Overview

The Auto-Evaluation Framework continuously assesses skill performance using multiple metrics and detects regressions. Research shows that **multi-metric evaluation** with **statistical monitoring** is essential.

### 5.2 Success Metrics

**Research Foundation**:
- [SkillOpt Evaluation](https://github.com/microsoft/SkillOpt) - Multi-split evaluation
- [Continuous Monitoring (2026)](https://tianpan.co/blog/2026-05-04-continuous-production-eval-statistical-quality-monitoring-llm-traffic) - Statistical quality monitoring

**Implementation**:

```python
from typing import Dict, List, Optional
from dataclasses import dataclass
import numpy as np

@dataclass
class EvaluationResult:
    """Result of skill evaluation."""
    skill_name: str
    version: str
    metrics: Dict[str, float]
    passed: bool
    issues: List[str]
    timestamp: datetime

class SkillEvaluator:
    """Evaluate skill performance."""
    
    def __init__(self):
        self.metric_thresholds = {
            'success_rate': 0.8,
            'avg_duration_ms': 5000,
            'avg_cost_usd': 0.10,
            'quality_score': 7.0
        }
    
    async def evaluate(
        self,
        skill_name: str,
        version: str,
        test_cases: List['TestCase']
    ) -> EvaluationResult:
        """Evaluate skill on test cases."""
        
        results = []
        
        for test_case in test_cases:
            result = await self._execute_test_case(
                skill_name,
                version,
                test_case
            )
            results.append(result)
        
        # Compute metrics
        metrics = self._compute_metrics(results)
        
        # Check thresholds
        passed, issues = self._check_thresholds(metrics)
        
        return EvaluationResult(
            skill_name=skill_name,
            version=version,
            metrics=metrics,
            passed=passed,
            issues=issues,
            timestamp=datetime.now()
        )
    
    async def _execute_test_case(
        self,
        skill_name: str,
        version: str,
        test_case: 'TestCase'
    ) -> Dict:
        """Execute single test case."""
        start_time = datetime.now()
        
        try:
            # Execute skill
            output = await self._execute_skill(
                skill_name,
                version,
                test_case.input
            )
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            # Check correctness
            correct = self._check_correctness(
                output,
                test_case.expected_output
            )
            
            return {
                'success': correct,
                'duration_ms': duration,
                'tokens': output.get('tokens', 0),
                'cost': output.get('cost', 0.0),
                'quality': output.get('quality', None)
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return {
                'success': False,
                'duration_ms': duration,
                'tokens': 0,
                'cost': 0.0,
                'quality': None,
                'error': str(e)
            }
    
    def _compute_metrics(self, results: List[Dict]) -> Dict[str, float]:
        """Compute aggregate metrics."""
        if not results:
            return {}
        
        successes = sum(1 for r in results if r['success'])
        
        metrics = {
            'success_rate': successes / len(results),
            'avg_duration_ms': np.mean([r['duration_ms'] for r in results]),
            'p95_duration_ms': np.percentile([r['duration_ms'] for r in results], 95),
            'avg_tokens': np.mean([r['tokens'] for r in results]),
            'avg_cost_usd': np.mean([r['cost'] for r in results]),
        }
        
        # Quality score (if available)
        quality_scores = [r['quality'] for r in results if r['quality'] is not None]
        if quality_scores:
            metrics['quality_score'] = np.mean(quality_scores)
        
        return metrics
    
    def _check_thresholds(
        self,
        metrics: Dict[str, float]
    ) -> Tuple[bool, List[str]]:
        """Check if metrics meet thresholds."""
        issues = []
        
        for metric, threshold in self.metric_thresholds.items():
            if metric not in metrics:
                continue
            
            value = metrics[metric]
            
            if metric == 'success_rate' and value < threshold:
                issues.append(
                    f"Success rate {value:.2%} below threshold {threshold:.2%}"
                )
            elif metric == 'avg_duration_ms' and value > threshold:
                issues.append(
                    f"Average duration {value:.0f}ms above threshold {threshold:.0f}ms"
                )
            elif metric == 'avg_cost_usd' and value > threshold:
                issues.append(
                    f"Average cost ${value:.4f} above threshold ${threshold:.4f}"
                )
            elif metric == 'quality_score' and value < threshold:
                issues.append(
                    f"Quality score {value:.1f} below threshold {threshold:.1f}"
                )
        
        passed = len(issues) == 0
        return passed, issues
```

**Continued in Part 3...**
