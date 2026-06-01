# Lyra Skills System Architecture

## Overview

The Lyra Skills System is an intelligent, self-evolving ecosystem that enables specialized capabilities through modular, discoverable, and automatically optimized skills. It provides curator, loader, manager, creator, auto-evaluation, and self-evolution capabilities.

## Core Principles

1. **Zero-Dependency Core**: Skills are self-contained with no external dependencies
2. **Progressive Disclosure**: Show only relevant skills based on context
3. **Lazy Loading**: Load skills on-demand to minimize overhead
4. **Self-Evolution**: Continuously improve through usage analysis
5. **Quality First**: Every skill must pass automated quality gates

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Lyra Skills System                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Curator    │  │   Manager    │  │   Creator    │      │
│  │              │  │              │  │              │      │
│  │ - Discovery  │  │ - Lifecycle  │  │ - Templates  │      │
│  │ - Scoring    │  │ - Versioning │  │ - Learning   │      │
│  │ - Loading    │  │ - Deps       │  │ - Builder    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Auto-Eval    │  │ Self-Evolve  │  │  Registry    │      │
│  │              │  │              │  │              │      │
│  │ - Metrics    │  │ - Analysis   │  │ - Index      │      │
│  │ - Benchmarks │  │ - Optimize   │  │ - Search     │      │
│  │ - Testing    │  │ - Pruning    │  │ - Cache      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Skill Definition Format

### Metadata Schema

```typescript
interface SkillMetadata {
  id: string;                    // Unique identifier (e.g., "frontend-react")
  name: string;                  // Display name
  version: string;               // Semantic version (e.g., "1.2.0")
  description: string;           // Brief description
  category: SkillCategory;       // Primary category
  tags: string[];                // Searchable tags
  author: {
    name: string;
    email?: string;
    url?: string;
  };
  
  // Trigger configuration
  triggers: {
    keywords?: string[];         // Auto-trigger on keywords
    patterns?: RegExp[];         // Auto-trigger on patterns
    fileTypes?: string[];        // Auto-trigger on file extensions
    contexts?: string[];         // Required context (e.g., "git", "node")
  };
  
  // Dependencies
  dependencies?: {
    skills?: string[];           // Required skills
    tools?: string[];            // Required tools
    minVersion?: string;         // Min Lyra version
  };
  
  // Quality metrics
  quality: {
    coverage?: number;           // Test coverage %
    rating?: number;             // User rating (1-5)
    usage?: number;              // Usage count
    successRate?: number;        // Success rate %
  };
  
  // Lifecycle
  status: "stable" | "beta" | "experimental" | "deprecated";
  createdAt: string;
  updatedAt: string;
}
```

### Skill Categories

```typescript
enum SkillCategory {
  // Engineering
  FRONTEND = "frontend",
  BACKEND = "backend",
  DEVOPS = "devops",
  TESTING = "testing",
  DEBUGGING = "debugging",
  
  // Design
  UI_UX = "ui-ux",
  SYSTEM_DESIGN = "system-design",
  API_DESIGN = "api-design",
  DATABASE_DESIGN = "database-design",
  
  // SRE
  MONITORING = "monitoring",
  INCIDENT_RESPONSE = "incident-response",
  CAPACITY_PLANNING = "capacity-planning",
  RELIABILITY = "reliability",
  
  // AI/ML
  AI_RESEARCH = "ai-research",
  MODEL_TRAINING = "model-training",
  DATA_SCIENCE = "data-science",
  
  // Architecture
  SOLUTION_ARCHITECTURE = "solution-architecture",
  CLOUD_ENGINEERING = "cloud-engineering",
  SECURITY = "security",
  
  // Product & Business
  PRODUCT_MANAGEMENT = "product-management",
  BUSINESS_ANALYSIS = "business-analysis",
  BRAINSTORMING = "brainstorming",
}
```

### Skill Implementation Structure

