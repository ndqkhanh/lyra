# Brainstorm: Skills System (§4.4) — Self-Evolving Skills Ecosystem

**Workstream**: §4.4 Skills System + Concrete Skills  
**Date**: 2026-05-31  
**Status**: Breakthrough ideas generated

---

## Sources Gathered

### Skills Frameworks
1. **SkillNet** — ZJU-NLP "npm for AI skills": search/install/create/evaluate/organize, auto-generates from repos/PDFs/logs, skill graph
2. **Claude Code Skills** — Agent Skills open standard, SKILL.md format, progressive disclosure
3. **Darwin Gödel Machine** — Self-rewriting coding agent, SWE-bench 20%→50%
4. **Self-Challenging LM Agents** — Generates own Code-as-Task problems for self-training
5. **claude-skills** — 330+ skills across engineering/research/PM/product/finance

### Self-Evolution & Learning
6. **SEAL** — Self-edits produce persistent weight updates via RL
7. **ADAS** — Meta agent search for agentic systems
8. **ReflecTool** — Reflection-aware tool-augmented agent, long-term memory of successful processes
9. **EvoTest** — Gradient-free evolutionary test-time learning
10. **Contextual Experience Replay** — Training-free self-improvement, synthesizes past experience

### Evaluation & Quality
11. **SkillNet evaluation** — 5 quality dimensions scoring
12. **Feedback Descent** — Pairwise textual-rationale feedback for artifact optimization
13. **MemGrad** — Textual gradients turn feedback into memory + prompt updates

---

## Novel Breakthrough Ideas (≥3 Required)

### Idea 1: **Self-Evolving Skills with Quality Gates**

**Sources Combined**:
- Darwin self-rewriting (20%→50% improvement)
- Self-Challenging LM Agents (generates own training problems)
- SkillNet evaluation (5 quality dimensions)
- Lyra's verification (§4.16 multi-stage verification)

**Mechanism**:
Skills **evolve themselves** through a gated process:

**Evolution loop**:
1. **Skill execution**: Skill runs on real tasks
2. **Outcome tracking**: Success/failure logged with context
3. **Pattern detection**: Identify failure patterns
4. **Self-modification**: Skill proposes improvements to itself
5. **Quality gates**: Improvements must pass 5 quality checks
6. **A/B testing**: New version tested against old version
7. **Adoption**: If new version wins, replace old version

**Quality gates** (SkillNet 5 dimensions):
1. **Correctness**: Does it solve the problem? (pass rate >90%)
2. **Efficiency**: Is it faster/cheaper? (latency <2× old, cost <1.5× old)
3. **Robustness**: Does it handle edge cases? (error rate <5%)
4. **Clarity**: Is the code/prompt readable? (complexity score <threshold)
5. **Safety**: Does it preserve safety invariants? (§4.17 safety checks)

**Example evolution**:
```
Skill: "Debug authentication bug"
Current version: Uses opus model, 10s latency, $0.50 cost

After 100 executions:
- Success rate: 85% (below 90% threshold)
- Common failure: Doesn't check JWT expiry

Self-modification proposal:
- Add JWT expiry check
- Switch to sonnet model (cheaper)

Quality gates:
1. Correctness: 95% pass rate ✓
2. Efficiency: 5s latency, $0.15 cost ✓
3. Robustness: 2% error rate ✓
4. Clarity: Complexity score 7/10 ✓
5. Safety: All invariants preserved ✓

A/B testing (20 tasks):
- Old version: 17/20 success (85%)
- New version: 19/20 success (95%)

→ New version wins → Adopt
```

**Self-challenging** (generates own training problems):
- Skill creates synthetic test cases
- Tests itself on synthetic cases
- Evolves to handle synthetic cases
- Generalizes to real cases

**Why It Beats Individual Sources**:
- Darwin alone: Self-rewriting but no quality gates
- SkillNet alone: Evaluation but no self-evolution
- **Fusion**: Gated self-evolution, A/B testing, quality-assured improvements

**Expected Impact**: 2-3× skill quality improvement over time, 50% cost reduction

**Rough Effort**: VERY HIGH (14-16 weeks) — evolution loop + quality gates + A/B testing

**Failure Modes**:
- Quality gates too strict → blocks valid improvements
- A/B testing insufficient → adopts worse version
- Self-modification too aggressive → breaks skill
- Evolution instability → skill thrashes between versions

---

### Idea 2: **Skills Graph with Composition & Dependencies**

**Sources Combined**:
- SkillNet skill graph (similarity/composition/dependency)
- Claude Code Skills progressive disclosure
- Lyra's model router (§4.5 complexity-based routing)
- ReflecTool tool-wise experience accumulation

**Mechanism**:
Organize skills into a **graph** with relationships:

**Graph structure**:
```
Nodes: Individual skills
Edges: Relationships between skills
  - Similarity: Skills that solve similar problems
  - Composition: Skill A uses Skill B
  - Dependency: Skill A requires Skill B
  - Conflict: Skills that shouldn't run together
```

**Skill selection via graph traversal**:
1. **Query arrives**: "Debug authentication bug"
2. **Similarity search**: Find skills similar to query
3. **Composition expansion**: If skill A needs skill B, load both
4. **Dependency resolution**: Load dependencies in order
5. **Conflict detection**: Don't load conflicting skills

**Example graph**:
```
"Debug auth bug" (query)
  ↓ similarity
"Debug JWT expiry" (skill)
  ↓ composition
"Parse JWT token" (skill)
  ↓ dependency
"Base64 decode" (skill)

→ Load all 3 skills in order
```

**Progressive disclosure** (Claude Code):
- Load only skill metadata initially (name + description)
- Load full SKILL.md body when selected
- Load referenced files only when needed
- Reduces context usage by 80-90%

**Complexity-based routing**:
- Simple skills → haiku
- Complex skills → sonnet/opus
- Skill metadata includes complexity score

