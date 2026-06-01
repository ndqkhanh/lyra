# Skills, Tools & Plugins Systems: Deep Research Report

**Research Date:** 2026-05-29  
**Researcher:** Senior AI Systems Architect  
**Target System:** Lyra Agent Harness

---

## Executive Summary

This report synthesizes breakthrough insights from 8+ leading AI agent systems to design a world-class extensibility architecture for Lyra. Key findings:

### 🎯 Core Breakthrough Insights

1. **Skills as Text-Space Neural Training** (SkillOpt): Skills evolve through trajectory-driven edits using epoch-based optimization without weight updates
2. **Knowing-Doing Gap** (Academic Research): Models excel at determining *when* to use tools but struggle with *how* to execute them effectively
3. **Network Learning Effect** (SkillOS): "One agent learns, all agents level up" - approved skills propagate across the entire agent network
4. **Harness-Agnostic Core** (ECC): Same skills/agents work across Claude Code, Cursor, OpenCode, Codex through adapter pattern
5. **Plugin Component Isolation** (Claude Code): Skills, agents, hooks, MCP servers, LSP servers, monitors as composable units

### 📊 Quantified Impact

- **SkillOS**: Demonstrates measurable improvement loop (↓ cost, ↓ time, ↑ quality per job)
- **SkillOpt**: Validation-gated updates ensure only improvements are retained
- **Academic Research Skills**: 31% error rate in initial implementation → systematic verification gates
- **ECC AgentShield**: 1282 tests, 102 rules, 3-agent red-team/blue-team/auditor pipeline

### 🚀 Recommended Architecture

**Three-Layer Extensibility System:**
1. **Skills Layer**: Declarative workflows with auto-learning and evolution
2. **Tools Layer**: Sandboxed execution with parameter validation and composition
3. **Plugins Layer**: Self-contained component bundles with lifecycle management

---

## 1. Skills Architecture Patterns

### 1.1 Skill Definition Formats

#### Claude Code Format (Industry Standard)

**Structure**: Markdown with YAML frontmatter

```yaml
---
name: skill-name
description: What this skill does and when to invoke it
tools: ["Read", "Grep", "Glob", "Bash"]
model: opus
effort: medium
maxTurns: 20
allowed-tools: ["Read", "Write", "Bash"]
disallowed-tools: ["WebFetch"]
---

# Skill Instructions

Detailed instructions for Claude on how to execute this skill.
Can include code examples, decision trees, and reference material.
```

**Key Features:**
- **Frontmatter metadata**: Controls execution context (model, tools, effort)
- **Tool scoping**: Explicit allow/deny lists for security
- **Model routing**: Pin skills to specific models (haiku/sonnet/opus)
- **Auto-discovery**: Files named `SKILL.md` in `skills/` directory
- **Supporting files**: Can include `reference.md`, `scripts/`, etc.

#### ECC Multi-Surface Format

**Structure**: Same markdown + YAML, but with cross-harness adapters

```yaml
---
name: skill-name
description: Skill purpose
tools: ["Read", "Grep", "Glob", "Bash"]
model: opus
shell: powershell  # Cross-platform shell selection
---
```