```
skill-name/
├── skill.json              # Metadata
├── README.md               # Documentation
├── prompt.md               # Main skill prompt
├── examples/               # Usage examples
│   ├── example1.md
│   └── example2.md
├── tests/                  # Test cases
│   ├── test1.yaml
│   └── test2.yaml
├── benchmarks/             # Performance benchmarks
│   └── benchmark.yaml
└── hooks/                  # Optional lifecycle hooks
    ├── pre-execute.ts
    └── post-execute.ts
```

### Skill Lifecycle

```
Discovery → Validation → Loading → Execution → Evaluation → Evolution
    ↓           ↓           ↓          ↓            ↓           ↓
  Curator    Manager     Loader     Runtime      Auto-Eval   Self-Evolve
```

**Phases:**

1. **Discovery**: Curator finds skills from local, global, and remote sources
2. **Validation**: Manager validates metadata, dependencies, and quality
3. **Loading**: Loader loads skill on-demand (lazy) or at startup (eager)
4. **Execution**: Runtime executes skill with context injection
5. **Evaluation**: Auto-Eval measures quality, performance, and outcomes
6. **Evolution**: Self-Evolve optimizes, improves, or prunes skills

## Component 1: Skills Curator

### Responsibilities

- Discover skills from multiple sources
- Score relevance based on context
- Manage intelligent loading strategies
- Implement progressive disclosure

### Discovery Sources

```typescript
interface SkillSource {
  type: "local" | "global" | "remote" | "marketplace";
  path: string;
  priority: number;
  enabled: boolean;
}

const defaultSources: SkillSource[] = [
  { type: "local", path: "./.lyra/skills", priority: 100, enabled: true },
  { type: "global", path: "~/.lyra/skills", priority: 80, enabled: true },
  { type: "remote", path: "https://skills.lyra.dev", priority: 50, enabled: true },
];
```

### Relevance Scoring Algorithm

```typescript
interface RelevanceScore {
  skill: SkillMetadata;
  score: number;
  reasons: string[];
}

function calculateRelevance(
  skill: SkillMetadata,
  context: ExecutionContext
): RelevanceScore {
  let score = 0;
  const reasons: string[] = [];
  
  // Keyword matching (0-30 points)
  const keywordMatches = skill.triggers.keywords?.filter(k =>
    context.userInput.toLowerCase().includes(k.toLowerCase())
  ) || [];
  score += Math.min(keywordMatches.length * 10, 30);
  if (keywordMatches.length > 0) {
    reasons.push(`Keywords: ${keywordMatches.join(", ")}`);
  }
  
  // File type matching (0-20 points)
  const fileTypeMatches = skill.triggers.fileTypes?.filter(ft =>
    context.files.some(f => f.endsWith(ft))
  ) || [];
  score += Math.min(fileTypeMatches.length * 10, 20);
  if (fileTypeMatches.length > 0) {
    reasons.push(`File types: ${fileTypeMatches.join(", ")}`);
  }
  
  // Context matching (0-20 points)
  const contextMatches = skill.triggers.contexts?.filter(c =>
    context.availableContexts.includes(c)
  ) || [];
  score += Math.min(contextMatches.length * 10, 20);
  
  // Quality metrics (0-30 points)
  score += (skill.quality.rating || 0) * 6;
  score += (skill.quality.successRate || 0) * 0.3;
  
  return { skill, score, reasons };
}
```

### Loading Strategies