**Why It Beats Individual Sources**:
- SkillNet alone: Graph but no progressive disclosure
- Claude Code alone: Progressive disclosure but no graph
- **Fusion**: Graph-based selection + progressive disclosure + complexity routing

**Expected Impact**: 80-90% context reduction, 100% dependency resolution

**Rough Effort**: VERY HIGH (12-14 weeks) — graph construction + traversal + progressive disclosure

**Failure Modes**:
- Graph construction inaccurate → wrong relationships
- Similarity search misses relevant skills
- Composition expansion too aggressive → loads too many skills
- Dependency resolution circular → infinite loop

---

### Idea 3: **Skills Marketplace with Automatic Curation**

**Sources Combined**:
- SkillNet auto-generation from repos/PDFs/logs
- claude-skills 330+ library
- Feedback Descent pairwise feedback optimization
- MemGrad textual gradients for prompt updates

**Mechanism**:
Automatically **curate skills** from multiple sources:

**Curation pipeline**:
1. **Discovery**: Scan GitHub repos, awesome lists, user logs
2. **Extraction**: Auto-generate SKILL.md from source
3. **Quality scoring**: Rate on 5 dimensions (SkillNet)
4. **Deduplication**: Merge similar skills
5. **Optimization**: Improve via feedback descent
6. **Publishing**: Add to marketplace

**Auto-generation** (SkillNet):
- From GitHub repo: Extract README + code → SKILL.md
- From PDF: Extract methodology → SKILL.md
- From conversation log: Extract successful pattern → SKILL.md
- From execution trajectory: Extract tool sequence → SKILL.md

**Quality scoring**:
```
Skill: "Deploy to AWS"
Sources: 5 GitHub repos, 2 PDFs, 10 user logs

Quality scores:
- Correctness: 0.85 (85% success rate in logs)
- Efficiency: 0.90 (fast deployment)
- Robustness: 0.70 (some edge case failures)
- Clarity: 0.95 (well-documented)
- Safety: 0.80 (some security concerns)

Overall: 0.84 → HIGH quality → Publish
```

**Feedback descent optimization**:
- Collect pairwise feedback: "Skill A better than Skill B because..."
- Generate textual rationales
- Update skill prompts based on rationales
- Iteratively improve

**Why It Beats Individual Sources**:
- SkillNet alone: Auto-generation but no marketplace
- claude-skills alone: Library but no auto-curation
- **Fusion**: Automatic curation + quality scoring + continuous optimization

**Expected Impact**: 10× skill library growth, 90%+ quality threshold

**Rough Effort**: VERY HIGH (14-16 weeks) — curation pipeline + auto-generation + optimization

**Failure Modes**:
- Auto-generation produces invalid skills
- Quality scoring inaccurate → publishes bad skills
- Deduplication too aggressive → loses unique skills
- Optimization overfits to feedback

---

### Idea 4: **Provider-Agnostic Skills with Fallback Strategies**

**Sources Combined**:
- Claude Code Skills open standard (works across providers)
- Lyra's provider abstraction (§4.5 multi-provider)
- Contextual Experience Replay (training-free self-improvement)
- Lyra's model router (§4.5)

**Mechanism**:
Skills work across **all providers** with smart fallbacks:

**Provider compatibility matrix**:
```
Skill: "Code review with tool use"
Requirements: Tool calling, JSON mode

Provider compatibility:
- Claude: ✓ (native support)
- DeepSeek: ✓ (native support)
- Qwen: ✓ (native support)
- GPT: ✓ (native support)
- Local (Llama): ✗ (no tool calling) → Fallback needed
```

**Fallback strategies**:
1. **Capability detection**: Check what provider supports
2. **Skill adaptation**: Modify skill for provider limitations
3. **Graceful degradation**: Reduce functionality if needed
4. **Provider routing**: Route to capable provider if available

**Example fallback**:
```
Skill: "Code review with tool use"
Provider: Local Llama (no tool calling)

Fallback strategy:
- Original: Use tool_use for file reading
- Fallback: Use prompt-based file reading (paste content in prompt)
- Degradation: Slower, less structured, but works

Result: Skill runs on local model with reduced functionality
```

**Deterministic skill matching** (§4.4 requirement):
- Don't rely on model auto-trigger (unreliable on small models)
- Use keyword/embedding/rule-based matching
- Fallback to deterministic selection if auto-trigger fails

**Why It Beats Individual Sources**:
- Claude Code alone: Open standard but no fallback strategies
- Provider abstraction alone: Handles calls but doesn't adapt skills
- **Fusion**: True multi-provider skills, automatic adaptation, graceful degradation

**Expected Impact**: 100% provider compatibility, 80% functionality preservation

**Rough Effort**: HIGH (10-12 weeks) — compatibility detection + adaptation + fallback logic

**Failure Modes**:
- Capability detection inaccurate → wrong fallback
- Adaptation loses too much functionality
- Graceful degradation too aggressive → skill unusable
- Provider routing fails → no capable provider available

---

## Advanced Ideas (Run 5)

### Idea 5 (ADVANCED): **Harness-Level Self-Optimization via Meta-Harness**