**Adapter Pattern:**
- `.claude-plugin/` - Claude Code native
- `.cursor/` - Cursor IDE (20 hook events vs Claude's 8)
- `.opencode/` - OpenCode (11+ plugin events)
- `.codex/` - Codex app/CLI with TOML config
- `.zed/`, `.gemini/`, `.agents/` - Additional harness adapters

**Breakthrough**: Same skill definition works across 6+ AI coding environments

#### Academic Research Skills Format

**Structure**: Multi-agent pipeline with quality gates

```yaml
---
status: production
data_access_level: verified_only  # raw/redacted/verified_only
task_type: outcome-gradable  # open-ended/outcome-gradable
---

# Agent Teams (7-13 specialized agents)
# Modes (full/quick/guided/socratic/systematic-review)
# Quality Gates (mandatory checkpoints with integrity verification)
```

**Key Innovations:**
- **Material Passport**: Cross-stage data handoff schema
- **Ground Truth Isolation**: Three data access levels prevent contamination
- **Anti-Hallucination**: Semantic Scholar + OpenAlex + Crossref triangulation
- **Cross-Model Verification**: Optional secondary model for integrity checks

#### SkillOS Format

**Structure**: Natural language documents that evolve

```markdown
# Skill: Sales Follow-up Email

## Context
Generate professional follow-up emails from call notes.

## Execution Steps
1. Extract key points from call notes
2. Identify action items and commitments
3. Draft email with professional tone
4. Include next steps and timeline

## Success Criteria
- All action items mentioned
- Professional tone maintained
- Clear next steps defined
```

**Breakthrough**: Skills stored as `best_skill.md` with versioned snapshots, evolved through trajectory-driven edits

### 1.2 Skill Discovery and Indexing

#### Claude Code Discovery Mechanism

**Auto-Discovery Rules:**
1. Scan `skills/` directory for `<name>/SKILL.md` structure
2. Scan `commands/` directory for flat `.md` files (legacy)
3. Single `SKILL.md` at plugin root (single-skill plugins)
4. Custom paths via `plugin.json` manifest

**Indexing Strategy:**
```json
{
  "skills": {
    "code-reviewer": {
      "path": "skills/code-reviewer/SKILL.md",
      "name": "code-reviewer",
      "description": "Review code for quality and security",
      "tools": ["Read", "Grep", "LSP"],
      "model": "opus",
      "tokenCost": {
        "alwaysOn": 100,
        "onInvoke": 2400
      }
    }
  }
}
```

**Token Cost Tracking:**
- **Always-on cost**: Skill description in every session
- **On-invoke cost**: Full skill content when executed
- Helps users understand context budget impact

#### ECC Discovery with State Store

**SQLite-Based Tracking:**
```sql
CREATE TABLE skills (
  id TEXT PRIMARY KEY,
  name TEXT,
  path TEXT,
  source TEXT,  -- plugin, project, user
  confidence REAL,  -- learned skills have confidence scores
  last_used TIMESTAMP,
  success_count INTEGER,
  failure_count INTEGER
);

CREATE TABLE skill_triggers (
  skill_id TEXT,
  trigger_pattern TEXT,
  trigger_type TEXT,  -- keyword, context, explicit
  FOREIGN KEY (skill_id) REFERENCES skills(id)
);
```

**Breakthrough**: Tracks skill effectiveness and auto-suggests based on success patterns

#### Obsidian Skills Discovery

**Agent Skills Specification Compliance:**
- Each skill in own directory: `skills/<skill-name>/SKILL.md`
- Auto-discovered by compatible agents
- No config changes needed
- Requires restart to load new skills

**Multi-Harness Support:**
- Claude Code: Place in `/.claude` folder at vault root
- Codex CLI: Copy `skills/` to `~/.codex/skills`
- OpenCode: Clone to `~/.opencode/skills/obsidian-skills/`

### 1.3 Skill Composition and Chaining

#### Sequential Composition (Pipeline Pattern)

**Example: Feature Development Pipeline**
```
/plan → /tdd → /implement → /code-review → /security-scan → /commit
```

**Implementation:**
```yaml
---
name: feature-pipeline
description: Complete feature development workflow
---

Execute in sequence:
1. Invoke planner skill to create implementation plan
2. Invoke tdd-guide skill to write tests first
3. Implement feature to pass tests
4. Invoke code-reviewer skill for quality check
5. Invoke security-reviewer skill for security analysis
6. Create commit with conventional commit message
```

#### Parallel Composition (Multi-Agent Pattern)

**Example: Comprehensive Code Analysis**
```yaml
---
name: deep-analysis
description: Multi-perspective code analysis
---

Launch in parallel:
1. Security analysis agent → security vulnerabilities
2. Performance analysis agent → bottlenecks and optimizations
3. Architecture analysis agent → design patterns and structure
4. Test coverage agent → coverage gaps and test quality

Synthesize results into unified report.
```

#### Conditional Composition (Decision Tree Pattern)

**Example: Smart Deployment**
```yaml
---
name: smart-deploy
description: Context-aware deployment
---

1. Check current branch
   - If main/master → production deployment
   - If staging → staging deployment
   - If feature/* → preview deployment

2. Run appropriate test suite
   - Production: full test suite + smoke tests
   - Staging: integration tests
   - Preview: unit tests only

3. Deploy with appropriate strategy
   - Production: blue-green deployment
   - Staging: rolling update
   - Preview: direct deployment
```

#### Skill Dependencies (Prerequisite Pattern)

**Example: Database Migration Skill**
```yaml
---
name: db-migrate
description: Run database migrations safely
dependencies:
  - backup-db  # Must run first
  - verify-schema  # Must validate before migration
---

1. Invoke backup-db skill
2. Invoke verify-schema skill
3. If verification passes:
   - Run migrations
   - Verify migration success
4. If migration fails:
   - Invoke restore-db skill
```

### 1.4 Skill Versioning and Lifecycle Management

#### SkillOpt Versioning Strategy

**Snapshot-Based Versioning:**
```
skills/
├── best_skill.md           # Current best version
├── history.json            # Training history
├── snapshots/
│   ├── epoch_001.md
│   ├── epoch_002.md
│   ├── epoch_003.md
│   └── epoch_004.md
└── runtime_state.json      # Checkpoint for resume
```

**Version Selection Logic:**
1. Validation-gated updates: Only accept improvements
2. Per-epoch snapshots enable rollback
3. Best version promoted after validation passes
4. Failed experiments preserved for analysis

#### Claude Code Plugin Versioning

**Semantic Versioning with Git Integration:**
```json
{
  "name": "my-plugin",
  "version": "2.1.0",  // Explicit version (optional)
  "repository": "https://github.com/user/plugin"
}
```

**Version Resolution Priority:**
1. `version` in `plugin.json` (explicit control)
2. `version` in marketplace entry
3. Git commit SHA (auto-versioning)
4. `unknown` (for non-git sources)

**Update Behavior:**
- **Explicit version**: Users get updates only when version bumped
- **Commit-SHA version**: Users get updates on every commit
- **Cache key**: Version determines if update needed

**Lifecycle Stages:**
```
Development → Testing → Staging → Production → Deprecated → Archived
```

#### ECC Skill Evolution Lifecycle

**Continuous Learning System:**
```
Session Execution → Trace Collection → Pattern Extraction → 
Skill Candidate → Testing → Approval → Skill Release → 
Network Propagation
```

**Instinct-Based Learning:**
```bash
/instinct-status   # View learned patterns with confidence scores
/evolve            # Cluster instincts into reusable skills
```

**Confidence Scoring:**
- Initial: 0.3 (newly learned)
- Validated: 0.7 (tested successfully)
- Proven: 0.9+ (multiple successful uses)

### 1.5 Skill Conflict Resolution

#### Namespace Collision Handling

**Plugin Namespacing (Claude Code):**
```
plugin-name:skill-name
```

**Example:**
- `ecc:code-review` (from ECC plugin)
- `custom:code-review` (from custom plugin)
- `code-review` (built-in, no namespace)

**Resolution Priority:**
1. Explicit namespace: `plugin:skill`
2. Project-local skills
3. User-global skills
4. Plugin skills (alphabetical by plugin name)
5. Built-in skills

#### Semantic Conflict Detection

**Duplicate Functionality Detection:**
```python
def detect_skill_overlap(skill_a, skill_b):
    """Detect if two skills have overlapping functionality."""
    
    # Compare descriptions with semantic similarity
    desc_similarity = cosine_similarity(
        embed(skill_a.description),
        embed(skill_b.description)
    )
    
    # Compare tool usage patterns
    tool_overlap = len(
        set(skill_a.tools) & set(skill_b.tools)
    ) / len(set(skill_a.tools) | set(skill_b.tools))
    
    # Compare trigger patterns
    trigger_overlap = jaccard_similarity(
        skill_a.triggers, skill_b.triggers
    )
    
    # Weighted score
    overlap_score = (
        0.5 * desc_similarity +
        0.3 * tool_overlap +
        0.2 * trigger_overlap
    )
    
    return overlap_score > 0.7  # Threshold for conflict
```

**Conflict Resolution Strategies:**
1. **Merge**: Combine complementary skills
2. **Specialize**: Split overlapping skills by use case
3. **Deprecate**: Remove redundant skill
4. **Namespace**: Keep both with explicit namespaces

#### Version Conflict Resolution

**Dependency Version Constraints:**
```json
{
  "dependencies": [
    {
      "name": "secrets-vault",
      "version": "~2.1.0"  // Compatible with 2.1.x
    },
    {
      "name": "helper-lib",
      "version": "^1.0.0"  // Compatible with 1.x.x
    }
  ]
}
```

**Conflict Resolution:**
- **Exact match**: Use specified version
- **Range match**: Use highest compatible version
- **Incompatible**: Fail with clear error message
- **Transitive**: Resolve dependency tree depth-first

---

## 2. Intelligent Skill Management Systems

### 2.1 Auto-Curation Mechanisms

#### SkillOS Network Learning

**"One Agent Learns, All Agents Level Up"**

```
Agent A executes job → Generates trace → Extracts lesson →
Creates skill candidate → Tests skill → Approves skill →
Skill released to network → All authorized agents gain skill
```

**Curation Pipeline:**
1. **Trace Collection**: Capture successful execution patterns
2. **Lesson Discovery**: Extract reusable patterns from traces
3. **Skill Generation**: Create candidate skill from lesson
4. **Canary Testing**: Test skill on subset of agents
5. **Approval Gate**: Human or automated approval
6. **Network Release**: Propagate to all authorized agents

**Metrics Tracking:**
```json
{
  "skill_id": "sales-follow-up",
  "metrics": {
    "cost_per_job": {
      "before": 0.45,
      "after": 0.32,
      "improvement": "29%"
    },
    "time_per_job": {
      "before": 120,
      "after": 85,
      "improvement": "29%"
    },
    "quality_score": {
      "before": 7.2,
      "after": 8.9,
      "improvement": "24%"
    }
  }
}
```

#### ECC Instinct System

**Pattern Extraction from Sessions:**
```python
class InstinctExtractor:
    def extract_patterns(self, session_history):
        """Extract reusable patterns from session."""
        
        patterns = []
        
        # Tool usage patterns
        tool_sequences = self.find_tool_sequences(session_history)
        
        # Decision patterns
        decision_trees = self.extract_decision_logic(session_history)
        
        # Error recovery patterns
        recovery_strategies = self.find_recovery_patterns(session_history)
        
        # Success patterns
        success_paths = self.identify_success_paths(session_history)
        
        for pattern in [tool_sequences, decision_trees, 
                       recovery_strategies, success_paths]:
            if self.is_reusable(pattern):
                patterns.append({
                    'pattern': pattern,
                    'confidence': self.calculate_confidence(pattern),
                    'context': self.extract_context(pattern)
                })
        
        return patterns
```

**Clustering into Skills:**
```bash
/evolve  # Cluster similar instincts into cohesive skills
```

**Auto-Curation Rules:**
- Confidence > 0.7: Suggest as skill candidate
- Used 3+ times: High-value pattern
- Success rate > 80%: Reliable pattern
- Context-specific: Tag with appropriate triggers

#### Academic Research Skills Quality Gates

**Mandatory Integrity Checkpoints:**
```yaml
stages:
  - name: "Stage 2.5: INTEGRITY"
    mandatory: true
    checks:
      - claim_audit: verify_citations_against_sources
      - contamination_check: detect_hallucination_signals
      - ground_truth_isolation: validate_data_access_levels
      - cross_model_verification: secondary_model_check
    
  - name: "Stage 4.5: INTEGRITY"
    mandatory: true
    checks:
      - writing_quality: detect_ai_patterns
      - citation_emission: verify_anchor_tags
      - style_consistency: check_against_profile
```

**Five HIGH-WARN Violation Classes:**
1. Citation without retrieval audit trail
2. Claim contradicts retrieved source
3. Data access level violation
4. Cross-model disagreement > 2 points
5. AI-frequent term density > threshold

**Auto-Curation Decision:**
- All checks pass → Approve skill
- 1 HIGH-WARN → Flag for review
- 2+ HIGH-WARN → Reject, require fixes

### 2.2 Context-Aware Skill Activation

#### Trigger Pattern Matching

**Keyword Triggers (ECC):**
```json
{
  "triggers": {
    "autopilot": "autopilot",
    "ralph": "ralph",
    "ulw": "ultrawork",
    "ccg": "ccg",
    "ralplan": "ralplan",
    "deep interview": "deep-interview",
    "deslop": "ai-slop-cleaner",
    "anti-slop": "ai-slop-cleaner"
  }
}
```

**Context-Based Triggers:**
```python
def should_activate_skill(skill, context):
    """Determine if skill should activate based on context."""
    
    # File type matching
    if skill.file_patterns:
        if any(fnmatch(context.file, pattern) 
               for pattern in skill.file_patterns):
            return True
    
    # Project type matching
    if skill.project_types:
        if context.project_type in skill.project_types:
            return True
    
    # Task type matching
    if skill.task_types:
        if context.task_type in skill.task_types:
            return True
    
    # Semantic matching
    if skill.semantic_triggers:
        similarity = cosine_similarity(
            embed(context.user_prompt),
            embed(skill.semantic_triggers)
        )
        if similarity > 0.75:
            return True
    
    return False
```

**Example Context Triggers:**
```yaml
---
name: python-debugger
triggers:
  file_patterns: ["**/*.py"]
  error_patterns: ["Traceback", "Exception", "Error"]
  keywords: ["debug", "fix bug", "error"]
---

---
name: react-component-builder
triggers:
  file_patterns: ["**/*.tsx", "**/*.jsx"]
  project_markers: ["package.json with react"]
  keywords: ["component", "react", "ui"]
---
```

#### Intelligent Loading Strategies

**Lazy Loading (Claude Code):**
```typescript
class SkillLoader {
  private loadedSkills: Map<string, Skill> = new Map();
  private skillIndex: Map<string, SkillMetadata> = new Map();
  
  async loadSkillOnDemand(skillName: string): Promise<Skill> {
    // Check cache first
    if (this.loadedSkills.has(skillName)) {
      return this.loadedSkills.get(skillName)!;
    }
    
    // Load from disk
    const metadata = this.skillIndex.get(skillName);
    const skill = await this.loadSkillFromPath(metadata.path);
    
    // Cache for session
    this.loadedSkills.set(skillName, skill);
    
    return skill;
  }
  
  async preloadHighPrioritySkills(context: SessionContext) {
    // Preload based on project type
    const projectSkills = this.getSkillsForProject(context.projectType);
    
    // Preload based on recent usage
    const recentSkills = this.getRecentlyUsedSkills(context.userId);
    
    // Preload based on time of day / workflow patterns
    const predictedSkills = this.predictLikelySkills(context);
    
    const toPreload = new Set([
      ...projectSkills,
      ...recentSkills,
      ...predictedSkills
    ]);
    
    await Promise.all(
      Array.from(toPreload).map(name => this.loadSkillOnDemand(name))
    );
  }
}
```

**Token Budget Management:**
```typescript
interface SkillTokenCost {
  alwaysOn: number;   // Cost of skill being available (description)
  onInvoke: number;   // Cost when skill is executed (full content)
}

class TokenBudgetManager {
  private readonly MAX_ALWAYS_ON_BUDGET = 5000;  // tokens
  
  selectSkillsForSession(
    availableSkills: Skill[],
    context: SessionContext
  ): Skill[] {
    // Score skills by relevance
    const scored = availableSkills.map(skill => ({
      skill,
      relevance: this.calculateRelevance(skill, context),
      cost: skill.tokenCost.alwaysOn
    }));
    
    // Sort by relevance / cost ratio
    scored.sort((a, b) => 
      (b.relevance / b.cost) - (a.relevance / a.cost)
    );
    
    // Select skills within budget
    const selected: Skill[] = [];
    let totalCost = 0;
    
    for (const {skill, cost} of scored) {
      if (totalCost + cost <= this.MAX_ALWAYS_ON_BUDGET) {
        selected.push(skill);
        totalCost += cost;
      }
    }
    
    return selected;
  }
}
```

### 2.3 Skill Learning from Trajectories

#### SkillOpt Training Loop

**Epoch-Based Optimization:**
```python
class SkillOptimizer:
    def train_skill(
        self,
        initial_skill: str,
        train_data: List[Task],
        val_data: List[Task],
        num_epochs: int = 4,
        batch_size: int = 40
    ):
        """Train skill using trajectory-driven edits."""
        
        best_skill = initial_skill
        best_score = self.evaluate(best_skill, val_data)
        
        for epoch in range(num_epochs):
            # Collect trajectories
            trajectories = self.collect_trajectories(
                skill=best_skill,
                tasks=train_data,
                batch_size=batch_size
            )
            
            # Generate skill updates from trajectories
            skill_updates = self.generate_updates(trajectories)
            
            # Apply updates
            candidate_skill = self.apply_updates(
                best_skill, skill_updates
            )
            
            # Validation gate
            candidate_score = self.evaluate(candidate_skill, val_data)
            
            if candidate_score > best_score:
                # Accept improvement
                best_skill = candidate_skill
                best_score = candidate_score
                self.save_snapshot(best_skill, epoch)
            else:
                # Reject, keep previous best
                print(f"Epoch {epoch}: No improvement, keeping previous")
        
        return best_skill, best_score
```

**Trajectory-Driven Edits:**
```python
def generate_updates(self, trajectories: List[Trajectory]) -> List[Edit]:
    """Extract skill improvements from execution trajectories."""
    
    updates = []
    
    # Analyze successful trajectories
    successful = [t for t in trajectories if t.success]
    
    # Find common patterns in successful executions
    patterns = self.extract_patterns(successful)
    
    # Analyze failed trajectories
    failed = [t for t in trajectories if not t.success]
    
    # Find failure modes
    failure_modes = self.analyze_failures(failed)
    
    # Generate edits to incorporate successes and avoid failures
    for pattern in patterns:
        if pattern.frequency > 0.7:  # Appears in 70%+ of successes
            updates.append(Edit(
                type="add_pattern",
                content=pattern.description,
                location="execution_steps"
            ))
    
    for failure_mode in failure_modes:
        updates.append(Edit(
            type="add_guard",
            content=f"Avoid: {failure_mode.description}",
            location="constraints"
        ))
    
    return updates
```

### 2.4 Self-Evolution Mechanisms

#### Meta-Skill Generation

**SkillOpt Meta-Skills:**
```python
def generate_meta_skill(base_skills: List[Skill]) -> Skill:
    """Generate higher-level strategy skill from base skills."""
    
    # Analyze when each base skill succeeds
    success_contexts = {}
    for skill in base_skills:
        success_contexts[skill.name] = analyze_success_context(skill)
    
    # Generate decision logic
    meta_skill_content = f"""
# Meta-Skill: {generate_name(base_skills)}

## Strategy Selection

"""
    
    for skill_name, contexts in success_contexts.items():
        meta_skill_content += f"""
### Use {skill_name} when:
{format_contexts(contexts)}
"""
    
    meta_skill_content += """
## Execution Flow

1. Analyze current context
2. Select appropriate base skill
3. Execute selected skill
4. If fails, try alternative skill
5. Learn from outcome
"""
    
    return Skill(
        name=generate_name(base_skills),
        content=meta_skill_content,
        type="meta",
        base_skills=base_skills
    )
```

#### Adaptive Skill Refinement

**Model-Adaptive Training (Research Paper Insight):**
```python
def adaptive_skill_training(skill: Skill, model: LLM) -> Skill:
    """Adapt skill to specific model's capabilities."""
    
    # Assess model's inherent knowledge
    knowledge_gaps = assess_model_knowledge(model)
    
    # Generate model-specific necessity labels
    # (Different models need tools for different queries)
    necessity_labels = generate_adaptive_labels(
        skill.tasks,
        model,
        knowledge_gaps
    )
    
    # Train skill with model-specific labels
    adapted_skill = train_with_labels(
        skill,
        necessity_labels,
        model
    )
    
    # Validate knowing-doing gap
    knowing_score = evaluate_tool_necessity_detection(adapted_skill, model)
    doing_score = evaluate_tool_execution_quality(adapted_skill, model)
    
    if doing_score < knowing_score - 0.2:  # Significant gap
        # Apply representation engineering to bridge gap
        adapted_skill = apply_activation_steering(
            adapted_skill,
            model,
            target="improve_execution"
        )
    
    return adapted_skill
```

**Continuous Improvement Loop:**
```
Execute Skill → Collect Metrics → Analyze Performance →
Generate Improvements → Test Improvements → 
Validation Gate → Update if Better → Repeat
```

### 2.5 Auto-Evaluation Systems

#### SkillOpt Evaluation Framework

**Multi-Split Evaluation:**
```python
class SkillEvaluator:
    def evaluate(
        self,
        skill: Skill,
        eval_data: List[Task],
        metrics: List[str]
    ) -> Dict[str, float]:
        """Evaluate skill on multiple metrics."""
        
        results = {metric: [] for metric in metrics}
        
        for task in eval_data:
            # Execute skill on task
            output = self.execute_skill(skill, task)
            
            # Compute metrics
            for metric in metrics:
                score = self.compute_metric(
                    metric,
                    output,
                    task.expected_output
                )
                results[metric].append(score)
        
        # Aggregate results
        return {
            metric: np.mean(scores)
            for metric, scores in results.items()
        }
    
    def compute_metric(
        self,
        metric: str,
        output: Any,
        expected: Any
    ) -> float:
        """Compute specific metric."""
        
        if metric == "exact_match":
            return 1.0 if output == expected else 0.0
        
        elif metric == "f1_score":
            return self.compute_f1(output, expected)
        
        elif metric == "success_rate":
            return 1.0 if self.is_successful(output) else 0.0
        
        elif metric == "cost_efficiency":
            return expected.value / output.cost
        
        elif metric == "time_efficiency":
            return expected.time / output.time
        
        else:
            raise ValueError(f"Unknown metric: {metric}")
```

**Benchmark-Specific Metrics:**
- **SearchQA**: Exact match, F1 score
- **DocVQA**: ANLS (Average Normalized Levenshtein Similarity)
- **ALFWorld**: Success rate
- **LiveMathematicianBench**: Correctness, proof validity
- **SpreadsheetBench**: Formula accuracy, output correctness

#### ECC Success Tracking

**Session-Level Metrics:**
```typescript
interface SkillMetrics {
  skillId: string;
  executions: number;
  successes: number;
  failures: number;
  avgDuration: number;
  avgTokens: number;
  avgCost: number;
  userSatisfaction: number;  // 1-5 rating
  lastUsed: Date;
}

class SkillMetricsTracker {
  async recordExecution(
    skillId: string,
    result: SkillExecutionResult
  ) {
    const metrics = await this.getMetrics(skillId);
    
    metrics.executions++;
    if (result.success) {
      metrics.successes++;
    } else {
      metrics.failures++;
    }
    
    // Update running averages
    metrics.avgDuration = this.updateAverage(
      metrics.avgDuration,
      result.duration,
      metrics.executions
    );
    
    metrics.avgTokens = this.updateAverage(
      metrics.avgTokens,
      result.tokens,
      metrics.executions
    );
    
    metrics.avgCost = this.updateAverage(
      metrics.avgCost,
      result.cost,
      metrics.executions
    );
    
    metrics.lastUsed = new Date();
    
    await this.saveMetrics(metrics);
    
    // Auto-deprecate low-performing skills
    if (this.shouldDeprecate(metrics)) {
      await this.deprecateSkill(skillId);
    }
  }
  
  shouldDeprecate(metrics: SkillMetrics): boolean {
    // Deprecate if:
    // - Success rate < 50% after 10+ executions
    // - Not used in 90+ days
    // - User satisfaction < 2.0
    
    const successRate = metrics.successes / metrics.executions;
    const daysSinceUse = (Date.now() - metrics.lastUsed.getTime()) / (1000 * 60 * 60 * 24);
    
    return (
      (metrics.executions >= 10 && successRate < 0.5) ||
      daysSinceUse > 90 ||
      metrics.userSatisfaction < 2.0
    );
  }
}
```

### 2.6 Auto-Compaction Strategies

#### Redundancy Detection

**Semantic Similarity Analysis:**
```python
def detect_redundant_skills(skills: List[Skill]) -> List[Tuple[Skill, Skill]]:
    """Find pairs of skills with redundant functionality."""
    
    redundant_pairs = []
    
    for i, skill_a in enumerate(skills):
        for skill_b in skills[i+1:]:
            # Compute similarity
            similarity = compute_skill_similarity(skill_a, skill_b)
            
            if similarity > 0.85:  # High similarity threshold
                redundant_pairs.append((skill_a, skill_b))
    
    return redundant_pairs

def compute_skill_similarity(skill_a: Skill, skill_b: Skill) -> float:
    """Compute multi-dimensional similarity."""
    
    # Description similarity (semantic)
    desc_sim = cosine_similarity(
        embed(skill_a.description),
        embed(skill_b.description)
    )
    
    # Tool usage similarity
    tools_a = set(skill_a.tools)
    tools_b = set(skill_b.tools)
    tool_sim = len(tools_a & tools_b) / len(tools_a | tools_b)
    
    # Execution pattern similarity
    pattern_sim = compare_execution_patterns(skill_a, skill_b)
    
    # Outcome similarity
    outcome_sim = compare_outcomes(skill_a, skill_b)
    
    # Weighted average
    return (
        0.3 * desc_sim +
        0.2 * tool_sim +
        0.3 * pattern_sim +
        0.2 * outcome_sim
    )
```

**Merge Strategy:**
```python
def merge_redundant_skills(
    skill_a: Skill,
    skill_b: Skill,
    metrics_a: SkillMetrics,
    metrics_b: SkillMetrics
) -> Skill:
    """Merge two redundant skills into one."""
    
    # Choose better-performing skill as base
    if metrics_a.successes / metrics_a.executions > metrics_b.successes / metrics_b.executions:
        base_skill = skill_a
        other_skill = skill_b
    else:
        base_skill = skill_b
        other_skill = skill_a
    
    # Extract unique strengths from other skill
    unique_patterns = extract_unique_patterns(other_skill, base_skill)
    
    # Merge descriptions
    merged_description = f"{base_skill.description}. Also handles: {other_skill.description}"
    
    # Merge tools
    merged_tools = list(set(base_skill.tools + other_skill.tools))
    
    # Merge execution steps
    merged_steps = merge_execution_steps(
        base_skill.steps,
        other_skill.steps,
        unique_patterns
    )
    
    return Skill(
        name=base_skill.name,
        description=merged_description,
        tools=merged_tools,
        steps=merged_steps,
        merged_from=[base_skill.name, other_skill.name]
    )
```

#### Obsolescence Detection

**Usage-Based Pruning:**
```python
def identify_obsolete_skills(
    skills: List[Skill],
    metrics: Dict[str, SkillMetrics],
    time_window_days: int = 90
) -> List[Skill]:
    """Identify skills that are no longer useful."""
    
    obsolete = []
    cutoff_date = datetime.now() - timedelta(days=time_window_days)
    
    for skill in skills:
        skill_metrics = metrics.get(skill.name)
        
        if not skill_metrics:
            # Never used
            obsolete.append(skill)
            continue
        
        # Check last usage
        if skill_metrics.lastUsed < cutoff_date:
            obsolete.append(skill)
            continue
        
        # Check success rate
        if skill_metrics.executions >= 5:
            success_rate = skill_metrics.successes / skill_metrics.executions
            if success_rate < 0.3:  # Consistently failing
                obsolete.append(skill)
                continue
        
        # Check if superseded by better skill
        if is_superseded(skill, skills, metrics):
            obsolete.append(skill)
    
    return obsolete
```

---

## 3. Tools System Design

### 3.1 Tool Definition and Registration

#### Claude Code Tool Architecture

**Built-in Tools (40+ tools):**
```typescript
interface Tool {
  name: string;
  description: string;
  parameters: ToolParameters;
  permissionRequired: boolean;
  handler: ToolHandler;
}

interface ToolParameters {
  type: "object";
  properties: Record<string, ParameterSchema>;
  required: string[];
}

interface ParameterSchema {
  type: "string" | "number" | "boolean" | "array" | "object";
  description: string;
  enum?: any[];
  items?: ParameterSchema;
  properties?: Record<string, ParameterSchema>;
}
```

**Example Tool Definition:**
```typescript
const ReadTool: Tool = {
  name: "Read",
  description: "Reads a file from the local filesystem",
  parameters: {
    type: "object",
    properties: {
      file_path: {
        type: "string",
        description: "The absolute path to the file to read"
      },
      offset: {
        type: "number",
        description: "Line number to start reading from"
      },
      limit: {
        type: "number",
        description: "Number of lines to read"
      },
      pages: {
        type: "string",
        description: "Page range for PDF files (e.g., '1-5')"
      }
    },
    required: ["file_path"]
  },
  permissionRequired: false,
  handler: async (params) => {
    // Implementation
  }
};
```

**MCP Tool Registration:**
```typescript
class MCPToolRegistry {
  private tools: Map<string, MCPTool> = new Map();
  
  async registerServer(serverConfig: MCPServerConfig) {
    const client = await this.connectToServer(serverConfig);
    
    // List available tools
    const toolsList = await client.request("tools/list");
    
    // Register each tool
    for (const toolDef of toolsList.tools) {
      const tool: MCPTool = {
        name: `${serverConfig.name}:${toolDef.name}`,
        description: toolDef.description,
        parameters: toolDef.inputSchema,
        server: serverConfig.name,
        handler: async (params) => {
          return await client.request("tools/call", {
            name: toolDef.name,
            arguments: params
          });
        }
      };
      
      this.tools.set(tool.name, tool);
    }
  }
  
  getAvailableTools(): Tool[] {
    return Array.from(this.tools.values());
  }
}
```

#### Hermes Agent Tools Architecture

**Toolset Distribution System:**
```python
class ToolsetManager:
    """Manage logical groupings of tools."""
    
    def __init__(self):
        self.toolsets = {
            "core": ["Read", "Write", "Edit", "Bash"],
            "web": ["WebSearch", "WebFetch", "Browser"],
            "code": ["LSP", "Grep", "Glob", "Format"],
            "ai": ["ImageGen", "TTS", "Embedding"],
            "data": ["Database", "API", "FileSystem"]
        }
    
    def enable_toolset(self, name: str):
        """Enable all tools in a toolset."""
        tools = self.toolsets.get(name, [])
        for tool in tools:
            self.enable_tool(tool)
    
    def get_active_tools(self) -> List[str]:
        """Get currently active tools."""
        return [
            tool for tool in self.all_tools
            if self.is_enabled(tool)
        ]
```

**Backend Abstraction Layer:**
```python
class ToolBackend(ABC):
    """Abstract backend for tool execution."""
    
    @abstractmethod
    async def execute(self, command: str, **kwargs) -> ToolResult:
        pass

class LocalBackend(ToolBackend):
    async def execute(self, command: str, **kwargs) -> ToolResult:
        # Execute locally
        pass

class DockerBackend(ToolBackend):
    async def execute(self, command: str, **kwargs) -> ToolResult:
        # Execute in Docker container
        pass

class SSHBackend(ToolBackend):
    async def execute(self, command: str, **kwargs) -> ToolResult:
        # Execute on remote host via SSH
        pass

class ModalBackend(ToolBackend):
    async def execute(self, command: str, **kwargs) -> ToolResult:
        # Execute on Modal serverless
        pass
```

### 3.2 Parameter Validation and Type Safety

#### Zod-Based Validation (MCP Pattern)

```typescript
import { z } from "zod";

// Define parameter schema
const ReadToolSchema = z.object({
  file_path: z.string().describe("Absolute path to file"),
  offset: z.number().int().positive().optional(),
  limit: z.number().int().positive().optional(),
  pages: z.string().regex(/^\d+(-\d+)?$/).optional()
});

type ReadToolParams = z.infer<typeof ReadToolSchema>;

// Validate at runtime
function validateToolParams<T>(
  schema: z.ZodSchema<T>,
  params: unknown
): T {
  try {
    return schema.parse(params);
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new ToolValidationError(
        `Invalid parameters: ${error.errors.map(e => 
          `${e.path.join('.')}: ${e.message}`
        ).join(', ')}`
      );
    }
    throw error;
  }
}

// Use in tool handler
async function handleReadTool(params: unknown): Promise<ToolResult> {
  const validated = validateToolParams(ReadToolSchema, params);
  
  // Type-safe execution
  const content = await readFile(validated.file_path, {
    offset: validated.offset,
    limit: validated.limit,
    pages: validated.pages
  });
  
  return { success: true, content };
}
```

#### Runtime Type Checking

```python
from typing import TypedDict, Literal, Optional
from pydantic import BaseModel, Field, validator

class BashToolParams(BaseModel):
    """Type-safe Bash tool parameters."""
    
    command: str = Field(..., description="Shell command to execute")
    timeout: Optional[int] = Field(
        None,
        ge=1000,
        le=600000,
        description="Timeout in milliseconds"
    )
    run_in_background: bool = Field(
        False,
        description="Run as background task"
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable description"
    )
    
    @validator('command')
    def validate_command(cls, v):
        if not v.strip():
            raise ValueError("Command cannot be empty")
        
        # Security checks
        dangerous_patterns = ['rm -rf /', 'dd if=', ':(){ :|:& };:']
        for pattern in dangerous_patterns:
            if pattern in v:
                raise ValueError(f"Dangerous command pattern detected: {pattern}")
        
        return v
    
    class Config:
        extra = "forbid"  # Reject unknown fields

# Usage
def execute_bash_tool(params: dict) -> ToolResult:
    validated = BashToolParams(**params)
    return execute_command(validated.command, validated.timeout)
```

### 3.3 Tool Execution Sandboxing and Security

#### Permission System (Claude Code)

**Permission Modes:**
```typescript
enum PermissionMode {
  Default = "default",        // Prompt for dangerous operations
  AcceptEdits = "acceptEdits", // Auto-approve edits, prompt for Bash
  Auto = "auto",              // Auto-approve most operations
  BypassPermissions = "bypassPermissions" // No prompts (dangerous)
}

interface PermissionRule {
  tool: string;
  pattern?: string;
  allow?: boolean;
  deny?: boolean;
}

class PermissionManager {
  private rules: PermissionRule[] = [];
  private mode: PermissionMode = PermissionMode.Default;
  
  async checkPermission(
    tool: string,
    params: any
  ): Promise<PermissionResult> {
    // Check deny rules first
    for (const rule of this.rules) {
      if (rule.deny && this.matchesRule(tool, params, rule)) {
        return { allowed: false, reason: "Denied by rule" };
      }
    }
    
    // Check allow rules
    for (const rule of this.rules) {
      if (rule.allow && this.matchesRule(tool, params, rule)) {
        return { allowed: true };
      }
    }
    
    // Fall back to mode-based decision
    return this.checkByMode(tool, params);
  }
  
  private matchesRule(
    tool: string,
    params: any,
    rule: PermissionRule
  ): boolean {
    if (rule.tool !== tool) return false;
    
    if (!rule.pattern) return true;
    
    // Pattern matching based on tool type
    if (tool === "Bash") {
      return this.matchCommandPattern(params.command, rule.pattern);
    } else if (tool === "Read" || tool === "Edit") {
      return this.matchPathPattern(params.file_path, rule.pattern);
    }
    
    return false;
  }
}
```

**Sandbox Execution (ECC AgentShield):**
```typescript
interface SandboxConfig {
  allowedPaths: string[];
  deniedPaths: string[];
  allowedCommands: string[];
  deniedCommands: string[];
  networkAccess: boolean;
  maxMemory: number;
  maxCPU: number;
  timeout: number;
}

class SandboxExecutor {
  async executeInSandbox(
    command: string,
    config: SandboxConfig
  ): Promise<ExecutionResult> {
    // Create isolated environment
    const sandbox = await this.createSandbox(config);
    
    try {
      // Pre-execution security scan
      const securityCheck = await this.scanCommand(command);
      if (!securityCheck.safe) {
        throw new SecurityError(securityCheck.reason);
      }
      
      // Execute with resource limits
      const result = await sandbox.execute(command, {
        timeout: config.timeout,
        maxMemory: config.maxMemory,
        maxCPU: config.maxCPU
      });
      
      // Post-execution audit
      await this.auditExecution(command, result);
      
      return result;
    } finally {
      await sandbox.cleanup();
    }
  }
  
  private async scanCommand(command: string): Promise<SecurityScan> {
    // Three-agent security pipeline
    const redTeam = await this.runRedTeamAnalysis(command);
    const blueTeam = await this.runBlueTeamAnalysis(command);
    const auditor = await this.runAuditorAnalysis(command, redTeam, blueTeam);
    
    return auditor;
  }
}
```

#### Container Isolation (Hermes)

```python
class ContainerBackend:
    """Execute tools in isolated containers."""
    
    def __init__(self, image: str = "ubuntu:22.04"):
        self.image = image
        self.containers = {}
    
    async def execute(
        self,
        command: str,
        mounts: List[str] = None,
        env: Dict[str, str] = None
    ) -> ToolResult:
        # Create ephemeral container
        container = await self.create_container(
            image=self.image,
            command=command,
            mounts=mounts or [],
            env=env or {},
            network_mode="none",  # No network by default
            read_only=True,       # Read-only filesystem
            memory_limit="512m",
            cpu_quota=50000       # 50% of one CPU
        )
        
        try:
            # Execute with timeout
            result = await container.run(timeout=120)
            return ToolResult(
                success=result.exit_code == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_code
            )
        finally:
            # Always cleanup
            await container.remove(force=True)
```

### 3.4 Tool Composition and Orchestration

#### Sequential Tool Chains

```python
class ToolChain:
    """Execute tools in sequence with data flow."""
    
    def __init__(self, tools: List[Tool]):
        self.tools = tools
    
    async def execute(self, initial_input: Any) -> Any:
        result = initial_input
        
        for tool in self.tools:
            try:
                result = await tool.execute(result)
            except ToolError as e:
                # Handle error with fallback or retry
                result = await self.handle_error(tool, e, result)
        
        return result
    
    async def handle_error(
        self,
        tool: Tool,
        error: ToolError,
        input_data: Any
    ) -> Any:
        # Retry with exponential backoff
        for attempt in range(3):
            await asyncio.sleep(2 ** attempt)
            try:
                return await tool.execute(input_data)
            except ToolError:
                if attempt == 2:
                    raise
        
        raise error
```

#### Parallel Tool Execution

```typescript
class ParallelToolExecutor {
  async executeParallel(
    toolCalls: ToolCall[]
  ): Promise<ToolResult[]> {
    // Group by dependencies
    const groups = this.groupByDependencies(toolCalls);
    
    const results: ToolResult[] = [];
    
    // Execute each group in parallel
    for (const group of groups) {
      const groupResults = await Promise.all(
        group.map(call => this.executeTool(call))
      );
      results.push(...groupResults);
    }
    
    return results;
  }
  
  private groupByDependencies(
    calls: ToolCall[]
  ): ToolCall[][] {
    // Build dependency graph
    const graph = new Map<string, Set<string>>();
    
    for (const call of calls) {
      graph.set(call.id, new Set(call.dependencies || []));
    }
    
    // Topological sort into execution groups
    return this.topologicalSort(graph, calls);
  }
}
```


### 6.2 Recommended Architecture for Lyra

#### Three-Layer Extensibility System

```
┌─────────────────────────────────────────────────────────────┐
│                     PLUGIN LAYER                             │
│  Self-contained bundles: skills + agents + hooks + MCP       │
│  Discovery, versioning, dependency management                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     SKILLS LAYER                             │
│  Declarative workflows with auto-learning and evolution      │
│  Trajectory extraction, validation gates, network learning   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     TOOLS LAYER                              │
│  Sandboxed execution, parameter validation, composition      │
│  Permission system, resource limits, audit logging           │
└─────────────────────────────────────────────────────────────┘
```

#### Component Design

**1. Skills System (lyra-skills)**

```python
# packages/lyra-skills/src/lyra_skills/core.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class SkillStatus(Enum):
    DRAFT = "draft"
    TESTING = "testing"
    VALIDATED = "validated"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"

@dataclass
class Skill:
    """Core skill definition."""
    name: str
    description: str
    content: str
    tools: List[str]
    model: str = "sonnet"
    status: SkillStatus = SkillStatus.DRAFT
    version: str = "1.0.0"
    confidence: float = 0.0
    metrics: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "tools": self.tools,
            "model": self.model,
            "status": self.status.value,
            "version": self.version,
            "confidence": self.confidence,
            "metrics": self.metrics
        }

class SkillRegistry:
    """Central registry for all skills."""
    
    def __init__(self, db_path: str):
        self.db = SkillDatabase(db_path)
        self.cache: Dict[str, Skill] = {}
    
    def register(self, skill: Skill) -> None:
        """Register a new skill."""
        self.db.insert(skill)
        self.cache[skill.name] = skill
    
    def get(self, name: str) -> Optional[Skill]:
        """Get skill by name."""
        if name in self.cache:
            return self.cache[name]
        
        skill = self.db.get(name)
        if skill:
            self.cache[name] = skill
        return skill
    
    def search(
        self,
        query: str,
        filters: Optional[Dict] = None
    ) -> List[Skill]:
        """Search skills by query and filters."""
        return self.db.search(query, filters)
    
    def update_metrics(
        self,
        name: str,
        metrics: Dict
    ) -> None:
        """Update skill metrics after execution."""
        skill = self.get(name)
        if skill:
            skill.metrics = metrics
            self.db.update(skill)
```

**2. Skill Learning Engine**

```python
# packages/lyra-skills/src/lyra_skills/learning.py

class SkillLearningEngine:
    """Extract skills from successful trajectories."""
    
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.trajectory_store = TrajectoryStore()
    
    async def learn_from_session(
        self,
        session_id: str
    ) -> List[Skill]:
        """Extract skill candidates from session."""
        
        # Get session trajectory
        trajectory = await self.trajectory_store.get(session_id)
        
        # Extract patterns
        patterns = self.extract_patterns(trajectory)
        
        # Generate skill candidates
        candidates = []
        for pattern in patterns:
            if self.is_reusable(pattern):
                skill = await self.generate_skill(pattern)
                candidates.append(skill)
        
        return candidates
    
    def extract_patterns(
        self,
        trajectory: Trajectory
    ) -> List[Pattern]:
        """Extract reusable patterns from trajectory."""
        
        patterns = []
        
        # Tool usage patterns
        tool_sequences = self.find_tool_sequences(trajectory)
        patterns.extend(tool_sequences)
        
        # Decision patterns
        decision_trees = self.extract_decision_logic(trajectory)
        patterns.extend(decision_trees)
        
        # Error recovery patterns
        recovery = self.find_recovery_patterns(trajectory)
        patterns.extend(recovery)
        
        return patterns
    
    async def generate_skill(
        self,
        pattern: Pattern
    ) -> Skill:
        """Generate skill from pattern."""
        
        # Use LLM to generate skill content
        prompt = f"""
Generate a reusable skill from this pattern:

Pattern Type: {pattern.type}
Context: {pattern.context}
Steps: {pattern.steps}
Success Rate: {pattern.success_rate}

Create a skill with:
1. Clear name and description
2. Step-by-step instructions
3. Tool requirements
4. Success criteria
"""
        
        response = await self.llm.generate(prompt)
        
        return Skill(
            name=self.generate_name(pattern),
            description=response.description,
            content=response.content,
            tools=pattern.tools,
            confidence=pattern.success_rate,
            status=SkillStatus.DRAFT
        )
```

**3. Skill Evolution System**

```python
# packages/lyra-skills/src/lyra_skills/evolution.py

class SkillEvolutionEngine:
    """Evolve skills through validation-gated updates."""
    
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.validator = SkillValidator()
    
    async def evolve_skill(
        self,
        skill_name: str,
        train_data: List[Task],
        val_data: List[Task],
        num_epochs: int = 4
    ) -> Skill:
        """Evolve skill using trajectory-driven edits."""
        
        skill = self.registry.get(skill_name)
        best_skill = skill
        best_score = await self.evaluate(skill, val_data)
        
        for epoch in range(num_epochs):
            # Collect trajectories
            trajectories = await self.collect_trajectories(
                skill=best_skill,
                tasks=train_data
            )
            
            # Generate updates
            updates = self.generate_updates(trajectories)
            
            # Apply updates
            candidate = self.apply_updates(best_skill, updates)
            
            # Validation gate
            candidate_score = await self.evaluate(candidate, val_data)
            
            if candidate_score > best_score:
                # Accept improvement
                best_skill = candidate
                best_score = candidate_score
                self.save_snapshot(best_skill, epoch)
            else:
                print(f"Epoch {epoch}: No improvement")
        
        # Update registry
        best_skill.status = SkillStatus.VALIDATED
        best_skill.confidence = best_score
        self.registry.register(best_skill)
        
        return best_skill
```

**4. Tools System (lyra-tools)**

```python
# packages/lyra-tools/src/lyra_tools/core.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class ToolParameters(BaseModel):
    """Base class for tool parameters with validation."""
    pass

class ToolResult(BaseModel):
    """Standard tool result format."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict = {}

class Tool(ABC):
    """Abstract base class for all tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @property
    @abstractmethod
    def parameters_schema(self) -> type[ToolParameters]:
        pass
    
    @abstractmethod
    async def execute(
        self,
        params: ToolParameters
    ) -> ToolResult:
        pass
    
    def validate_params(self, params: Dict) -> ToolParameters:
        """Validate and parse parameters."""
        return self.parameters_schema(**params)

class ToolRegistry:
    """Central registry for all tools."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.permissions = PermissionManager()
    
    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool
    
    async def execute(
        self,
        tool_name: str,
        params: Dict,
        context: ExecutionContext
    ) -> ToolResult:
        """Execute a tool with permission checks."""
        
        tool = self.tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool not found: {tool_name}"
            )
        
        # Check permissions
        if not await self.permissions.check(tool_name, params, context):
            return ToolResult(
                success=False,
                error=f"Permission denied for {tool_name}"
            )
        
        # Validate parameters
        try:
            validated_params = tool.validate_params(params)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Invalid parameters: {str(e)}"
            )
        
        # Execute with sandbox
        try:
            result = await self.execute_sandboxed(
                tool,
                validated_params,
                context
            )
            return result
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Execution failed: {str(e)}"
            )
```

**5. Plugin System (lyra-plugins)**

```python
# packages/lyra-plugins/src/lyra_plugins/core.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

@dataclass
class PluginManifest:
    """Plugin manifest definition."""
    name: str
    version: str
    description: str
    author: Optional[Dict] = None
    dependencies: List[Dict] = None
    skills_path: Optional[str] = None
    agents_path: Optional[str] = None
    hooks_path: Optional[str] = None
    mcp_servers: Optional[Dict] = None

class Plugin:
    """Plugin container."""
    
    def __init__(self, path: Path, manifest: PluginManifest):
        self.path = path
        self.manifest = manifest
        self.skills: List[Skill] = []
        self.agents: List[Agent] = []
        self.hooks: List[Hook] = []
    
    async def load(self) -> None:
        """Load all plugin components."""
        await self.load_skills()
        await self.load_agents()
        await self.load_hooks()
    
    async def load_skills(self) -> None:
        """Load skills from plugin."""
        if not self.manifest.skills_path:
            return
        
        skills_dir = self.path / self.manifest.skills_path
        for skill_file in skills_dir.glob("*/SKILL.md"):
            skill = await self.parse_skill(skill_file)
            self.skills.append(skill)

class PluginManager:
    """Manage plugin lifecycle."""
    
    def __init__(
        self,
        skill_registry: SkillRegistry,
        tool_registry: ToolRegistry
    ):
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry
        self.plugins: Dict[str, Plugin] = {}
    
    async def install_plugin(
        self,
        source: str,
        scope: str = "user"
    ) -> Plugin:
        """Install a plugin."""
        
        # Download/copy plugin
        plugin_path = await self.download_plugin(source)
        
        # Load manifest
        manifest = await self.load_manifest(plugin_path)
        
        # Resolve dependencies
        await self.resolve_dependencies(manifest)
        
        # Create plugin
        plugin = Plugin(plugin_path, manifest)
        await plugin.load()
        
        # Register components
        for skill in plugin.skills:
            self.skill_registry.register(skill)
        
        # Store plugin
        self.plugins[manifest.name] = plugin
        
        return plugin
    
    async def reload_plugin(self, name: str) -> None:
        """Reload a plugin."""
        plugin = self.plugins.get(name)
        if not plugin:
            raise ValueError(f"Plugin not found: {name}")
        
        # Unload current
        await self.unload_plugin(plugin)
        
        # Reload
        await plugin.load()
        
        # Re-register
        for skill in plugin.skills:
            self.skill_registry.register(skill)
```

### 6.3 Implementation Roadmap

#### Phase 1: Foundation (Weeks 1-2)

**Goals:**
- Implement core skill system
- Add skill registry with SQLite backend
- Create skill definition format (YAML + Markdown)

**Deliverables:**
- `lyra-skills` package with `Skill`, `SkillRegistry`
- Skill storage and retrieval
- Basic skill execution

**Success Criteria:**
- Can define skills in YAML + Markdown
- Can register and retrieve skills
- Can execute skills with tool calls

#### Phase 2: Tools Enhancement (Weeks 3-4)

**Goals:**
- Expand tool set (20+ tools)
- Add parameter validation with Pydantic
- Implement permission system

**Deliverables:**
- `lyra-tools` package with tool registry
- 20+ tools: Read, Write, Edit, Bash, Grep, Glob, LSP, etc.
- Permission manager with allow/deny rules

**Success Criteria:**
- All tools have type-safe parameters
- Permission system blocks unauthorized access
- Tools can be composed in sequences

#### Phase 3: Skill Learning (Weeks 5-6)

**Goals:**
- Implement trajectory collection
- Add pattern extraction
- Create skill generation from patterns

**Deliverables:**
- `SkillLearningEngine` with trajectory analysis
- Pattern extraction algorithms
- LLM-based skill generation

**Success Criteria:**
- Can extract patterns from sessions
- Can generate skill candidates
- Candidates have >0.7 confidence

#### Phase 4: Skill Evolution (Weeks 7-8)

**Goals:**
- Implement validation-gated updates
- Add epoch-based training
- Create snapshot versioning

**Deliverables:**
- `SkillEvolutionEngine` with training loop
- Validation framework
- Snapshot storage

**Success Criteria:**
- Skills improve through training
- Only improvements are retained
- Can rollback to previous versions

#### Phase 5: Plugin System (Weeks 9-10)

**Goals:**
- Implement plugin discovery
- Add plugin loading and caching
- Create dependency resolution

**Deliverables:**
- `lyra-plugins` package
- Plugin manifest format
- Plugin manager with lifecycle

**Success Criteria:**
- Can install plugins from GitHub
- Plugins can bundle skills/agents/hooks
- Dependencies are resolved correctly

#### Phase 6: Security & Sandboxing (Weeks 11-12)

**Goals:**
- Implement sandbox execution
- Add resource limits
- Create audit logging

**Deliverables:**
- Sandbox executor with Docker backend
- Resource limit enforcement
- Audit trail for all executions

**Success Criteria:**
- Tools run in isolated containers
- Resource limits are enforced
- All executions are logged

---

## 7. Skill Library Design

### 7.1 Engineering Skills (10 skills)

#### Backend Engineering

**1. api-designer**
- Design RESTful APIs with OpenAPI specs
- Generate endpoint definitions
- Create request/response schemas
- Tools: Read, Write, LSP

**2. database-architect**
- Design database schemas
- Create migrations
- Optimize queries
- Tools: Read, Write, Bash, LSP

**3. microservices-builder**
- Scaffold microservice architecture
- Set up service communication
- Implement health checks
- Tools: Read, Write, Bash, Grep

#### Frontend Engineering

**4. react-component-builder**
- Create React components with TypeScript
- Implement hooks and state management
- Add accessibility features
- Tools: Read, Write, Edit, LSP

**5. ui-designer**
- Design UI layouts with Tailwind CSS
- Create responsive designs
- Implement design systems
- Tools: Read, Write, Edit

#### DevOps & SRE

**6. ci-cd-engineer**
- Set up CI/CD pipelines
- Configure GitHub Actions / GitLab CI
- Implement deployment strategies
- Tools: Read, Write, Bash

**7. infrastructure-coder**
- Write Terraform / CloudFormation
- Manage Kubernetes manifests
- Configure cloud resources
- Tools: Read, Write, Bash, LSP

**8. monitoring-specialist**
- Set up observability stack
- Create dashboards and alerts
- Implement distributed tracing
- Tools: Read, Write, Bash

#### Cloud Engineering

**9. aws-architect**
- Design AWS architectures
- Configure services (EC2, S3, RDS, Lambda)
- Implement security best practices
- Tools: Read, Write, Bash

**10. kubernetes-operator**
- Manage Kubernetes clusters
- Deploy applications
- Troubleshoot issues
- Tools: Bash, Read, Grep

### 7.2 Design Skills (5 skills)

**11. system-designer**
- Create system architecture diagrams
- Design component interactions
- Document design decisions
- Tools: Read, Write

**12. ux-researcher**
- Conduct user research
- Create user personas
- Design user flows
- Tools: Read, Write, WebSearch

**13. ui-prototyper**
- Create wireframes and mockups
- Design interactive prototypes
- Implement design feedback
- Tools: Read, Write, Edit

**14. accessibility-auditor**
- Audit WCAG compliance
- Fix accessibility issues
- Implement ARIA attributes
- Tools: Read, Edit, LSP

**15. design-system-builder**
- Create design system documentation
- Build component libraries
- Maintain design tokens
- Tools: Read, Write, Edit

### 7.3 Research Skills (5 skills)

**16. ai-researcher**
- Conduct AI/ML research
- Review academic papers
- Implement research papers
- Tools: Read, Write, WebSearch, WebFetch

**17. market-analyst**
- Conduct market research
- Analyze competitors
- Create market reports
- Tools: WebSearch, WebFetch, Read, Write

**18. data-scientist**
- Analyze datasets
- Build ML models
- Create visualizations
- Tools: Read, Write, Bash, Python

**19. academic-writer**
- Write research papers
- Format citations
- Create bibliographies
- Tools: Read, Write, WebSearch

**20. literature-reviewer**
- Review academic literature
- Synthesize findings
- Create literature reviews
- Tools: Read, Write, WebSearch, WebFetch

### 7.4 Management Skills (5 skills)

**21. product-manager**
- Write PRDs
- Create roadmaps
- Prioritize features
- Tools: Read, Write

**22. business-analyst**
- Analyze requirements
- Create user stories
- Design workflows
- Tools: Read, Write

**23. project-planner**
- Create project plans
- Estimate timelines
- Track progress
- Tools: Read, Write

**24. technical-writer**
- Write documentation
- Create tutorials
- Maintain wikis
- Tools: Read, Write, Edit

**25. code-reviewer**
- Review code quality
- Check security issues
- Suggest improvements
- Tools: Read, Grep, LSP

### 7.5 Specialized Skills (5 skills)

**26. security-auditor**
- Audit security vulnerabilities
- Check OWASP Top 10
- Implement security fixes
- Tools: Read, Grep, LSP, Bash

**27. performance-optimizer**
- Profile performance
- Identify bottlenecks
- Implement optimizations
- Tools: Read, Bash, LSP

**28. test-engineer**
- Write unit tests
- Create integration tests
- Implement E2E tests
- Tools: Read, Write, Edit, Bash

**29. documentation-generator**
- Generate API docs
- Create README files
- Maintain changelogs
- Tools: Read, Write, LSP

**30. migration-specialist**
- Plan migrations
- Execute data migrations
- Validate migration success
- Tools: Read, Write, Bash

---

## 8. Conclusion

### 8.1 Key Takeaways

1. **Skills as Evolvable Assets**: Skills should be treated as first-class citizens that learn and improve over time through trajectory-driven edits and validation gates.

2. **Network Learning Effect**: Approved skills should propagate across the agent network, enabling "one agent learns, all agents level up."

3. **Three-Layer Architecture**: Separate concerns into plugins (packaging), skills (workflows), and tools (execution) for maximum flexibility.

4. **Security by Design**: Implement sandboxing, permission systems, and audit logging from the start, not as afterthoughts.

5. **Measurable Improvement**: Track metrics (cost, time, quality) to prove skills are actually improving, not just changing.

6. **Cross-Platform Compatibility**: Design for portability across different AI coding environments through adapter patterns.

### 8.2 Next Steps for Lyra

1. **Immediate (Next Sprint)**:
   - Implement core skill system with registry
   - Add 10 essential tools with validation
   - Create skill definition format

2. **Short-term (Next Month)**:
   - Add trajectory collection and pattern extraction
   - Implement skill learning engine
   - Create 20+ initial skills

3. **Medium-term (Next Quarter)**:
   - Build skill evolution system with validation gates
   - Implement plugin architecture
   - Add sandbox execution

4. **Long-term (Next 6 Months)**:
   - Deploy network learning across agent fleet
   - Build skill marketplace
   - Achieve measurable improvement metrics

### 8.3 Success Metrics

**Technical Metrics:**
- Skill execution success rate > 80%
- Skill evolution improvement rate > 20% per epoch
- Tool execution latency < 2 seconds (p95)
- Plugin load time < 500ms

**Business Metrics:**
- Cost per task reduction: 30%
- Time per task reduction: 30%
- Quality score improvement: 25%
- User satisfaction: 4.5/5.0

**Adoption Metrics:**
- 100+ skills in library
- 50+ plugins available
- 1000+ skill executions per day
- 90% of tasks use skills

---

## References

1. SkillOpt: https://github.com/microsoft/SkillOpt
2. SkillOS: https://github.com/MontrealAI/skillos
3. Claude Code Docs: https://code.claude.com/docs
4. ECC: https://github.com/affaan-m/ECC
5. Academic Research Skills: https://github.com/Imbad0202/academic-research-skills
6. Hermes Agent: https://github.com/nousresearch/hermes-agent
7. Obsidian Skills: https://github.com/kepano/obsidian-skills
8. Andrej Karpathy Skills: https://github.com/forrestchang/andrej-karpathy-skills

---

**End of Report**