```typescript
enum LoadingStrategy {
  LAZY = "lazy",           // Load on first use
  EAGER = "eager",         // Load at startup
  PREDICTIVE = "predictive", // Load based on prediction
  MANUAL = "manual",       // Load only when explicitly requested
}

class SkillLoader {
  private cache = new Map<string, Skill>();
  private loadingPromises = new Map<string, Promise<Skill>>();
  
  async load(skillId: string, strategy: LoadingStrategy): Promise<Skill> {
    // Check cache first
    if (this.cache.has(skillId)) {
      return this.cache.get(skillId)!;
    }
    
    // Prevent duplicate loading
    if (this.loadingPromises.has(skillId)) {
      return this.loadingPromises.get(skillId)!;
    }
    
    const promise = this.loadSkill(skillId);
    this.loadingPromises.set(skillId, promise);
    
    try {
      const skill = await promise;
      this.cache.set(skillId, skill);
      return skill;
    } finally {
      this.loadingPromises.delete(skillId);
    }
  }
  
  private async loadSkill(skillId: string): Promise<Skill> {
    const metadata = await this.loadMetadata(skillId);
    const prompt = await this.loadPrompt(skillId);
    const examples = await this.loadExamples(skillId);
    
    return {
      metadata,
      prompt,
      examples,
      execute: this.createExecutor(metadata, prompt),
    };
  }
}
```

### Progressive Disclosure

```typescript
interface DisclosureConfig {
  maxSkillsShown: number;      // Max skills to show at once
  minRelevanceScore: number;   // Min score to show
  groupByCategory: boolean;    // Group by category
  showReasons: boolean;        // Show relevance reasons
}

function discloseSkills(
  scores: RelevanceScore[],
  config: DisclosureConfig
): RelevanceScore[] {
  return scores
    .filter(s => s.score >= config.minRelevanceScore)
    .sort((a, b) => b.score - a.score)
    .slice(0, config.maxSkillsShown);
}
```

## Component 2: Skills Manager

### Responsibilities

- Manage skill lifecycle (install, update, remove)
- Handle version control and compatibility
- Resolve dependencies
- Detect and resolve conflicts

### Lifecycle Management

```typescript
class SkillManager {
  async install(skillId: string, version?: string): Promise<void> {
    // 1. Validate skill exists
    const metadata = await this.fetchMetadata(skillId, version);
    
    // 2. Check compatibility
    await this.checkCompatibility(metadata);
    
    // 3. Resolve dependencies
    const deps = await this.resolveDependencies(metadata);
    
    // 4. Install dependencies first
    for (const dep of deps) {
      await this.install(dep.id, dep.version);
    }
    
    // 5. Download and install skill
    await this.downloadSkill(skillId, version);
    
    // 6. Run post-install hooks
    await this.runHooks(skillId, "post-install");
    
    // 7. Update registry
    await this.registry.add(metadata);
  }
  
  async update(skillId: string, targetVersion?: string): Promise<void> {
    const current = await this.registry.get(skillId);
    const latest = await this.fetchLatestVersion(skillId);
    const target = targetVersion || latest.version;
    
    if (current.version === target) {
      return; // Already up to date
    }
    
    // Check breaking changes
    const breaking = await this.checkBreakingChanges(
      current.version,
      target
    );
    
    if (breaking.length > 0) {
      throw new Error(
        `Breaking changes detected: ${breaking.join(", ")}`
      );
    }
    
    await this.install(skillId, target);
  }
  
  async remove(skillId: string): Promise<void> {
    // 1. Check if other skills depend on this
    const dependents = await this.findDependents(skillId);
    
    if (dependents.length > 0) {
      throw new Error(
        `Cannot remove ${skillId}: required by ${dependents.join(", ")}`
      );
    }
    
    // 2. Run pre-remove hooks
    await this.runHooks(skillId, "pre-remove");
    
    // 3. Remove skill files
    await this.deleteSkillFiles(skillId);
    
    // 4. Update registry
    await this.registry.remove(skillId);
  }
}
```

### Dependency Resolution