**Sources Fused**: Meta-Harness outer-loop search (#121) + Darwin Gödel Machine (#261-262) + MOSS source-level rewriting (#87) + HASP executable Program Functions (#102)

**Mechanism**: Extend skill evolution from prompt-level to HARNESS-level:
1. Meta-agent observes skill execution across 100+ tasks
2. Identifies structural failures: "skill X always fails because tool Y is unavailable on provider Z"
3. Proposes harness modifications: add fallback tool, restructure skill pipeline, add provider check
4. Validates via replay of failed tasks in sandbox
5. Promotes via user-consent-gated deployment

**Why It Beats Individual Sources**: Darwin self-rewrites code but with no provider awareness. Meta-Harness searches the harness space but not triggered by skill failures. MOSS rewrites source but for entire agents, not skills. This fuses all three: skill-failure-triggered, provider-aware, harness-level optimization.

**Expected Impact**: +7-15 points on cross-provider skill success rate (Meta-Harness showed +7.7 baseline)
**Rough Effort**: VERY HIGH (12-14 weeks) — harness-level search + sandbox validation + safety gates

### Idea 6 (ADVANCED): **Skills as Trainable Parameters with Population Validation**

**Sources Fused**: SkillOpt text-space optimization (#117) + FORGE population broadcast (#103) + CODESKILL RL-based policy (#95) + BenchTrace reflection evaluation (#96)

**Mechanism**: Treat each skill variant as a "parameter" in a population:
1. Generate N skill variants (different prompts, tool sequences, model preferences)
2. Run each variant on the same benchmark tasks
3. Rank by success rate + cost + latency (SkillOpt-style multi-objective)
4. Broadcast top performers' "genes" (prompt fragments, tool choices) to bottom performers (FORGE-style)
5. Mutate with bounded edits (SkillOpt add/delete/replace)
6. Validate against BenchTrace reflection evaluation (does the improved skill actually understand WHY it improved?)

**Why It Beats Individual Sources**: SkillOpt trains sequentially; FORGE broadcasts in parallel. CODESKILL uses hand-crafted RL rewards; this uses population fitness. BenchTrace adds the critical reflection check: "did the skill get better, or just lucky?"

**Expected Impact**: 52/52 best-or-tied (SkillOpt baseline) with convergence in 40% fewer iterations (FORGE acceleration)
**Rough Effort**: HIGH (8-10 weeks) — population management + gene broadcasting + reflection validation

---

## Parked Ideas (Not Yet Advanced)

1. **Skills analytics**: Track usage, success rate, cost per skill
2. **Skills versioning**: Semantic versioning for skills, rollback support
3. **Skills testing**: Automated test suite for each skill
4. **Skills documentation**: Auto-generate docs from SKILL.md
5. **Skills collaboration**: Multiple users contribute to shared skills

---

## Promoted to Plan (B) Breakthrough Tier

**Selected**: Idea 1 (Self-Evolving Skills) + Idea 2 (Skills Graph)

**Rationale**:
- Idea 1: Highest quality improvement (2-3×), gated self-evolution, A/B testing
- Idea 2: Highest context reduction (80-90%), graph-based selection, progressive disclosure
- Idea 3: Good but overlaps with existing curation patterns
- Idea 4: Critical for multi-provider but overlaps with §4.5 router

---

## ═══ ALGORITHMIC FUSION DEEPENING — Run 10 ═══

### Algorithm 1: Darwin+SkillOpt Fusion — Self-Evolving Skills with Bounded Evolution

```typescript
// ============================================================
// Self-Evolving Skills — Darwin Gödel Machine × SkillOpt × Quality Gates
// ============================================================

interface SkillVariant {
  id: string;
  skillId: string;
  content: string;           // Full SKILL.md body
  tokenCount: number;
  parentId: string | null;
  generation: number;
  metrics: EvolutionMetrics;
  createdAt: number;
}

interface EvolutionMetrics {
  successRate: number;
  avgTokens: number;
  avgLatencyMs: number;
  errorCount: number;
  executionCount: number;
}

interface ExecutionRecord {
  taskType: string;
  success: boolean;
  tokens: number;
  latencyMs: number;
  errors: string[];
  timestamp: number;
}

interface SkillArchive {
  variants: SkillVariant[];  // Max 50, evict worst
  executionLog: ExecutionRecord[];
  slidingWindow: ExecutionRecord[];  // Last 100
}

// ── Monitor: Track execution outcomes over a sliding window ──

class EvolutionMonitor {
  private window: ExecutionRecord[] = [];
  private readonly WINDOW_SIZE = 100;
  private readonly FAILURE_THRESHOLD = 0.1;
  private readonly MIN_EXECUTIONS = 20;

  record(execution: ExecutionRecord): void {
    this.window.push(execution);
    if (this.window.length > this.WINDOW_SIZE) {
      this.window.shift();
    }
  }

  shouldEvolve(): boolean {
    if (this.window.length < this.MIN_EXECUTIONS) return false;
    const failures = this.window.filter((e) => !e.success).length;
    const failureRate = failures / this.window.length;
    return failureRate > this.FAILURE_THRESHOLD;
  }

  getFailurePatterns(): string[] {
    // Cluster errors by type to identify which patterns dominate
    const errorCounts = new Map<string, number>();
    for (const record of this.window) {
      if (!record.success) {
        for (const err of record.errors) {
          errorCounts.set(err, (errorCounts.get(err) ?? 0) + 1);
        }
      }
    }
    return [...errorCounts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([err]) => err);
  }
}

// ── Generate: Create N=5 variants via bounded edits ──

type EditOperation =
  | { type: 'add_sentence'; after: string; text: string }
  | { type: 'delete_sentence'; contains: string }
  | { type: 'reorder'; section: string; newPosition: number }
  | { type: 'rephrase'; original: string; replacement: string }
  | { type: 'adjust_weight'; trigger: string; newWeight: number };

class VariantGenerator {
  private readonly MAX_TOKEN_CHANGE = 50;
  private readonly NUM_VARIANTS = 5;
  private readonly GENERATION_MODEL = 'deepseek-chat-flash';
  private readonly TOKEN_COST_PER_MTok = 0.27;

  async generateVariants(parent: SkillVariant, patterns: string[]): Promise<SkillVariant[]> {
    const variants: SkillVariant[] = [];

    for (let i = 0; i < this.NUM_VARIANTS; i++) {
      // Each variant gets exactly ONE edit operation (bounded)
      const operation = await this.sampleBoundedEdit(parent, patterns);
      const newContent = this.applyEdit(parent.content, operation);
      const tokenDelta = this.tokenDiff(parent.content, newContent);

      if (Math.abs(tokenDelta) > this.MAX_TOKEN_CHANGE) {
        // Clamp: if edit exceeds bound, try a smaller operation
        const clampedOp = this.clampEdit(operation, this.MAX_TOKEN_CHANGE);
        continue; // skip this variant, try next sampling
      }

      variants.push({
        id: crypto.randomUUID(),
        skillId: parent.skillId,
        content: newContent,
        tokenCount: this.countTokens(newContent),
        parentId: parent.id,
        generation: parent.generation + 1,
        metrics: { successRate: 0, avgTokens: 0, avgLatencyMs: 0, errorCount: 0, executionCount: 0 },
        createdAt: Date.now(),
      });
    }

    return variants;
  }

  private async sampleBoundedEdit(
    skill: SkillVariant,
    failurePatterns: string[],
  ): Promise<EditOperation> {
    // LLM proposes a single-edit operation based on failure patterns
    const prompt = `Skill: "${skill.content.substring(0, 200)}..."
    Failure patterns: ${failurePatterns.join(', ')}
    Propose ONE bounded edit operation (JSON) that addresses the most frequent failure pattern.
    Format: { "type": "add_sentence|delete_sentence|reorder|rephrase|adjust_weight", ... }
    Max 50 token change.`;

    const response = await this.callCheapLLM(prompt);
    return JSON.parse(response) as EditOperation;
  }

  private applyEdit(content: string, op: EditOperation): string {
    switch (op.type) {
      case 'add_sentence':
        return content.replace(op.after, `${op.after}\n${op.text}`);
      case 'delete_sentence':
        return content.replace(new RegExp(`.*${op.contains}.*\n?`), '');
      case 'reorder':
        return this.reorderSection(content, op.section, op.newPosition);
      case 'rephrase':
        return content.replace(op.original, op.replacement);
      case 'adjust_weight':
        return content.replace(
          new RegExp(`trigger: ${op.trigger}.*`),
          (match) => match.replace(/weight: \d+/, `weight: ${op.newWeight}`),
        );
    }
  }

  private tokenDiff(a: string, b: string): number {
    return this.countTokens(b) - this.countTokens(a);
  }

  private countTokens(text: string): number {
    return Math.ceil(text.length / 4); // approximate
  }

  private clampEdit(op: EditOperation, maxTokens: number): EditOperation {
    // Reduce the scope of an edit to stay within token budget
    if (op.type === 'add_sentence') {
      return { ...op, text: op.text.substring(0, maxTokens * 4) };
    }
    return op;
  }

  private reorderSection(content: string, section: string, newPos: number): string {
    const lines = content.split('\n');
    const sectionIdx = lines.findIndex((l) => l.includes(section));
    if (sectionIdx === -1) return content;
    const [moved] = lines.splice(sectionIdx, 1);
    lines.splice(Math.min(newPos, lines.length), 0, moved);
    return lines.join('\n');
  }

  private async callCheapLLM(prompt: string): Promise<string> {
    // Placeholder: call DeepSeek Flash ($0.27/MTok)
    // Cost per call: ~500 tokens → $0.000135
    return '{"type":"add_sentence","after":"## Steps","text":"Always validate JWT expiry before proceeding"}';
  }
}

// ── Validate: Test each variant on held-out tasks ──

class VariantValidator {
  private readonly HELD_OUT_TASKS = 20;

  async validate(
    variant: SkillVariant,
    parent: SkillVariant,
    allRecords: ExecutionRecord[],
  ): Promise<ValidationResult> {
    // Select tasks that both the parent and the held-out set have seen
    const parentPassingTasks = allRecords
      .filter((r) => r.success === true)
      .slice(0, this.HELD_OUT_TASKS * 0.7);

    const heldOutGeneric = this.generateSyntheticTasks(this.HELD_OUT_TASKS * 0.3);

    const testTasks = [...parentPassingTasks, ...heldOutGeneric];
    let regressions = 0;
    let improvements = 0;
    let newFailures = 0;

    for (const task of testTasks) {
      const parentResult = task.success; // known from history
      const variantResult = await this.executeOnTask(variant, task);

      if (parentResult === true && variantResult === false) {
        regressions++; // Previously passing task now fails → REJECT
      }
      if (parentResult === false && variantResult === true) {
        improvements++; // Previously failing task now passes
      }
      if (variantResult === false) {
        newFailures++;
      }
    }

    return {
      variantId: variant.id,
      regressions,
      improvements,
      newFailures,
      netScore: improvements - 2 * regressions,
      passedSafety: false, // filled by safetyGate
    };
  }

  private generateSyntheticTasks(count: number): ExecutionRecord[] {
    return Array.from({ length: count }, (_, i) => ({
      taskType: `synthetic-${i}`,
      success: true, // unknown until tested
      tokens: 0,
      latencyMs: 0,
      errors: [],
      timestamp: Date.now(),
    }));
  }

  private async executeOnSkill(
    skill: SkillVariant,
    task: ExecutionRecord,
  ): Promise<boolean> {
    // Sandboxed execution of the skill variant on the task
    // Returns true if skill completes task successfully
    return Math.random() > 0.2; // placeholder
  }
}

interface ValidationResult {
  variantId: string;
  regressions: number;
  improvements: number;
  newFailures: number;
  netScore: number;
  passedSafety: boolean;
}

// ── Select: Best variant wins ──

class VariantSelector {
  select(variants: ValidationResult[]): ValidationResult | null {
    const candidates = variants.filter((v) => v.regressions === 0);
    if (candidates.length === 0) return null; // No safe candidate
    return candidates.reduce((best, curr) =>
      curr.netScore > best.netScore ? curr : best,
    );
  }
}

// ── Safety Gate: Proteus red-team + Progent SMT + behavioral safety ──

class SafetyGate {
  private readonly RED_TEAM_ROUNDS = 5;

  async gate(variant: SkillVariant): Promise<SafetyVerdict> {
    // 1. Proteus red-team: adversarial probing of the skill
    const redTeamResult = await this.proteusRedTeam(variant, this.RED_TEAM_ROUNDS);
    if (redTeamResult.violations > 0) {
      return { passed: false, reason: `Proteus found ${redTeamResult.violations} violations` };
    }

    // 2. Progent SMT policy check: verify skill respects safety constraints
    const smtResult = await this.progentSMTCheck(variant);
    if (!smtResult.compliant) {
      return { passed: false, reason: `SMT violation: ${smtResult.violation}` };
    }

    // 3. Behavioral safety benchmark: run on standard safety eval set
    const benchmarkResult = await this.behavioralBenchmark(variant);
    if (benchmarkResult.safetyScore < 0.95) {
      return { passed: false, reason: `Safety score ${benchmarkResult.safetyScore} < 0.95` };
    }

    return { passed: true };
  }

  private async proteusRedTeam(
    skill: SkillVariant,
    rounds: number,
  ): Promise<{ violations: number }> {
    // Run the skill against adversarial inputs designed to trigger unsafe behavior
    return { violations: 0 }; // placeholder
  }

  private async progentSMTCheck(
    skill: SkillVariant,
  ): Promise<{ compliant: boolean; violation?: string }> {
    // Encode skill safety invariants as SMT constraints and verify satisfiability
    return { compliant: true }; // placeholder
  }

  private async behavioralBenchmark(
    skill: SkillVariant,
  ): Promise<{ safetyScore: number }> {
    // Run standard safety evaluation benchmarks
    return { safetyScore: 0.98 }; // placeholder
  }
}

interface SafetyVerdict {
  passed: boolean;
  reason?: string;
}

// ── Evolution Pipeline Orchestrator ──

class SkillEvolutionPipeline {
  private monitor = new EvolutionMonitor();
  private generator = new VariantGenerator();
  private validator = new VariantValidator();
  private selector = new VariantSelector();
  private safety = new SafetyGate();
  private archive = new Map<string, SkillArchive>();

  async onExecutionComplete(skillId: string, record: ExecutionRecord): Promise<void> {
    let archive = this.archive.get(skillId);
    if (!archive) {
      archive = { variants: [], executionLog: [], slidingWindow: [] };
      this.archive.set(skillId, archive);
    }

    archive.executionLog.push(record);
    this.monitor.record(record);

    // TRIGGER: Failure rate > 10% AND min 20 executions
    if (!this.monitor.shouldEvolve()) return;

    const parent = archive.variants[archive.variants.length - 1];
    const patterns = this.monitor.getFailurePatterns();

    // GENERATE: 5 variants
    const variants = await this.generator.generateVariants(parent, patterns);
    // Token cost: ~500 tokens/variant × 5 = 2,500 tokens @ $0.27/MTok = $0.000675

    // VALIDATE: Test on 20 held-out tasks
    const results: ValidationResult[] = [];
    for (const variant of variants) {
      const result = await this.validator.validate(variant, parent, archive.executionLog);
      results.push(result);
    }

    // SELECT: Variant with max(improvements - 2*regressions), zero regressions
    const selected = this.selector.select(results);
    if (!selected) {
      console.warn(`[Evolution] No safe variant for skill ${skillId}, sticking with parent`);
      return;
    }

    // SAFETY GATE: Proteus + SMT + behavioral benchmark
    const selectedVariant = variants.find((v) => v.id === selected.variantId)!;
    const verdict = await this.safety.gate(selectedVariant);
    if (!verdict.passed) {
      console.warn(`[Evolution] Safety gate rejected variant for skill ${skillId}: ${verdict.reason}`);
      return;
    }

    // ADOPT: Replace parent in archive
    archive.variants.push({ ...selectedVariant, metrics: await this.estimateMetrics(selectedVariant) });

    // ARCHIVE PRUNE: Keep max 50, evict worst (lowest netScore)
    if (archive.variants.length > 50) {
      const evolved = archive.variants.slice(1); // keep current, remove oldest
      archive.variants = evolved;
    }

    console.log(`[Evolution] Skill ${skillId} evolved to gen ${selectedVariant.generation}`);
    // Expected: 2-3x improvement after 10 cycles
  }

  private async estimateMetrics(variant: SkillVariant): Promise<EvolutionMetrics> {
    return {
      successRate: 0,
      avgTokens: variant.tokenCount,
      avgLatencyMs: 0,
      errorCount: 0,
      executionCount: 0,
    };
  }
}

// ── Token Cost Summary per Evolution Cycle ──
// GENERATE: 2,500 tokens @ $0.27/MTok = $0.000675
// VALIDATE: 20 tasks × ~5,000 tokens = 100,000 tokens @ $3/MTok (Sonnet) = $0.30
// SAFETY:   5 rounds × ~2,000 tokens = 10,000 tokens @ $3/MTok = $0.03
// Total per cycle: ~$0.33 (cheap model for gen, Sonnet for validation)
// Expected: 2-3x improvement after 10 cycles per skill
```

---

### Algorithm 2: Progressive Disclosure for Harness-Level Skill Loading

```typescript
// ============================================================
// Progressive Disclosure — 3-Level Harness Skill Loading
// ============================================================

interface SkillMetadata {
  name: string;
  description: string;
  triggers: string[];
  tags: string[];
  complexity: number;      // 0-1
  requiredCapabilities: string[];
  providerCompatibility: string[];
}

interface SkillDescriptor {
  metadata: SkillMetadata;
  body?: string;           // Full SKILL.md content (Level 2+)
  references?: string[];   // Referenced file paths (Level 3)
}

type LoadingLevel = 'metadata' | 'full-body' | 'references';

class ProgressiveSkillLoader {
  // LEVEL 1: Metadata — loaded at session start for ALL skills
  private metadataIndex: Map<string, SkillMetadata> = new Map();
  // LEVEL 2: Full body — loaded lazily on trigger match
  private bodyCache: Map<string, string> = new Map();
  // LEVEL 3: References — loaded on task context demand
  private referenceCache: Map<string, string> = new Map();

  private readonly METADATA_COST_PER_SKILL = 50;    // tokens
  private readonly BODY_COST_PER_SKILL = 500;        // tokens (typical min)
  private readonly BODY_COST_MAX = 2000;             // tokens (typical max)
  private readonly TOTAL_SKILLS = 50;

  // ── Deterministic keyword matching (works on any model, including DeepSeek) ──

  private keywordIndex: Map<string, string[]> = new Map();
  // Map from keyword → skill names, e.g., "debug" → ["debug-auth", "debug-performance"]

  private embeddingIndex: Map<string, Float32Array> = new Map();
  // Embeddings for fallback similarity search

  buildIndexes(): void {
    for (const [name, meta] of this.metadataIndex) {
      // Keyword index: extract keywords from triggers, tags, and description
      const keywords = this.extractKeywords(meta);
      for (const kw of keywords) {
        const existing = this.keywordIndex.get(kw) ?? [];
        existing.push(name);
        this.keywordIndex.set(kw, existing);
      }
    }
  }

  private extractKeywords(meta: SkillMetadata): string[] {
    const tokens = [
      ...meta.triggers.map((t) => t.toLowerCase()),
      ...meta.tags.map((t) => t.toLowerCase()),
      ...meta.description.toLowerCase().split(/\s+/).filter((w) => w.length > 3),
    ];
    return [...new Set(tokens)];
  }

  // ── Determine Level 1 cost (always paid) ──

  getLevel1TokenCost(): number {
    return this.metadataIndex.size * this.METADATA_COST_PER_SKILL;
    // 50 skills × 50 tokens = 2,500 tokens
  }

  // ── Select skills for Level 2 load ──

  async selectSkillsForLevel2(
    query: string,
    userTriggers?: string[],
  ): Promise<string[]> {
    // Stage 1: Deterministic keyword match (always runs, zero LLM cost)
    const keywordMatches = new Set<string>();
    const queryKeywords = this.extractKeywords({
      triggers: userTriggers ?? [],
      tags: [],
      description: query,
      name: '',
      complexity: 0,
      requiredCapabilities: [],
      providerCompatibility: [],
    });

    for (const kw of queryKeywords) {
      const matches = this.keywordIndex.get(kw) ?? [];
      for (const m of matches) keywordMatches.add(m);
    }

    if (keywordMatches.size > 0) {
      return [...keywordMatches];
    }

    // Stage 2: Embedding similarity fallback (only when keyword match misses)
    const queryEmbedding = await this.computeEmbedding(query);
    const scored = [...this.embeddingIndex.entries()]
      .map(([name, emb]) => ({
        name,
        similarity: this.cosineSimilarity(queryEmbedding, emb),
      }))
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, 5)  // Top 5 by similarity
      .map((s) => s.name);

    if (scored.length > 0) return scored;

    // Stage 3: LLM auto-trigger (last resort, requires capable model)
    // Only used when deterministic + embedding both fail and model supports it
    return [];
  }

  // ── Load Level 2: Full SKILL.md body ──

  async loadLevel2(skillName: string): Promise<string | null> {
    if (this.bodyCache.has(skillName)) {
      return this.bodyCache.get(skillName)!; // already loaded
    }

    const body = await this.readSkillFile(`skills/${skillName}/SKILL.md`);
    this.bodyCache.set(skillName, body);

    return body;
  }

  // ── Load Level 3: Referenced files (on demand) ──

  async loadLevel3(skillName: string, referencePath: string): Promise<string | null> {
    const cacheKey = `${skillName}:${referencePath}`;
    if (this.referenceCache.has(cacheKey)) {
      return this.referenceCache.get(cacheKey)!;
    }

    const content = await this.readSkillFile(`skills/${skillName}/${referencePath}`);
    this.referenceCache.set(cacheKey, content);

    return content;
  }

  // ── Smart eviction when context budget is tight ──

  async evictToFitTokenBudget(targetBudget: number): Promise<void> {
    let currentTokens = this.getCurrentTotalTokens();

    // Evict Level 3 first (referenced files, least likely to be needed again)
    while (currentTokens > targetBudget && this.referenceCache.size > 0) {
      const oldestKey = this.referenceCache.keys().next().value!;
      const content = this.referenceCache.get(oldestKey)!;
      currentTokens -= this.countTokens(content);
      this.referenceCache.delete(oldestKey);
    }

    // Evict Level 2 if still over budget (keep body for currently active skills)
    while (currentTokens > targetBudget && this.bodyCache.size > 0) {
      const oldestKey = this.bodyCache.keys().next().value!;
      const content = this.bodyCache.get(oldestKey)!;
      currentTokens -= this.countTokens(content);
      this.bodyCache.delete(oldestKey);
    }
  }

  private getCurrentTotalTokens(): number {
    let total = this.getLevel1TokenCost();
    for (const body of this.bodyCache.values()) total += this.countTokens(body);
    for (const ref of this.referenceCache.values()) total += this.countTokens(ref);
    return total;
  }

  private countTokens(text: string): number {
    return Math.ceil(text.length / 4);
  }

  private async readSkillFile(path: string): Promise<string> {
    // Read from filesystem — placeholder
    return `# ${path}\nInstructions...`;
  }

  private async computeEmbedding(text: string): Promise<Float32Array> {
    // Compute embedding — placeholder using local embedding model
    return new Float32Array(384);
  }

  private cosineSimilarity(a: Float32Array, b: Float32Array): number {
    let dot = 0, normA = 0, normB = 0;
    for (let i = 0; i < a.length; i++) {
      dot += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }
    return dot / (Math.sqrt(normA) * Math.sqrt(normB));
  }
}

// ── Token Savings Calculation ──
// Eager loading:    50 skills × 1,250 tokens (avg body) = 62,500 tokens
// Level 1 only:     50 × 50 = 2,500 tokens
// Level 1+2 (10):   2,500 + 10 × 1,250 = 15,000 tokens
// Level 1+2+3 (few): 2,500 + 10 × 1,250 + 3 × 500 = 16,500 tokens
// Savings vs eager: (62,500 - 16,500) / 62,500 = 73.6% token reduction
// Worst case (all 50 triggered): same as eager — no loss
```

---

### Algorithm 3: FORGE Population Broadcast for Lyra Skills Evolution

```typescript
// ============================================================
// FORGE-Style Population Broadcast — Cross-Instance Skill Evolution
// ============================================================

interface LyraInstance {
  id: string;
  skills: Map<string, string>;   // skillId → skill content
  taskHistory: TaskOutcome[];
  successRate: number;
  avgTokenCost: number;
  fitness: number;                // successRate - lambda * tokenCost
}

interface TaskOutcome {
  skillId: string;
  taskType: string;
  success: boolean;
  tokens: number;
  trace: string[];                // execution trace steps
}

interface BroadcastRule {
  condition: string;              // e.g., "When debugging JWT expiry"
  preferredAction: string;        // e.g., "validate decoding before checking claims"
  alternative: string;            // e.g., "checking claims first"
  reason: string;                 // e.g., "decoding return false leaks time"
  sourceInstance: string;
  broadcastRound: number;
}