```typescript
interface Dependency {
  id: string;
  version: string;
  optional: boolean;
}

class DependencyResolver {
  async resolve(skill: SkillMetadata): Promise<Dependency[]> {
    const deps: Dependency[] = [];
    const visited = new Set<string>();
    
    await this.resolveDependencies(skill, deps, visited);
    
    // Topological sort to ensure correct install order
    return this.topologicalSort(deps);
  }
  
  private async resolveDependencies(
    skill: SkillMetadata,
    deps: Dependency[],
    visited: Set<string>
  ): Promise<void> {
    if (visited.has(skill.id)) {
      return; // Already processed
    }
    
    visited.add(skill.id);
    
    for (const depId of skill.dependencies?.skills || []) {
      const depMetadata = await this.fetchMetadata(depId);
      
      // Check for circular dependencies
      if (this.hasCircularDependency(depMetadata, skill.id)) {
        throw new Error(
          `Circular dependency detected: ${skill.id} <-> ${depId}`
        );
      }
      
      deps.push({
        id: depId,
        version: depMetadata.version,
        optional: false,
      });
      
      // Recursively resolve dependencies
      await this.resolveDependencies(depMetadata, deps, visited);
    }
  }
}
```

### Conflict Detection

```typescript
interface Conflict {
  type: "version" | "duplicate" | "incompatible";
  skills: string[];
  message: string;
}

class ConflictDetector {
  detectConflicts(skills: SkillMetadata[]): Conflict[] {
    const conflicts: Conflict[] = [];
    
    // Check for duplicate IDs
    const idMap = new Map<string, SkillMetadata[]>();
    for (const skill of skills) {
      if (!idMap.has(skill.id)) {
        idMap.set(skill.id, []);
      }
      idMap.get(skill.id)!.push(skill);
    }
    
    for (const [id, duplicates] of idMap) {
      if (duplicates.length > 1) {
        conflicts.push({
          type: "duplicate",
          skills: duplicates.map(s => `${s.id}@${s.version}`),
          message: `Multiple versions of ${id} detected`,
        });
      }
    }
    
    // Check for incompatible dependencies
    for (const skill of skills) {
      for (const depId of skill.dependencies?.skills || []) {
        const dep = skills.find(s => s.id === depId);
        if (dep && !this.isCompatible(skill, dep)) {
          conflicts.push({
            type: "incompatible",
            skills: [skill.id, depId],
            message: `${skill.id} requires incompatible version of ${depId}`,
          });
        }
      }
    }
    
    return conflicts;
  }
}
```

## Component 3: Skills Creator

### Responsibilities

- Generate skills from templates
- Learn from existing examples
- Provide interactive skill builder
- Generate code for common patterns

### Template-Based Generation

```typescript
interface SkillTemplate {
  id: string;
  name: string;
  category: SkillCategory;
  variables: TemplateVariable[];
  files: TemplateFile[];
}

interface TemplateVariable {
  name: string;
  type: "string" | "number" | "boolean" | "array";
  description: string;
  default?: any;
  required: boolean;
}

class SkillCreator {
  async createFromTemplate(
    templateId: string,
    variables: Record<string, any>
  ): Promise<SkillMetadata> {
    const template = await this.loadTemplate(templateId);
    
    // Validate variables
    this.validateVariables(template.variables, variables);
    
    // Generate skill files
    const files = await this.generateFiles(template, variables);
    
    // Create skill metadata
    const metadata: SkillMetadata = {
      id: variables.skillId,
      name: variables.skillName,
      version: "1.0.0",
      description: variables.description,
      category: template.category,
      tags: variables.tags || [],
      author: variables.author,
      triggers: variables.triggers || {},
      quality: {
        coverage: 0,
        rating: 0,
        usage: 0,
        successRate: 0,
      },
      status: "experimental",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    // Write files
    await this.writeSkillFiles(metadata.id, files);
    
    return metadata;
  }
}
```

### Learning from Examples

```typescript
class SkillLearner {
  async learnFromExamples(examples: SkillExample[]): Promise<SkillTemplate> {
    // Extract common patterns
    const patterns = this.extractPatterns(examples);
    
    // Identify variables
    const variables = this.identifyVariables(patterns);
    
    // Generate template structure
    const template: SkillTemplate = {
      id: this.generateTemplateId(patterns),
      name: this.generateTemplateName(patterns),
      category: this.inferCategory(patterns),
      variables,
      files: this.generateTemplateFiles(patterns, variables),
    };
    
    return template;
  }
  
  private extractPatterns(examples: SkillExample[]): Pattern[] {
    const patterns: Pattern[] = [];
    
    // Analyze metadata patterns
    const metadataPatterns = this.analyzeMetadata(examples);
    patterns.push(...metadataPatterns);
    
    // Analyze prompt patterns
    const promptPatterns = this.analyzePrompts(examples);
    patterns.push(...promptPatterns);
    
    // Analyze trigger patterns
    const triggerPatterns = this.analyzeTriggers(examples);
    patterns.push(...triggerPatterns);
    
    return patterns;
  }
}
```