const LAMBDA = 0.001;             // Weight for token cost in fitness function
const BROADCAST_INTERVAL = 100;   // Every K=100 task executions
const POPULATION_SIZE = 5;

class ForgePopulationBroadcast {
  private instances: LyraInstance[] = [];
  private broadcastRules: BroadcastRule[] = [];
  private round: number = 0;
  private convergenceCount: number = 0;
  private readonly CONVERGENCE_THRESHOLD = 3;

  // ── Initialize N instances with different skill configurations ──

  constructor() {
    for (let i = 0; i < POPULATION_SIZE; i++) {
      this.instances.push(this.createDiverseInstance(i));
    }
  }

  private createDiverseInstance(index: number): LyraInstance {
    // Each instance starts with a different initial skill mix
    const baseSkills = this.getBaseSkills();
    const variations = [
      { provider: 'claude', temperature: 0.3, skillBias: 'conservative' },
      { provider: 'claude', temperature: 0.7, skillBias: 'exploratory' },
      { provider: 'deepseek', temperature: 0.3, skillBias: 'efficient' },
      { provider: 'deepseek', temperature: 0.7, skillBias: 'creative' },
      { provider: 'mixture', temperature: 0.5, skillBias: 'balanced' },
    ];

    const config = variations[index % variations.length];
    return {
      id: `lyra-${index}`,
      skills: this.applyVariation(baseSkills, config),
      taskHistory: [],
      successRate: 0,
      avgTokenCost: 0,
      fitness: 0,
    };
  }