### Interactive Builder

```typescript
class InteractiveSkillBuilder {
  async build(): Promise<SkillMetadata> {
    console.log("🎯 Lyra Skill Builder\n");
    
    // Step 1: Basic info
    const basicInfo = await this.promptBasicInfo();
    
    // Step 2: Category and tags
    const categorization = await this.promptCategorization();
    
    // Step 3: Triggers
    const triggers = await this.promptTriggers();
    
    // Step 4: Dependencies
    const dependencies = await this.promptDependencies();
    
    // Step 5: Generate or write prompt
    const prompt = await this.promptContent();
    
    // Step 6: Add examples
    const examples = await this.promptExamples();
    
    // Step 7: Create skill
    return this.creator.create({
      ...basicInfo,
      ...categorization,
      triggers,
      dependencies,
      prompt,
      examples,
    });
  }
  
  private async promptBasicInfo() {
    const id = await this.prompt("Skill ID (e.g., frontend-react):");
    const name = await this.prompt("Skill Name:");
    const description = await this.prompt("Description:");
    const author = await this.prompt("Author:");
    
    return { id, name, description, author };
  }
}
```

## Component 4: Auto-Evaluation System

### Responsibilities

- Measure quality metrics (correctness, performance, usability)
- Run benchmark suites
- Perform automated testing
- Profile performance

### Quality Metrics

```typescript
interface QualityMetrics {
  correctness: CorrectnessMetrics;
  performance: PerformanceMetrics;
  usability: UsabilityMetrics;
  overall: number; // 0-100
}

interface CorrectnessMetrics {
  testsPassed: number;
  testsFailed: number;
  coverage: number;
  successRate: number;
}

interface PerformanceMetrics {
  avgExecutionTime: number;
  p95ExecutionTime: number;
  memoryUsage: number;
  tokenUsage: number;
}

interface UsabilityMetrics {
  userRating: number;
  usageCount: number;
  errorRate: number;
  documentationScore: number;
}

class AutoEvaluator {
  async evaluate(skillId: string): Promise<QualityMetrics> {
    const skill = await this.loader.load(skillId);
    
    // Run correctness tests
    const correctness = await this.evaluateCorrectness(skill);
    
    // Run performance benchmarks
    const performance = await this.evaluatePerformance(skill);
    
    // Analyze usability
    const usability = await this.evaluateUsability(skill);
    
    // Calculate overall score
    const overall = this.calculateOverallScore(
      correctness,
      performance,
      usability
    );
    
    return { correctness, performance, usability, overall };
  }
  
  private calculateOverallScore(
    correctness: CorrectnessMetrics,
    performance: PerformanceMetrics,
    usability: UsabilityMetrics
  ): number {
    // Weighted average
    const weights = {
      correctness: 0.5,
      performance: 0.3,
      usability: 0.2,
    };
    
    const correctnessScore = correctness.successRate * 100;
    const performanceScore = this.normalizePerformance(performance);
    const usabilityScore = usability.userRating * 20;
    
    return (
      correctnessScore * weights.correctness +
      performanceScore * weights.performance +
      usabilityScore * weights.usability
    );
  }
}
```

### Benchmark Suite