  // ── Every K=100 task executions per instance ──

  async maybeBroadcast(instanceId: string): Promise<void> {
    const instance = this.instances.find((i) => i.id === instanceId);
    if (!instance) return;
    if (instance.taskHistory.length % BROADCAST_INTERVAL !== 0) return;

    // a) Rank instances by fitness
    this.updateFitnessScores();
    const ranked = [...this.instances].sort((a, b) => b.fitness - a.fitness);
    const topPerformer = ranked[0];

    // b) Extract rules from top performer's successful traces
    const newRules = await this.extractRules(topPerformer);
    this.broadcastRules.push(...newRules);
    this.round++;

    // c) Broadcast rules to all instances
    for (const instance of this.instances) {
      if (instance.id === topPerformer.id) continue; // skip source
      await this.mergeRules(instance, newRules);
    }

    // d) Check convergence
    this.checkConvergence(newRules);
  }

  // ── Fitness: successRate - lambda * avgTokenCost ──

  private updateFitnessScores(): void {
    for (const instance of this.instances) {
      const total = instance.taskHistory.length;
      if (total === 0) {
        instance.fitness = 0;
        continue;
      }
      const successes = instance.taskHistory.filter((t) => t.success).length;
      instance.successRate = successes / total;
      instance.avgTokenCost =
        instance.taskHistory.reduce((sum, t) => sum + t.tokens, 0) / total;
      instance.fitness = instance.successRate - LAMBDA * instance.avgTokenCost;
    }
  }