```typescript
interface Benchmark {
  id: string;
  name: string;
  description: string;
  input: any;
  expectedOutput: any;
  timeout: number;
}

class BenchmarkRunner {
  async runBenchmarks(skillId: string): Promise<BenchmarkResult[]> {
    const skill = await this.loader.load(skillId);
    const benchmarks = await this.loadBenchmarks(skillId);
    
    const results: BenchmarkResult[] = [];
    
    for (const benchmark of benchmarks) {
      const result = await this.runBenchmark(skill, benchmark);
      results.push(result);
    }
    
    return results;
  }
  
  private async runBenchmark(
    skill: Skill,
    benchmark: Benchmark
  ): Promise<BenchmarkResult> {
    const startTime = Date.now();
    const startMemory = process.memoryUsage().heapUsed;
    
    try {
      const output = await Promise.race([
        skill.execute(benchmark.input),
        this.timeout(benchmark.timeout),
      ]);
      
      const endTime = Date.now();
      const endMemory = process.memoryUsage().heapUsed;
      
      const passed = this.compareOutput(output, benchmark.expectedOutput);
      
      return {
        benchmarkId: benchmark.id,
        passed,
        executionTime: endTime - startTime,
        memoryUsed: endMemory - startMemory,
        output,
      };
    } catch (error) {
      return {
        benchmarkId: benchmark.id,
        passed: false,
        error: error.message,
      };
    }
  }
}
```

### Automated Testing

```typescript
interface TestCase {
  id: string;
  description: string;
  input: any;
  expectedOutput: any;
  assertions: Assertion[];
}

class SkillTester {
  async test(skillId: string): Promise<TestResult> {
    const skill = await this.loader.load(skillId);
    const tests = await this.loadTests(skillId);
    
    let passed = 0;
    let failed = 0;
    const failures: TestFailure[] = [];
    
    for (const test of tests) {
      try {
        const output = await skill.execute(test.input);
        
        // Run assertions
        for (const assertion of test.assertions) {
          if (!this.runAssertion(assertion, output)) {
            failed++;
            failures.push({
              testId: test.id,
              assertion: assertion.description,
              expected: assertion.expected,
              actual: output,
            });
            break;
          }
        }
        
        passed++;
      } catch (error) {
        failed++;
        failures.push({
          testId: test.id,
          error: error.message,
        });
      }
    }
    
    return {
      total: tests.length,
      passed,
      failed,
      coverage: this.calculateCoverage(skill, tests),
      failures,
    };
  }
}
```

## Component 5: Self-Evolution System

### Responsibilities

- Analyze usage patterns
- Generate skill improvement suggestions
- Automatically optimize skills
- Prune unused skills

### Usage Pattern Analysis

```typescript
interface UsagePattern {
  skillId: string;
  totalInvocations: number;
  successfulInvocations: number;
  failedInvocations: number;
  avgExecutionTime: number;
  commonContexts: string[];
  commonTriggers: string[];
  userFeedback: Feedback[];
}

class UsageAnalyzer {
  async analyze(skillId: string, timeRange: TimeRange): Promise<UsagePattern> {
    const logs = await this.loadLogs(skillId, timeRange);
    
    return {
      skillId,
      totalInvocations: logs.length,
      successfulInvocations: logs.filter(l => l.success).length,
      failedInvocations: logs.filter(l => !l.success).length,
      avgExecutionTime: this.calculateAvgTime(logs),
      commonContexts: this.extractCommonContexts(logs),
      commonTriggers: this.extractCommonTriggers(logs),
      userFeedback: await this.loadFeedback(skillId, timeRange),
    };
  }
  
  async identifyImprovementOpportunities(
    pattern: UsagePattern
  ): Promise<Improvement[]> {
    const improvements: Improvement[] = [];
    
    // Low success rate
    if (pattern.successfulInvocations / pattern.totalInvocations < 0.8) {
      improvements.push({
        type: "correctness",
        priority: "high",
        description: "Success rate below 80%",
        suggestion: "Review failed invocations and improve error handling",
      });
    }
    
    // Slow execution
    if (pattern.avgExecutionTime > 5000) {
      improvements.push({
        type: "performance",
        priority: "medium",
        description: "Average execution time > 5s",
        suggestion: "Optimize prompt or add caching",
      });
    }
    
    // Low usage
    if (pattern.totalInvocations < 10) {
      improvements.push({
        type: "usability",
        priority: "low",
        description: "Low usage count",
        suggestion: "Improve triggers or documentation",
      });
    }
    
    return improvements;
  }
}
```