  // ── LLM distills RULES from top performer's successful execution traces ──

  private async extractRules(instance: LyraInstance): Promise<BroadcastRule[]> {
    const successfulTraces = instance.taskHistory
      .filter((t) => t.success)
      .slice(-BROADCAST_INTERVAL); // Last 100 successful tasks

    // Group by skillId to find per-skill patterns
    const perSkill = new Map<string, TaskOutcome[]>();
    for (const trace of successfulTraces) {
      const group = perSkill.get(trace.skillId) ?? [];
      group.push(trace);
      perSkill.set(trace.skillId, group);
    }

    const rules: BroadcastRule[] = [];
    for (const [skillId, traces] of perSkill) {
      if (traces.length < 3) continue; // not enough data

      // LLM prompt to distill a rule from the traces
      const prompt = `You are analyzing ${traces.length} successful executions of skill "${skillId}".
    Extract a single actionable rule in this format:
    "When [condition], prefer [action] over [alternative] because [reason]"
    
    Trace summaries:
    ${traces.slice(0, 5).map((t) => `- Task: ${t.taskType}, Steps: ${t.trace.slice(0, 3).join(' -> ')}`).join('\n')}
    
    Rule:`;

      const ruleText = await this.callLLM(prompt);
      const parsed = this.parseRule(ruleText, instance.id);
      if (parsed) rules.push(parsed);
    }

    return rules;
    // Token cost per broadcast: ~2,000 tokens for extraction
  }