### Automatic Optimization

```typescript
class SkillOptimizer {
  async optimize(skillId: string): Promise<OptimizationResult> {
    const skill = await this.loader.load(skillId);
    const pattern = await this.analyzer.analyze(skillId, { days: 30 });
    
    const optimizations: Optimization[] = [];
    
    // Optimize triggers based on usage
    const triggerOpt = await this.optimizeTriggers(skill, pattern);
    if (triggerOpt) optimizations.push(triggerOpt);
    
    // Optimize prompt based on failures
    const promptOpt = await this.optimizePrompt(skill, pattern);
    if (promptOpt) optimizations.push(promptOpt);
    
    // Optimize examples based on common contexts
    const exampleOpt = await this.optimizeExamples(skill, pattern);
    if (exampleOpt) optimizations.push(exampleOpt);
    
    // Apply optimizations
    for (const opt of optimizations) {
      await this.applyOptimization(skillId, opt);
    }
    
    return {
      skillId,
      optimizations,
      estimatedImprovement: this.estimateImprovement(optimizations),
    };
  }
  
  private async optimizeTriggers(
    skill: Skill,
    pattern: UsagePattern
  ): Promise<Optimization | null> {
    // Add common triggers that aren't already present
    const newTriggers = pattern.commonTriggers.filter(
      t => !skill.metadata.triggers.keywords?.includes(t)
    );
    
    if (newTriggers.length === 0) return null;
    
    return {
      type: "triggers",
      description: `Add ${newTriggers.length} common triggers`,
      changes: {
        triggers: {
          keywords: [
            ...(skill.metadata.triggers.keywords || []),
            ...newTriggers,
          ],
        },
      },
    };
  }
}
```

### Skill Pruning

```typescript
class SkillPruner {
  async identifyUnusedSkills(threshold: number = 30): Promise<string[]> {
    const allSkills = await this.registry.list();
    const unused: string[] = [];
    
    for (const skill of allSkills) {
      const pattern = await this.analyzer.analyze(skill.id, { days: 90 });
      
      // Mark as unused if:
      // 1. No invocations in last 90 days
      // 2. Success rate < 20%
      // 3. No dependencies
      if (
        pattern.totalInvocations === 0 ||
        (pattern.successfulInvocations / pattern.totalInvocations < 0.2 &&
          pattern.totalInvocations < threshold)
      ) {
        const dependents = await this.manager.findDependents(skill.id);
        if (dependents.length === 0) {
          unused.push(skill.id);
        }
      }
    }
    
    return unused;
  }
  
  async prune(skillIds: string[], dryRun: boolean = true): Promise<PruneResult> {
    const results: PruneResult = {
      removed: [],
      kept: [],
      errors: [],
    };
    
    for (const skillId of skillIds) {
      try {
        if (!dryRun) {
          await this.manager.remove(skillId);
        }
        results.removed.push(skillId);
      } catch (error) {
        results.errors.push({ skillId, error: error.message });
      }
    }
    
    return results;
  }
}
```

## Integration with Lyra Components

### CLI Integration

```typescript
// lyra skills list
async function listSkills(options: ListOptions) {
  const curator = new SkillsCurator();
  const skills = await curator.discover();
  
  if (options.category) {
    skills = skills.filter(s => s.category === options.category);
  }
  
  console.table(skills.map(s => ({
    ID: s.id,
    Name: s.name,
    Category: s.category,
    Version: s.version,
    Status: s.status,
    Rating: s.quality.rating || "N/A",
  })));
}

// lyra skills install <skill-id>
async function installSkill(skillId: string, options: InstallOptions) {
  const manager = new SkillManager();
  await manager.install(skillId, options.version);
  console.log(`✓ Installed ${skillId}`);
}

// lyra skills create
async function createSkill() {
  const builder = new InteractiveSkillBuilder();
  const skill = await builder.build();
  console.log(`✓ Created skill: ${skill.id}`);
}

// lyra skills eval <skill-id>
async function evaluateSkill(skillId: string) {
  const evaluator = new AutoEvaluator();
  const metrics = await evaluator.evaluate(skillId);
  console.log(`Quality Score: ${metrics.overall}/100`);
  console.log(`Correctness: ${metrics.correctness.successRate * 100}%`);
  console.log(`Performance: ${metrics.performance.avgExecutionTime}ms`);
}

// lyra skills optimize <skill-id>
async function optimizeSkill(skillId: string) {
  const optimizer = new SkillOptimizer();
  const result = await optimizer.optimize(skillId);
  console.log(`Applied ${result.optimizations.length} optimizations`);
  console.log(`Estimated improvement: ${result.estimatedImprovement}%`);
}
```

### Runtime Integration

```typescript
class LyraRuntime {
  private curator: SkillsCurator;
  private loader: SkillLoader;
  
  async initialize() {
    // Discover and load skills at startup
    const skills = await this.curator.discover();
    
    // Load high-priority skills eagerly
    const eagerSkills = skills.filter(s => 
      s.metadata.triggers.contexts?.includes("startup")
    );
    
    for (const skill of eagerSkills) {
      await this.loader.load(skill.id, LoadingStrategy.EAGER);
    }
  }
  
  async executeWithSkills(context: ExecutionContext) {
    // Score and select relevant skills
    const scores = await this.curator.scoreRelevance(context);
    const relevant = scores.filter(s => s.score > 50);
    
    // Load relevant skills
    for (const score of relevant) {
      await this.loader.load(score.skill.id, LoadingStrategy.LAZY);
    }
    
    // Execute with skills in context
    return this.execute(context, relevant.map(s => s.skill));
  }
}
```

## File Structure

```
.lyra/
├── skills/                    # Local skills
│   ├── frontend-react/
│   ├── backend-node/
│   └── ...
├── skills-cache/              # Cached remote skills
├── skills-registry.json       # Installed skills registry
└── skills-config.json         # Skills system configuration

~/.lyra/
├── skills/                    # Global skills
├── templates/                 # Skill templates
└── marketplace/               # Marketplace cache

Project structure:
skill-name/
├── skill.json                 # Metadata
├── README.md                  # Documentation
├── prompt.md                  # Main prompt
├── examples/                  # Usage examples
├── tests/                     # Test cases
├── benchmarks/                # Benchmarks
└── hooks/                     # Lifecycle hooks
```

## Configuration

```json
{
  "skills": {
    "sources": [
      {
        "type": "local",
        "path": "./.lyra/skills",
        "priority": 100,
        "enabled": true
      },
      {
        "type": "global",
        "path": "~/.lyra/skills",
        "priority": 80,
        "enabled": true
      },
      {
        "type": "remote",
        "url": "https://skills.lyra.dev",
        "priority": 50,
        "enabled": true
      }
    ],
    "loading": {
      "strategy": "lazy",
      "cacheEnabled": true,
      "cacheTTL": 3600
    },
    "disclosure": {
      "maxSkillsShown": 10,
      "minRelevanceScore": 30,
      "groupByCategory": true,
      "showReasons": true
    },
    "autoEval": {
      "enabled": true,
      "schedule": "daily",
      "minQualityScore": 60
    },
    "selfEvolution": {
      "enabled": true,
      "autoOptimize": true,
      "autoPrune": false,
      "pruneThreshold": 30
    }
  }
}
```

## API Reference

See implementation examples above for detailed API usage.

## Next Steps

1. Implement core components (Curator, Manager, Creator)
2. Build CLI commands for skill management
3. Create initial skill templates
4. Develop auto-evaluation framework
5. Implement self-evolution system
6. Build skills marketplace
7. Create comprehensive skill catalog (see SKILLS-CATALOG.md)