  private parseRule(text: string, sourceInstance: string): BroadcastRule | null {
    const match = text.match(
      /When\s+(.+?),\s*prefer\s+(.+?)\s+over\s+(.+?)\s+because\s+(.+)/i,
    );
    if (!match) return null;

    return {
      condition: match[1].trim(),
      preferredAction: match[2].trim(),
      alternative: match[3].trim(),
      reason: match[4].trim(),
      sourceInstance,
      broadcastRound: this.round,
    };
  }

  // ── Each instance MERGES broadcast rules via A-MAC admission control ──

  private async mergeRules(
    instance: LyraInstance,
    rules: BroadcastRule[],
  ): Promise<void> {
    for (const rule of rules) {
      // A-MAC Step 1: Novelty check — skip if already in local pool
      const alreadyKnown = this.broadcastRules.some(
        (r) =>
          r.condition === rule.condition &&
          r.preferredAction === rule.preferredAction,
      );
      if (alreadyKnown) continue;

      // A-MAC Step 2: Utility check — LLM assesses applicability
      const applicability = await this.assessUtility(instance, rule);
      if (applicability < 0.5) {
        console.log(`[FORGE] Instance ${instance.id} rejected rule: ${rule.condition} (utility: ${applicability})`);
        continue;
      }

      // Apply the rule to the instance's skill content
      const affectedSkills = this.findAffectedSkills(instance, rule.condition);
      for (const skillId of affectedSkills) {
        const currentContent = instance.skills.get(skillId) ?? '';
        instance.skills.set(skillId, this.injectRule(currentContent, rule));
        console.log(`[FORGE] Instance ${instance.id} adopted rule: "${rule.condition}" into skill ${skillId}`);
      }
    }
    // Token cost per merge: ~500 tokens/rule × 5 rules = 2,500 tokens
  }

  private async assessUtility(instance: LyraInstance, rule: BroadcastRule): Promise<number> {
    // Prompt LLM to assess how useful this rule is given the instance's task distribution
    const taskDistribution = [...new Set(instance.taskHistory.map((t) => t.taskType))].slice(0, 10);
    const prompt = `Instance task types: ${taskDistribution.join(', ')}
    Rule: When ${rule.condition}, prefer ${rule.preferredAction} over ${rule.alternative}
    Applicability (0-1): `;

    const response = await this.callLLM(prompt);
    return parseFloat(response);
  }

  // ── Inject the rule as a sentence in the skill body ──

  private injectRule(skillContent: string, rule: BroadcastRule): string {
    const ruleSentence = `- When ${rule.condition}, prefer ${rule.preferredAction} over ${rule.alternative} (broadcast rule from ${rule.sourceInstance})`;
    return skillContent.replace('## Instructions', `## Instructions\n${ruleSentence}`);
  }

  private findAffectedSkills(instance: LyraInstance, condition: string): string[] {
    const keywords = condition.toLowerCase().split(/\s+/);
    const affected: string[] = [];
    for (const [skillId] of instance.skills) {
      const matchCount = keywords.filter((kw) => skillId.toLowerCase().includes(kw)).length;
      if (matchCount > 0) affected.push(skillId);
    }
    return affected.length > 0 ? affected : [...instance.skills.keys()].slice(0, 1);
  }

  // ── Convergence: 3 consecutive broadcasts with no improvement ──

  private checkConvergence(newRules: BroadcastRule[]): void {
    if (newRules.length === 0) {
      this.convergenceCount++;
    } else {
      this.convergenceCount = 0;
    }

    if (this.convergenceCount >= this.CONVERGENCE_THRESHOLD) {
      console.log(`[FORGE] Population converged after ${this.round} broadcast rounds`);
      console.log(`[FORGE] Best fitness: ${Math.max(...this.instances.map((i) => i.fitness)).toFixed(4)}`);
      console.log(`[FORGE] Total rules distilled: ${this.broadcastRules.length}`);
      // Expected: 40% token reduction + 1.7-7.7x improvement
    }
  }

  private getBaseSkills(): Map<string, string> {
    return new Map([
      ['debug-auth', '## Debug Authentication\n...'],
      ['code-review', '## Code Review\n...'],
      ['deploy-aws', '## Deploy to AWS\n...'],
      ['optimize-performance', '## Optimize Performance\n...'],
    ]);
  }

  private applyVariation(
    base: Map<string, string>,
    config: typeof this.createDiverseInstance extends (i: number) => infer R
      ? R['skills'] extends Map<string, string> ? any : never
      : never,
  ): Map<string, string> {
    // Perturb base skills based on config
    return new Map(base); // placeholder
  }

  private async callLLM(prompt: string): Promise<string> {
    return 'When JWT decoding returns false, prefer checking token expiry first over reading claims because it is faster and avoids unnecessary claims parsing';
  }
}

// ── Expected Performance Summary ──
// Token cost per broadcast: 2,000 (extraction) + 5 × 500 (merge) = 4,500 tokens
// Cost: 4,500 tokens @ $0.27/MTok (DeepSeek Flash) = $0.0012 or @ $3/MTok (Sonnet) = $0.0135
// Convergence: typically 10-20 broadcast rounds = 10-20 × $0.0135 = $0.14-0.27 total
// Token reduction: 40% (rules compress lessons vs raw examples)
// Quality improvement: 1.7-7.7x over homogeneous population (FORGE baseline)
```

---

**END OF BRAINSTORM**
